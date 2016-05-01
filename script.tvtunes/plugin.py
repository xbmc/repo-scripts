# -*- coding: utf-8 -*-
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

# Import the common settings
from resources.lib.settings import Settings
from resources.lib.settings import log
from resources.lib.settings import os_path_join
from resources.lib.settings import os_path_split
from resources.lib.settings import list_dir
from resources.lib.settings import normalize_string
from resources.lib.settings import dir_exists
from resources.lib.themeFetcher import TvTunesFetcher
from resources.lib.themeFinder import ThemeFiles
from resources.lib.screensaver import launchScreensaver

ADDON = xbmcaddon.Addon(id='script.tvtunes')
ICON = ADDON.getAddonInfo('icon')
FANART = ADDON.getAddonInfo('fanart')


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
        li = xbmcgui.ListItem(ADDON.getLocalizedString(32201), iconImage=ICON)
        li.setProperty("Fanart_Image", FANART)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # TV Shows
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.TVSHOWS})
        li = xbmcgui.ListItem(ADDON.getLocalizedString(32202), iconImage=ICON)
        li.setProperty("Fanart_Image", FANART)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Music Videos
        url = self._build_url({'mode': 'folder', 'foldername': MenuNavigator.MUSICVIDEOS})
        li = xbmcgui.ListItem(ADDON.getLocalizedString(32203), iconImage=ICON)
        li.setProperty("Fanart_Image", FANART)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Add a blank line before the filters
        li = xbmcgui.ListItem("", iconImage=ICON)
        li.setProperty("Fanart_Image", FANART)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url="", listitem=li, isFolder=False)

        # Filter: Show only missing themes
        url = self._build_url({'mode': 'filter', 'filtertype': 'MissingThemesOnly'})
        filterTitle = "  %s" % ADDON.getLocalizedString(32204)
        li = xbmcgui.ListItem(filterTitle, iconImage=ICON)
        li.setProperty("Fanart_Image", FANART)
        li.setInfo('video', {'PlayCount': self.missingThemesOnly})
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        # Action: Retrieve missing themes
        url = self._build_url({'mode': 'action', 'actiontype': 'RetrieveMissingAudioThemes'})
        filterTitle = "  %s" % ADDON.getLocalizedString(32205)
        li = xbmcgui.ListItem(filterTitle, iconImage=ICON)
        li.setProperty("Fanart_Image", FANART)
        li.addContextMenuItems([], replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        # Action: Retrieve missing themes
        # Add the moment only the Theme Library supports videos
        if Settings.getSearchEngine() in [Settings.ALL_ENGINES, Settings.THEMELIBRARY]:
            url = self._build_url({'mode': 'action', 'actiontype': 'RetrieveMissingVideoThemes'})
            filterTitle = "  %s" % ADDON.getLocalizedString(32209)
            li = xbmcgui.ListItem(filterTitle, iconImage=ICON)
            li.setProperty("Fanart_Image", FANART)
            li.addContextMenuItems([], replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        # Action: Start Screensaver
        url = self._build_url({'mode': 'screensaver', 'actiontype': 'StartScreensaver'})
        filterTitle = "  %s" % ADDON.getLocalizedString(32208)
        li = xbmcgui.ListItem(filterTitle, iconImage=ICON)
        li.setProperty("Fanart_Image", FANART)
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
                url = self._build_url({'mode': 'findtheme', 'foldername': target, 'path': path.encode("utf-8"), 'title': videoItem['title'].encode("utf-8"), 'isTvShow': videoItem['isTvShow'], 'year': videoItem['year'], 'imdb': videoItem['imdb'], 'originaltitle': videoItem['originaltitle'].encode("utf-8")})
            else:
                url = self._build_url({'mode': 'findtheme', 'foldername': target, 'path': path.encode("utf-8"), 'title': videoItem['title'].encode("utf-8"), 'isTvShow': videoItem['isTvShow'], 'year': videoItem['year'], 'imdb': videoItem['imdb']})
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Do a lookup in the database for the given type of videos
    def getVideos(self, jsonGet, target):
        origTitleRequest = ', "imdbnumber", "originaltitle"'
        if target == MenuNavigator.MUSICVIDEOS:
            origTitleRequest = ''

        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.%s", "params": {"properties": ["title", "file", "thumbnail", "fanart", "year"%s], "sort": { "method": "title" } }, "id": 1}' % (jsonGet, origTitleRequest))
#        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.%s", "params": {"properties": ["title", "file", "thumbnail", "fanart", "imdbnumber", "year"%s], "sort": { "method": "title" } }, "id": 1}' % (jsonGet, origTitleRequest))
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
                videoItem['year'] = item['year']

                videoItem['isTvShow'] = False
                if target == MenuNavigator.TVSHOWS:
                    videoItem['isTvShow'] = True

                if item['thumbnail'] is None:
                    item['thumbnail'] = 'DefaultFolder.png'
                else:
                    videoItem['thumbnail'] = item['thumbnail']
                videoItem['fanart'] = item['fanart']

                if 'originaltitle' in item:
                    videoItem['originaltitle'] = item['originaltitle']
                else:
                    videoItem['originaltitle'] = None

                if 'imdbnumber' in item:
                    videoItem['imdb'] = item['imdbnumber']
                else:
                    videoItem['imdb'] = None

                Videolist.append(videoItem)
        return Videolist

    # Checks if a theme exists in a directory
    def _doesThemeExist(self, directory, checkParent=False, incAudioThemes=True, incVideoThemes=True):
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
            audioOnly = False
            videoOnly = False
            if not incAudioThemes:
                videoOnly = True
            if not incVideoThemes:
                audioOnly = True

            themeFileRegEx = Settings.getThemeFileRegEx(audioOnly=audioOnly, videoOnly=videoOnly)

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
    def fetchTheme(self, title, path, originaltitle=None, isTvShow=None, year=None, imdb=None):
        # If there is already a theme then start playing it
        self._startPlayingExistingTheme(path)

        if Settings.isThemeDirEnabled() and self._doesThemeExist(path, True):
            # Prompt user if we should move themes in the parent
            # directory into the theme directory
            moveExistingThemes = xbmcgui.Dialog().yesno(ADDON.getLocalizedString(32105), ADDON.getLocalizedString(32206), ADDON.getLocalizedString(32207))

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
        videoItem = {'title': normtitle, 'path': path, 'originalTitle': originaltitle, 'isTvShow': isTvShow, 'year': year, 'imdb': imdb}
        videoList.append(videoItem)
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
        del themeFiles

    def _stopPlayingTheme(self):
        # Check if a tune is already playing
        if xbmc.Player().isPlayingAudio():
            xbmc.Player().stop()
        while xbmc.Player().isPlayingAudio():
            xbmc.sleep(5)

    # Does a search for all the missing themes
    def fetchMissingThemes(self, incAudioThemes=True, incVideoThemes=False):
        # Prompt the user to see if they want all the themes or just some
        # of them
        displayList = []
        displayList.append(ADDON.getLocalizedString(32210))
        displayList.append(ADDON.getLocalizedString(32211))
        displayList.append(ADDON.getLocalizedString(32212))
        displayList.append(ADDON.getLocalizedString(32213))

        # Show the list to the user
        select = xbmcgui.Dialog().select(ADDON.getLocalizedString(32105), displayList)
        if select < 0:
            log("fetchMissingThemes: Cancelled by user")
            return

        # It could take a little while to get the videos so show the busy dialog
        xbmc.executebuiltin("ActivateWindow(busydialog)")

        tvShows = []
        if (select == 0) or (select == 1):
            log("fetchMissingThemes: Checking TV Shows")
            tvShows = self.getVideos('GetTVShows', MenuNavigator.TVSHOWS)
        movies = []
        if (select == 0) or (select == 2):
            log("fetchMissingThemes: Checking Movies")
            movies = self.getVideos('GetMovies', MenuNavigator.MOVIES)
        music = []
        if (select == 0) or (select == 3):
            log("fetchMissingThemes: Checking Music Videos")
            music = self.getVideos('GetMusicVideos', MenuNavigator.MUSICVIDEOS)

        videoList = []

        moveExistingThemes = None

        for videoItem in (tvShows + movies + music):
            # Get the path where the theme should be stored
            path = self.getPathForVideoItem(videoItem)
            # Skip items that already have themes
            if self._doesThemeExist(path, False, incAudioThemes, incVideoThemes):
                continue

            if Settings.isThemeDirEnabled() and self._doesThemeExist(path, True, incAudioThemes, incVideoThemes):
                if moveExistingThemes is None:
                    xbmc.executebuiltin("Dialog.Close(busydialog)")
                    # Prompt user if we should move themes in the parent
                    # directory into the theme directory
                    moveExistingThemes = xbmcgui.Dialog().yesno(ADDON.getLocalizedString(32105), ADDON.getLocalizedString(32206), ADDON.getLocalizedString(32207))
                    xbmc.executebuiltin("ActivateWindow(busydialog)")

                # Check if we need to move a theme file
                if moveExistingThemes:
                    log("fetchAllMissingThemes: Moving theme for %s" % videoItem['title'])
                    self._moveToThemeFolder(path)
                continue

            normtitle = normalize_string(videoItem['title']).encode("utf-8")
            normOriginalTitle = None
            if videoItem['originaltitle'] is not None:
                normOriginalTitle = normalize_string(videoItem['originaltitle']).encode("utf-8")

            videoItem = {'title': normtitle, 'path': path.encode("utf-8"), 'originalTitle': normOriginalTitle, 'isTvShow': videoItem['isTvShow'], 'year': videoItem['year'], 'imdb': videoItem['imdb']}
            videoList.append(videoItem)

        xbmc.executebuiltin("Dialog.Close(busydialog)")

        if len(videoList) > 0:
            fetcher = TvTunesFetcher(videoList, incAudioThemes, incVideoThemes)
            del fetcher

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

    # Record what the plugin deals with, files in our case
    xbmcplugin.setContent(addon_handle, 'files')

    # Get the current mode from the arguments, if none set, then use None
    mode = args.get('mode', None)

    log("TvTunesPlugin: Called with addon_handle = %d" % addon_handle)

    # If None, then at the root
    if mode is None:
        log("TvTunesPlugin: Mode is NONE - showing root menu")
        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.showRootMenu()
        del menuNav

    elif mode[0] == 'folder':
        log("TvTunesPlugin: Mode is FOLDER")

        # Get the actual folder that was navigated to
        foldername = args.get('foldername', None)

        if (foldername is not None) and (len(foldername) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.showFolder(foldername[0])
            del menuNav

    elif mode[0] == 'findtheme':
        log("TvTunesPlugin: Mode is FIND THEME")

        # Get the actual title and path that was navigated to
        title = args.get('title', None)
        path = args.get('path', None)
        originaltitle = args.get('originaltitle', None)
        isTvShow = args.get('isTvShow', False)
        year = args.get('year', None)
        imdb = args.get('imdb', None)

        if originaltitle is not None:
            originaltitle = originaltitle[0]
        if isTvShow is not None:
            if isTvShow[0] in [False, 'False']:
                isTvShow = False
            else:
                isTvShow = True
        if year is not None:
            year = year[0]
        if imdb is not None:
            imdb = imdb[0]

        # Perform the fetch
        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.fetchTheme(title[0], path[0], originaltitle, isTvShow, year, imdb)
        del menuNav

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

        incAudio = False
        incVideo = False

        actionType = args.get('actiontype', None)
        if actionType is not None:
            if actionType[0] in ['RetrieveMissingAudioThemes']:
                incAudio = True
            if actionType[0] in ['RetrieveMissingVideoThemes']:
                incVideo = True

        # Only one action at the moment
        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.fetchMissingThemes(incAudio, incVideo)
        del menuNav

    elif mode[0] == 'screensaver':
        log("TvTunesPlugin: Mode is Screensaver")
        # Launch the screensaver
        launchScreensaver()
