# *
# *      Copyright (C) 2005-2010 Team XBMC
# *      http://www.xbmc.org
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
# *  along with XBMC; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
# */


import sys
import os
import xbmcaddon
__scriptname__ = "Bootable Disk Wizard"
__author__ = "Team XBMC"
__GUI__    = "ronie"
__version__ = "0.9.4"

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources', 'lib' ) )
sys.path.append (BASE_RESOURCE_PATH)

__settings__ = xbmcaddon.Addon(id='script.bootable.disk.wizard')
__language__ = __settings__.getLocalizedString

if ( __name__ == "__main__" ):
    import gui
    ui = gui.GUI( "script-%s.xml" % (__scriptname__.replace(" ","-")) , os.getcwd(), "Default")
    ui.doModal()
    del ui
    sys.modules.clear()
