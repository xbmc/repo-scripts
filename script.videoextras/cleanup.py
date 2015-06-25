# -*- coding: utf-8 -*-
import sys
import os
import traceback
import xbmc
import xbmcaddon


__addon__ = xbmcaddon.Addon(id='script.videoextras')
__version__ = __addon__.getAddonInfo('version')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

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
        del extrasDb

        # Also tidy up any of the cache files that exist
        CacheCleanup.removeAllCachedFiles()

    except:
        log("VideoExtrasCleanup: %s" % traceback.format_exc(), xbmc.LOGERROR)
