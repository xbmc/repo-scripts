#   Copyright (C) 2021 Lunatixz
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

import json, os, random, datetime, requests, itertools

from six.moves     import urllib
from simplecache   import use_cache, SimpleCache
from kodi_six      import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode


# Plugin Info
ADDON_ID       = 'screensaver.google.earth'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE       = REAL_SETTINGS.getLocalizedString
KODI_MONITOR   = xbmc.Monitor()

# Global Info
BASE_URL       = 'https://earthview.withgoogle.com'
NEXT_JSON      = '/_api/%s.json'
BASE_API       = (REAL_SETTINGS.getSetting("Last") or NEXT_JSON%('marble-canyon-united-states-2000'))
TIMER          = [30,60,120,240][int(REAL_SETTINGS.getSetting("RotateTime"))]
IMG_CONTROLS   = [30000,30100]
CYC_CONTROL    = itertools.cycle(IMG_CONTROLS).__next__ #py3

class GUI(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        self.isExiting = False
        self.cache     = SimpleCache()
        self.baseAPI   = BASE_API
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)
            
            
    def notificationDialog(self, message, header=ADDON_NAME, sound=False, time=4000, icon=ICON):
        try: xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
        except Exception as e:
            self.log("notificationDialog Failed! " + str(e), xbmc.LOGERROR)
            xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
        return True
         
         
    def onInit(self):
        self.winid = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        self.winid.setProperty('earth_animation', 'okay' if REAL_SETTINGS.getSetting("Animate") == 'true' else 'nope')
        self.winid.setProperty('earth_time'     , 'okay' if REAL_SETTINGS.getSetting("Time") == 'true' else 'nope')
        self.winid.setProperty('earth_overlay'  , 'okay' if REAL_SETTINGS.getSetting("Overlay") == 'true' else 'nope')
        self.startRotation()


    def loadJSON(self, item):
        try: return json.loads(item, strict=False)
        except Exception as e: self.log("loadJSON failed! %s\n%s"%(e,item), xbmc.LOGERROR)
          

    def openURL(self, url, param={}, header={'User-agent': 'Mozilla/5.0 (Windows NT 6.2; rv:24.0) Gecko/20100101 Firefox/24.0'}, life=datetime.timedelta(hours=24)):
        self.log('getURL, url = %s, header = %s'%(url, header))
        cacheresponse = self.cache.get('%s.getURL, url = %s.%s.%s'%(ADDON_NAME,url,param,header))
        if not cacheresponse:
            try:
                req = requests.get(url, param, headers=header)
                cacheresponse = req.json()
                req.close()
            except Exception as e: 
                self.log("getURL, Failed! %s"%(e), xbmc.LOGERROR)
                self.notificationDialog(LANGUAGE(30001))
                return {}
            self.cache.set('%s.getURL, url = %s.%s.%s'%(ADDON_NAME,url,param,header), json.dumps(cacheresponse), expiration=life)
            return cacheresponse
        return self.loadJSON(cacheresponse)
     
     
    def setImage(self, id):
        try:
            results = self.openURL('%s%s'%(BASE_URL,self.baseAPI))
            self.getControl(id).setImage(results['photoUrl'])
            self.getControl(id+1).setLabel(('%s, %s'%(results.get('region',' '),results.get('country',''))).strip(' ,'))
            baseAPI = NEXT_JSON%(results['nextSlug'])
        except Exception as e:
            self.log("setImage Failed! " + str(e), xbmc.LOGERROR)
            baseAPI = NEXT_JSON%('marble-canyon-united-states-2000')
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

                     
    def onAction(self, action):
        self.isExiting = True
        self.close()