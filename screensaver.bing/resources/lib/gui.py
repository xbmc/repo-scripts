#   Copyright (C) 2021 Lunatixz
#
#
# This file is part of Bing ScreenSaver.
#
# Bing ScreenSaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Bing ScreenSaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Bing ScreenSaver.  If not, see <http://www.gnu.org/licenses/>.

import json, os, random, datetime, requests

from six.moves     import urllib
from simplecache   import use_cache, SimpleCache
from kodi_six      import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode
from itertools     import cycle

# Plugin Info
ADDON_ID       = 'screensaver.bing'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE       = REAL_SETTINGS.getLocalizedString
KODI_MONITOR   = xbmc.Monitor()

BASE_URL       = 'https://www.bing.com'
POTD_JSON      = 'https://www.bing.com/hpimagearchive.aspx?format=js&idx=%i&n=8&mkt=%s'%(random.randint(0,7),xbmc.getLanguage(xbmc.ISO_639_1, True))
TIMER          = [30,60,120,240][int(REAL_SETTINGS.getSetting("RotateTime"))]
RANDOM         = REAL_SETTINGS.getSetting("Randomize") == 'true'
IDX_LST        = [1,2,3,4,5,6,7,0]
CYC_INTER      = cycle(IDX_LST).__next__

class GUI(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        self.cache     = SimpleCache()
        self.isExiting = False
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)
            
            
    def notificationDialog(self, message, header=ADDON_NAME, sound=False, time=4000, icon=ICON):
        try: xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
        except Exception as e:
            self.log("notificationDialog Failed! " + str(e), xbmc.LOGERROR)
            xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
        return True
         
         
    def onInit( self ):
        self.winid = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        self.winid.setProperty('bing_time'     , 'okay' if REAL_SETTINGS.getSetting("Time")    == 'true' else 'nope')
        self.winid.setProperty('bing_animation', 'okay' if REAL_SETTINGS.getSetting("Animate") == 'true' else 'nope')
        self.winid.setProperty('bing_overlay'  , 'okay' if REAL_SETTINGS.getSetting("Overlay") == 'true' else 'nope')
        self.PanelItems = self.getControl(101)
        self.PanelItems.addItems(list(self.prepareImages(self.openURL(POTD_JSON))))
        self.startRotation()
        
        
    def startRotation(self):
        while not KODI_MONITOR.abortRequested() and not self.isExiting:
            xbmc.executebuiltin('SetFocus(101)')
            xbmc.executebuiltin("Control.Move(101,%s)"%(str(random.randint(0,7)) if RANDOM else str(CYC_INTER())))
            if KODI_MONITOR.waitForAbort(TIMER): break

        
    def onAction(self, action ):
        self.isExiting = True
        self.close()
        

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
        
        
    def prepareImages(self, response):
        if 'images' in response:
            for img in response['images']: 
                liz = xbmcgui.ListItem('"%s"'%(img.get('title')),offscreen=True)
                liz.setArt({'thumb':'%s%s'%(BASE_URL,img['url'])})
                yield liz