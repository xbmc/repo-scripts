# -*- coding: utf-8 -*-
# Reference:
# http://wiki.xbmc.org/index.php?title=Audio/Video_plugin_tutorial
import sys
import os
import traceback
import re
import urllib
import urlparse
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson


__addon__    = xbmcaddon.Addon(id='script.tvtunes')
__icon__     = __addon__.getAddonInfo('icon')
__fanart__   = __addon__.getAddonInfo('fanart')
__cwd__      = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath( os.path.join( __cwd__, 'resources' ).encode("utf-8") ).decode("utf-8")
__lib__      = xbmc.translatePath( os.path.join( __resource__, 'lib' ).encode("utf-8") ).decode("utf-8")


sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join
from settings import os_path_split
from settings import list_dir
from settings import normalize_string

from fetcher import TvTunesFetcher


###################################################################
# Class to handle the navigation information for the plugin
###################################################################
class MenuNavigator():
    MOVIES = 'movies'
    TVSHOWS = 'tvshows'
    MUSICVIDEOS = 'musicvideos'

    def __init__(self, base_url, addon_handle):
        self.base_url = base_url
        self.addon_handle = addon_handle

    # Creates a URL for a directory
    def _build_url(self, query):
        return self.base_url + '?' + urllib.urlencode(query)

    # Display the default list of items in the root menu
    def showRootMenu(self):
        # Movies
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.MOVIES})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32201), iconImage=__icon__)
        li.setProperty( "Fanart_Image", __fanart__ )
        li.addContextMenuItems( [], replaceItems=True )
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # TV Shows
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.TVSHOWS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32202), iconImage=__icon__)
        li.setProperty( "Fanart_Image", __fanart__ )
        li.addContextMenuItems( [], replaceItems=True )
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Music Videos
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.MUSICVIDEOS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32203), iconImage=__icon__)
        li.setProperty( "Fanart_Image", __fanart__ )
        li.addContextMenuItems( [], replaceItems=True )
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)
     
        xbmcplugin.endOfDirectory(self.addon_handle)

    # Show the list of videos in a given set
    def showFolder(self, foldername):
        # Check for the special case of manually defined folders
        if foldername == MenuNavigator.TVSHOWS:
            self.setVideoList('GetTVShows', MenuNavigator.TVSHOWS)
        elif foldername == MenuNavigator.MOVIES:
            self.setVideoList('GetMovies', MenuNavigator.MOVIES)
        elif foldername == MenuNavigator.MUSICVIDEOS:
            self.setVideoList('GetMusicVideos', MenuNavigator.MUSICVIDEOS)


    # Produce the list of videos and flag which ones have themes
    def setVideoList(self, jsonGet, target):
        videoItems = self.getVideos(jsonGet, target)
        
        for videoItem in videoItems:
            # Get the path where the theme should be stored
            if Settings.isCustomPathEnabled():
                path = os_path_join(Settings.getCustomPath(), normalize_string(videoItem['title']))
            else:
                path = videoItem['file']
                # Handle stacked files that have a custom file name format
                if path.startswith("stack://"):
                    path = path.replace("stack://", "").split(" , ", 1)[0]
                # Need to remove the filename from the end  as we just want the directory
                fileExt = os.path.splitext( path )[1]
                # If this is a file, then get it's parent directory
                if fileExt != None and fileExt != "":
                    path = os.path.dirname( path )

            # Create the list-item for this video            
            li = xbmcgui.ListItem(videoItem['title'], iconImage=videoItem['thumbnail'])
            # Remove the default context menu
            li.addContextMenuItems( [], replaceItems=True )
            # Set the background image
            if videoItem['fanart'] != None:
                li.setProperty( "Fanart_Image", videoItem['fanart'] )
            # If theme already exists flag it using the play count
            # This will normally put a tick on the GUI
            if self._doesThemeExist(path):
                li.setInfo('video', { 'PlayCount': 1 })
            url = self._build_url({'mode': 'findtheme', 'foldername': target, 'path': path.encode("utf-8"), 'title': videoItem['title'].encode("utf-8")})
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        xbmcplugin.endOfDirectory(self.addon_handle)


    # Do a lookup in the database for the given type of videos
    def getVideos(self, jsonGet, target):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.%s", "params": {"properties": ["title", "file", "thumbnail", "fanart"], "sort": { "method": "title" } }, "id": 1}' % jsonGet)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        log( json_response )
        Videolist = []
        if "result" in json_query and json_response['result'].has_key(target):
            for item in json_response['result'][target]:
                videoItem = {}
                videoItem['title'] = item['title']
                # The file is actually the path for a TV Show, the video file for movies
                videoItem['file'] = item['file']
                
                if item['thumbnail'] == None:
                    item['thumbnail'] = 'DefaultFolder.png'
                else:
                    videoItem['thumbnail'] = item['thumbnail']
                videoItem['fanart'] = item['fanart']

                Videolist.append(videoItem)
        return Videolist

    # Checks if a theme exists in a directory
    def _doesThemeExist(self, directory):
        log("doesThemeExist: Checking directory: %s" % directory)
        # Check for custom theme directory
        if Settings.isThemeDirEnabled():
            themeDir = os_path_join(directory, Settings.getThemeDirectory())
            # Check if this directory exists
            if not xbmcvfs.exists(themeDir):
                workingPath = directory
                # If the path currently ends in the directory separator
                # then we need to clear an extra one
                if (workingPath[-1] == os.sep) or (workingPath[-1] == os.altsep):
                    workingPath = workingPath[:-1]
                # If not check to see if we have a DVD VOB
                if (os_path_split(workingPath)[1] == 'VIDEO_TS') or (os_path_split(workingPath)[1] == 'BDMV'):
                    # Check the parent of the DVD Dir
                    themeDir = os_path_split(workingPath)[0]
                    themeDir = os_path_join(themeDir, Settings.getThemeDirectory())
            directory = themeDir

        # check if the directory exists before searching
        if xbmcvfs.exists(directory):
            # Generate the regex
            themeFileRegEx = Settings.getThemeFileRegEx()

            dirs, files = list_dir( directory )
            for aFile in files:
                m = re.search(themeFileRegEx, aFile, re.IGNORECASE)
                if m:
                    log("doesThemeExist: Found match: " + aFile)
                    return True
        # Check if an NFO file exists
        nfoFileName = os_path_join(directory, "tvtunes.nfo")
        if xbmcvfs.exists(nfoFileName):
            log("doesThemeExist: Found match: " + nfoFileName)
            return True
        return False



################################
# Main of the TvTunes Plugin
################################
if __name__ == '__main__':
    # Get all the arguments
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    args = urlparse.parse_qs(sys.argv[2][1:])

    # Get the current mode from the arguments, if none set, then use None
    mode = args.get('mode', None)
    
    log("TvTunesPlugin: Called with addon_handle = %d" % addon_handle)
    
    # If None, then at the root
    if mode == None:
        log("TvTunesPlugin: Mode is NONE - showing root menu")
        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.showRootMenu()
    elif mode[0] == 'folder':
        log("TvTunesPlugin: Mode is FOLDER")

        # Get the actual folder that was navigated to
        foldername = args.get('foldername', None)

        if (foldername != None) and (len(foldername) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.showFolder(foldername[0])

    elif mode[0] == 'findtheme':
        log("TvTunesPlugin: Mode is FIND THEME")

        # Get the actual title and path that was navigated to
        title = args.get('title', None)
        path = args.get('path', None)
        
        # Perform the fetch
        videoList = []
        normtitle = normalize_string(title[0])
        videoList.append([normtitle, path[0], normtitle])
        TvTunesFetcher(videoList)


