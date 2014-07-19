#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 KenV99
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

import os
import sys
import xbmc
import xbmcaddon
import xbmcgui

__addon__ = xbmcaddon.Addon('script.ambibox')
__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode('utf-8')
__settings__ = xbmcaddon.Addon("script.ambibox")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
__language__ = __settings__.getLocalizedString
sys.path.append(__resource__)

from ambibox import AmbiBox
abx = AmbiBox(__settings__.getSetting("host"), int(__settings__.getSetting("port")))
str_cmd = sys.argv[1]


def notification(text, *silence):
    """
    Display an XBMC notification box, optionally turn off sound associated with it
    @type text: str
    @type silence: bool
    """
    text = text.encode('utf-8')
    if __settings__.getSetting("notification") == 'true':
        icon = __settings__.getAddonInfo("icon")
        smallicon = icon.encode("utf-8")
        # xbmc.executebuiltin('Notification(AmbiBox,' + text + ',1000,' + smallicon + ')')
        dialog = xbmcgui.Dialog()
        if silence:
            dialog.notification('Ambibox', text, smallicon, 1000, False)
        else:
            dialog.notification('Ambibox', text, smallicon, 1000, True)

try:
    if str_cmd == 'on':
        if abx.connect() == 0:
            abx.lock()
            abx.turnOn()
            abx.unlock()
            __settings__.setSetting(id='manual_switch', value='on')
            notification(__language__(32069))  # @[LEDs On] 
    if str_cmd == 'off':
        if abx.connect() == 0:
            abx.lock()
            abx.turnOff()
            abx.unlock()
            __settings__.setSetting(id='manual_switch', value='off')
            notification(__language__(32070))  # @[LEDs Off] 
except Exception, e:
    pass

"""
<f7 mod="ctrl">XBMC.RunScript(special://home\addons\script.ambibox\switch.py, on)</f7>
"""