#!/usr/bin/env python
# -*- coding: utf-8 -*-
import xbmcaddon
import xbmc
import xbmcplugin
import xbmcgui
import os
import sys
import re
import staticutils
if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

ADDON = xbmcaddon.Addon()
ID = ADDON.getAddonInfo('id')
NAME = ADDON.getAddonInfo('name')
VERSION = ADDON.getAddonInfo('version')
PATH = ADDON.getAddonInfo('path')
DATA_PATH = ADDON.getAddonInfo('profile')
PATH_T = xbmc.translatePath(PATH).decode('utf-8')
DATA_PATH_T = xbmc.translatePath(DATA_PATH).decode('utf-8')
IMAGE_PATH_T = os.path.join(PATH_T, 'resources', 'media', "")
LANGUAGE = ADDON.getLocalizedString

HANDLE=int(sys.argv[1])

def executebuiltin(func,block=False):
    if isinstance (func,str):
        func = func.decode("utf-8", 'ignore')
    xbmc.executebuiltin(func.encode('utf-8'),block)


def notify(msg):
    message = 'Notification(%s,%s)' % (ID, msg)
    xbmc.executebuiltin(message)

def log(msg, level=2):
    if isinstance(msg, str):
        msg = msg.decode("utf-8", 'ignore')
    message = u'%s: %s' % (ID, msg)
    if level > 1:
        xbmc.log(msg=message.encode("utf-8", 'ignore'), level=xbmc.LOGDEBUG)
    else:
        xbmc.log(msg=message.encode("utf-8", 'ignore'), level=xbmc.LOGNOTICE)
        if level == 0:
            notify(msg)

def getSetting(setting):
    return ADDON.getSetting(setting).strip()

def getSettingAsBool(setting):
    return getSetting(setting).lower() == "true"

def getSettingAsNum(setting):
    num=0
    try:
        num=float(getSetting(setting))
    except:
        pass
    return num

def setSetting(setting,value):
    ADDON.setSetting(id=setting, value=str(value))

def getKeyboard():
    return xbmc.Keyboard()

def addListItem(label="", params={}, label2=None, thumb=None, fanart=None, 
                videoInfo={}, properties={}, isFolder=True):
    item=xbmcgui.ListItem(label,label2)
    item.setArt({'thumb': thumb, 'fanart': fanart})
    item.setInfo( 'video', videoInfo)
    if not isFolder: properties['IsPlayable']='true'
    if isinstance(params,dict):
        url=staticutils.parameters(params)
    else:
        url = params
    for key, value in properties.iteritems():
        item.setProperty(key, value)
    return xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=item, isFolder=isFolder)

def setResolvedUrl(url="", solved=True, subs=[]):
    item = xbmcgui.ListItem(path = url)
    item.setSubtitles(subs)
    xbmcplugin.setResolvedUrl(HANDLE, solved, item)
    sys.exit()

def append_subtitle(sUrl, subtitlename, sync=False, provider=None):
    #listitem = createListItem({'label': 'Italian', 'label2': subtitlename, 'thumbnailImage': 'it'})
    if not provider:
        tUrl = {'action': 'download', 'subid':sUrl}
    elif provider == 'ItalianSubs':
        p=re.search('subtitle_id=(?P<SUBID>[0-9]+)',sUrl,re.IGNORECASE)
        if not p:
            return False
        tUrl = "plugin://service.subtitles.itasa/?action=download&subid={subid}".format(subid=p.group('SUBID'))
    else:
        tUrl = {'action': 'download', 'url':sUrl}
    log("aggiungo il sottotitolo '" + subtitlename + "' alla lista",3)
    return addListItem(label="Italian", label2=subtitlename, params=tUrl, thumb="it", 
                       properties={"sync": 'true' if sync else 'false', "hearing_imp": "false"}, isFolder=False)

def setContent(type='videos'):
    xbmcplugin.setContent(HANDLE, type)

def endScript(message=None,loglevel=2, closedir=True):
    if message:
        log(message,loglevel)
    if closedir:
        xbmcplugin.endOfDirectory(handle=HANDLE, succeeded=True)
    sys.exit()

def createAddonFolder():
    if not os.path.isdir(DATA_PATH_T):
        log("Creating the addon data folder")
        os.makedirs(DATA_PATH_T)

def getShowID():
    json_query = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":1,"properties":["tvshowid"]},"id":1}' )
    json_player_getitem = json.loads(unicode(json_query, 'utf-8', errors='ignore'))
    if json_player_getitem.has_key('result') and json_player_getitem['result']['item']['type'] == 'episode':
        json_query = xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"VideoLibrary.GetTVShowDetails","params":{"tvshowid":%s, "properties": ["imdbnumber"]}}' % (json_player_getitem['result']['item']['tvshowid']) )
        json_getepisodedetails = json.loads(unicode(json_query, 'utf-8', errors='ignore'))
        if json_getepisodedetails.has_key('result') and json_getepisodedetails['result']['tvshowdetails']['imdbnumber']!='':
            return str(json_getepisodedetails['result']['tvshowdetails']['imdbnumber'])
    return False

def containsLanguage(strlang,langs):
    for lang in strlang.decode('utf-8').split(','):
        if xbmc.convertLanguage(lang, xbmc.ISO_639_2) in langs:
            return True
    return False

def isPlayingVideo():
    return xbmc.Player().isPlayingVideo()

def getInfoLabel(lbl):
    return xbmc.getInfoLabel(lbl)

def getEpisodeInfo():
    episode = {}
    episode['tvshow'] = staticutils.normalizeString(xbmc.getInfoLabel('VideoPlayer.TVshowtitle'))    # Show
    episode['season'] = xbmc.getInfoLabel('VideoPlayer.Season')                                    # Season
    episode['episode'] = xbmc.getInfoLabel('VideoPlayer.Episode')                                  # Episode
    file_original_path = xbmc.Player().getPlayingFile().decode('utf-8')                 # Full path
    
    if str(episode['episode']).lower().find('s') > -1:                                             # Check if season is "Special"
        episode['season'] = 0
        episode['episode'] = int(str(episode['episode'])[-1:])

    elif file_original_path.find('rar://') > -1:
        file_original_path = os.path.dirname(file_original_path[6:])

    elif file_original_path.find('stack://') > -1:
        file_original_path = file_original_path.split(' , ')[0][8:]

    episode['filename'] = os.path.splitext(os.path.basename(file_original_path))[0]

    return episode

log("Starting module '%s' version '%s' with command '%s'" % (NAME, VERSION, sys.argv[2]), 1)