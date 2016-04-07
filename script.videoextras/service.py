# -*- coding: utf-8 -*-
import sys
import os
import traceback
import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui

# Add JSON support for queries
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

# Import the common settings
from resources.lib.settings import Settings
from resources.lib.settings import log
from resources.lib.settings import os_path_join
from resources.lib.settings import dir_exists
# Load the core Video Extras classes
from resources.lib.core import VideoExtrasBase
# Load the cache cleaner
from resources.lib.CacheCleanup import CacheCleanup

ADDON = xbmcaddon.Addon(id='script.videoextras')
CWD = ADDON.getAddonInfo('path').decode("utf-8")
PROFILE_DIR = xbmc.translatePath(ADDON.getAddonInfo('profile')).decode("utf-8")
RES_DIR = xbmc.translatePath(os.path.join(CWD, 'resources').encode("utf-8")).decode("utf-8")


#####################################
# Main class for the Extras Service
#####################################
class VideoExtrasService():
    LIST_TAG = "_list"

    def __init__(self):
        # special://skin - This path points to the currently active skin's root directory.
        skinExtrasOverlayBase = xbmc.translatePath("special://skin").decode("utf-8")
        skinExtrasOverlayBase = os_path_join(skinExtrasOverlayBase, "media")

        # Now check to see if the user has defines a different overlay image in the
        # settings, as that is the main one that will be used
        self.skinExtrasOverlay = Settings.getCustomOverlayImage()
        self.skinExtrasOverlayList = Settings.getCustomListImage()

        # Next check the skin specific overlay
        if self.skinExtrasOverlay in [None, '']:
            self.skinExtrasOverlay = os_path_join(skinExtrasOverlayBase, "videoextras_overlay.png")
        if self.skinExtrasOverlayList in [None, '']:
            self.skinExtrasOverlayList = os_path_join(skinExtrasOverlayBase, "videoextras_overlay_list.png")

        log("VideoExtrasService: Looking for image overlay file: %s" % self.skinExtrasOverlay)

        if not xbmcvfs.exists(self.skinExtrasOverlay):
            log("VideoExtrasService: No custom image, using default")
            # Add default image setting to skinExtrasOverlay
            self.skinExtrasOverlay = os_path_join(RES_DIR, "skins")
            self.skinExtrasOverlay = os_path_join(self.skinExtrasOverlay, "icons")
            self.skinExtrasOverlay = os_path_join(self.skinExtrasOverlay, "overlay1.png")

        log("VideoExtrasService: Looking for list image overlay file: %s" % self.skinExtrasOverlayList)

        if not xbmcvfs.exists(self.skinExtrasOverlayList):
            log("VideoExtrasService: No custom wide image, using default")
            # Add default image setting to skinExtrasOverlay
            self.skinExtrasOverlayList = os_path_join(RES_DIR, "skins")
            self.skinExtrasOverlayList = os_path_join(self.skinExtrasOverlayList, "icons")
            self.skinExtrasOverlayList = os_path_join(self.skinExtrasOverlayList, "list1.png")

        self.forceOverlayOverwrite = False

        # We now know the file that we are going to use for the overlay
        # Check to see if this is different from the last overlay file used
        filename = os_path_join(PROFILE_DIR, "overlay_image_used.txt")
        try:
            previousOverlay = None
            if xbmcvfs.exists(filename):
                fileHandle = xbmcvfs.File(filename, 'r')
                previousOverlay = fileHandle.read()
                fileHandle.close()

            # Check if the overlay has changed
            if self.skinExtrasOverlay != previousOverlay:
                self.forceOverlayOverwrite = True
                # Update the record of the file we are now using
                if xbmcvfs.exists(filename):
                    xbmcvfs.delete(filename)
                fileHandle = xbmcvfs.File(filename, 'w')
                fileHandle.write(self.skinExtrasOverlay.encode("UTF-8"))
                fileHandle.close()
        except:
            log("VideoExtrasService: Failed to write: %s" % filename, xbmc.LOGERROR)
            log("VideoExtrasService: %s" % traceback.format_exc(), xbmc.LOGERROR)

    # Regenerates all of the cached extras
    def cacheAllExtras(self):
        if not (xbmc.abortRequested or xbmc.getCondVisibility("Window.IsVisible(shutdownmenu)")):
            self.createExtrasCache('GetMovies', Settings.MOVIES, 'movieid')
        if not (xbmc.abortRequested or xbmc.getCondVisibility("Window.IsVisible(shutdownmenu)")):
            self.createExtrasCache('GetTVShows', Settings.TVSHOWS, 'tvshowid')
        if not (xbmc.abortRequested or xbmc.getCondVisibility("Window.IsVisible(shutdownmenu)")):
            self.createExtrasCache('GetMusicVideos', Settings.MUSICVIDEOS, 'musicvideoid')

    # Checks all the given movies/TV/music videos to see if they have any extras
    # and if they do, then cretaes a cached file containing the titles of the video
    # that owns them
    def createExtrasCache(self, jsonGet, target, dbid):
        log("VideoExtrasService: Creating cache for %s" % target)
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.%s", "params": { "properties": ["title", "file"] },  "id": 1}' % jsonGet)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads(json_query)

        extrasCacheString = ""

        if ("result" in json_query) and (target in json_query['result']):
            # Get the list of movies paths from the movie list returned
            items = json_query['result'][target]
            for item in items:
                # Check to see if exit has been called, if so stop
                if xbmc.abortRequested or xbmc.getCondVisibility("Window.IsVisible(shutdownmenu)"):
                    return

                log("VideoExtrasService: %s detected: %s = %s" % (target, item['title'], item['file']))
                videoExtras = VideoExtrasBase(item['file'], target, item['title'])
                # Only checking for the existence of extras - no need for DB or default Fanart
                firstExtraFile = videoExtras.findExtras(True)
                del videoExtras
                # Check if any extras exist for this movie
                if firstExtraFile:
                    log("VideoExtrasService: Extras found for (%d) %s" % (item[dbid], item['title']))
                    extrasCacheString = ("%s[%d]%s" % (extrasCacheString, item[dbid], os.linesep))
                    # Add the overlay image for this item
                    self._createOverlayFile(target, item[dbid], self.skinExtrasOverlay)
                    self._createOverlayFile(target, item[dbid], self.skinExtrasOverlayList, VideoExtrasService.LIST_TAG)
                else:
                    # No extras so remove the file if it exists
                    self._removeOverlayFile(target, item[dbid])
                    self._removeOverlayFile(target, item[dbid], VideoExtrasService.LIST_TAG)

    # Calculates where a given overlay file should be
    def _createTargetPath(self, target, dbid, postfix=''):
        # Get the path where the file exists
        rootPath = os_path_join(PROFILE_DIR, target)
        if not dir_exists(rootPath):
            # Directory does not exist yet, create one
            xbmcvfs.mkdirs(rootPath)

        # Generate the name of the file that the overlay will be copied to
        targetFile = os_path_join(rootPath, ("%d%s.png" % (dbid, postfix)))
        return targetFile

    # Creates the overlay file in the expected location
    def _createOverlayFile(self, target, dbid, srcfile, postfix=''):
        # Generate the name of the file that the overlay will be copied to
        targetFile = self._createTargetPath(target, dbid, postfix)

        # Check if the file exists
        if xbmcvfs.exists(targetFile) and not self.forceOverlayOverwrite:
            return

        try:
            # Now the path exists, need to copy the file over to it, giving it the name of the DBID
            xbmcvfs.copy(srcfile, targetFile)
        except:
            log("VideoExtrasService: Failed to create file: %s" % targetFile, xbmc.LOGERROR)
            log("VideoExtrasService: %s" % traceback.format_exc(), xbmc.LOGERROR)

    # Removes an overlay
    def _removeOverlayFile(self, target, dbid, postfix=''):
        # Generate the name of the file that the overlay will be removed from
        targetFile = self._createTargetPath(target, dbid, postfix)

        if xbmcvfs.exists(targetFile):
            try:
                # Now the path exists, need to copy the file over to it, giving it the name of the DBID
                xbmcvfs.delete(targetFile)
            except:
                log("VideoExtrasService: Failed to delete file: %s" % targetFile, xbmc.LOGERROR)
                log("VideoExtrasService: %s" % traceback.format_exc(), xbmc.LOGERROR)


