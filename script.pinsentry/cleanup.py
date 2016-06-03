# -*- coding: utf-8 -*-
import traceback
import xbmc
import xbmcaddon

# Import the common settings
from resources.lib.settings import log
# Load the database interface
from resources.lib.database import PinSentryDB

ADDON = xbmcaddon.Addon(id='script.pinsentry')


#########################
# Main
#########################
if __name__ == '__main__':
    log("PinSentryCleanup: Cleanup called (version %s)" % ADDON.getAddonInfo('version'))

    try:
        # Start by removing the database
        extrasDb = PinSentryDB()
        extrasDb.cleanDatabase()
        del extrasDb
    except:
        log("PinSentryCleanup: %s" % traceback.format_exc(), xbmc.LOGERROR)
