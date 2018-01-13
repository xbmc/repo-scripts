# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import urllib
import urllib2
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import shutil
import re
from zipfile import ZipFile
from cStringIO import StringIO
import uuid

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')) \
    .decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')) \
    .decode("utf-8")
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp')) \
    .decode("utf-8")

sys.path.append(__resource__)

from ti_utilities import OSDBServer, log, normalizeString, languageTranslate

from lat2cyr import Lat2Cyr


REGEX_EXPRESSIONS = [ '[Ss]([0-9]+)[][._-]*[Ee]([0-9]+)([^\\\\/]*)$',
                      '[\._ \-]([0-9]+)x([0-9]+)([^\\/]*)',                     # foo.1x09
                      '[\._ \-]([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',          # foo.109
                      '([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',
                      '[\\\\/\\._ -]([0-9]+)([0-9][0-9])[^\\/]*',
                      'Season ([0-9]+) - Episode ([0-9]+)[^\\/]*',              # Season 01 - Episode 02
                      'Season ([0-9]+) Episode ([0-9]+)[^\\/]*',                # Season 01 Episode 02
                      '[\\\\/\\._ -][0]*([0-9]+)x[0]*([0-9]+)[^\\/]*',
                      '[[Ss]([0-9]+)\]_\[[Ee]([0-9]+)([^\\/]*)',                #foo_[s01]_[e01]
                      '[\._ \-][Ss]([0-9]+)[\.\-]?[Ee]([0-9]+)([^\\/]*)',       #foo, s01e01, foo.s01.e01, foo.s01-e01
                      's([0-9]+)ep([0-9]+)[^\\/]*',                             #foo - s01ep03, foo - s1ep03
                      '[Ss]([0-9]+)[][ ._-]*[Ee]([0-9]+)([^\\\\/]*)$',
                      '[\\\\/\\._ \\[\\(-]([0-9]+)x([0-9]+)([^\\\\/]*)$'
                     ]

def openURLAdress(url, postData=None):
    try:
        useragent = {'User-Agent': "Mozilla/5.0"}
        req = urllib2.Request(url, headers=useragent)
        if postData:
            data = urllib.urlencode(postData)
            website = urllib2.urlopen(req, data)
        else:
            website = urllib2.urlopen(req)
    except urllib2.URLError, e:
        if hasattr(e, 'reason'):
            print 'We failed to reach a server.'
            print 'Reason: ', e.reason
            return False
        elif hasattr(e, 'code'):
            print 'The server couldn\'t fulfill the request.'
            print 'Error code: ', e.code
            return False
    except socket.timeout as e:
        # catched
        print type(e)
        return False
    else:
        # read html code
        html = website.read()
        website.close()
        return html


def Search(item):
    osdb_server = OSDBServer()
    subtitles_list = []

    if not subtitles_list:
        # log(__name__, "Search for [%s] by name" %
        #     (os.path.basename(item['file_original_path']),))
        log(__name__, "Search for [%s] by name" % item['title'])
        log(__name__, 'TVshow: %s' % item['tvshow'])
        log(__name__, 'Season: %s' % item['season'])
        log(__name__, 'Episode: %s' % item['episode'])
        subtitles_list = osdb_server.search_subtitles(item['title'],
                                                      item['tvshow'],
                                                      item['season'],
                                                      item['episode'],
                                                      item['3let_language'],
                                                      item['year'])

    if subtitles_list:
        for it in subtitles_list:
            listitem = xbmcgui.ListItem(label=it["language_name"],
                                        label2=it["filename"],
                                        iconImage=it["rating"],
                                        thumbnailImage=it["language_flag"]
                                        )

            listitem.setProperty("sync", ("false", "true")[it["sync"]])
            listitem.setProperty("hearing_imp", ("false", "true")
                                 [it.get("hearing_imp", False)])

            url = "plugin://%s/?action=download&ID=%s&filename=%s&language_name=%s" % (__scriptid__,
                                            it["ID"],
                                            it["filename"],
                                            it["language_name"]
                                            )

            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),
                                        url=url,
                                        listitem=listitem,
                                        isFolder=False)


