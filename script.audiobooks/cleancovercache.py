# -*- coding: utf-8 -*-
import sys
import os
import traceback
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui


__addon__ = xbmcaddon.Addon(id='script.audiobooks')
__version__ = __addon__.getAddonInfo('version')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log
from settings import dir_exists
from settings import os_path_join


#########################
# Main
#########################
if __name__ == '__main__':
    log("AudioBookCoverCleanup: Cover cache cleanup called (version %s)" % __version__)

    coverCache = Settings.getCoverCacheLocation()

    if dir_exists(coverCache):
        try:
            log("AudioBookCoverCleanup: Checking cache files %s" % coverCache)

            # Remove the jpg and png files in the directory first
            dirs, files = xbmcvfs.listdir(coverCache)
            for aFile in files:
                log("AudioBookCoverCleanup: Removing file %s" % aFile)
                if aFile.endswith('.jpg') or aFile.endswith('.jpeg') or aFile.endswith('.png'):
                    coverFile = os_path_join(coverCache, aFile)
                    xbmcvfs.delete(coverFile)
            # Now remove the actual directory
            xbmcvfs.rmdir(coverCache)

        except:
            log("AudioBookCoverCleanup: %s" % traceback.format_exc(), xbmc.LOGERROR)

    xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), __addon__.getLocalizedString(32009))
