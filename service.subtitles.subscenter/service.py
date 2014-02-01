# -*- coding: utf-8 -*-

import os
import re
import sys
import urllib
import urllib2
import json
import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import shutil
import unicodedata

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')).decode("utf-8")
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp')).decode("utf-8")

sys.path.append(__resource__)

BASE_URL = "http://www.subscenter.org"
releases_types = ['2011', '2009', '2012', '2010', '2013', '2014', 'web-dl', 'webrip', '480p', '720p', '1080p', 'h264',
                  'x264', 'xvid', 'ac3', 'aac', 'hdtv', 'dvdscr', 'dvdrip', 'ac3', 'brrip', 'bluray', 'dd51', 'divx',
                  'proper', 'repack', 'pdtv', 'rerip', 'dts']
#===============================================================================
# Regular expression patterns
#===============================================================================
MULTI_RESULTS_PAGE_PATTERN = u"עמוד (?P<curr_page>\d*) \( סך הכל: (?P<total_pages>\d*) \)"
MOVIES_SEARCH_RESULTS_PATTERN = '<div class="generalWindowRight">.*?<a href="[^"]+(/he/subtitle/movie/.*?)">.*?<div class="generalWindowBottom">'
TV_SEARCH_RESULTS_PATTERN = '<div class="generalWindowRight">.*?<a href="[^"]+(/he/subtitle/series/.*?)">.*?<div class="generalWindowBottom">'

#===============================================================================
# Private utility functions
#===============================================================================
def normalizeString(str):
    return unicodedata.normalize(
        'NFKD', unicode(unicode(str, 'utf-8'))
    ).encode('ascii', 'ignore')


def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg,)).encode('utf-8'), level=xbmc.LOGDEBUG)

# Returns the content of the given URL. Used for both html and subtitle files.
# Based on Titlovi's service.py
def getURL(url):
    # Fix URLs with spaces in them
    url = url.replace(" ", "%20")
    content = None
    log(__scriptname__, "Getting url: %s" % (url))
    try:
        req = urllib2.Request(url)
        req.add_header('User-Agent',
                       'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:26.0) Gecko/20100101 Firefox/26.0')
        response = urllib2.urlopen(req)
        content = None if response.code != 200 else response.read()
        response.close()
    except Exception as e:
        log(__scriptname__, "Failed to get url: %s\n%s" % (url, e))
        # Second parameter is the filename
    return content


def get_url_filename(url):
    # Fix URLs with spaces in them
    url = url.replace(" ", "%20")
    filename = None
    log(__scriptname__, "Getting url: %s" % (url))
    try:
        seperator = "filename="
        response = urllib.urlopen(url)
        filename = response.headers['Content-Disposition']
        filename = filename[filename.index(seperator) + len(seperator):]
    except Exception as e:
        log(__scriptname__, "Failed to get url: %s\n%s" % (url, e))
        # Second parameter is the filename
    return filename


def get_rating(subsfile, videofile):
    x = 0
    rating = 0
    log(__scriptname__, "# Comparing Releases:\n %s [subtitle-rls] \n %s [filename-rls]" % (subsfile, videofile))
    videofile = "".join(videofile.split('.')[:-1]).lower()
    subsfile = subsfile.lower().replace('.', '')
    videofile = videofile.replace('.', '')
    for release_type in releases_types:
        if release_type in videofile:
            x += 1
            if (release_type in subsfile): rating += 1
    if x: rating = (rating / float(x)) * 4
    # Compare group name
    if videofile.split('-')[-1] == subsfile.split('-')[-1]:
        rating += 1
    # Group name didn't match
    # try to see if group name is in the beginning (less info on file less weight)
    elif videofile.split('-')[0] == subsfile.split('-')[-1]:
        rating += 0.5
    if rating > 0:
        rating *= 2
    log(__scriptname__, "# Result is: %f" % rating)
    return round(rating)

