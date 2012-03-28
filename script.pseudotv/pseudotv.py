#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os, threading
import xbmc, xbmcgui
import xbmcaddon

from resources.lib.Globals import *



# Script constants
__scriptname__ = "PseudoTV"
__author__     = "Jason102"
__url__        = "http://github.com/Jasonra/XBMC-PseudoTV"
__version__    = VERSION
__settings__   = xbmcaddon.Addon(id='script.pseudotv')
__language__   = __settings__.getLocalizedString
__cwd__        = __settings__.getAddonInfo('path')


import resources.lib.Overlay as Overlay


MyOverlayWindow = Overlay.TVOverlay("script.pseudotv.TVOverlay.xml", __cwd__, "default")

for curthread in threading.enumerate():
    try:
        log("Active Thread: " + str(curthread.name), xbmc.LOGERROR)

        if curthread.name != "MainThread":
            try:
                curthread.join()
            except:
                pass

            log("Joined " + curthread.name)
    except:
        pass

del MyOverlayWindow
xbmcgui.Window(10000).setProperty("PseudoTVRunning", "False")

