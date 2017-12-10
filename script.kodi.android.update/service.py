#     Copyright (C) 2017 Team-Kodi
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

import traceback
import xbmc, xbmcaddon, xbmcgui, xbmcvfs

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

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg.encode("utf-8")), level)

class Service(object):
    def __init__(self):
        try:
            self.lastPath = REAL_SETTINGS.getSetting("LastPath")
            if not CACHE and CLEAN and xbmcvfs.exists(self.lastPath):
                log('Service, removing last download')
                xbmcvfs.delete(self.lastPath)
                xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30007), ICON, 4000)
        except Exception as e:
            log("Service Failed! " + str(e), xbmc.LOGERROR)
        
if __name__ == '__main__':
    Service()