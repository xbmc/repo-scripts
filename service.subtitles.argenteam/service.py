# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import urllib
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import shutil
import unicodedata
import re
import string
import difflib
import HTMLParser

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

from ArgenteamUtilities import log, geturl

main_url_search = "http://www.argenteam.net/search/"
main_url = "http://www.argenteam.net/"

# Seasons as strings for searching
seasons = ["Specials", "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"]
seasons = seasons + ["Eleventh", "Twelfth", "Thirteenth", "Fourteenth", "Fifteenth", "Sixteenth", "Seventeenth",
                     "Eighteenth", "Nineteenth", "Twentieth"]
seasons = seasons + ["Twenty-first", "Twenty-second", "Twenty-third", "Twenty-fourth", "Twenty-fifth", "Twenty-sixth",
                     "Twenty-seventh", "Twenty-eighth", "Twenty-ninth"]

'''
<div class="search-item-desc">
    <a href="/episode/29322/The.Mentalist.%282008%29.S01E01-Pilot">
    
<div class="search-item-desc">
    <a href="/movie/25808/Awake.%282007%29">
'''

search_results_pattern = "<div\sclass=\"search-item-desc\">(.+?)<a\shref=\"/(episode|movie)/(.+?)/(.+?)\">(.+?)</a>"

subtitle_pattern = "<div\sclass=\"links\">(.+?)<strong>Descargado:</strong>(.+?)ve(ces|z)(.+?)<div>(.+?)<a\shref=\"/subtitles/(.+?)/(.+?)\">(.+?)</a>"



def find_movie(content, title, year):
    url_found = None
    h = HTMLParser.HTMLParser()
    for matches in re.finditer(movie_season_pattern, content, re.IGNORECASE | re.DOTALL):
        found_title = matches.group('title')
        found_title = h.unescape(found_title)
        log(__name__, "Found movie on search page: %s (%s)" % (found_title, matches.group('year')))
        if string.find(string.lower(found_title), string.lower(title)) > -1:
            if matches.group('year') == year:
                log(__name__, "Matching movie found on search page: %s (%s)" % (found_title, matches.group('year')))
                url_found = matches.group('link')
                break
    return url_found


def find_subtitles(content):
    #url_found = None
    possible_matches = []
    #ll_tvshows = []

    h = HTMLParser.HTMLParser()
    for matches in re.finditer(subtitle_pattern, content, re.IGNORECASE | re.DOTALL | re.UNICODE):
        id = matches.group(6)
        filename=urllib.unquote_plus(matches.group(7))
        downloads = (int(matches.group(2)) / 1000) / 2
        log(__name__, "Encontrado subtitulo: %s" % filename)
        possible_matches.append({'id':id, 'filename':filename,'downloads':downloads})

    return possible_matches


def append_subtitle(items):

    items.sort(key=lambda x: x['rating'], reverse=True)
    index = 0
    for item in items:
        index += 1
        listitem = xbmcgui.ListItem(label=item['lang'],
                                label2=item['filename'],
                                iconImage=item['rating'],
                                thumbnailImage=item['image'])

        #listitem.setProperty("sync",  'true' if item["sync"] else 'false')
        #listitem.setProperty("hearing_imp", 'true' if item["hearing_imp"] else 'false')

        ## below arguments are optional, it can be used to pass any info needed in download function
        ## anything after "action=download&" will be sent to addon once user clicks listed subtitle to downlaod
        url = "plugin://%s/?action=download&actionsortorder=%s&link=%s&filename=%s&id=%s" % (__scriptid__,
                                                                    str(index).zfill(2),
                                                                    item['link'],
                                                                    item['filename'],
                                                                    item['id'])

        ## add it to list, this can be done as many times as needed for all subtitles found
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)

def search_movie(title, year, languages, filename):
    title = string.strip(title)

    log(__name__, "Search movie = %s" % title)
    search_string = "%s (%s)" % (title, year)
    search_pack(search_string)

def search_tvshow(tvshow, season, episode, title, languages, filename):
    tvshow = string.strip(tvshow)

    #Prevent that the "US" acronym interfere with the search in the site
    tvshow = tvshow.replace("(US)","")

    search_string = "%s S%#02dE%#02d %s" % (tvshow, int(season), int(episode), title)

    log(__name__, "Search tvshow = %s" % search_string)
    search_pack(search_string)

def search_pack(search_string):
    url = main_url_search + urllib.quote_plus(search_string)
    content, response_url = geturl(url)

    #Check if gives more than tv show or movie pack
    pack_urls = []
    for matches in re.finditer(search_results_pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE | re.UNICODE):
        tipo = matches.group(2)
        id = matches.group(3)
        link = matches.group(4)
    
        url_subtitle = "http://www.argenteam.net/" + tipo +"/"+ id +"/"+link
        print url_subtitle
        pack_urls.append(url_subtitle)

    subs = []
    if len(pack_urls) > 0:
        for url_pack in pack_urls:
            pack_content, response_url = geturl(url_pack)
            subs.extend(search_common(pack_content))
    else:
        subs.extend(search_common(content))

    append_subtitle(subs)

