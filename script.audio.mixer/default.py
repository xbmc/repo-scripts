#/*
# *      Copyright (C) 2005-2013 Team XBMC
# *      http://xbmc.org
# *
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING.  If not, see
# *  <http://www.gnu.org/licenses/>.
# *
# */

import sys
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
CWD = ADDON.getAddonInfo('path')

xbmc.log("%s: started" % (ADDONID), level=xbmc.LOGDEBUG)

if (__name__ == "__main__"):
    from lib import gui
    ui = gui.GUI( "%s.xml" % ADDONID.replace(".", "-"), CWD, "Default")
    ui.doModal()
    del ui
    sys.modules.clear()
