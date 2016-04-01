# -*- coding: utf-8 -*-
import sys
import os
import traceback
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
from settings import Settings
from settings import log
from settings import dir_exists
from settings import os_path_join


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
