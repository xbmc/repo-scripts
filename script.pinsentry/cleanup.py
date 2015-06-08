# -*- coding: utf-8 -*-
import sys
import os
import traceback
import xbmc
import xbmcaddon


__addon__ = xbmcaddon.Addon(id='script.pinsentry')
__version__ = __addon__.getAddonInfo('version')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import log

# Load the database interface
from database import PinSentryDB


#########################
# Main
#########################
if __name__ == '__main__':
    log("PinSentryCleanup: Cleanup called (version %s)" % __version__)

    try:
        # Start by removing the database
        extrasDb = PinSentryDB()
        extrasDb.cleanDatabase()
        del extrasDb
    except:
        log("PinSentryCleanup: %s" % traceback.format_exc(), xbmc.LOGERROR)
