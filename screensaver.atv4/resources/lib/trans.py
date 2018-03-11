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
from commonatv import addon


class ScreensaverTrans(xbmcgui.WindowXMLDialog):

    class ExitMonitor(xbmc.Monitor):

        def __init__(self, activated_callback):
            self.activated_callback = activated_callback

        def onScreensaverDeactivated(self):
            self.activated_callback()

    def onInit(self):
        self.exit_monitor = self.ExitMonitor(self.exit)

    def exit(self):
        addon.setSetting("is_locked", "false")
        self.close()

    def onAction(self, action):
        self.exit()
