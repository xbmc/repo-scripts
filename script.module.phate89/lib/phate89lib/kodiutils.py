#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
from urllib.parse import urlencode
import json
import xbmc
import xbmcaddon
import xbmcplugin
import xbmcgui
from . import staticutils

ADDON = xbmcaddon.Addon()
ID = ADDON.getAddonInfo('id')
NAME = ADDON.getAddonInfo('name')
VERSION = ADDON.getAddonInfo('version')
PATH = ADDON.getAddonInfo('path')
DATA_PATH = ADDON.getAddonInfo('profile')
PATH_T = xbmc.translatePath(PATH)
DATA_PATH_T = xbmc.translatePath(DATA_PATH)
IMAGE_PATH_T = os.path.join(PATH_T, 'resources', 'media', "")
LANGUAGE = ADDON.getLocalizedString
KODILANGUAGE = xbmc.getLocalizedString

HANDLE = int(sys.argv[1])


def executebuiltin(func, block=False):
    xbmc.executebuiltin(func, block)


def notify(msg):
    xbmcgui.Dialog().notification(ID, msg)


def log(msg, level=2):
    message = u'%s: %s' % (ID, msg)
    if level > 1:
        xbmc.log(msg=message, level=xbmc.LOGDEBUG)
    else:
        xbmc.log(msg=message, level=xbmc.LOGINFO)
        if level == 0:
            notify(msg)


def py2_decode(s):
    return s


def py2_encode(s):
    return s


def getSetting(setting):
    return ADDON.getSetting(setting).strip()


def getSettingAsBool(setting):
    return getSetting(setting).lower() == "true"


def getSettingAsNum(setting):
    num = 0
    try:
        num = float(getSetting(setting))
    except ValueError:
        pass
    return num


def setSetting(setting, value):
    ADDON.setSetting(id=setting, value=str(value))


def getKeyboard():
    return xbmc.Keyboard()


def getKeyboardText(heading, default='', hidden=False):
    kb = xbmc.Keyboard(default, heading)
    kb.setHiddenInput(hidden)
    kb.doModal()
    if (kb.isConfirmed()):
        return kb.getText()
    return False


def showOkDialog(heading, line):
    xbmcgui.Dialog().ok(heading, line)


def addListItem(label="", params=None, label2=None, thumb=None, fanart=None, poster=None, arts=None,
                videoInfo=None, properties=None, isFolder=True):
    if arts is None:
        arts = {}
    if properties is None:
        properties = {}
    item = xbmcgui.ListItem(label, label2)
    if thumb:
        arts['thumb'] = thumb
    if fanart:
        arts['fanart'] = fanart
    if poster:
        arts['poster'] = poster
    item.setArt(arts)
    item.setInfo('video', videoInfo)
    if not isFolder:
        properties['IsPlayable'] = 'true'
    if isinstance(params, dict):
        url = staticutils.parameters(params)
    else:
        url = params
    for key, value in list(properties.items()):
        item.setProperty(key, value)
    return xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=item, isFolder=isFolder)


def setResolvedUrl(url="", solved=True, subs=None, headers=None, ins=None, insdata=None):
    headerUrl = ""
    if headers:
        headerUrl = urlencode(headers)
    item = xbmcgui.ListItem(path=url + "|" + headerUrl)
    if subs is not None:
        item.setSubtitles(subs)
    if ins:
        item.setProperty('inputstreamaddon', ins)
        item.setProperty('inputstream', ins)
        if insdata:
            for key, value in list(insdata.items()):
                item.setProperty(ins + '.' + key, value)
    xbmcplugin.setResolvedUrl(HANDLE, solved, item)
    sys.exit()


def append_subtitle(sUrl, subtitlename, sync=False, provider=None):
    #listitem = createListItem({'label': 'Italian', 'label2': subtitlename, 'thumbnailImage': 'it'})
    if not provider:
        tUrl = {'action': 'download', 'subid': sUrl}
    else:
        tUrl = {'action': 'download', 'url': sUrl}
    log("Add subtitle '" + subtitlename + "' to the kist", 3)
    return addListItem(label="Italian", label2=subtitlename, params=tUrl, thumb="it",
                       properties={"sync": 'true' if sync else 'false', "hearing_imp": "false"},
                       isFolder=False)


def setContent(ctype='videos'):
    xbmcplugin.setContent(HANDLE, ctype)


def endScript(message=None, loglevel=2, closedir=True):
    if message:
        log(message, loglevel)
    if closedir:
        xbmcplugin.endOfDirectory(handle=HANDLE, succeeded=True)
    sys.exit()


def createAddonFolder():
    if not os.path.isdir(DATA_PATH_T):
        log("Creating the addon data folder")
        os.makedirs(DATA_PATH_T)


def getShowID():
    json_query = xbmc.executeJSONRPC((
        '{"jsonrpc":"2.0","method":"Player.GetItem","params":'
        '{"playerid":1,"properties":["tvshowid"]},"id":1}'))
    jsn_player_item = json.loads(json_query, 'utf-8', errors='ignore')
    if 'result' in jsn_player_item and jsn_player_item['result']['item']['type'] == 'episode':
        json_query = xbmc.executeJSONRPC((
            '{"jsonrpc":"2.0","id":1,"method":"VideoLibrary.GetTVShowDetails","params":'
            '{"tvshowid":%s, "properties": ["imdbnumber"]}}') % (
                jsn_player_item['result']['item']['tvshowid']))
        jsn_ep_det = json.loads(json_query, 'utf-8', errors='ignore')
        if 'result' in jsn_ep_det and jsn_ep_det['result']['tvshowdetails']['imdbnumber'] != '':
            return str(jsn_ep_det['result']['tvshowdetails']['imdbnumber'])
    return False


def containsLanguage(strlang, langs):
    for lang in strlang.split(','):
        if xbmc.convertLanguage(lang, xbmc.ISO_639_2) in langs:
            return True
    return False


def isPlayingVideo():
    return xbmc.Player().isPlayingVideo()


def getInfoLabel(lbl):
    return xbmc.getInfoLabel(lbl)


def getRegion(r):
    return xbmc.getRegion(r)


def getEpisodeInfo():
    episode = {}
    episode['tvshow'] = staticutils.normalizeString(
        xbmc.getInfoLabel('VideoPlayer.TVshowtitle'))    # Show
    episode['season'] = xbmc.getInfoLabel(
        'VideoPlayer.Season')                            # Season
    episode['episode'] = xbmc.getInfoLabel(
        'VideoPlayer.Episode')                           # Episode
    file_original_path = xbmc.Player().getPlayingFile()  # Full path

    # Check if season is "Special"
    if str(episode['episode']).lower().find('s') > -1:
        episode['season'] = 0
        episode['episode'] = int(str(episode['episode'])[-1:])

    elif file_original_path.find('rar://') > -1:
        file_original_path = os.path.dirname(file_original_path[6:])

    elif file_original_path.find('stack://') > -1:
        file_original_path = file_original_path.split(' , ')[0][8:]

    episode['filename'] = os.path.splitext(os.path.basename(file_original_path))[0]

    return episode


def getFormattedDate(dt):
    fmt = getRegion('datelong')
    fmt = fmt.replace("%A", KODILANGUAGE(dt.weekday() + 11))
    fmt = fmt.replace("%B", KODILANGUAGE(dt.month + 20))
    return dt.strftime(py2_encode(fmt))


log("Starting module '%s' version '%s' with command '%s'" % (NAME, VERSION, sys.argv[2]), 1)
