#
#  MythBox for XBMC
#
#  Copyright (C) 2011 analogue@yahoo.com 
#  http://mythbox.googlecode.com
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

__scriptname__   = "MythBox for XBMC"
__author__       = "analogue@yahoo.com"
__url__          = "http://mythbox.googlecode.com"
__hg_url__       = "https://mythbox.googlecode.com/hg/"
__credits__      = "bunch of ppl"

if __name__ == '__main__':
    print __scriptname__
    
    # WinPDB debugger
    #import rpdb2 
    #rpdb2.start_embedded_debugger('xxx')

    import os, sys, xbmcaddon
    scriptDir = xbmcaddon.Addon('script.mythbox').getAddonInfo('path')
    sys.path.append(os.path.join(scriptDir, 'resources', 'src'))

    import xbmcgui
    import xbmc
    splash = xbmcgui.WindowXML('mythbox_splash.xml', scriptDir)
    splash.show()
    
    from mythbox.bootstrapper import BootStrapper
    BootStrapper(splash).run()