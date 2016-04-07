# -*- coding: utf-8 -*-
import re
import traceback
import xbmc
import xbmcvfs
import xbmcaddon

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join

ADDON = xbmcaddon.Addon(id='script.videoextras')
PROFILE_DIR = xbmc.translatePath(ADDON.getAddonInfo('profile')).decode("utf-8")


#################################
# Class to tidy up any
#################################
class CacheCleanup():

    # Cleans out all the cached files
    @staticmethod
    def removeAllCachedFiles():
        CacheCleanup.removeCacheFile(Settings.MOVIES, True)
        CacheCleanup.removeCacheFile(Settings.TVSHOWS, True)
        CacheCleanup.removeCacheFile(Settings.MUSICVIDEOS, True)

        CacheCleanup.removeCacheFile('overlay_image_used.txt')

    # Removes the cache file for a given type
    @staticmethod
    def removeCacheFile(target, isDir=False):
        try:
            fullFilename = os_path_join(PROFILE_DIR, target)

            log("VideoExtrasCleanup: Checking cache file %s" % fullFilename)

            # If the file already exists, delete it
            if xbmcvfs.exists(fullFilename):
                if isDir:
                    # Remove the png files in the directory first
                    dirs, files = xbmcvfs.listdir(fullFilename)
                    for aFile in files:
                        m = re.search("[0-9]+[a-zA-Z_]*.png", aFile, re.IGNORECASE)
                        if m:
                            pngFile = os_path_join(fullFilename, aFile)
                            xbmcvfs.delete(pngFile)
                    # Now remove the actual directory
                    xbmcvfs.rmdir(fullFilename)
                else:
                    xbmcvfs.delete(fullFilename)
        except:
            log("CacheCleanup: %s" % traceback.format_exc(), xbmc.LOGERROR)
