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


__addon__      = xbmcaddon.Addon()
__scriptname__ = __addon__.getAddonInfo('name')
__author__     = "Team XBMC"
__GUI__        = "Team XBMC"
__scriptId__   = __addon__.getAddonInfo('id')
__language__   = __addon__.getLocalizedString
__version__    = __addon__.getAddonInfo("version")
__cwd__        = __addon__.getAddonInfo('path')
__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")

sys.path.append (__resource__)

xbmc.log("##### [%s] - Version: %s" % (__scriptname__,__version__,),level=xbmc.LOGDEBUG )

if ( __name__ == "__main__" ):
    import gui
    ui = gui.GUI( "%s.xml" % __scriptId__.replace(".","-") , __cwd__, "Default")
    ui.doModal()
    del ui
    sys.modules.clear()
