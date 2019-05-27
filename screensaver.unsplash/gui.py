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

import urllib, urllib2, socket, random, itertools
import xbmc, xbmcaddon, xbmcvfs, xbmcgui

# Plugin Info
ADDON_ID       = 'screensaver.unsplash'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile').decode('utf-8')
ENABLE_KEYS    = REAL_SETTINGS.getSetting("Enable_Keys") == 'true'
KEYWORDS       = urllib.quote(REAL_SETTINGS.getSetting("Keywords").encode("utf-8"))
USER           = REAL_SETTINGS.getSetting("User").encode("utf-8").replace('@','')
COLLECTION     = REAL_SETTINGS.getSetting("Collection").encode("utf-8")
PHOTO_TYPE     = ['featured','random','user','collection'][int(REAL_SETTINGS.getSetting("PhotoType"))]
BASE_URL       = 'https://source.unsplash.com'
URL_PARAMS     = '/%s'%PHOTO_TYPE
TIMER          = [30,60,120,240][int(REAL_SETTINGS.getSetting("RotateTime"))]
ANIMATION      = 'okay' if REAL_SETTINGS.getSetting("Animate") == 'true' else 'nope'
TIME           = 'okay' if REAL_SETTINGS.getSetting("Time") == 'true' else 'nope'
IMG_CONTROLS   = [30000,30001]
CYC_CONTROL    = itertools.cycle(IMG_CONTROLS).next
KODI_MONITOR   = xbmc.Monitor()
RES            = ['1280x720','1920x1080','3840x2160'][int(REAL_SETTINGS.getSetting("Resolution"))]

if PHOTO_TYPE in ['featured','random']: IMAGE_URL  = BASE_URL + URL_PARAMS + '/%s/?%s'%(RES, KEYWORDS if ENABLE_KEYS else BASE_URL + URL_PARAMS)
elif PHOTO_TYPE == 'user': IMAGE_URL  = BASE_URL + URL_PARAMS + '/%s/%s' %(USER, RES)
else: IMAGE_URL  = BASE_URL + URL_PARAMS + '/%s/%s' %(COLLECTION, RES)
    
class GUI(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        self.isExiting = False
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
            
            
    def onInit( self ):
        self.winid = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        self.winid.setProperty('unsplash_animation', ANIMATION)
        self.winid.setProperty('unsplash_time', TIME)
        self.startRotation()

         
    def setImage(self, id):
        image = self.openURL(IMAGE_URL)
        image = image if len(image) > 0 else self.openURL(IMAGE_URL)
        self.getControl(id).setImage(image)
        

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
        except urllib2.URLError, e: self.log("openURL Failed! " + str(e), xbmc.LOGERROR)
        except socket.timeout, e: self.log("openURL Failed! " + str(e), xbmc.LOGERROR)
        return ''