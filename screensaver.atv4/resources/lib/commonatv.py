"""
   Copyright (C) 2015- enen92
   This file is part of screensaver.atv4 - https://github.com/enen92/screensaver.atv4

   SPDX-License-Identifier: GPL-2.0-only
   See LICENSE for more information.
"""

import os
import xbmcaddon
import xbmcgui

addon = xbmcaddon.Addon()
addon_path = addon.getAddonInfo('path')
addon_icon = addon.getAddonInfo('icon')
dialog = xbmcgui.Dialog()

applefeed = "http://a1.v2.phobos.apple.com.edgesuite.net/us/r1000/000/Features/atv/AutumnResources/videos/entries.json"
applelocalfeed = os.path.join(addon_path, "resources", "entries.json")
places = ["All", "London", "Hawaii", "New York City", "San Francisco",
          "China", "Greenland", "Dubai", "Los Angeles", "Liwa", "Hong Kong"]


def translate(text):
    return addon.getLocalizedString(text)


def notification(header, message, time=2000, icon=addon_icon,
                 sound=True):
    xbmcgui.Dialog().notification(header, message, icon, time, sound)
