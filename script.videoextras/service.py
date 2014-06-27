# -*- coding: utf-8 -*-
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
import sys
import os
import traceback
#Modules XBMC
import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon

# Add JSON support for queries
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson


__addon__     = xbmcaddon.Addon(id='script.videoextras')
__addonid__   = __addon__.getAddonInfo('id')
__version__   = __addon__.getAddonInfo('version')
__cwd__       = __addon__.getAddonInfo('path').decode("utf-8")
__profile__   = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__resource__  = xbmc.translatePath( os.path.join( __cwd__, 'resources' ).encode("utf-8") ).decode("utf-8")
__lib__  = xbmc.translatePath( os.path.join( __resource__, 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join

# Load the core Video Extras classes
from core import VideoExtrasBase

# Load the cache cleaner
from CacheCleanup import CacheCleanup

#####################################
# Main class for the Extras Service
#####################################
class VideoExtrasService():
    LIST_TAG = "_list"
    
    def __init__(self):
        # special://skin - This path points to the currently active skin's root directory. 
        skinExtrasOverlayBase = xbmc.translatePath( "special://skin" ).decode("utf-8")
        skinExtrasOverlayBase = os_path_join(skinExtrasOverlayBase, "media")
        self.skinExtrasOverlay = os_path_join(skinExtrasOverlayBase, "videoextras_overlay.png")
        self.skinExtrasOverlayList = os_path_join(skinExtrasOverlayBase, "videoextras_overlay" + VideoExtrasService.LIST_TAG + ".png")

        log("VideoExtrasService: Looking for image overlay file: %s" % self.skinExtrasOverlay)

        if not xbmcvfs.exists(self.skinExtrasOverlay):
            log("VideoExtrasService: No custom image, using default")
            # Add default image setting to skinExtrasOverlay
            self.skinExtrasOverlay = os_path_join(__resource__, "skins")
            self.skinExtrasOverlay = os_path_join(self.skinExtrasOverlay, "Default")
            self.skinExtrasOverlay = os_path_join(self.skinExtrasOverlay, "media")
            self.skinExtrasOverlay = os_path_join(self.skinExtrasOverlay, "overlay.png")

        log("VideoExtrasService: Looking for list image overlay file: %s" % self.skinExtrasOverlayList)

        if not xbmcvfs.exists(self.skinExtrasOverlayList):
            log("VideoExtrasService: No custom wide image, using default")
            # Add default image setting to skinExtrasOverlay
            self.skinExtrasOverlayList = os_path_join(__resource__, "skins")
            self.skinExtrasOverlayList = os_path_join(self.skinExtrasOverlayList, "Default")
            self.skinExtrasOverlayList = os_path_join(self.skinExtrasOverlayList, "media")
            self.skinExtrasOverlayList = os_path_join(self.skinExtrasOverlayList, "overlay" + VideoExtrasService.LIST_TAG + ".png")

        self.forceOverlayOverwrite = False
        
        # We now know the file that we are going to use for the overlay
        # Check to see if this is different from the last overlay file used
        filename = os_path_join(__profile__, "overlay_image_used.txt")
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
            log("VideoExtrasService: Failed to write: %s" % filename)
            log("VideoExtrasService: %s" % traceback.format_exc())


    # Regenerates all of the cached extras
    def cacheAllExtras(self):
        self.createExtrasCache('GetMovies', Settings.MOVIES, 'movieid')
        self.createExtrasCache('GetTVShows', Settings.TVSHOWS, 'tvshowid')
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
    
        if "result" in json_query and json_query['result'].has_key(target):
            # Get the list of movies paths from the movie list returned
            items = json_query['result'][target]
            for item in items:
                # Check to see if exit has been called, if so stop
                if xbmc.getCondVisibility("Window.IsVisible(shutdownmenu)") or xbmc.abortRequested:
                    sys.exit()
                
                log("VideoExtrasService: %s detected: %s = %s" % (target, item['title'], item['file']))
                videoExtras = VideoExtrasBase(item['file'], target)
                # Only checking for the existence of extras - no need for DB or default Fanart
                firstExtraFile = videoExtras.findExtras(True)
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
        rootPath = os_path_join(__profile__, target)
        if not xbmcvfs.exists(rootPath):
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
            log("VideoExtrasService: Failed to create file: %s" % targetFile)
            log("VideoExtrasService: %s" % traceback.format_exc())

    # Removes an overlay
    def _removeOverlayFile(self, target, dbid, postfix=''):
        # Generate the name of the file that the overlay will be removed from
        targetFile = self._createTargetPath(target, dbid, postfix)

        if xbmcvfs.exists(targetFile):
            try:
                # Now the path exists, need to copy the file over to it, giving it the name of the DBID
                xbmcvfs.delete(targetFile)
            except:
                log("VideoExtrasService: Failed to delete file: %s" % targetFile)
                log("VideoExtrasService: %s" % traceback.format_exc())


###################################
# Main of the Video Extras Service
###################################
if __name__ == '__main__':
    log("VideoExtrasService: Starting service (version %s)" % __version__)

    log("VideoExtrasService: Directory for overlay images is %s" % __profile__)

    # Make sure that the service option is enabled    
    if Settings.isServiceEnabled():
        try:
            # Construct the service class
            service = VideoExtrasService()
            
            # Refresh the caches
            service.cacheAllExtras()

        except:
            log("VideoExtrasService: %s" % traceback.format_exc(), xbmc.LOGERROR)
    else:
        # Service not enabled
        log("VideoExtrasService: Service disabled in settings")
        # Clean any cached extras
        CacheCleanup.removeAllCachedFiles()
    
    # Now just let the service exit - it has done it's job