# The function receives a subtitles page id number, a list of user selected
# languages and the current subtitles list and adds all found subtitles matching
# the language selection to the subtitles list.
def prepare_subtitle_list(subtitle_page_uri, language_list, file_name):
    subtitles_list = []
    # Retrieve the subtitles page (html)
    try:
        subtitlePage = getURL(BASE_URL + subtitle_page_uri)
    except:
        # Didn't find the page - no such episode?
        return

    # Didn't find the page - no such episode?
    if not subtitlePage:
        return

    log(__scriptname__, "data=%s" % (subtitlePage))
    found_subtitles = json.loads(subtitlePage, encoding="utf-8")

    for language in found_subtitles.keys():
        if xbmc.convertLanguage(language, xbmc.ISO_639_2) in language_list:
            for translator in found_subtitles[language]:
                for quality in found_subtitles[language][translator]:
                    for rating in found_subtitles[language][translator][quality]:
                        current = found_subtitles[language][translator][quality][rating]
                        title = current["subtitle_version"]
                        subtitle_rate = get_rating(title, file_name)
                        subtitles_list.append(
                            {'lang_index': language_list.index(xbmc.convertLanguage(language, xbmc.ISO_639_2)),
                             'filename': title,
                             'link': current["key"],
                             'language_name': xbmc.convertLanguage(language, xbmc.ENGLISH_NAME),
                             'language_flag': language,
                             'ID': current["id"],
                             'rating': str(subtitle_rate),
                             'sync': subtitle_rate >= 8,
                             'hearing_imp': current["hearing_impaired"] > 0
                            })
    return subtitles_list


def search(item):
    if item['tvshow']:
        searchString = item['tvshow'].replace(" ", "+")
    else:
        searchString = item['title'].replace(" ", "+")
    log(__scriptname__, "Search string = %s" % (searchString.lower()))

    # Retrieve the search results (html)
    searchResults = getURL(BASE_URL + "/he/subtitle/search/?q=" + searchString.lower())
    # Search most likely timed out, no results
    if not searchResults:
        return

    # Look for subtitles page links
    if item['tvshow']:
        subtitleIDs = re.findall(TV_SEARCH_RESULTS_PATTERN, searchResults, re.DOTALL)
    else:
        subtitleIDs = re.findall(MOVIES_SEARCH_RESULTS_PATTERN, searchResults, re.DOTALL)
        # Look for more subtitle pages

    pages = re.search(MULTI_RESULTS_PAGE_PATTERN, unicode(searchResults, "utf-8"))
    # If we found them look inside for subtitles page links
    if (pages):
        # Limit to only 2 pages
        while (int(pages.group("curr_page")) <= 2):
            searchResults = getURL(BASE_URL + "/he/subtitle/search/?q=" + searchString.lower() + "&page=" + str(
                int(pages.group("curr_page")) + 1))

            if item['tvshow']:
                tempSIDs = re.findall(TV_SEARCH_RESULTS_PATTERN, searchResults, re.DOTALL)
            else:
                tempSIDs = re.findall(MOVIES_SEARCH_RESULTS_PATTERN, searchResults, re.DOTALL)

            for sid in tempSIDs:
                subtitleIDs.append(sid)
            pages = re.search(MULTI_RESULTS_PAGE_PATTERN, unicode(searchResults, "utf-8"))

    # Uniqify the list
    subtitleIDs = list(set(subtitleIDs))
    # If looking for tvshows try to append season and episode to url
    for i in range(len(subtitleIDs)):
        subtitleIDs[i] = subtitleIDs[i].replace("/subtitle/", "/cinemast/data/")
        if item['tvshow']:
            subtitleIDs[i] = subtitleIDs[i].replace("/series/", "/series/sb/")
            subtitleIDs[i] += item["season"] + "/" + item["episode"] + "/"
        else:
            subtitleIDs[i] = subtitleIDs[i].replace("/movie/", "/movie/sb/")

    file_name = os.path.basename(item['file_original_path']);
    subtitles_list = []
    for sid in subtitleIDs:
        subtitles_list += prepare_subtitle_list(sid, item['3let_language'], file_name)

    if subtitles_list:
        # Sort the subtitles
        subtitles_list = sorted(subtitles_list, key=lambda x: int(float(x['rating'])), reverse=True)
        for it in subtitles_list:
            listitem = xbmcgui.ListItem(label=it["language_name"],
                                        label2=it["filename"],
                                        iconImage=it["rating"],
                                        thumbnailImage=it["language_flag"]
            )
            if it["sync"]:
                listitem.setProperty("sync", "true")
            else:
                listitem.setProperty("sync", "false")

            if it.get("hearing_imp", False):
                listitem.setProperty("hearing_imp", "true")
            else:
                listitem.setProperty("hearing_imp", "false")

            url = "plugin://%s/?action=download&link=%s&ID=%s&filename=%s" % (
                __scriptid__, it["link"], it["ID"], it["filename"])
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)


