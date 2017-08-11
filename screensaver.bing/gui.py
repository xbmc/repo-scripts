#   Copyright (C) 2017 Lunatixz
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

import urllib, urllib2, socket, json, os, random
import xbmc, xbmcaddon, xbmcvfs, xbmcgui
from simplecache import use_cache, SimpleCache

# Plugin Info
ADDON_ID       = 'screensaver.bing'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile').decode('utf-8')
BASE_URL       = 'https://www.bing.com'
POTD_JSON      = '/HPImageArchive.aspx?format=js&idx=0&n=8&mkt=en-US'
KODI_MONITOR   = xbmc.Monitor()
TIMER          = [30,60,120,240][int(REAL_SETTINGS.getSetting("RotateTime"))]
RANDOM         = REAL_SETTINGS.getSetting("Randomize") == 'true'
ANIMATION      = 'okay' if REAL_SETTINGS.getSetting("Animate") == 'true' else 'nope'
xbmcgui.Window(10000).setProperty('bing_animation', ANIMATION)

class GUI(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        self.cache = SimpleCache()
        self.isExiting = False
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
            
            
    def onInit( self ):
        self.PanelItems = self.getControl(101)
        self.PanelItems.addItems(self.prepareImages(self.openURL(BASE_URL + POTD_JSON)))
        self.startRotation()
        
        
    def startRotation(self):
        while not KODI_MONITOR.abortRequested():
            xbmc.executebuiltin('SetFocus(101)')
            if KODI_MONITOR.waitForAbort(TIMER) == True or self.isExiting == True:
                break
            seek = str(random.randint(1,7)) if RANDOM == True else '1'
            xbmc.executebuiltin("Control.Move(101,%s)"%seek)
        
        
    def onFocus( self, controlId ):
        pass
    
   
    def onClick( self, controlId ):
        pass

        
    def onAction( self, action ):
        self.isExiting = True
        self.close()
        

    def uni(self, string, encoding='utf-8'):
        if isinstance(string, basestring):
            if not isinstance(string, unicode):
               string = unicode(string, encoding)
        return string

        
    def ascii(self, string):
        if isinstance(string, basestring):
            if isinstance(string, unicode):
               string = string.encode('ascii', 'ignore')
        return string
                
              
    def loadJson(self, string):
        if len(string) == 0:
            return {}
        try:
            return json.loads(self.uni(string))
        except Exception,e:
            return {}
          

    @use_cache(1)
    def openURL(self, url):
        try:
            request = urllib2.Request(url)
            request.add_header('User-Agent','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11')
            page = urllib2.urlopen(request, timeout = 15)
            return self.loadJson(page.read())
        except urllib2.URLError, e:
            self.log("openURL Failed! " + str(e), xbmc.LOGERROR)
        except socket.timeout, e:
            self.log("openURL Failed! " + str(e), xbmc.LOGERROR)
        return {}
        
     
    def prepareImages(self, responce):
        imageLST = []
        if 'images' in responce:
            for img in responce['images']:
                imageLST.append(xbmcgui.ListItem(self.ascii(img['copyright']),thumbnailImage=(BASE_URL + img['url'])))
        return imageLST