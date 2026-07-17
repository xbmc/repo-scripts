"""
Kodi video capturer for Hyperion.

Copyright (c) 2013-2023 Hyperion Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import xbmc
import xbmcaddon
from resources.lib.gui import GuiHandler
from resources.lib.logger import Logger
from resources.lib.monitor import HyperionMonitor
from resources.lib.settings import SettingsManager

ADDON_NAME = "script.service.hyperion"


def main() -> None:
    addon = xbmcaddon.Addon(ADDON_NAME)
    logger = Logger(addon.getAddonInfo("name"))
    settings_manager = SettingsManager(addon.getSettings(), logger)
    player = xbmc.Player()
    output_handler = GuiHandler(addon, settings_manager)
    monitor = HyperionMonitor(settings_manager, player, output_handler, logger)
    monitor.main_loop()


if __name__ == "__main__":
    main()
