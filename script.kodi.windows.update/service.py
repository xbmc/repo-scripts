#     Copyright (C) 2020 Team-Kodi
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# -*- coding: utf-8 -*-

import platform, traceback, json, sys
import xbmc, xbmcaddon, xbmcgui, xbmcvfs

# Plugin Info
ADDON_ID      = 'script.kodi.windows.update'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
LANGUAGE      = REAL_SETTINGS.getLocalizedString

## GLOBALS ##
DEBUG         = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
CLEAN         = REAL_SETTINGS.getSetting('Disable_Maintenance') == 'false'
CACHE         = REAL_SETTINGS.getSetting('Disable_Cache') == 'false'
VER_QUERY     = '{"jsonrpc":"2.0","method":"Application.GetProperties","params":{"properties":["version"]},"id":1}'

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg.encode("utf-8")), level)

class Service(object):
    def __init__(self):
        self.myMonitor = xbmc.Monitor()
        self.setSettings()
        lastPath = REAL_SETTINGS.getSetting("LastPath") # CACHE = Keep last download, CLEAN = Remove all downloads
        if not CACHE and CLEAN and xbmcvfs.exists(lastPath): self.deleteLast(lastPath)
        
                
    def deleteLast(self, lastPath):
        log('deleteLast')
        #some file systems don't release the file lock instantly.
        for count in range(3):
            if self.myMonitor.waitForAbort(1): return 
            try: 
                if xbmcvfs.delete(lastPath): return
            except: pass
                

    def setSettings(self):
        log('setSettings')
        [func() for func in [self.getBuild,self.getPlatform,self.getVersion]]
              
              
    def getBuild(self):
        log('getBuild')
        REAL_SETTINGS.setSetting("Build",json.dumps(json.loads(xbmc.executeJSONRPC(VER_QUERY) or '').get('result',{}).get('version',{})))
        
        
    def getPlatform(self): 
        log('getPlatform')
        count = 0
        try:
            while not self.myMonitor.abortRequested() and count < 15:
                count += 1 
                if self.myMonitor.waitForAbort(1): return
                build = platform.machine()
                if len(build) > 0: return REAL_SETTINGS.setSetting("Platform",build)
        except Exception as e: log("getVersion Failed! " + str(e), xbmc.LOGERROR)
        
        
    def getVersion(self):
        log('getVersion')
        count = 0
        try:
            while not self.myMonitor.abortRequested() and count < 15:
                count += 1 
                if self.myMonitor.waitForAbort(1): return
                build = (xbmc.getInfoLabel('System.OSVersionInfo') or 'busy')
                if build.lower() != 'busy': return REAL_SETTINGS.setSetting("Version",str(build))
        except Exception as e: log("getVersion Failed! " + str(e), xbmc.LOGERROR)
              
if __name__ == '__main__': Service()