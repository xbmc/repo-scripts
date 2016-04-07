# -*- coding: utf-8 -*-
import traceback
import xbmc
import xbmcaddon

# Import the common settings
from resources.lib.settings import log
# Load the database interface
from resources.lib.database import ExtrasDB
# Load the cache cleaner
from resources.lib.CacheCleanup import CacheCleanup

ADDON = xbmcaddon.Addon(id='script.videoextras')


#########################
# Main
#########################
if __name__ == '__main__':
    log("VideoExtrasCleanup: Cleanup called (version %s)" % ADDON.getAddonInfo('version'))

    try:
        # Start by removing the database
        extrasDb = ExtrasDB()
        extrasDb.cleanDatabase()
        del extrasDb

        # Also tidy up any of the cache files that exist
        CacheCleanup.removeAllCachedFiles()

    except:
        log("VideoExtrasCleanup: %s" % traceback.format_exc(), xbmc.LOGERROR)
