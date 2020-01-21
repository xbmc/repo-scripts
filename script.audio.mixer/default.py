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
import os
import xbmc
import xbmcaddon


ADDON = xbmcaddon.Addon()
ADDONNAME = ADDON.getAddonInfo('name')
ADDONID = ADDON.getAddonInfo('id')
LANGUAGE = ADDON.getLocalizedString
VERSION = ADDON.getAddonInfo("version")
CWD = ADDON.getAddonInfo('path')
PROFILE = xbmc.translatePath(ADDON.getAddonInfo('profile'))
RESOURCE = xbmc.translatePath(os.path.join(CWD, 'resources', 'lib' ))

sys.path.append(RESOURCE)

xbmc.log("%s: version %s" % (ADDONNAME,VERSION), level=xbmc.LOGDEBUG)

if ( __name__ == "__main__" ):
    import gui
    ui = gui.GUI( "%s.xml" % ADDONID.replace(".","-"), CWD, "Default")
    ui.doModal()
    del ui
    sys.modules.clear()
