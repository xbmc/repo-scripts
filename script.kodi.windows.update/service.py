#  Copyright (C) 2026 Team-Kodi
#
#  This file is part of script.kodi.windows.update
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSES/README.md for more information.
#
# -*- coding: utf-8 -*-
from default import *

PATH  = REAL_SETTINGS.getSetting("LastPath")
CACHE = REAL_SETTINGS.getSetting('Disable_Cache') == 'false'
CLEAN = REAL_SETTINGS.getSetting('Disable_Maintenance') == 'false'

class Service(object):
    myMonitor = xbmc.Monitor()
    
    def __init__(self):
        self.getBuild()
        self.getPlatform()
        self.getVersion()
        self.chkLastFile()
        
                
    def getBuild(self):
        try:
            build = json.dumps(json.loads(xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Application.GetProperties","params":{"properties":["version"]},"id":1}') or '').get('result',{}).get('version',{}))
            REAL_SETTINGS.setSetting("Build",build)
            log(f'Service: getBuild = {build}')
        except Exception as e: log(f"Service: getBuild failed!\n{e}", xbmc.LOGERROR)
            
            
    def getPlatform(self): 
        try:
            for count in range(15):
                machine = platform.machine()
                if len(machine) > 0: 
                    REAL_SETTINGS.setSetting("Platform",machine)
                    log(f'Service: getPlatform = {machine}')
                    return
                if self.myMonitor.waitForAbort(1): return
        except Exception as e: log(f"Service: getPlatform failed!\n{e}", xbmc.LOGERROR)
        
        
    def getVersion(self):
        try:
            for count in range(15):
                version = (xbmc.getInfoLabel('System.OSVersionInfo') or 'busy')
                if version.lower() != 'busy': 
                    REAL_SETTINGS.setSetting("Version",str(version))
                    log(f'Service: getVersion = {version}')
                    return
                if self.myMonitor.waitForAbort(1): return
        except Exception as e: log(f"Service: getVersion failed!\n{e}", xbmc.LOGERROR)
              
              
    def chkLastFile(self):
        # CACHE = Keep last download, CLEAN = Remove all downloads
        if xbmcvfs.exists(PATH):
            if not CACHE and CLEAN:
                log(f'Service: chkLastFile = {PATH}')
                deleteFile(PATH)
                xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30007), ICON, 4000)
              
              
if __name__ == '__main__': Service()
