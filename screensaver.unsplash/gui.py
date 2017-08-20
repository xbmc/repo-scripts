#   Copyright (C) 2017 Lunatixz
#
#
# This file is part of Unsplash Photo ScreenSaver.
#
# Unsplash Photo ScreenSaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Unsplash Photo ScreenSaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Unsplash Photo ScreenSaver.  If not, see <http://www.gnu.org/licenses/>.

import urllib, urllib2, socket, random
import xbmc, xbmcaddon, xbmcvfs, xbmcgui

# Plugin Info
ADDON_ID       = 'screensaver.unsplash'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile').decode('utf-8')
ENABLE_KEYS    = REAL_SETTINGS.getSetting("Enable_Keys") == 'true'
KEYWORDS       = urllib.quote_plus(REAL_SETTINGS.getSetting("Keywords").encode("utf-8"))
USER           = urllib.quote_plus(REAL_SETTINGS.getSetting("User").encode("utf-8"))
COLLECTION     = urllib.quote_plus(REAL_SETTINGS.getSetting("Collection").encode("utf-8"))
PHOTO_TYPE     = ['featured','random','user','collection'][int(REAL_SETTINGS.getSetting("PhotoType"))]
BASE_URL       = 'https://source.unsplash.com'
URL_PARAMS     = '/%s'%PHOTO_TYPE
TIMER          = [30,60,120,240][int(REAL_SETTINGS.getSetting("RotateTime"))]
ANIMATION      = 'okay' if REAL_SETTINGS.getSetting("Animate") == 'true' else 'nope'
TIME           = REAL_SETTINGS.getSetting("Time") == 'true'

if PHOTO_TYPE in ['featured','random']:
    IMAGE_URL  = BASE_URL + URL_PARAMS + '/1920x1200/?%s'%KEYWORDS if ENABLE_KEYS else BASE_URL + URL_PARAMS
elif PHOTO_TYPE == 'user':
    IMAGE_URL  = BASE_URL + URL_PARAMS + '/%s/1920x1200' %USER
else:
    IMAGE_URL  = BASE_URL + URL_PARAMS + '/%s/1920x1200' %COLLECTION
    
KODI_MONITOR   = xbmc.Monitor()
class GUI(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        self.isExiting = False
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
            
            
    def onInit( self ):
        self.winid = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        self.winid.setProperty('unsplash_animation', ANIMATION)
        self.imageControl = self.getControl(30000)
        self.timeControl  = self.getControl(30001)
        self.timeControl.setVisible(TIME)
        self.startRotation()
        
        
    def startRotation(self):
        while not KODI_MONITOR.abortRequested():
            self.imageControl.setImage(self.openURL(IMAGE_URL))
            if KODI_MONITOR.waitForAbort(TIMER) == True or self.isExiting == True:
                break
        
        
    def onAction( self, action ):
        self.isExiting = True
        self.close()
        
        
    def openURL(self, url):
        try:
            self.log("openURL url = " + url)
            request = urllib2.Request(url)
            request.add_header('User-Agent','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11')
            page = urllib2.urlopen(request, timeout = 15)
            url = page.geturl()
            self.log("openURL return url = " + url)
            return url
        except urllib2.URLError, e:
            self.log("openURL Failed! " + str(e), xbmc.LOGERROR)
        except socket.timeout, e:
            self.log("openURL Failed! " + str(e), xbmc.LOGERROR)
        return ''