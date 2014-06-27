# -*- coding: utf-8 -*-
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
import sys
import os
import traceback
#Modules XBMC
import xbmc
import xbmcaddon


__addon__     = xbmcaddon.Addon(id='script.videoextras')
__version__   = __addon__.getAddonInfo('version')
__cwd__       = __addon__.getAddonInfo('path').decode("utf-8")
__resource__  = xbmc.translatePath( os.path.join( __cwd__, 'resources' ).encode("utf-8") ).decode("utf-8")
__lib__  = xbmc.translatePath( os.path.join( __resource__, 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import log

# Load the database interface
from database import ExtrasDB

# Load the cache cleaner
from CacheCleanup import CacheCleanup


#########################
# Main
#########################
if __name__ == '__main__':
    log("VideoExtrasCleanup: Cleanup called (version %s)" % __version__)

    try:
        # Start by removing the database
        extrasDb = ExtrasDB()
        extrasDb.cleanDatabase()

        # Also tidy up any of the cache files that exist
        CacheCleanup.removeAllCachedFiles()

    except:
        log("VideoExtrasCleanup: %s" % traceback.format_exc(), xbmc.LOGERROR)

