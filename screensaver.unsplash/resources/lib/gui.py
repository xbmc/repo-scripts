#   Copyright (C) 2021 Lunatixz
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

import json, os, random, datetime, itertools, requests

from six.moves     import urllib
from kodi_six      import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode


# Plugin Info
ADDON_ID       = 'screensaver.unsplash'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE       = REAL_SETTINGS.getLocalizedString
KODI_MONITOR   = xbmc.Monitor()

ENABLE_KEYS    = REAL_SETTINGS.getSetting("Enable_Keys") == 'true'
KEYWORDS       = "" if not ENABLE_KEYS else urllib.parse.quote(REAL_SETTINGS.getSetting("Keywords"))
USER           = REAL_SETTINGS.getSetting("User").replace('@','')
COLLECTION     = REAL_SETTINGS.getSetting("Collection")
CATEGORY       = urllib.parse.quote(REAL_SETTINGS.getSetting("Category"))

BASE_URL       = 'https://source.unsplash.com'
RES            = ['1280x720','1920x1080','3840x2160'][int(REAL_SETTINGS.getSetting("Resolution"))]
RES_PARAMS     = ['&fit=fit&fm=jpg&w=1280&h=720','&fit=fit&fm=jpg&w=1920&h=1080','&fit=fit&fm=jpg&w=3840&h=2160'][int(REAL_SETTINGS.getSetting("Resolution"))]
TYPE_PARAMS    = ['{res}/daily','category/weekly/{res}','random?{keyword}{resp}','featured?{keyword}{resp}',
                  'user/{user}/{res}','{user}/likes/{res}',
                  'collection/{cid}/{res}','category/{cat}/{res}'][int(REAL_SETTINGS.getSetting("PhotoType"))]
URL_PARAMS     = '%s/%s'%(BASE_URL,TYPE_PARAMS)
IMAGE_URL      = URL_PARAMS.format(res=RES,keyword=KEYWORDS,user=USER,cid=COLLECTION,cat=CATEGORY,resp=RES_PARAMS)

TIMER          = [30,60,120,240][int(REAL_SETTINGS.getSetting("RotateTime"))]
IMG_CONTROLS   = [30000,30001]
CYC_CONTROL    = itertools.cycle(IMG_CONTROLS).__next__ #py3

class GUI(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
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
        self.winid.setProperty('unsplash_animation', 'okay' if REAL_SETTINGS.getSetting("Animate") == 'true' else 'nope')
        self.winid.setProperty('unsplash_time'     , 'okay' if REAL_SETTINGS.getSetting("Time") == 'true' else 'nope')
        self.winid.setProperty('unsplash_overlay'  , 'okay' if REAL_SETTINGS.getSetting("Overlay") == 'true' else 'nope')
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


    def onAction(self, action):
        self.log("onAction")
        self.isExiting = True
        self.close()
        
    
    def openURL(self, url):
        try:
            self.log("openURL url = " + url)
            request = urllib.request.Request(url)
            request.add_header('User-Agent','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11')
            page = urllib.request.urlopen(request, timeout = 15)
            url = page.geturl()
            self.log("openURL return url = " + url)
            return url
        except Exception as e: self.log("openURL, Failed! " + str(e), xbmc.LOGERROR)
        return ''