# Check theYouTube settings are correct, we will automatically disable the
# option if the YouTube addon is not installed
def checkYouTubeSettings():
    # Check to see if the YouTube support is enabled
    if Settings.isYouTubeSearchSupportEnabled():
        # It is enabled in settings, but we should check to ensure that the
        # YouTube addon is actually installed
        youtubeInstalled = False
        try:
            youtubeAddon = xbmcaddon.Addon(id='plugin.video.youtube')
            if youtubeAddon not in [None, ""]:
                youtubeInstalled = True
        except:
            # We will get an exception if we can not find the YouTube addon
            youtubeInstalled = False

        if not youtubeInstalled:
            # There is no YouTube addon installed, so disable this option in settings
            log("VideoExtrasService: Disabling YouTube support as addon not installed")
            Settings.disableYouTubeSearchSupport()


# Check Vimeo settings are correct, we will automatically disable the
# option if the Vimeo addon is not installed
def checkVimeoSettings():
    # Check to see if the Vimeo support is enabled
    if Settings.isVimeoSearchSupportEnabled():
        # It is enabled in settings, but we should check to ensure that the
        # Vimeo addon is actually installed
        vimeoInstalled = False
        try:
            vimeoAddon = xbmcaddon.Addon(id='plugin.video.vimeo')
            if vimeoAddon not in [None, ""]:
                vimeoInstalled = True
        except:
            # We will get an exception if we can not find the Vimeo addon
            vimeoInstalled = False

        if not vimeoInstalled:
            # There is no Vimeo addon installed, so disable this option in settings
            log("VideoExtrasService: Disabling Vimeo support as addon not installed")
            Settings.disableVimeoSearchSupport()


