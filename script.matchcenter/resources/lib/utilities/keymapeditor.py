# -*- coding: utf-8 -*-
'''
    script.matchcenter - Football information for Kodi
    A program addon that can be mapped to a key on your remote to display football information.
    Livescores, Event details, Line-ups, League tables, next and previous matches by team. Follow what
    others are saying about the match in twitter.
    Copyright (C) 2016 enen92

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
import xbmcgui
import traceback
from resources.lib.utilities.common_addon import *

### Key mapp            
def run():
    try:
        xbmc.executebuiltin("ActivateWindow(10147)")
        window = xbmcgui.Window(10147)
        xbmc.sleep(100)
        window.getControl(1).setLabel(translate(32000))
        window.getControl(5).setText(translate(32065))
        while xbmc.getCondVisibility("Window.IsActive(10147)"):
            xbmc.sleep(100)
        ret = xbmcgui.Dialog().yesno(translate(32000), translate(32067))
        if ret:
            xbmc.executebuiltin("RunAddon(script.keymap)")

    except:
        traceback.print_stack()
        xbmc.executebuiltin("XBMC.Notification('"+translate(32000)+"','"+translate(32066)+"','2000','')")