def old_extractor(temp_archive, subtitle_list = []):
    exts = [".srt", ".sub", ".txt", ".smi", ".ssa", ".ass"]
    zip_exts = [".zip", ".rar"]
    for subfile in xbmcvfs.listdir(temp_archive)[1]:
            file = os.path.join(__temp__, subfile.decode('utf-8'))
            log(__name__, 'archive names: %s' % file)
            if (os.path.splitext(file)[1] in exts):
                subtitle_list.append(file)
            elif (os.path.splitext(file)[1] in zip_exts):
                log(__name__, 'Found archive file %s' % file)
                xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (file, __temp__,))
                    .encode('utf-8'), True)
                old_extractor(file, subtitle_list)
    return subtitle_list

def Download(url, filename, language_name=None):
    if xbmcvfs.exists(__temp__):
        shutil.rmtree(__temp__)
    xbmcvfs.mkdirs(__temp__)
    subtitle_list = []

    try:
        log(__name__, "Download using 'ZipFile' method")
        # response = urllib2.urlopen(url)
        # raw = response.read()
        raw = openURLAdress(url)
        archive = ZipFile(StringIO(raw), 'r')
        log(__name__, "archive: %s" % archive)
        files = archive.namelist()
        files.sort()
        index = 1

        log(__name__, "files: %s" % files)

        for file in files:
            contents = archive.read(file)
            extension = file[file.rfind('.') + 1:]

            if len(files) == 1:
                dest = os.path.join(__temp__, "%s.%s" %
                                    (str(uuid.uuid4()), extension))
            else:
                dest = os.path.join(__temp__, "%s.%d.%s" %
                                    (str(uuid.uuid4()), index, extension))

            log(__name__, 'dest: %s' % dest)
            f = open(dest, 'wb')
            f.write(contents)
            f.close()

            if language_name == 'Serbian' and __addon__.getSetting("autocyrillic") == "true":
                lat2cyr = Lat2Cyr()
                subCyr = lat2cyr.convert2cyrillic(dest)
                log(__name__, 'Cyrillic sub: %s' % subCyr)
                subtitle_list.append(subCyr)
            elif language_name == 'Croatian' and __addon__.getSetting("autocyrillicCroation") == "true":
                lat2cyr = Lat2Cyr()
                subCyr = lat2cyr.convert2cyrillic(dest)
                log(__name__, 'Croatian cyrillic sub: %s' % subCyr)
                subtitle_list.append(subCyr)
            subtitle_list.append(dest)

            index += 1
    except:
        log(__name__, "Download using 'old' method")
        # exts = [".srt", ".sub", ".txt", ".smi", ".ssa", ".ass"]
        response = urllib2.urlopen(url)
        temp_filename = response.info()['Content-Disposition']
        pos = temp_filename.find('filename=')
        temp_filename = temp_filename[pos+9:]
        content = response.read()
        response.close()
        # zip = os.path.join(__temp__, "titlovi.zip")
        temp_file = os.path.join(__temp__, temp_filename)
        log(__name__, "Downloaded as: %s" % temp_file)

        with open(temp_file, "wb") as subFile:
            subFile.write(content)
        subFile.close()
        xbmc.sleep(500)
        xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (temp_file, __temp__,))
            .encode('utf-8'), True)

        subtitle_list = old_extractor(temp_file)
        log(__name__, 'Number of subs: %s' % len(subtitle_list))

        # for subfile in xbmcvfs.listdir(temp_file)[1]:
        #     file = os.path.join(__temp__, subfile.decode('utf-8'))
        #     log(__name__, 'archive names: %s' % file)
        #     if (os.path.splitext(file)[1] in exts):
        #         subtitle_list.append(file)

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
        if (params[len(params)-1] == '/'):
            params = params[0:len(params)-2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]

    return param

params = get_params()

