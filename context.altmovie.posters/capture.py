#   Copyright (C) 2018 Lunatixz
#
#
# This file is part of Alternative Movie Poster.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Alternative Movie Poster.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import os, sys, time, datetime, re, traceback
import urlparse, urllib, urllib2, socket, json
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

from simplecache import SimpleCache
from bs4 import BeautifulSoup

# Plugin Info
ADDON_ID      = 'context.altmovie.posters'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString

## GLOBALS
TIMEOUT       = 15
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
SEARCHDEPTH   = int(REAL_SETTINGS.getSetting('Search_Depth'))

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
      
socket.setdefaulttimeout(TIMEOUT)  
class ALTPOSTERS(object):
    def __init__(self):
        self.cache  = SimpleCache()
        title = (xbmc.getInfoLabel('ListItem.Title') or xbmc.getInfoLabel('ListItem.Label') or None)
        dbID  = (xbmc.getInfoLabel('ListItem.DBID')  or -1)
        if title is None or (xbmc.getInfoLabel('ListItem.DBTYPE') or '') != 'movie':
            xbmcgui.Dialog().notification(ADDON_NAME,LANGUAGE(30001), ICON, 4000)
            return
        self.searchTitle(title, dbID)
        
           
    def openURL(self, url):
        try:
            log('openURL, url = ' + str(url))
            cacheresponse = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if not cacheresponse:
                request = urllib2.Request(url)
                request.add_header('User-Agent','Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; en-US)')
                cacheresponse = urllib2.urlopen(request, timeout=TIMEOUT).read()
                self.cache.set(ADDON_NAME + '.openURL, url = %s'%url, cacheresponse, expiration=datetime.timedelta(days=28))
            return cacheresponse
        except Exception as e: log("openURL Failed! " + str(e), xbmc.LOGERROR)
        return ''
            
                
    def searchTitle(self, title, dbID):
        log('searchTitle, title = ' + title)
        listItems = []
        xbmc.executebuiltin('ActivateWindow(busydialog)')
        for idx in range(1,SEARCHDEPTH):
            try:
                SEARCHURL = 'http://www.alternativemovieposters.com/page/%d/?s=%s'
                soup  = BeautifulSoup(self.openURL(SEARCHURL%(idx,urllib.quote_plus(title))), "html.parser")
                items = soup('div' , {'class': 'fusion-post-wrapper'})
                if not items or len(items) == 0: break
                for item in items:
                    url = item('div' , {'class': 'fusion-image-wrapper'})[0].find('img').attrs['src']
                    label = item('div' , {'class': 'fusion-post-content post-content'})[0].find('a').get_text()
                    listItems.append(xbmcgui.ListItem(label, thumbnailImage=url, path=url))
            except: break
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        if len(listItems) > 0:
            select = xbmcgui.Dialog().select(LANGUAGE(32001)%(title), listItems, useDetails=True)
            if select > -1: self.setImage(title, dbID, listItems[select].getPath())
        else: xbmcgui.Dialog().notification(ADDON_NAME,LANGUAGE(32002)%(title), ICON, 4000)

        
    def setImage(self, title, dbID, url):
        log('setImage, url = ' + url)
        if not xbmcgui.Dialog().yesno(ADDON_NAME, LANGUAGE(32003)%(title)): return
        xbmcgui.Dialog().notification(ADDON_NAME,LANGUAGE(32004)%(title), ICON, 4000)
        json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.SetMovieDetails","params":{"movieid" : %s, "thumbnail" : "%s", "art" : %s},"id":1}' % (dbID,url,json.dumps({"poster":url})))
        xbmc.executeJSONRPC(json_query)
        xbmc.executebuiltin("Container.Refresh")
        
if __name__ == '__main__': ALTPOSTERS()