###################################
# Main of the Video Extras Service
###################################
if __name__ == '__main__':
    log("VideoExtrasService: Starting service (version %s)" % ADDON.getAddonInfo('version'))

    # Record if the Context menu should be displayed
    if Settings.showOnContextMenu():
        xbmcgui.Window(10025).setProperty("VideoExtrasShowContextMenu", "true")
    else:
        xbmcgui.Window(10025).clearProperty("VideoExtrasShowContextMenu")

    log("VideoExtrasService: Directory for overlay images is %s" % PROFILE_DIR)

    # This is a bit of a hack, but we want to force the default paths for the
    # images if they are not set.  This way it will point to the directory containing
    # all the overlay images to start with, meaning that it will be the directory
    # shown to the user if they choose to change the icons
    if ADDON.getSetting("useCustomImages") != "true":
        if ADDON.getSetting('overlayImage') in [None, '']:
            skinExtrasOverlay = os_path_join(RES_DIR, "skins")
            skinExtrasOverlay = os_path_join(skinExtrasOverlay, "icons")
            skinExtrasOverlay = os_path_join(skinExtrasOverlay, "overlay1.png")
            ADDON.setSetting('overlayImage', skinExtrasOverlay)
        if ADDON.getSetting('listImage') in [None, '']:
            skinExtrasList = os_path_join(RES_DIR, "skins")
            skinExtrasList = os_path_join(skinExtrasList, "icons")
            skinExtrasList = os_path_join(skinExtrasList, "list1.png")
            ADDON.setSetting('listImage', skinExtrasList)

    # Check the YouTube settings are correct, we will automatically disable the
    # option if the YouTube addon is not installed
    checkYouTubeSettings()

    # Check the Vimeo settings are correct, we will automatically disable the
    # option if the Vimeo addon is not installed
    checkVimeoSettings()

    # Make sure that the service option is enabled
    if Settings.isServiceEnabled():
        try:
            # Construct the service class
            service = VideoExtrasService()

            # Refresh the caches
            service.cacheAllExtras()
            del service
        except:
            log("VideoExtrasService: %s" % traceback.format_exc(), xbmc.LOGERROR)
    else:
        # Service not enabled
        log("VideoExtrasService: Service disabled in settings")
        # Clean any cached extras
        CacheCleanup.removeAllCachedFiles()

    # Now just let the service exit - it has done it's job
