# -*- coding: utf-8 -*-

import os
import sys

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from urllib.parse import unquote

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmcvfs.translatePath(__addon__.getAddonInfo('path'))
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))
__resource__ = xbmcvfs.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
__temp__ = xbmcvfs.translatePath(os.path.join(__profile__, 'temp'))

sys.path.append(__resource__)

from SUBUtilities import SubsHelper, log, normalizeString, parse_rls_title, clean_title


def search(item):
    helper = SubsHelper()
    subtitles_list = helper.get_subtitle_list(item)
    if subtitles_list:
        for it in subtitles_list:
            listitem = xbmcgui.ListItem(label=it["language_name"], label2=it["filename"])
            listitem.setArt({'icon': str(it["rating"]), 'thumb': it["language_flag"]})

            if it["sync"]:
                listitem.setProperty("sync", "true")
            else:
                listitem.setProperty("sync", "false")

            if it.get("hearing_imp", False):
                listitem.setProperty("hearing_imp", "true")
            else:
                listitem.setProperty("hearing_imp", "false")

            url = "plugin://%s/?action=download&id=%s&sub_id=%s&filename=%s&language=%s" % (
                __scriptid__, it["id"], it["sub_id"], it["filename"], it["language_flag"])
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)


def download(id, sub_id, filename, language):
    subtitle_list = []
    exts = [".srt", ".sub"]

    filename = os.path.join(__temp__, "%s.%s.srt" % (filename, language))

    helper = SubsHelper()
    helper.download(id, sub_id, filename)

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


def title_from_focused_item(item_data):
    label_type = xbmc.getInfoLabel("ListItem.DBTYPE")  # movie/tvshow/season/episode
    label_movie_title = xbmc.getInfoLabel("ListItem.OriginalTitle")
    is_movie = xbmc.getCondVisibility("Container.Content(movies)") or label_type == 'movie'
    is_episode = xbmc.getCondVisibility("Container.Content(episodes)") or label_type == 'episode'

    title = ''
    if is_movie and label_movie_title and item_data['year']:
        title = label_movie_title + " " + item_data['year']
    elif is_episode and item_data['tvshow'] and item_data['season'] and item_data['episode']:
        title = ("%s S%.2dE%.2d" % (item_data['tvshow'], int(item_data['season']), int(item_data['episode'])))

    return title


params = get_params()


def collect_initial_data():
    item_data = {
        'temp': False,
        'rar': False,
        '3let_language': [],
        'preferredlanguage': unquote(params.get('preferredlanguage', ''))
    }

    item_data['preferredlanguage'] = xbmc.convertLanguage(item_data['preferredlanguage'], xbmc.ISO_639_2)

    if xbmc.Player().isPlaying():
        item_data['year'] = xbmc.getInfoLabel("VideoPlayer.Year")  # Year
        item_data['season'] = str(xbmc.getInfoLabel("VideoPlayer.Season"))  # Season
        item_data['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))  # Episode
        item_data['tvshow'] = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
        item_data['title'] = normalizeString(
            xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))  # try to get original title
        item_data['file_original_path'] = unquote(xbmc.Player().getPlayingFile())  # Full path of a playing file

        if item_data['title'] == "":
            log("VideoPlayer.OriginalTitle not found")
            item_data['title'] = normalizeString(
                xbmc.getInfoLabel("VideoPlayer.Title"))  # no original title, get just Title

    else:
        item_data['year'] = xbmc.getInfoLabel("ListItem.Year")
        item_data['season'] = xbmc.getInfoLabel("ListItem.Season")
        item_data['episode'] = xbmc.getInfoLabel("ListItem.Episode")
        item_data['tvshow'] = xbmc.getInfoLabel("ListItem.TVShowTitle")
        item_data['title'] = title_from_focused_item(item_data)
        item_data['file_original_path'] = ""

    return item_data


if params['action'] in ['search', 'manualsearch']:
    log("Version: '%s'" % (__version__,))
    log("Action '%s' called" % (params['action']))

    if params['action'] == 'manualsearch':
        params['searchstring'] = unquote(params['searchstring'])

    item = collect_initial_data()

    if params['action'] == 'manualsearch':
        if item['season'] != '' or item['episode']:
            item['tvshow'] = params['searchstring']
        else:
            item['title'] = params['searchstring']

    for lang in unquote(params['languages']).split(","):
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
    subs = download(params["id"], params["sub_id"], params["filename"], params["language"])
    ## we can return more than one subtitle for multi CD versions, for now we are still working out how to handle that in XBMC core
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False)

elif params['action'] == 'login':
    helper = SubsHelper()
    helper.login(True)
    __addon__.openSettings()

xbmcplugin.endOfDirectory(int(sys.argv[1]))  ## send end of directory to XBMC
