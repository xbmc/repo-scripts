#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2015 Philipp Temminghoff (phil65@kodi.tv)
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

import sys
import xbmc
import xbmcaddon
from resources.lib import gui

ADDON = xbmcaddon.Addon()
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path').decode("utf-8")


class Main:

    def __init__(self):
        xbmc.log("version %s started" % ADDON_VERSION)
        self._parse_argv()
        wnd = gui.get_window(lat=self.params.get("lat"),
                             lon=self.params.get("lon"),
                             location=self.params.get("location"),
                             folder=self.params.get("folder"))
        wnd.doModal()

    def _parse_argv(self):
        self.infos = []
        self.params = {}
        for arg in sys.argv[1:]:
            param = arg.replace('"', '').replace("'", " ")
            if param.startswith('info='):
                self.infos.append(param[5:])
            else:
                try:
                    self.params[param.split("=")[0].lower()] = "=".join(param.split("=")[1:]).strip()
                except:
                    pass

if (__name__ == "__main__"):
    Main()
xbmc.log('finished')