def search_common(content):
    if content is not None:
        log(__name__, "Resultados encontrados...")
        object_subtitles = find_subtitles(content)
        items = []
        if object_subtitles is not None:
            log(__name__, "Buscando subtitulos...")
            
            for sub in object_subtitles:
                item = {}
                item['lang'] = "Spanish"
                item['filename'] = sub['filename']
                item['rating'] = str(sub['downloads'])
                item['image'] = 'es'
                item['id'] = sub['id']
                item['link'] = main_url + "subtitles/" + sub['id'] + "/" + sub['filename']
                items.append(item)
        
        return items

def search_manual(searchstr, languages, filename):
    search_pack(prepare_search_string(searchstr))
    
def search_filename(filename, languages):
    title, year = xbmc.getCleanMovieTitle(filename)
    log(__name__, "clean title: \"%s\" (%s)" % (title, year))
    try:
        yearval = int(year)
    except ValueError:
        yearval = 0
    if title and yearval > 1900:
        search_movie(title, year, item['3let_language'], filename)
    else:
        match = re.search(r'\WS(?P<season>\d\d)E(?P<episode>\d\d)', title, flags=re.IGNORECASE)
        if match is not None:
            tvshow = string.strip(title[:match.start('season')-1])
            season = string.lstrip(match.group('season'), '0')
            episode = string.lstrip(match.group('episode'), '0')
            search_tvshow(tvshow, season, episode, '', item['3let_language'], filename)
        else:
            search_manual(filename, item['3let_language'], filename)


def search(item):
    filename = os.path.splitext(os.path.basename(item['file_original_path']))[0]
    log(__name__, "Search_argenteam='%s', filename='%s', addon_version=%s" % (item, filename, __version__))

    if item['mansearch']:
        search_manual(item['mansearchstr'], item['3let_language'], filename)
    elif item['tvshow']:
        search_tvshow(item['tvshow'], item['season'], item['episode'], item['title'], item['3let_language'], filename)
    elif item['title'] and item['year']:
        search_movie(item['title'], item['year'], item['3let_language'], filename)
    else:
        search_filename(filename, item['3let_language'])

def prepare_search_string(s):
    s = string.strip(s)
    #s = urllib.quote_plus(s)
    #s = re.sub(r'\s', '-', s)
    return s

def download(id, url, filename, search_string=""):
    subtitle_list = []
    exts = [".srt", ".sub", ".txt", ".smi", ".ssa", ".ass"]
    ## Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
    ## pass that to XBMC to copy and activate
    if xbmcvfs.exists(__temp__):
        shutil.rmtree(__temp__)
    xbmcvfs.mkdirs(__temp__)

    filename = os.path.join(__temp__, filename + ".zip")

    sub = urllib.urlopen(url).read()
    with open(filename, "wb") as subFile:
        subFile.write(sub)
    subFile.close()

    xbmc.sleep(500)
    xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (filename, __temp__,)).encode('utf-8'), True)

    for file in xbmcvfs.listdir(__temp__)[1]:
        file = os.path.join(__temp__, file)
        if os.path.splitext(file)[1] in exts:
            if search_string and string.find(string.lower(file), string.lower(search_string)) == -1:
                continue
            log(__name__, "=== returning subtitle file %s" % file)
            subtitle_list.append(file)

    return subtitle_list
    

def normalizeString(str):
    return unicodedata.normalize(
        'NFKD', unicode(unicode(str, 'utf-8'))
    ).encode('ascii', 'ignore')


def get_params():
    param = {}
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = paramstring
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]

    return param


params = get_params()

if params['action'] == 'search' or params['action'] == 'manualsearch':
    item = {}
    item['temp'] = False
    item['rar'] = False
    item['mansearch'] = False
    item['year'] = xbmc.getInfoLabel("VideoPlayer.Year")                             # Year
    item['season'] = str(xbmc.getInfoLabel("VideoPlayer.Season"))                    # Season
    item['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                  # Episode
    item['tvshow'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))   # Show
    item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))  # try to get original title
    item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))  # Full path
    item['3let_language'] = []

    if 'searchstring' in params:
        item['mansearch'] = True
        item['mansearchstr'] = params['searchstring']
        print params['searchstring']

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        item['3let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

    if item['title'] == "":
        item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title

    if item['episode'].lower().find("s") > -1:                                      # Check if season is "Special"
        item['season'] = "0"                                                          #
        item['episode'] = item['episode'][-1:]

    if item['file_original_path'].find("http") > -1:
        item['temp'] = True

    elif item['file_original_path'].find("rar://") > -1:
        item['rar'] = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif item['file_original_path'].find("stack://") > -1:
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    search(item)

elif params['action'] == 'download':
    ## we pickup all our arguments sent from def Search()
    if 'find' in params:
        subs = download(params["link"], params["find"])
    else:
        subs = download(params["id"],params["link"], params["filename"])
    ## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that
    ## in XBMC core
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False)

xbmcplugin.endOfDirectory(int(sys.argv[1]))  # send end of directory to XBMC
  
  
  
  
  
  
  
  
  
    
