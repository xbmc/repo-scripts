"""
   Copyright (C) 2015- enen92
   This file is part of screensaver.atv4 - https://github.com/enen92/screensaver.atv4

   SPDX-License-Identifier: GPL-2.0-only
   See LICENSE for more information.
"""

import xbmc
import xbmcgui
from .commonatv import addon


class ScreensaverTrans(xbmcgui.WindowXMLDialog):

    class ExitMonitor(xbmc.Monitor):

        def __init__(self, activated_callback):
            self.activated_callback = activated_callback

        def onScreensaverDeactivated(self):
            self.activated_callback()

    def onInit(self):
        self.exit_monitor = self.ExitMonitor(self.exit)

    def exit(self):
        addon.setSettingBool("is_locked", False)
        self.close()

    def onAction(self, action):
        self.exit()
