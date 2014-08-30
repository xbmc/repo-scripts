# -*- coding: utf-8 -*-
import os
import sys
import re
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs


__addon__ = xbmcaddon.Addon(id='script.tvtunes')
__addonid__ = __addon__.getAddonInfo('id')
__language__ = __addon__.getLocalizedString
__icon__ = __addon__.getAddonInfo('icon')
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

from themeFetcher import TvTunesFetcher


###############################################################
# Class to make it easier to see which screen is being checked
###############################################################
class WindowShowing():

    @staticmethod
    def isMovieInformation():
        return xbmc.getCondVisibility("Window.IsVisible(movieinformation)")

    @staticmethod
    def isTv():
        if xbmc.getCondVisibility("Container.Content(tvshows)"):
            return True
        if xbmc.getCondVisibility("Container.Content(Seasons)"):
            return True
        if xbmc.getCondVisibility("Container.Content(Episodes)"):
            return True

        folderPathId = "videodb://2/2/"
        # The ID for the TV Show Title changed in Gotham
        if Settings.getXbmcMajorVersion() > 12:
            folderPathId = "videodb://tvshows/titles/"
        if xbmc.getInfoLabel("container.folderpath") == folderPathId:
            return True  # TvShowTitles

        return False


#################################
# Core TvTunes Scraper class
#################################
class TvTunesScraper:
    def __init__(self):
        # Get the name of the theme we are looking for
        videoItem = self.getSoloVideo()

        # Check if multiple themes are suported
        if not Settings.isMultiThemesSupported():
            # Check if a theme already exists
            if self._doesThemeExist(videoItem[1]):
                # Prompt the user to see if we should overwrite the theme
                if not xbmcgui.Dialog().yesno(__language__(32103), __language__(32104)):
                    # No not want to overwrite, so quit
                    log("TvTunesScraper: %s already exists" % (os_path_join(videoItem[1], "theme.*")))
                    return

        # Perform the fetch
        videoList = []
        videoList.append(videoItem)
        TvTunesFetcher(videoList)

    # Handles the case where there is just a single theme to look for
    # and it has been invoked from the given video location
    def getSoloVideo(self):
        log("getSoloVideo: solo mode")

        # Used to pass the name and path via the command line
        # This caused problems with non ascii characters, so now
        # we just look at the screen details
        # The solo option is only available from the info screen
        # Looking at the TV Show information page
        if WindowShowing.isTv():
            videoName = xbmc.getInfoLabel("ListItem.TVShowTitle")
            log("getSoloVideo: TV Show detected %s" % videoName)
        else:
            videoName = xbmc.getInfoLabel("ListItem.Title")
            log("getSoloVideo: Movie detected %s" % videoName)

        # Now get the video path
        videoPath = None
        if WindowShowing.isMovieInformation() and WindowShowing.isTv():
            videoPath = xbmc.getInfoLabel("ListItem.FilenameAndPath")
        if videoPath is None or videoPath == "":
            videoPath = xbmc.getInfoLabel("ListItem.Path")
        log("getSoloVideo: Video Path %s" % videoPath)

        # Check if there is an "Original Title Defines
        originalTitle = xbmc.getInfoLabel("ListItem.OriginalTitle")
        if (originalTitle is not None) and (originalTitle != ""):
            originalTitle = normalize_string(originalTitle)
        else:
            originalTitle = None

        normVideoName = normalize_string(videoName)
        log("getSoloVideo: videoName = %s" % normVideoName)

        # If the main title and the original title are the same
        # Then no need to use the original title
        if (originalTitle == normVideoName):
            originalTitle = None

        if Settings.isCustomPathEnabled():
            videoPath = os_path_join(Settings.getCustomPath(), normVideoName)
        else:
            log("getSoloVideo: Solo dir = %s" % videoPath)
            # Need to clean the path if we are going to store the file there
            # Handle stacked files that have a custom file name format
            if videoPath.startswith("stack://"):
                videoPath = videoPath.replace("stack://", "").split(" , ", 1)[0]
            # Need to remove the filename from the end  as we just want the directory
            # if not os.path.isdir(videoPath):
            fileExt = os.path.splitext(videoPath)[1]
            # If this is a file, then get it's parent directory
            if fileExt is not None and fileExt != "":
                videoPath = os.path.dirname(videoPath)

        log("getSoloVideo: videoPath = %s" % videoPath)

#         try:
#             decodedPath = videoPath.decode("utf-8")
#             videoPath = decodedPath
#         except:
#             pass

        return [normVideoName, videoPath, originalTitle]

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

            dirs, files = list_dir(directory)
            for aFile in files:
                m = re.search(themeFileRegEx, aFile, re.IGNORECASE)
                if m:
                    log("doesThemeExist: Found match: " + aFile)
                    return True
        return False


if __name__ == "__main__":
    TvTunesScraper()
