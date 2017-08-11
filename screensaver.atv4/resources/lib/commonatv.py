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

import xbmcaddon
import xbmcgui
import os

addon = xbmcaddon.Addon()
addon_path = addon.getAddonInfo('path')
dialog = xbmcgui.Dialog()

applefeed = "http://a1.phobos.apple.com/us/r1000/000/Features/atv/AutumnResources/videos/entries.json"
applelocalfeed = os.path.join(addon_path,"resources","entries.json")
places = ["All", "London", "Hawaii", "New York City", "San Francisco",
          "China", "Greenland", "Dubai", "Los Angeles", "Liwa", "Hong Kong"]


def translate(text):
    return addon.getLocalizedString(text).encode('utf-8')


def notification(header, message, time=2000, icon=addon.getAddonInfo('icon'), sound=True):
    xbmcgui.Dialog().notification(header, message, icon, time, sound)
