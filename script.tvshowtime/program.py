#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import threading
import xbmc
import xbmcgui
import xbmcaddon
import unicodedata
import json

from resources.lib.tvshowtime import GetCode
from resources.lib.tvshowtime import Authorize
from resources.lib.tvshowtime import IsChecked
from resources.lib.tvshowtime import MarkAsWatched
from resources.lib.tvshowtime import MarkAsUnWatched
from resources.lib.tvshowtime import GetUserInformations

__addon__         = xbmcaddon.Addon()
__cwd__           = __addon__.getAddonInfo('path')
__icon__          = __addon__.getAddonInfo("icon")
__scriptname__    = __addon__.getAddonInfo('name')
__version__       = __addon__.getAddonInfo('version')
__language__      = __addon__.getLocalizedString
__resource_path__ = os.path.join(__cwd__, 'resources', 'lib')
__resource__      = xbmc.translatePath(__resource_path__).decode('utf-8')

__token__ = __addon__.getSetting('token')
__facebook__ = __addon__.getSetting('facebook')
__twitter__ = __addon__.getSetting('twitter')

def start():
    menuitems = []
    if __token__ is '':
        menuitems.append(__language__(33801))
    else:
        menuitems.append(__language__(33803))
        menuitems.append(__language__(33802))
    startmenu = xbmcgui.Dialog().select(__scriptname__, menuitems)
    if startmenu < 0: return
    elif startmenu == 0 and __token__ is '':
        _login = GetCode()
        if _login.is_code:
            Authorization(_login.verification_url, _login.user_code, _login.device_code)
        else:
            xbmcgui.Dialog().ok(__scriptname__, __language__(33804))
    elif startmenu == 1:
        logout = xbmcgui.Dialog().yesno(__scriptname__, __language__(33805))
        if logout == True:
            __addon__.setSetting('token', '')
            return
        start()
    else:
        first_step()
        
def Authorization(verification_url, user_code, device_code):
    pDialog = xbmcgui.DialogProgress()
    pDialog.create(__scriptname__, "%s: %s" % (__language__(33806), verification_url), "%s: %s" % (__language__(33807), user_code))
    for i in range(0, 100):
        pDialog.update(i)
        xbmc.sleep(5000)  
        if pDialog.iscanceled(): return
        _authorize = Authorize(device_code)
        if _authorize.is_authorized:
            __addon__.setSetting('token', _authorize.access_token)
            user = GetUserInformations(_authorize.access_token)
            if user.is_authenticated:
                xbmcgui.Dialog().ok(__scriptname__, '%s %s' % (__language__(32902), user.username), __language__(33808))
            return
    pDialog.close()

def first_step():
    which_way = xbmcgui.Dialog().select(__language__(33901), ["TVShow Time > Kodi", "Kodi > TVShow Time"])
    if which_way < 0: return
    tvshows = []
    tvshowsid = []
    command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"sort": { "order": "ascending", "method": "label" }}, "id": 1}'
    result = json.loads(xbmc.executeJSONRPC(command))                     
    for i in range(0, result['result']['limits']['total']):
        tvshows.append(result['result']['tvshows'][i]['label'])
        tvshowsid.append(result['result']['tvshows'][i]['tvshowid'])
    tvshows.insert(0, __language__(33902))
    tvshowsid.insert(0, "0")
    whattvshow = xbmcgui.Dialog().select(__language__(33903), tvshows)
    if whattvshow < 0: return
    elif whattvshow == 0:
        scan(which_way)
    else:
        seasons = []
        command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params":{"tvshowid": %s, "properties": ["season"], "sort": { "order": "ascending", "method": "season" }}, "id": 1}' % tvshowsid[whattvshow]
        result = json.loads(xbmc.executeJSONRPC(command))                     
        for i in range(0, result['result']['limits']['total']):
            seasons.append(str(result['result']['episodes'][i]['season']))
        seasons = remove_duplicates(seasons)
        seasons.insert(0, __language__(33904))
        whatseason = xbmcgui.Dialog().select(__language__(33905), seasons)
        if whatseason < 0: return
        elif whatseason == 0:
            scan(which_way, tvshowsid[whattvshow])
        else:
            scan(which_way, tvshowsid[whattvshow], whatseason)
        
def remove_duplicates(values):
    output = []
    seen = set()
    for value in values:
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output

