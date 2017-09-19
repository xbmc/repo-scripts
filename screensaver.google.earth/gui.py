#   Copyright (C) 2017 Lunatixz
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

import json, os, random
import xbmc, xbmcaddon, xbmcvfs, xbmcgui

# Plugin Info
ADDON_ID       = 'screensaver.google.earth'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile').decode('utf-8')

# Global Info
KODI_MONITOR   = xbmc.Monitor()
JSON_FILE      = xbmc.translatePath(os.path.join(ADDON_PATH,'resources','earthview.json'))
JSON_FILE_EXT  = xbmc.translatePath(os.path.join(SETTINGS_LOC,'earthview.json'))
ANIMATION      = 'okay' if REAL_SETTINGS.getSetting("Animate") == 'true' else 'nope'
TIME           = 'okay' if REAL_SETTINGS.getSetting("Time") == 'true' else 'nope'
TIMER          = [30,60,120,240][int(REAL_SETTINGS.getSetting("RotateTime"))]


class GUI(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        self.isExiting = False
        self.earthView = self.loadJson()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
            
            
    def onInit(self):
        self.winid = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        self.winid.setProperty('earth_animation', ANIMATION)
        self.winid.setProperty('earth_time', TIME)
        self.PanelItems = self.getControl(101)
        self.PanelItems.addItems(list(self.prepareImages(self.earthView)))
        self.startRotation()
    
    
    def loadJson(self):
        FILE = JSON_FILE_EXT if xbmcvfs.exists(JSON_FILE_EXT) else JSON_FILE
        with open(FILE) as data: 
            return json.load(data)
     
     
    def prepareImages(self, results):
        for img in results:
            label = '%s, %s'%(img['country'],img['region']) if len(img['region']) > 0 else '%s'%(img['country'])
            listitem = xbmcgui.ListItem(label)
            listitem.setArt({"thumb":img['image'],"poster":img['image']})
            yield listitem
        
        
    def startRotation(self):
        while not KODI_MONITOR.abortRequested():
            xbmc.executebuiltin('SetFocus(101)')
            seek = str(random.randint(1,len(self.earthView)))
            xbmc.executebuiltin("Control.Move(101,%s)"%seek)
            if KODI_MONITOR.waitForAbort(TIMER) == True or self.isExiting == True:
                break
                
                
    def onAction( self, action ):
        self.isExiting = True
        self.close()