# -*- coding: utf-8 -*-
'''
    script.screensaver.cocktail - A random cocktail recipe screensaver for kodi 
    Copyright (C) 2015 enen92,Zag

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
import sys
import xbmcgui
from resources.lib.common_cocktail import *

class ScreensaverPreview(xbmcgui.WindowXMLDialog):
    
    class ExitMonitor(xbmc.Monitor):

        def __init__(self, exit_callback):
            self.exit_callback = exit_callback

        def onScreensaverDeactivated(self):
            self.exit_callback()

    def onInit(self):
        self.exit_monitor = self.ExitMonitor(self.exit)
        xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.ContextMenu", "id": 1}')

    def exit(self):
        self.close()
        #Call the screensaver asynchronously and die
        xbmc.executebuiltin('RunAddon(script.screensaver.cocktail,teste)')

if __name__ == '__main__':
    if not xbmc.getCondVisibility('Window.IsActive(script-cocktail-Cocktailplayer.xml)'):
        #Start preview window
        screensaver = ScreensaverPreview(
            'script-cocktail-preview.xml',
            addon_path,
            'default',
            '',
        )
        screensaver.doModal()
        xbmc.sleep(100)
        del screensaver

    else:
        sys.exit(0)
    