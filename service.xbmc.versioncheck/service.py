#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2013 XBMC Foundation
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

import xbmc
import xbmcgui
import xbmcaddon

class Main:
    def __init__(self):
        xbmc.sleep(10000)
        if xbmcaddon.Addon('xbmc.addon').getAddonInfo('version') < "12.0.0":
            xbmcgui.Dialog().ok('Version check',
                                'This XBMC version is out of support',
                                'A newer stable version of XBMC is available.',
                                'Visit http://xbmc.org for more information.')
            xbmcgui.Dialog().ok('Version check',
                                'There will be no more plugin or add-ons updates',
                                'for this version. Please upgrade.',
                                'Visit http://xbmc.org for more information.')

if (__name__ == "__main__"):
    Main()
