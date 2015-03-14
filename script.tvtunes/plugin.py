# -*- coding: utf-8 -*-
# Reference:
# http://wiki.xbmc.org/index.php?title=Audio/Video_plugin_tutorial
import sys
import os
import re
import urllib
import urlparse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson


__addon__ = xbmcaddon.Addon(id='script.tvtunes')
__icon__ = __addon__.getAddonInfo('icon')
__fanart__ = __addon__.getAddonInfo('fanart')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")


sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join
from settings import os_path_split
from settings import list_dir
from settings import normalize_string
from settings import dir_exists

from themeFetcher import TvTunesFetcher
from themeFinder import ThemeFiles
from screensaver import launchScreensaver


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

        # Get the current state of the filter
        currentSetting = xbmcgui.Window(12003).getProperty("TvTunes_BrowserMissingThemesOnly")
        if currentSetting == "true":
            self.missingThemesOnly = 1
        else:
            self.missingThemesOnly = 0

    # Creates a URL for a directory
    def _build_url(self, query):
        return self.base_url + '?' + urllib.urlencode(query)

    # Display the default list of items in the root menu
    def showRootMenu(self):
        # Movies
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.MOVIES})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32201), iconImage=__icon__)
        li.setProperty("Fanart_Image", __fanart__)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # TV Shows
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.TVSHOWS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32202), iconImage=__icon__)
        li.setProperty("Fanart_Image", __fanart__)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Music Videos
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.MUSICVIDEOS})
        li = xbmcgui.ListItem(__addon__.getLocalizedString(32203), iconImage=__icon__)
        li.setProperty("Fanart_Image", __fanart__)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Add a blank line before the filters
        li = xbmcgui.ListItem("", iconImage=__icon__)
        li.setProperty("Fanart_Image", __fanart__)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url="", listitem=li, isFolder=False)

        # Filter: Show only missing themes
        url = self._build_url({'mode': 'filter', 'filtertype': 'MissingThemesOnly'})
        filterTitle = "  %s" % __addon__.getLocalizedString(32204)
        li = xbmcgui.ListItem(filterTitle, iconImage=__icon__)
        li.setProperty("Fanart_Image", __fanart__)
        li.setInfo('video', {'PlayCount': self.missingThemesOnly})
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        # Action: Retrieve missing themes
        url = self._build_url({'mode': 'action', 'actiontype': 'RetrieveMissingThemes'})
        filterTitle = "  %s" % __addon__.getLocalizedString(32205)
        li = xbmcgui.ListItem(filterTitle, iconImage=__icon__)
        li.setProperty("Fanart_Image", __fanart__)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        # Action: Start Screensaver
        url = self._build_url({'mode': 'screensaver', 'actiontype': 'StartScreensaver'})
        filterTitle = "  %s" % __addon__.getLocalizedString(32208)
        li = xbmcgui.ListItem(filterTitle, iconImage=__icon__)
        li.setProperty("Fanart_Image", __fanart__)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

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
            path = self.getPathForVideoItem(videoItem)

            # Create the list-item for this video
            li = xbmcgui.ListItem(videoItem['title'], iconImage=videoItem['thumbnail'])
            # Remove the default context menu
            li.addContextMenuItems([], replaceItems=True)
            # Set the background image
            if videoItem['fanart'] is not None:
                li.setProperty("Fanart_Image", videoItem['fanart'])
            # If theme already exists flag it using the play count
            # This will normally put a tick on the GUI
            if self._doesThemeExist(path):
                # A theme already exists, see if we are showing only missing themes
                if self.missingThemesOnly == 1:
                    # skip this theme
                    continue

                li.setInfo('video', {'PlayCount': 1})
            # Check the parent directory
            elif Settings.isThemeDirEnabled() and self._doesThemeExist(path, True):
                # The Theme directory is set, there is no theme in there
                # but we have a theme that will play, so flag it
                li.setProperty("ResumeTime", "50")

            if videoItem['originaltitle'] is not None:
                url = self._build_url({'mode': 'findtheme', 'foldername': target, 'path': path.encode("utf-8"), 'title': videoItem['title'].encode("utf-8"), 'originaltitle': videoItem['originaltitle'].encode("utf-8")})
            else:
                url = self._build_url({'mode': 'findtheme', 'foldername': target, 'path': path.encode("utf-8"), 'title': videoItem['title'].encode("utf-8")})
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Do a lookup in the database for the given type of videos
    def getVideos(self, jsonGet, target):
        origTitleRequest = ', "originaltitle"'
        if target == MenuNavigator.MUSICVIDEOS:
            origTitleRequest = ''

        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.%s", "params": {"properties": ["title", "file", "thumbnail", "fanart"%s], "sort": { "method": "title" } }, "id": 1}' % (jsonGet, origTitleRequest))
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        log(json_response)
        Videolist = []
        if ("result" in json_response) and (target in json_response['result']):
            for item in json_response['result'][target]:
                videoItem = {}
                videoItem['title'] = item['title']
                # The file is actually the path for a TV Show, the video file for movies
                videoItem['file'] = item['file']

                if item['thumbnail'] is None:
                    item['thumbnail'] = 'DefaultFolder.png'
                else:
                    videoItem['thumbnail'] = item['thumbnail']
                videoItem['fanart'] = item['fanart']

                if 'originaltitle' in item:
                    videoItem['originaltitle'] = item['originaltitle']
                else:
                    videoItem['originaltitle'] = None

                Videolist.append(videoItem)
        return Videolist

    # Checks if a theme exists in a directory
    def _doesThemeExist(self, directory, checkParent=False):
        log("doesThemeExist: Checking directory: %s" % directory)
        # Check for custom theme directory
        if Settings.isThemeDirEnabled():
            themeDir = os_path_join(directory, Settings.getThemeDirectory())
            # Check if this directory exists
            if not dir_exists(themeDir):
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

        # Check to see if we need to check the parent directory
        if checkParent:
            directory = os_path_split(directory)[0]

        # check if the directory exists before searching
        if dir_exists(directory):
            # Generate the regex
            themeFileRegEx = Settings.getThemeFileRegEx()

            dirs, files = list_dir(directory)
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

    # Fetch a single theme
    def fetchTheme(self, title, path, originaltitle=None):
        # If there is already a theme then start playing it
        self._startPlayingExistingTheme(path)

        if Settings.isThemeDirEnabled() and self._doesThemeExist(path, True):
            # Prompt user if we should move themes in the parent
            # directory into the theme directory
            moveExistingThemes = xbmcgui.Dialog().yesno(__addon__.getLocalizedString(32105), __addon__.getLocalizedString(32206), __addon__.getLocalizedString(32207))

            # Check if we need to move a theme file
            if moveExistingThemes:
                log("fetchAllMissingThemes: Moving theme for %s" % title)
                self._moveToThemeFolder(path)
                # Stop playing any theme that started
                self._stopPlayingTheme()
                # Now reload the screen to reflect the change
                xbmc.executebuiltin("Container.Refresh")
                return

        if originaltitle is not None:
            originaltitle = normalize_string(originaltitle)

        # Perform the fetch
        videoList = []
        normtitle = normalize_string(title)
        videoList.append([normtitle, path, originaltitle])
        TvTunesFetcher(videoList)

        # Stop playing any theme that started
        self._stopPlayingTheme()

        # Now reload the screen to reflect the change
        xbmc.executebuiltin("Container.Refresh")

    def _startPlayingExistingTheme(self, path):
        log("startPlayingExistingTheme: Playing existing theme for %s" % path)
        # Search for the themes
        themeFiles = ThemeFiles(path)
        if themeFiles.hasThemes():
            playlist = themeFiles.getThemePlaylist()
            # Stop playing any existing theme
            self._stopPlayingTheme()
            xbmc.Player().play(playlist)
        else:
            log("No themes found for %s" % path)

    def _stopPlayingTheme(self):
        # Check if a tune is already playing
        if xbmc.Player().isPlayingAudio():
            xbmc.Player().stop()
        while xbmc.Player().isPlayingAudio():
            xbmc.sleep(5)

    # Does a search for all the missing themes
    def fetchAllMissingThemes(self):
        tvShows = self.getVideos('GetTVShows', MenuNavigator.TVSHOWS)
        movies = self.getVideos('GetMovies', MenuNavigator.MOVIES)
        music = self.getVideos('GetMusicVideos', MenuNavigator.MUSICVIDEOS)

        videoList = []

        moveExistingThemes = None

        for videoItem in (tvShows + movies + music):
            # Get the path where the theme should be stored
            path = self.getPathForVideoItem(videoItem)
            # Skip items that already have themes
            if self._doesThemeExist(path):
                continue

            if Settings.isThemeDirEnabled() and self._doesThemeExist(path, True):
                if moveExistingThemes is None:
                    # Prompt user if we should move themes in the parent
                    # directory into the theme directory
                    moveExistingThemes = xbmcgui.Dialog().yesno(__addon__.getLocalizedString(32105), __addon__.getLocalizedString(32206), __addon__.getLocalizedString(32207))

                # Check if we need to move a theme file
                if moveExistingThemes:
                    log("fetchAllMissingThemes: Moving theme for %s" % videoItem['title'])
                    self._moveToThemeFolder(path)
                continue

            normtitle = normalize_string(videoItem['title']).encode("utf-8")
            normOriginalTitle = None
            if videoItem['originaltitle'] is not None:
                normOriginalTitle = normalize_string(videoItem['originaltitle']).encode("utf-8")
            videoList.append([normtitle, path.encode("utf-8"), normOriginalTitle])

        if len(videoList) > 0:
            TvTunesFetcher(videoList)

    # Moves a theme that is not in a theme folder to a theme folder
    def _moveToThemeFolder(self, directory):
        log("moveToThemeFolder: path = %s" % directory)

        # Handle the case where we have a disk image
        if (os_path_split(directory)[1] == 'VIDEO_TS') or (os_path_split(directory)[1] == 'BDMV'):
            directory = os_path_split(directory)[0]

        dirs, files = list_dir(directory)
        for aFile in files:
            m = re.search(Settings.getThemeFileRegEx(directory), aFile, re.IGNORECASE)
            if m:
                srcpath = os_path_join(directory, aFile)
                log("fetchAllMissingThemes: Found match: %s" % srcpath)
                targetpath = os_path_join(directory, Settings.getThemeDirectory())
                # Make sure the theme directory exists
                if not dir_exists(targetpath):
                    try:
                        xbmcvfs.mkdir(targetpath)
                    except:
                        log("fetchAllMissingThemes: Failed to create directory: %s" % targetpath, True, xbmc.LOGERROR)
                        break
                else:
                    log("moveToThemeFolder: directory already exists %s" % targetpath)
                # Add the filename to the path
                targetpath = os_path_join(targetpath, aFile)
                if not xbmcvfs.rename(srcpath, targetpath):
                    log("moveToThemeFolder: Failed to move file from %s to %s" % (srcpath, targetpath))

    # Searches for the path from a video item
    def getPathForVideoItem(self, videoItem):
        path = ""
        # Get the path where the theme should be stored
        if Settings.isCustomPathEnabled():
            path = os_path_join(Settings.getCustomPath(), normalize_string(videoItem['title']))
        else:
            path = videoItem['file']
            # Handle stacked files that have a custom file name format
            if path.startswith("stack://"):
                path = path.replace("stack://", "").split(" , ", 1)[0]
            # Need to remove the filename from the end  as we just want the directory
            fileExt = os.path.splitext(path)[1]
            # If this is a file, then get it's parent directory
            if fileExt is not None and fileExt != "":
                path = os_path_split(path)[0]

        return path


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
    if mode is None:
        log("TvTunesPlugin: Mode is NONE - showing root menu")
        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.showRootMenu()
    elif mode[0] == 'folder':
        log("TvTunesPlugin: Mode is FOLDER")

        # Get the actual folder that was navigated to
        foldername = args.get('foldername', None)

        if (foldername is not None) and (len(foldername) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.showFolder(foldername[0])

    elif mode[0] == 'findtheme':
        log("TvTunesPlugin: Mode is FIND THEME")

        # Get the actual title and path that was navigated to
        title = args.get('title', None)
        path = args.get('path', None)
        originaltitle = args.get('originaltitle', None)

        if originaltitle is not None:
            originaltitle = originaltitle[0]

        # Perform the fetch
        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.fetchTheme(title[0], path[0], originaltitle)

    elif mode[0] == 'filter':
        log("TvTunesPlugin: Mode is FILTER")

        # Only one filter at the moment

        # Get the current state of the filter
        currentSetting = xbmcgui.Window(12003).getProperty("TvTunes_BrowserMissingThemesOnly")
        if currentSetting == "true":
            xbmcgui.Window(12003).clearProperty("TvTunes_BrowserMissingThemesOnly")
        else:
            xbmcgui.Window(12003).setProperty("TvTunes_BrowserMissingThemesOnly", "true")

        # Now reload the screen to reflect the change
        xbmc.executebuiltin("Container.Refresh")

    elif mode[0] == 'action':
        log("TvTunesPlugin: Mode is ACTION")

        # Only one action at the moment
        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.fetchAllMissingThemes()

    elif mode[0] == 'screensaver':
        log("TvTunesPlugin: Mode is Screensaver")
        # Launch the screensaver
        launchScreensaver()