def scan(way, whattvshow = 0, whatseason = 0):
    if whattvshow == 0:
        command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "properties": ["season", "episode", "showtitle", "playcount", "tvshowid"] }, "id": 1}'
    elif whatseason == 0:
        command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params":{"tvshowid": %s, "properties": ["season", "episode", "showtitle", "playcount", "tvshowid"]}, "id": 1}' % whattvshow
    else:
        command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params":{"tvshowid": %s, "season": %s, "properties": ["season", "episode", "showtitle", "playcount", "tvshowid"]}, "id": 1}' % (whattvshow, whatseason)
        
    if way == 0:
        pDialog = xbmcgui.DialogProgressBG()
        pDialog.create('TVShow Time > Kodi', __language__(33906))
        pDialog.update(0, message=__language__(33906))
        result = json.loads(xbmc.executeJSONRPC(command))  
        total = result['result']['limits']['total']                                      
        for i in range(0, total):
            filename = '%s.S%sE%s' % (formatName(result['result']['episodes'][i]['showtitle']), result['result']['episodes'][i]['season'], result['result']['episodes'][i]['episode'])
            log('tvshowtitle=%s' % filename)
            episode = IsChecked(__token__, filename)
            if episode.is_found:
                log("episode.is_found=%s" % episode.is_found)
                if episode.is_watched == True: episode.is_watched = 1
                else: episode.is_watched = 0
                log("kodi.playcount=%s" % result['result']['episodes'][i]['playcount'])
                log("tvst.playcount=%s" % episode.is_watched)
                if result['result']['episodes'][i]['playcount'] <> episode.is_watched:
                    log('TVST->Kodi (%s)' % episode.is_watched)
                    command2 = '{"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.SetEpisodeDetails", "params": {"episodeid" : %s, "playcount": %s}}' % (result['result']['episodes'][i]['episodeid'], episode.is_watched)
                    result2 = json.loads(xbmc.executeJSONRPC(command2))
            pDialog.update(((100/total)*(i+1)), message=filename)
            if ((i+1) % 30) == 0 and i < (total-1):
                pDialog.update(((100/total)*(i+1)), message=__language__(33908))
                xbmc.sleep(60000)
        pDialog.close()
        xbmcgui.Dialog().ok("TVShow Time > Kodi", __language__(33907))  
    else:
        pDialog = xbmcgui.DialogProgressBG()
        pDialog.create('Kodi > TVShow Time', __language__(33906))
        pDialog.update(0, message=__language__(33906))
        result = json.loads(xbmc.executeJSONRPC(command))  
        total = result['result']['limits']['total']                                      
        for i in range(0, total):
            filename = '%s.S%sE%s' % (formatName(result['result']['episodes'][i]['showtitle']), result['result']['episodes'][i]['season'], result['result']['episodes'][i]['episode'])
            log('tvshowtitle=%s' % filename)
            #episode = IsChecked(__token__, filename)
            #if episode.is_found:
            #    log("episode.is_found=%s" % episode.is_found)
            #    if episode.is_watched == True: episode.is_watched = 1
            #    else: episode.is_watched = 0
            log("kodi.playcount=%s" % result['result']['episodes'][i]['playcount'])
            #    log("tvst.playcount=%s" % episode.is_watched)
            #    if result['result']['episodes'][i]['playcount'] <> episode.is_watched:
            log('Kodi->TVST (%s)' % result['result']['episodes'][i]['playcount'])
            if result['result']['episodes'][i]['playcount'] == 1:
                checkin = MarkAsWatched(__token__, filename, __facebook__, __twitter__)
            else:
                checkin = MarkAsUnWatched(__token__, filename)
            pDialog.update(((100/total)*(i+1)), message=filename)
            if ((i+1) % 30) == 0 and i < (total-1):
                pDialog.update(((100/total)*(i+1)), message=__language__(33908))
                xbmc.sleep(60000)
        pDialog.close()
        xbmcgui.Dialog().ok("Kodi > TVShow Time", __language__(33907))  

def formatNumber(number):
    if len(number) < 2:
         number = '0%s' % number
    return number
     
def formatName(filename):
    filename = filename.strip()
    filename = filename.replace(' ', '.')
    return filename	 
    
def notif(msg, time=5000):
    xbmcgui.Dialog().notification(encode(__scriptname__), encode(msg), time=time, icon=__icon__)

def log(msg):
    xbmc.log("### [%s] - %s" % (__scriptname__, encode(msg), ),
            level=xbmc.LOGDEBUG) #100 #xbmc.LOGDEBUG

def encode(string):
    result = ''
    try:
        result = string.encode('UTF-8','replace')
    except UnicodeDecodeError:
        result = 'Unicode Error'
    return result         

start()
