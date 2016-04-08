# -*- coding: utf-8 -*-
import traceback
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui

# Import the common settings
from resources.lib.settings import Settings
from resources.lib.settings import log
from resources.lib.settings import dir_exists
from resources.lib.settings import os_path_join

ADDON = xbmcaddon.Addon(id='script.ebooks')


#########################
# Main
#########################
if __name__ == '__main__':
    log("EBookCoverCleanup: Cover cache cleanup called (version %s)" % ADDON.getAddonInfo('version'))

    coverCache = Settings.getCoverCacheLocation()

    if dir_exists(coverCache):
        try:
            log("EBookCoverCleanup: Checking cache files %s" % coverCache)

            # Remove the jpg and png files in the directory first
            dirs, files = xbmcvfs.listdir(coverCache)
            for aFile in files:
                log("EBookCoverCleanup: Removing file %s" % aFile)
                if aFile.endswith('.jpg') or aFile.endswith('.jpeg') or aFile.endswith('.png'):
                    coverFile = os_path_join(coverCache, aFile)
                    xbmcvfs.delete(coverFile)
            # Now remove the actual directory
            xbmcvfs.rmdir(coverCache)

        except:
            log("EBookCoverCleanup: %s" % traceback.format_exc(), xbmc.LOGERROR)

    xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32009))
