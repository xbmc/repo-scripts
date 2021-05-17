#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     06 Dec 2020, (7:21 AM)

    Copyright:
        Copyright (C) 2021 Josh Sunnex

        This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
        Public License as published by the Free Software Foundation, version 3.

        This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
        implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
        for more details.

        You should have received a copy of the GNU General Public License along with this program.
        If not, see <https://www.gnu.org/licenses/>.

"""

import xbmc
import xbmcaddon
import sys

__addon__ = xbmcaddon.Addon()


class Default(object):

    def download_dependencies(self):
        from resources import fetch_dependencies
        dependencies = fetch_dependencies.UnmanicDependencies()
        dependencies.fetch_ffmpeg()

    def run(self):
        if len(sys.argv) > 1:
            exec_method = sys.argv[1]
            xbmc.log("Unmanic called with arg: '{}' - exists:{}".format(exec_method, hasattr(self, exec_method)),
                     level=xbmc.LOGDEBUG)
            getattr(self, exec_method)()
        else:
            __addon__.openSettings()


if __name__ == '__main__':
    default = Default()
    default.run()
