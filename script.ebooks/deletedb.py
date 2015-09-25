# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui


__addon__ = xbmcaddon.Addon(id='script.ebooks')
__version__ = __addon__.getAddonInfo('version')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import log
from settings import os_path_join


#########################
# Main
#########################
if __name__ == '__main__':
    log("EBookDeleteDb: Delete book database called (version %s)" % __version__)

    configPath = xbmc.translatePath(__addon__.getAddonInfo('profile'))
    databasefile = os_path_join(configPath, "ebooks_database.db")
    log("EBookDeleteDb: Database file location = %s" % databasefile)

    # If the database file exists, delete it
    if xbmcvfs.exists(databasefile):
        xbmcvfs.delete(databasefile)
        log("EBookDeleteDb: Removed database: %s" % databasefile)
    else:
        log("EBookDeleteDb: No database exists: %s" % databasefile)

    xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), __addon__.getLocalizedString(32014))
