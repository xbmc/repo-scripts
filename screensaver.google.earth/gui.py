#   Copyright (C) 2018 Lunatixz
#
#
# This file is part of Earth View ScreenSaver.
#
# Earth View ScreenSaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Earth View ScreenSaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Earth View ScreenSaver.  If not, see <http://www.gnu.org/licenses/>.

import json, os, random, itertools, urllib2, datetime
import xbmc, xbmcaddon, xbmcvfs, xbmcgui

from simplecache import SimpleCache, use_cache

# Plugin Info
ADDON_ID       = 'screensaver.google.earth'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
ICON           = REAL_SETTINGS.getAddonInfo('icon')
LANGUAGE       = REAL_SETTINGS.getLocalizedString

# Global Info
KODI_MONITOR   = xbmc.Monitor()
BASE_URL       = 'https://earthview.withgoogle.com'
DEFAULT_JSON   = '/_api/marble-canyon-united-states-2000.json'
BASE_API       = (REAL_SETTINGS.getSetting("Last") or DEFAULT_JSON)
ANIMATION      = 'okay' if REAL_SETTINGS.getSetting("Animate") == 'true' else 'nope'
TIME           = 'okay' if REAL_SETTINGS.getSetting("Time") == 'true' else 'nope'
TIMER          = [30,60,120,240][int(REAL_SETTINGS.getSetting("RotateTime"))]
IMG_CONTROLS   = [30000,30100]
CYC_CONTROL    = itertools.cycle(IMG_CONTROLS).next

class GUI(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        self.isExiting = False
        self.cache     = SimpleCache()
        self.baseAPI   = BASE_API
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
            
            
    def onInit(self):
        self.winid = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        self.winid.setProperty('earth_animation', ANIMATION)
        self.winid.setProperty('earth_time', TIME)
        self.startRotation()
    
    
    def openURL(self, url):
        try:
            self.log('openURL, url = ' + str(url))
            cacheresponse = self.cache.get(ADDON_NAME + '.openURL, url = %s'%url)
            if not cacheresponse:
                cacheresponse = (urllib2.urlopen(urllib2.Request(url), timeout=15)).read()
                self.cache.set(ADDON_NAME + '.openURL, url = %s'%url, cacheresponse, expiration=datetime.timedelta(days=28))
            return cacheresponse
        except Exception as e:
            self.log("openURL Failed! " + str(e), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(32001), ICON, 4000)
            return ''
            
     
    def setImage(self, id):
        try:
            results = json.loads(self.openURL('%s%s'%(BASE_URL,self.baseAPI)))
            self.getControl(id).setImage(results['photoUrl'])
            self.getControl(id+1).setLabel(('%s, %s'%(results.get('region',' '),results.get('country',''))).strip(' ,'))
            baseAPI = results['nextApi']
        except: baseAPI = DEFAULT_JSON
        self.baseAPI = baseAPI
        
        
    def startRotation(self):
        self.currentID = IMG_CONTROLS[0]
        self.nextID    = IMG_CONTROLS[1]
        self.setImage(self.currentID)
        while not KODI_MONITOR.abortRequested():
            self.getControl(self.nextID).setVisible(False)
            self.getControl(self.currentID).setVisible(True)
            self.nextID    = self.currentID
            self.currentID = CYC_CONTROL()
            self.setImage(self.currentID)
            if KODI_MONITOR.waitForAbort(TIMER) == True or self.isExiting == True: break
        REAL_SETTINGS.setSetting("Last",self.baseAPI)

                     
    def onAction( self, action ):
        self.isExiting = True
        self.close()