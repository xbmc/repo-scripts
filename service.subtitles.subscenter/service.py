# -*- coding: utf-8 -*-

import os
import sys
import urllib
import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import json
from requests import post


__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = unicode(xbmc.translatePath(__addon__.getAddonInfo('path')), 'utf-8')
__profile__ = unicode(xbmc.translatePath(__addon__.getAddonInfo('profile')), 'utf-8')
__resource__ = unicode(xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')), 'utf-8')
__temp__ = unicode(xbmc.translatePath(os.path.join(__profile__, 'temp')), 'utf-8')

sys.path.append(__resource__)

from SUBUtilities import SubscenterHelper, log, normalizeString, clear_store, parse_rls_title, clean_title


def search(item):
    helper = SubscenterHelper()
    subtitles_list = helper.get_subtitle_list(item)
    if subtitles_list:
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

            url = "plugin://%s/?action=download&link=%s&id=%s&filename=%s&language=%s" % (
                __scriptid__, it["link"], it["id"], it["filename"], it["language_flag"])
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)


def download(id, language, key, filename):
    subtitle_list = []
    exts = [".srt", ".sub"]

    zip_filename = os.path.join(__temp__, "subs.zip")

    helper = SubscenterHelper()
    helper.download(id, language, key, filename, zip_filename)

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

def mirror_sub(id, filename, sub_file):
    try:
        playerid_query = '{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}'
        playerid = json.loads(xbmc.executeJSONRPC(playerid_query))['result'][0]['playerid']
        imdb_id_query = '{"jsonrpc": "2.0", "method": "Player.GetItem", "params": {"playerid": ' + str(playerid) + ', "properties": ["imdbnumber"]}, "id": 1}'
        imdb_id = json.loads(xbmc.executeJSONRPC (imdb_id_query))['result']['item']['imdbnumber']
    except:
        imdb_id = 0

    values = {}
    values['id'] = id
    values['versioname'] = filename
    values['source'] = 'subscenter'
    values['year'] = xbmc.getInfoLabel("VideoPlayer.Year")
    values['season'] = str(xbmc.getInfoLabel("VideoPlayer.Season"))
    values['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))
    values['imdb'] = str(imdb_id)
    values['tvshow'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))
    values['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))
    values['file_original_path'] = urllib.unquote(unicode(xbmc.Player().getPlayingFile(), 'utf-8'))
    url = 'http://api.wizdom.xyz/upload.php'
    try:
        post(url, files={'sub': open(sub_file, 'rb')}, data=values)
    except:
        pass

def takeTitleFromFocusedItem():
    labelType = xbmc.getInfoLabel("ListItem.DBTYPE")  #movie/tvshow/season/episode
    labelMovieTitle = xbmc.getInfoLabel("ListItem.OriginalTitle")
    labelYear = xbmc.getInfoLabel("ListItem.Year")
    labelTVShowTitle = xbmc.getInfoLabel("ListItem.TVShowTitle")
    labelSeason = xbmc.getInfoLabel("ListItem.Season")
    labelEpisode = xbmc.getInfoLabel("ListItem.Episode")
    isItMovie = xbmc.getCondVisibility("Container.Content(movies)") or labelType == 'movie'
    isItEpisode = xbmc.getCondVisibility("Container.Content(episodes)") or labelType == 'episode'

    title = 'SearchFor...'
    if isItMovie and labelMovieTitle and labelYear:
        title = labelMovieTitle + " " + labelYear
    elif isItEpisode and labelTVShowTitle and labelSeason and labelEpisode:
        title = ("%s S%.2dE%.2d" % (labelTVShowTitle, int(labelSeason), int(labelEpisode)))

    return title


params = get_params()

if params['action'] in ['search', 'manualsearch']:
    log("Version: '%s'" % (__version__,))
    log("Action '%s' called" % (params['action']))

    if params['action'] == 'manualsearch':
        params['searchstring'] = urllib.unquote(params['searchstring'])

    item = {}
    
    if xbmc.Player().isPlaying():
        item['temp'] = False
        item['rar'] = False
        item['year'] = xbmc.getInfoLabel("VideoPlayer.Year")  # Year
        item['season'] = str(xbmc.getInfoLabel("VideoPlayer.Season"))  # Season
        item['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))  # Episode
        item['tvshow'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
        item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))  # try to get original title
        item['file_original_path'] = urllib.unquote(unicode(xbmc.Player().getPlayingFile(), 'utf-8'))  # Full path of a playing file
        item['3let_language'] = []
        item['preferredlanguage'] = unicode(urllib.unquote(params.get('preferredlanguage', '')), 'utf-8')
        item['preferredlanguage'] = xbmc.convertLanguage(item['preferredlanguage'], xbmc.ISO_639_2)

    else:
        item['temp'] = False
        item['rar'] = False
        item['year'] = ""
        item['season'] = ""
        item['episode'] = ""
        item['tvshow'] = ""
        item['title'] = takeTitleFromFocusedItem()
        item['file_original_path'] = ""
        item['3let_language'] = []
        item['preferredlanguage'] = unicode(urllib.unquote(params.get('preferredlanguage', '')), 'utf-8')
        item['preferredlanguage'] = xbmc.convertLanguage(item['preferredlanguage'], xbmc.ISO_639_2)


    if item['title'] == "":
        log("VideoPlayer.OriginalTitle not found")
        item['title'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))  # no original title, get just Title

    if params['action'] == 'manualsearch':
        if item['season'] != '' or item['episode']:
            item['tvshow'] = params['searchstring']
        else:
            item['title'] = params['searchstring']

    for lang in unicode(urllib.unquote(params['languages']), 'utf-8').split(","):
        item['3let_language'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

    log("Item before cleaning: \n    %s" % item)

    # clean title + tvshow params
    clean_title(item)
    parse_rls_title(item)

    if item['episode'].lower().find("s") > -1:  # Check if season is "Special"
        item['season'] = "0"
        item['episode'] = item['episode'][-1:]

    if item['file_original_path'].find("http") > -1:
        item['temp'] = True

    elif item['file_original_path'].find("rar://") > -1:
        item['rar'] = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif item['file_original_path'].find("stack://") > -1:
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]
    log("%s" % item)
    search(item)


elif params['action'] == 'download':
    ## we pickup all our arguments sent from def search()
    subs = download(params["id"], params["language"], params["link"], params["filename"])
    ## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that in XBMC core
    for sub in subs:
        if params["language"] == 'he' and xbmc.Player().isPlaying():
            mirror_sub(params["id"], params["filename"], sub)
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False)

elif params['action'] == 'clear_store':
    clear_store()

elif params['action'] == 'login':
    clear_store(False)
    helper = SubscenterHelper()
    helper.login(True)
    __addon__.openSettings()

xbmcplugin.endOfDirectory(int(sys.argv[1]))  ## send end of directory to XBMC
