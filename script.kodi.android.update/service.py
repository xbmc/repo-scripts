#  Copyright (C) 2020 Team-Kodi
#
#  This file is part of script.kodi.android.update
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSES/README.md for more information.
#
# -*- coding: utf-8 -*-

import platform, traceback, json
from kodi_six import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs

# Plugin Info
ADDON_ID      = 'script.kodi.android.update'
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
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg), level)

class Service(object):
    def __init__(self):
        self.myMonitor = xbmc.Monitor()
        self.setSettings()
        lastPath = REAL_SETTINGS.getSetting("LastPath") # CACHE = Keep last download, CLEAN = Remove all downloads
        if not CACHE and CLEAN and xbmcvfs.exists(lastPath): self.deleteLast(lastPath)
               
               
    def deleteLast(self, lastPath):
        log('deleteLast')
        try:
            xbmcvfs.delete(lastPath)
            xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30007), ICON, 4000)
        except Exception as e: log("deleteLast Failed! " + str(e), xbmc.LOGERROR)
            
            
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