def download(id, key, filename, stack=False):
    subtitle_list = []
    exts = [".srt", ".sub"]

    ## Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
    ## pass that to XBMC to copy and activate
    if xbmcvfs.exists(__temp__):
        shutil.rmtree(__temp__)
    xbmcvfs.mkdirs(__temp__)

    zip = os.path.join(__temp__, "subs.zip")
    url = BASE_URL + "/subtitle/download/he/" + str(id) + "/?v=" + filename + "&key=" + key
    log(__scriptname__, "Fetching subtitles using url %s" % url)
    f = urllib.urlopen(url)
    with open(zip, "wb") as subFile:
        subFile.write(f.read())
    subFile.close()
    xbmc.sleep(500)
    xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (zip, __temp__,)).encode('utf-8'), True)

    for file in xbmcvfs.listdir(__temp__)[1]:
        full_path = os.path.join(__temp__, file)
        if os.path.splitext(full_path)[1] in exts:
            subtitle_list.append(full_path)

    return subtitle_list


def get_params(string=""):
    param = []
    if string == "":
        paramstring = sys.argv[2]
    else:
        paramstring = string
    if len(paramstring) >= 2:
        params = paramstring
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]

    return param


params = get_params()

log(__scriptname__, "params: %s" % (params))

if params['action'] in ['search', 'manualsearch']:
    log(__scriptname__, "action '%s' called" % (params['action']))
    item = {}
    item['temp'] = False
    item['rar'] = False
    item['year'] = xbmc.getInfoLabel("VideoPlayer.Year")                           # Year
    item['season'] = str(xbmc.getInfoLabel("VideoPlayer.Season"))                    # Season
    item['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                   # Episode
    item['tvshow'] = params['searchstring'] if params['action'] == 'manualsearch' \
        else normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))   # Show
    item['title'] = params['searchstring'] if params['action'] == 'manualsearch' \
        else normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")) # try to get original title
    item['file_original_path'] = urllib.unquote(
        xbmc.Player().getPlayingFile().decode('utf-8'))  # Full path of a playing file
    item['3let_language'] = []

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        item['3let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

    if item['title'] == "":
        log(__scriptname__, "VideoPlayer.OriginalTitle not found")
        item['title'] = params['searchstring'] if params['action'] == 'manualsearch' \
            else normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title

    if item['episode'].lower().find("s") > -1:                                # Check if season is "Special"
        item['season'] = "0"
        item['episode'] = item['episode'][-1:]

    if ( item['file_original_path'].find("http") > -1 ):
        item['temp'] = True

    elif ( item['file_original_path'].find("rar://") > -1 ):
        item['rar'] = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif ( item['file_original_path'].find("stack://") > -1 ):
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    search(item)


elif params['action'] == 'download':
    ## we pickup all our arguments sent from def search()
    subs = download(params["ID"], params["link"], params["filename"])
    ## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that in XBMC core
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False)

xbmcplugin.endOfDirectory(int(sys.argv[1])) ## send end of directory to XBMC