if params['action'] == 'search':
    log(__name__, "action 'search' called")
    item = {}
    item['temp'] = False
    item['rar'] = False
    item['mansearch'] = False
    item['year'] = xbmc.getInfoLabel("VideoPlayer.Year")  # Year
    item['season'] = str(xbmc.getInfoLabel("VideoPlayer.Season"))  # Season
    item['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))  # Episode

    if 'searchstring' in params:
        item['mansearch'] = True
        item['mansearchstr'] = params['searchstring']

    # Show
    item['tvshow'] = normalizeString(
        xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))
    # try to get original title
    item['title'] = normalizeString(
        xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))

    # Full path of a playing file
    item['file_original_path'] = urllib.unquote(
        xbmc.Player().getPlayingFile().decode('utf-8'))

    if item['title'] == "":
        log(__name__, "VideoPlayer.OriginalTitle not found")
         # no original title, get just Title
        item['title'] = normalizeString(
            xbmc.getInfoLabel("VideoPlayer.Title"))

    # if (item['title'].find('[B]')):
    item['title'] = item['title'].replace('[B]', '')
    item['title'] = item['title'].replace('[/B]', '')
    item['title'] = item['title'].replace('  ', ' ')

    find_year = re.findall('\((\d{4})\)', item['title'])
    if find_year:
        # if found year remove year from title
        item['title'] = item['title'].replace(' (' + find_year[0] + ')', '')
        if not item['year']:
            item['year'] = find_year[0]
    else:
        if not item['year']:
            item['year'] = ''

    # Check if season is "Special"
    if item['episode'].lower().find("s") > -1:
        item['season'] = "0"
        item['episode'] = item['episode'][-1:]

    if (item['file_original_path'].find("http") > -1):
        item['temp'] = True

    elif (item['file_original_path'].find("rar://") > -1):
        item['rar'] = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif (item['file_original_path'].find("stack://") > -1):
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    #['scc','eng']
    item['3let_language'] = []

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        item['3let_language'].append(languageTranslate(lang, 0, 2))

    Search(item)

elif params['action'] == 'download':

    osdb_server = OSDBServer()
    url_base = "https://titlovi.com/download/?type=1&mediaid=%s"
    url = url_base % params["ID"]
    log(__name__, 'link: %s' % url)
    # Serbian
    language_name = params["language_name"]

    if language_name == 'Serbian':
        subs = Download(url, params["filename"], language_name)
    elif language_name == 'Croatian':
        subs = Download(url, params["filename"], language_name)
    else:
        subs = Download(url, params["filename"])

    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),
                                    url=sub,
                                    listitem=listitem,
                                    isFolder=False)


elif params['action'] == 'manualsearch':
    log(__name__, "action 'manualsearch' called")
    item = {}
    item['tvshow'] = []
    item['season'] = 0
    item['episode'] = 0
    item['temp'] = False
    item['rar'] = False
    item['mansearch'] = False

    if 'searchstring' in params:
        item['mansearch'] = True
        item['title'] = normalizeString(params['searchstring'])

    # item['title'] = item['title'].replace('%20', ' ')
    item['title'] = unquoted = urllib.unquote(item['title'])

    # Search for year in this format (2010)
    find_year = re.findall('\((\d{4})\)', item['title'])
    if find_year:
        # if found year remove year from title
        item['title'] = item['title'].replace(' (' + find_year[0] + ')', '')
        item['year'] = find_year[0]
    else:
        item['year'] = ''

    log(__name__, 'Title: %s' % item['title'])

    i = 1
    for regex in REGEX_EXPRESSIONS:
        find_season = re.findall(regex, item['title'])
        if len(find_season) > 0 :
            log( __name__ , "Regex File Se: %s, Ep: %s," % (str(find_season[0][0]),str(find_season[0][1]),) )
            season = find_season[0][0]
            episode = find_season[0][1]
            item['season'] = int(season)
            item['episode'] = int(episode)
            if i == 2:
                item['tvshow'] = item['title'].replace('%sx%s' % (int(season), episode), '')
                break
            elif i == 3 or i == 4 or i == 5:
                item['tvshow'] = item['title'].replace('%s%s' % (int(season), episode), '')
                break
            elif i == 10:
                item['tvshow'] = item['title'].replace('S%sE%s' % (season, episode), '')
                break
            elif i == 11:
                item['tvshow'] = item['title'].replace('s%sep%s' % (season, episode), '')
                break
            else:
                item['tvshow'] = item['title']
        i += 1

    item['3let_language'] = []  # ['scc','eng']

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        item['3let_language'].append(languageTranslate(lang, 0, 2))

    Search(item)
    # xbmc.executebuiltin(u'Notification(%s,%s,2000,%s)' %
    #                     (__scriptname__,
    #                     __language__(32004),
    #                     os.path.join(__cwd__, "icon.png")
    #                      ))

xbmcplugin.endOfDirectory(int(sys.argv[1]))
