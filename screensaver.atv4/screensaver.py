# -*- coding: utf-8 -*-
'''
    screensaver.atv4
    Copyright (C) 2015 enen92

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import xbmc
from trans import ScreensaverTrans
from resources.lib.commonatv import *


class ScreensaverPreview(xbmcgui.WindowXMLDialog):
    
    class ExitMonitor(xbmc.Monitor):

        def __init__(self, exit_callback):
            self.exit_callback = exit_callback

        def onScreensaverDeactivated(self):
            self.exit_callback()

    def onInit(self):
        self.exit_monitor = self.ExitMonitor(self.exit)
        self.getControl(32502).setLabel(translate(32025))
        xbmc.executebuiltin("SetProperty(screensaver-atv4-loading,1,home)")
        xbmc.sleep(1000)
        xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.ContextMenu", "id": 1}')

    def exit(self):
        xbmc.executebuiltin("ClearProperty(screensaver-atv4-loading,Home)")
        self.close()

        #Call the script and die
        xbmc.executebuiltin('RunAddon(screensaver.atv4)')


if __name__ == '__main__':
    if addon.getSetting("is_locked") == "false":
        if addon.getSetting("show-notifications") == "true":
            xbmc.executebuiltin("Notification(%s,%s,%i,%s)" % (translate(32000), translate(32017),1,os.path.join(addon_path,"icon.png")))
        
        #Start window
        screensaver = ScreensaverPreview(
            'screensaver-atv4.xml',
            addon_path,
            'default',
            '',
        )
        screensaver.doModal()
        xbmc.sleep(100)
        del screensaver
    else:
        #Transparent placeholder
        trans = ScreensaverTrans(
            'screensaver-atv4-trans.xml',
            addon_path,
            'default',
            '',
        )
        trans.doModal()
        xbmc.sleep(100)
        del trans