# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui


ADDON = xbmcaddon.Addon(id='script.ebooks')
CWD = ADDON.getAddonInfo('path').decode("utf-8")
RES_DIR = xbmc.translatePath(os.path.join(CWD, 'resources').encode("utf-8")).decode("utf-8")
LIB_DIR = xbmc.translatePath(os.path.join(RES_DIR, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(LIB_DIR)

# Import the common settings
from settings import log
from settings import os_path_join


#########################
# Main
#########################
if __name__ == '__main__':
    log("EBookDeleteDb: Delete book database called (version %s)" % ADDON.getAddonInfo('version'))

    configPath = xbmc.translatePath(ADDON.getAddonInfo('profile'))
    databasefile = os_path_join(configPath, "ebooks_database.db")
    log("EBookDeleteDb: Database file location = %s" % databasefile)

    # If the database file exists, delete it
    if xbmcvfs.exists(databasefile):
        xbmcvfs.delete(databasefile)
        log("EBookDeleteDb: Removed database: %s" % databasefile)
    else:
        log("EBookDeleteDb: No database exists: %s" % databasefile)

    xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32014))
