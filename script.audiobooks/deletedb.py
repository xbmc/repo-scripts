# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import os_path_join

ADDON = xbmcaddon.Addon(id='script.audiobooks')


#########################
# Main
#########################
if __name__ == '__main__':
    log("AudioBookDeleteDb: Delete audiobook database called (version %s)" % ADDON.getAddonInfo('version'))

    configPath = xbmc.translatePath(ADDON.getAddonInfo('profile'))
    databasefile = os_path_join(configPath, "audiobooks_database.db")
    log("AudioBookDeleteDb: Database file location = %s" % databasefile)

    # If the database file exists, delete it
    if xbmcvfs.exists(databasefile):
        xbmcvfs.delete(databasefile)
        log("AudioBookDeleteDb: Removed database: %s" % databasefile)
    else:
        log("AudioBookDeleteDb: No database exists: %s" % databasefile)

    xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32013))
