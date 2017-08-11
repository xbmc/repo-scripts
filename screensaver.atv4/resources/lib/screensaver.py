# -*- coding: utf-8 -*-
"""
    screensaver.atv4
    Copyright (C) 2015-2017 enen92

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
"""
import xbmc
import xbmcgui
from trans import ScreensaverTrans
from commonatv import translate, addon, addon_path, notification


class ScreensaverPreview(xbmcgui.WindowXMLDialog):

    @staticmethod
    class ExitMonitor(xbmc.Monitor):

        def __init__(self, exit_callback):
            self.exit_callback = exit_callback

        def onScreensaverDeactivated(self):
            self.exit_callback()

    def onInit(self):
        self.exit_monitor = self.ExitMonitor(self.exit)
        self.getControl(32502).setLabel(translate(32025))
        self.setProperty("screensaver-atv4-loading", "1")
        self.exit_monitor.waitForAbort(1)
        self.send_input()

    @staticmethod
    def send_input():
        xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.ContextMenu", "id": 1}')

    @staticmethod
    def runAddon():
        xbmc.executebuiltin('RunAddon(screensaver.atv4)')

    def exit(self):
        self.clearProperty("screensaver-atv4-loading")
        self.close()
        # Call the script and die
        self.runAddon()



def run():
    if not xbmc.getCondVisibility("Player.HasMedia"):
        if addon.getSetting("is_locked") == "false":
            if addon.getSetting("show-notifications") == "true":
                notification(translate(32000), translate(32017))

            if addon.getSetting("show-previewwindow") == "true":
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
                monitor = ScreensaverPreview.ExitMonitor(ScreensaverPreview.runAddon())
                ScreensaverPreview.send_input()

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
    else:
        # Just call deactivate
        ScreensaverPreview.send_input()