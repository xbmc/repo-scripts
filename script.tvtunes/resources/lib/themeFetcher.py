# -*- coding: utf-8 -*-
import urllib
import os
import re
import unicodedata
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import traceback
import math

import urllib2
from BeautifulSoup import BeautifulSoup
import HTMLParser


__addon__ = xbmcaddon.Addon(id='script.tvtunes')
__addonid__ = __addon__.getAddonInfo('id')
__language__ = __addon__.getLocalizedString
__icon__ = __addon__.getAddonInfo('icon')

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join
from settings import os_path_split
from settings import dir_exists

from library import ThemeLibrary
import soundcloud

try:
    from metahandler import metahandlers
except Exception:
    log("ThemeLibrary: metahandler Import Failed %s" % traceback.format_exc(), xbmc.LOGERROR)


#################################
# Core TvTunes Scraper class
#################################
class TvTunesFetcher():
    def __init__(self, videoList, incAudioThemes=True, incVideoThemes=True):
        self.includeAudio = incAudioThemes
        self.includeVideo = incVideoThemes

        # Set up the addon directories if they do not already exist
        if not dir_exists(xbmc.translatePath('special://profile/addon_data/%s' % __addonid__).decode("utf-8")):
            xbmcvfs.mkdir(xbmc.translatePath('special://profile/addon_data/%s' % __addonid__).decode("utf-8"))
        if not dir_exists(xbmc.translatePath('special://profile/addon_data/%s/temp' % __addonid__).decode("utf-8")):
            xbmcvfs.mkdir(xbmc.translatePath('special://profile/addon_data/%s/temp' % __addonid__).decode("utf-8"))

        # Get the currently selected search engine
        self.searchEngine = Settings.getSearchEngine()

        if self.searchEngine == Settings.PROMPT_ENGINE:
            isManualSearch, engineSelected = self.promptForSearchEngine(False)
            # Exit if no engine was selected
            if engineSelected is None:
                return

        # Now we have the list of programs to search for, perform the scan
        # The video list is in the format [videoName, Path, DisplayName]
        self.scan(videoList)

    # Search for themes
    def scan(self, videoList):
        total = len(videoList)

        if total > 1:
            multiVideoProgressDialog = xbmcgui.DialogProgress()
            multiVideoProgressDialog.create(__language__(32105), __language__(32106))

            count = 0
            for show in videoList:
                count = count + 1
                title = show.get('title', "")
                multiVideoProgressDialog.update((count * 100) / total, ("%s %s" % (__language__(32107), title.decode("utf-8"))), ' ')
                if multiVideoProgressDialog.iscanceled():
                    multiVideoProgressDialog.close()
                    xbmcgui.Dialog().ok(__language__(32108), __language__(32109))
                    break

                if not self.scanSingleItem(show, showProgressDialog=False):
                    # Give the user an option to stop searching the remaining themes
                    # as they did not select one for this show, but only prompt
                    # if there are more to be processed
                    if (count < total) and Settings.isAutoDownloadPromptUser():
                        if not xbmcgui.Dialog().yesno(__language__(32105), __language__(32119)):
                            break

            multiVideoProgressDialog.close()
        elif total == 1:
            # Just a single item - it will use it's own progress dialog
            self.scanSingleItem(videoList[0])

    # Search for a single theme
    def scanSingleItem(self, show, showProgressDialog=True):
        title = show.get('title', None)
        originalTitle = show.get('originalTitle', None)
        isTvShow = show.get('isTvShow', None)
        year = show.get('year', None)
        imdb = show.get('imdb', None)

        theme_list = self.searchThemeList(title, originalTitle, isTvShow, year, imdb, manual=False, showProgressDialog=showProgressDialog)
        selectedTheme = None

        # Check the case where we have an automatic download enabled
        if (len(theme_list) == 1) and (Settings.getAutoDownloadSetting() == Settings.AUTO_DOWNLOAD_SINGLE_ITEM):
            selectedTheme = theme_list[0]
        elif len(theme_list) > 0:
            if Settings.getAutoDownloadSetting() == Settings.AUTO_DOWNLOAD_PRIORITY_1:
                # The themes are already in priority order, so see if the first theme is
                # of the correct priority
                if theme_list[0].getPriority() < 2:
                    selectedTheme = theme_list[0]
            elif Settings.getAutoDownloadSetting() == Settings.AUTO_DOWNLOAD_PRIORITY_1_OR_2:
                if theme_list[0].getPriority() < 3:
                    selectedTheme = theme_list[0]

        # If there is still no theme selected, prompt the user
        if (selectedTheme is None) and Settings.isAutoDownloadPromptUser():
            # Prompt the user to select which theme they want
            selectedTheme = self.getUserChoice(theme_list, title, originalTitle, isTvShow, year, imdb)

        retVal = False
        if selectedTheme:
            retVal = True
            savePath = show.get('path', None)
            self.download(selectedTheme, savePath)

        return retVal

    # Download the theme
    def download(self, themeDetails, path):
        theme_url = themeDetails.getMediaURL()
        log("download: %s" % theme_url)

        fileType = ".mp3"
        # For video files check what type they are
        if Settings.isVideoFile(theme_url):
            fileExt = os.path.splitext(theme_url)[1]
            # If this is a file, then get it's parent directory
            # Also limit file extensions to a maximum of 4 characters
            if fileExt is not None and fileExt != "" and len(fileExt) < 5:
                fileType = fileExt

        # Check for custom theme directory
        if Settings.isThemeDirEnabled():
            themeDir = os_path_join(path, Settings.getThemeDirectory())
            if not dir_exists(themeDir):
                workingPath = path
                # If the path currently ends in the directory separator
                # then we need to clear an extra one
                if (workingPath[-1] == os.sep) or (workingPath[-1] == os.altsep):
                    workingPath = workingPath[:-1]
                # If not check to see if we have a DVD VOB
                if (os_path_split(workingPath)[1] == 'VIDEO_TS') or (os_path_split(workingPath)[1] == 'BDMV'):
                    log("DVD image detected")
                    # Check the parent of the DVD Dir
                    themeDir = os_path_split(workingPath)[0]
                    themeDir = os_path_join(themeDir, Settings.getThemeDirectory())
            path = themeDir

        log("target directory: %s" % path)

        theme_file = self.getNextThemeFileName(path, fileType)
        tmpdestination = xbmc.translatePath('special://profile/addon_data/%s/temp/%s' % (__addonid__, theme_file)).decode("utf-8")
        destination = os_path_join(path, theme_file)

        # Create a progress dialog for the  download
        downloadProgressDialog = xbmcgui.DialogProgress()
        downloadProgressDialog.create(__language__(32105), __language__(32106))

        try:
            def _report_hook(count, blocksize, totalsize):
                percent = int(float(count * blocksize * 100) / totalsize)
                downloadProgressDialog.update(percent, __language__(32110) + ' ' + theme_url, __language__(32111) + ' ' + destination)
            if not dir_exists(path):
                try:
                    xbmcvfs.mkdir(path)
                except:
                    log("download: problem with path: %s" % destination, True, xbmc.LOGERROR)
            fp, h = urllib.urlretrieve(theme_url, tmpdestination, _report_hook)
            log(h)
            copy = xbmcvfs.copy(tmpdestination, destination)
            if copy:
                log("download: copy successful")
            else:
                log("download: copy failed")
            xbmcvfs.delete(tmpdestination)
        except:
            log("download: Theme download Failed!!!", True, xbmc.LOGERROR)
            log("download: %s" % traceback.format_exc(), True, xbmc.LOGERROR)

        # Make sure the progress dialog has been closed
        downloadProgressDialog.close()

    # Retrieve the theme that the user has selected
    def getUserChoice(self, theme_list, showname, alternativeTitle=None, isTvShow=None, year=None, imdb=None):
        searchname = showname
        selectedTheme = None
        while selectedTheme is None:
            # Get the selection list to display to the user
            displayList = []
            # start with the custom option to manual search
            displayList.insert(0, __language__(32120) % "")

            # Now add all the other entries
            for theme in theme_list:
                displayList.append(theme.getDisplayString())

            # Show the list to the user
            select = xbmcgui.Dialog().select(("%s %s" % (__language__(32112), searchname.decode("utf-8"))), displayList)
            if select == -1:
                log("getUserChoice: Cancelled by user")
                return None
            else:
                if select == 0:
                    # Search using the alternative engine
                    isManualSearch, engineSelected = self.promptForSearchEngine()

                    # If no engine was selected, show the same list
                    if engineSelected is None:
                        continue

                    if isManualSearch:
                        # Manual search selected, prompt the user
                        kb = xbmc.Keyboard(showname, __language__(32113), False)
                        kb.doModal()
                        result = kb.getText()
                        if (result is None) or (result == ""):
                            log("getUserChoice: No text entered by user")
                            return None
                        # Set what was searched for
                        theme_list = self.searchThemeList(result, None, isTvShow, year, imdb, manual=True)
                        searchname = result
                    else:
                        theme_list = self.searchThemeList(searchname, alternativeTitle, isTvShow, year, imdb)
                else:
                    # Not the first entry selected, so change the select option
                    # so the index value matches the theme list
                    select = select - 1
                    # Returns true if the preview was confirmed as the target
                    if theme_list[select].playPreview():
                        selectedTheme = theme_list[select]

        return selectedTheme

    # Perform the actual search on the configured web site
    def searchThemeList(self, showname, alternativeTitle=None, isTvShow=None, year=None, imdb=None, manual=False, showProgressDialog=True):
        if (alternativeTitle is None) or (alternativeTitle == ""):
            log("searchThemeList: Search for %s" % showname)
        else:
            log("searchThemeList: Search for %s (%s)" % (showname, alternativeTitle))

        theme_list = []
        searchListing = None

        # Check if the search engine being used is GoEar
        if self.searchEngine == Settings.GOEAR:
            # Goeear is selected
            searchListing = GoearListing(self.includeAudio, self.includeVideo)
        elif self.searchEngine == Settings.SOUNDCLOUD:
            # Soundcloud is selected
            searchListing = SoundcloudListing(self.includeAudio, self.includeVideo)
        elif self.searchEngine == Settings.TELEVISION_TUNES:
            # Television Tunes
            searchListing = TelevisionTunesListing(self.includeAudio, self.includeVideo)
        elif self.searchEngine == Settings.THEMELIBRARY:
            # Theme Library Selected
            searchListing = ThemeLibraryListing(self.includeAudio, self.includeVideo)
        elif self.searchEngine == Settings.PLEXLIBRARY:
            # Plex Library Selected
            searchListing = PlexLibraryListing(self.includeAudio, self.includeVideo)

        # Check the special case where we use all the engines
        if self.searchEngine == Settings.ALL_ENGINES:
            # As part of this, we reset the search engine back to the default in settings
            # We do not want them doing this search all the time!
            self.searchEngine = Settings.getSearchEngine()

            themeLibraryList = ThemeLibraryListing(self.includeAudio, self.includeVideo).themeSearch(showname, alternativeTitle, isTvShow=isTvShow, year=year, imdb=imdb, showProgressDialog=showProgressDialog)

            plexLibraryList = []
            try:
                plexLibraryList = PlexLibraryListing(self.includeAudio, self.includeVideo).themeSearch(showname, alternativeTitle, isTvShow=isTvShow, year=year, imdb=imdb, showProgressDialog=showProgressDialog)
            except:
                log("searchThemeList: (Plex) %s" % traceback.format_exc(), xbmc.LOGERROR)

            tvtunesList = []
            try:
                tvtunesList = TelevisionTunesListing(self.includeAudio, self.includeVideo).themeSearch(showname, alternativeTitle, showProgressDialog=showProgressDialog)
            except:
                log("searchThemeList: (TV Tunes) %s" % traceback.format_exc(), xbmc.LOGERROR)

            goearList = []
            try:
                goearList = GoearListing(self.includeAudio, self.includeVideo).themeSearch(showname, alternativeTitle, showProgressDialog=showProgressDialog)
            except:
                log("searchThemeList: (Goear) %s" % traceback.format_exc(), xbmc.LOGERROR)

            soundcloudList = []
            try:
                soundcloudList = SoundcloudListing(self.includeAudio, self.includeVideo).themeSearch(showname, alternativeTitle, showProgressDialog=showProgressDialog)
            except:
                log("searchThemeList: (Soundcloud) %s" % traceback.format_exc(), xbmc.LOGERROR)

            # Join all the entries into one list
            theme_list = themeLibraryList + plexLibraryList + tvtunesList + goearList + soundcloudList
            # Now sort the list
            theme_list.sort()
        else:
            # Call the correct search option, depends if a manual search or not
            if manual:
                theme_list = searchListing.search(showname, showProgressDialog)
            else:
                theme_list = searchListing.themeSearch(showname, alternativeTitle, isTvShow=isTvShow, year=year, imdb=imdb, showProgressDialog=showProgressDialog)

        return theme_list

    # Calculates the next filename to use when downloading multiple themes
    def getNextThemeFileName(self, path, fileType=".mp3"):
        themeFileName = "theme" + fileType
        if Settings.isMultiThemesSupported() and xbmcvfs.exists(os_path_join(path, "theme" + fileType)):
            idVal = 1
            while xbmcvfs.exists(os_path_join(path, "theme" + str(idVal) + fileType)):
                idVal = idVal + 1
            themeFileName = "theme" + str(idVal) + fileType
        log("Next Theme Filename = " + themeFileName)
        return themeFileName

    # Prompt the user to select a different search option
    def promptForSearchEngine(self, showManualOptions=True):
        displayList = []
        # Add the theme library first
        displayList.insert(0, __language__(32125))
        displayList.insert(1, __language__(32132))
        displayList.insert(2, Settings.TELEVISION_TUNES)
        displayList.insert(3, Settings.SOUNDCLOUD)
        displayList.insert(4, Settings.GOEAR)

        manualSearchOffset = 5

        displayList.insert(manualSearchOffset, "** %s **" % __language__(32121))

        if showManualOptions:
            displayList.insert(manualSearchOffset + 1, "%s %s" % (Settings.TELEVISION_TUNES, __language__(32118)))
            displayList.insert(manualSearchOffset + 2, "%s %s" % (Settings.SOUNDCLOUD, __language__(32118)))
            displayList.insert(manualSearchOffset + 3, "%s %s" % (Settings.GOEAR, __language__(32118)))

        isManualSearch = False

        # Show the list to the user
        select = xbmcgui.Dialog().select((__language__(32120) % ""), displayList)
        if select == -1:
            log("promptForSearchEngine: Cancelled by user")
            return False, None
        else:
            if select == 0:
                self.searchEngine = Settings.THEMELIBRARY
            elif select == 1:
                self.searchEngine = Settings.PLEXLIBRARY
            if (select == 2) or (select == (manualSearchOffset + 1)):
                self.searchEngine = Settings.TELEVISION_TUNES
            elif (select == 3) or (select == (manualSearchOffset + 2)):
                self.searchEngine = Settings.SOUNDCLOUD
            elif (select == 4) or (select == (manualSearchOffset + 3)):
                self.searchEngine = Settings.GOEAR
            elif (select == 5):
                self.searchEngine = Settings.ALL_ENGINES

            # Record if this is a manual search
            if select > manualSearchOffset:
                isManualSearch = True

        log("promptForSearchEngine: New search engine is %s" % self.searchEngine)
        return isManualSearch, self.searchEngine


###########################################################
# Holds the details of each theme retrieved from a search
###########################################################
class ThemeItemDetails():
    def __init__(self, trackName, trackUrl, trackLength="", trackQuality="", albumname=""):
        # Remove any HTML characters from the name
        h = HTMLParser.HTMLParser()
        self.trackName = h.unescape(trackName)
        self.trackUrl = trackUrl
        self.trackLength = trackLength
        self.trackQuality = trackQuality
        self.albumname = albumname

        # Start with a very low priority
        self.priority = 100

    # Checks if the theme this points to is the same
    def __eq__(self, other):
        if other is None:
            return False
        # Check if the URL is the same as that will make it unique
        return self.trackUrl == other.trackUrl

    # lt defined for sorting order only
    def __lt__(self, other):
        # Sort by priority first
        if self.priority != other.priority:
            return self.priority < other.priority

        # Order just on the name of the file
        return self.trackName < other.trackName

    # Get the raw track name
    def getName(self):
        # If there is an album name, prepend that
        fullTrackName = self.trackName
        if (self.albumname is not None) and (self.albumname != ""):
            fullTrackName = "%s / %s" % (self.trackName, self.albumname)

        return fullTrackName

    def getAlbumName(self):
        return self.albumname

    # Get the display name that could include extra information
    def getDisplayString(self):
        displayRating = ""
        if self.priority == 1:  # Top Priority
            displayRating = '* '
        elif self.priority == 2:
            displayRating = '~ '
        elif self.priority == 3:
            displayRating = '+ '
        elif self.priority == 4:
            displayRating = '- '

        return "%s%s%s%s" % (displayRating, self.getName(), self.trackLength, self.trackQuality)

    # Get the URL used to download the theme
    def getMediaURL(self):
        return self.trackUrl

    def setPriority(self, rating):
        self.priority = rating

    def getPriority(self):
        return self.priority

    # Plays a preview of the given file
    def playPreview(self, theme_url=None):
        if theme_url is None:
            theme_url = self.getMediaURL()
        log("playPreview: Theme URL = %s" % theme_url)

        # Play the theme for the user
        listitem = xbmcgui.ListItem(self.getName())
        listitem.setInfo('music', {'Title': self.getName()})
        # Check if a tune is already playing
        if xbmc.Player().isPlayingAudio():
            xbmc.Player().stop()
        while xbmc.Player().isPlayingAudio():
            xbmc.sleep(5)

        xbmcgui.Window(10025).setProperty("TvTunesIsAlive", "true")
        xbmcgui.Window(10025).setProperty("PlayingBackgroundMedia", "true")
        xbmc.Player().play(theme_url, listitem)
        # Prompt the user to see if this is the theme to download
        isSelected = xbmcgui.Dialog().yesno(__language__(32103), __language__(32114))

        # Now stop playing the preview theme
        if xbmc.Player().isPlayingAudio():
            xbmc.Player().stop()
        xbmcgui.Window(10025).clearProperty('TvTunesIsAlive')
        xbmcgui.Window(10025).clearProperty('PlayingBackgroundMedia')
        return isSelected


###########################################################
# Class to control the progress bar dialog
###########################################################
class DummyProgressDialog():
    def __init__(self, showTitle="", percetageProgressDivisor=1):
        pass

    def updateProgress(self, percentageProgress=50):
        pass

    def isUserCancelled(self, displayNotice=True):
        return False

    def closeProgress(self):
        pass


class ProgressDialog(DummyProgressDialog):
    def __init__(self, showTitle="", percetageProgressDivisor=1):
        self.showTitle = showTitle.decode("utf-8")
        self.progressDialog = xbmcgui.DialogProgress()
        self.progressDialog.create(__language__(32105), __language__(32106))

        # The percetageProgressDivisor is a value that allows us to pass a single progress
        # bar around and let lots of different areas think they are going 100% of the
        # progress bar, but they are actually only doing part of it
        self.percetageProgressDivisor = percetageProgressDivisor
        self.divisorProgress = 0

    # Update how far through the progress this operation is
    def updateProgress(self, percentageProgress=50):
        # percentageProgress can be done by
        # (count*100)/total

        # Offset based on the percentage divisor
        alignedProgress = percentageProgress / self.percetageProgressDivisor
        alignedProgress = ((self.divisorProgress * 100) / self.percetageProgressDivisor) + alignedProgress

        if percentageProgress == 100:
            self.divisorProgress = self.divisorProgress + 1

        self.progressDialog.update(int(percentageProgress), ("%s %s" % (__language__(32107), self.showTitle)), ' ')

    # Check if the user has cancelled the operation
    def isUserCancelled(self, displayNotice=True):
        userCancelled = False

        if self.progressDialog.iscanceled():
            self.closeProgress()
            if displayNotice:
                xbmcgui.Dialog().ok(__language__(32108), __language__(32109), __language__(32115))
            userCancelled = True

        return userCancelled

    # Close the progress dialog
    def closeProgress(self):
        self.progressDialog.close()


###########################################################
# Class to define the interface for listings from websites
###########################################################
class DefaultListing():
    def __init__(self, incAudioThemes=True, incVideoThemes=True):
        self.includeAudio = incAudioThemes
        self.includeVideo = incVideoThemes

    # Perform the search for the theme (Manual search)
    def search(self, showname, showProgressDialog=True):
        progressDialog = DummyProgressDialog(showname)
        if showProgressDialog:
            progressDialog = ProgressDialog(showname)

        # Perform the search
        searchResults = self._search(showname, progressDialog)

        # If there is a progress dialog, make sure it is closed
        progressDialog.closeProgress()

        return searchResults

    def _search(self, showname, progressDialog):
        # Always has a custom implementation
        return []

    # Searches for a given subset of themes, trying to reduce the list
    def themeSearch(self, name, alternativeTitle=None, isTvShow=None, year=None, imdb=None, showProgressDialog=True):
        log("DefaultListing: ThemeSearch for %s" % name)

        progressDialog = DummyProgressDialog(name)
        if showProgressDialog:
            percetageProgressDivisor = 1
            if alternativeTitle:
                percetageProgressDivisor = 2
            progressDialog = ProgressDialog(name, percetageProgressDivisor)

        # Default is to just do a normal search
        cleanTitle = self.commonTitleCleanup(name)

        # Start by getting the tracks, we can just do this once, and then run
        # different filters on them
        tracks = self._search(cleanTitle, progressDialog)

        # Create the default regex that will be used to filter
        regex = self.getFilterRegex(cleanTitle, True)
        cleanRegex = self.getFilterRegex(cleanTitle)

        # Now check the entries against the regex
        themeDetailsList, lowPriorityTracks = self.getRegExMatchList(tracks, regex, priority=1)

        alternativeCleanRegex = None
        alternativeTracks = None
        lowPriorityAlternateTracks = []
        # If there is an alternative title for this movie or show then
        # search for that as well and merge the results
        if (alternativeTitle is not None) and (alternativeTitle != "") and not progressDialog.isUserCancelled(False):
            # Note: No need to clean the title of things like brackets when comparing
            # the alternative title
            alternativeTracks = self._search(alternativeTitle, progressDialog)
            alternativeRegex = self.getFilterRegex(alternativeTitle, True)
            alternativeCleanRegex = self.getFilterRegex(alternativeTitle)

            # Now check the entries against the regex
            filteredAlternativeTracks, lowPriorityAlternateTracks = self.getRegExMatchList(alternativeTracks, alternativeRegex, priority=1)
            themeDetailsList = self.mergeThemeLists(themeDetailsList, filteredAlternativeTracks)

        # Special filter here that does not include the album name, and does not have the appendices set
        if len(lowPriorityTracks) > 0:
            log("DefaultListing: Processing low priority album name tracks")
            nextThemeList, lowPriorityTracks = self.getRegExMatchList(lowPriorityTracks, cleanRegex, priority=2, checkAlbumOnly=True)
            # Now append the next set of themes to the list
            themeDetailsList = self.mergeThemeLists(themeDetailsList, nextThemeList)

        if len(lowPriorityAlternateTracks) > 0:
            log("DefaultListing: Processing low priority alternate album tracks")
            filteredAlternativeTracks, lowPriorityAlternateTracks = self.getRegExMatchList(lowPriorityAlternateTracks, alternativeCleanRegex, priority=2, checkAlbumOnly=True)
            themeDetailsList = self.mergeThemeLists(themeDetailsList, filteredAlternativeTracks)

        # If no entries found doing the custom search then just search for the name only
        if len(lowPriorityTracks) > 0:
            log("DefaultListing: Processing low priority tracks, regex filtering on title")

            nextThemeList, lowPriorityTracks = self.getRegExMatchList(lowPriorityTracks, cleanRegex, priority=3)
            # Now append the next set of themes to the list
            themeDetailsList = self.mergeThemeLists(themeDetailsList, nextThemeList)

        if len(lowPriorityAlternateTracks) > 0:
            log("DefaultListing: Processing low priority alternate tracks, regex filtering on title")
            filteredAlternativeTracks, lowPriorityAlternateTracks = self.getRegExMatchList(lowPriorityAlternateTracks, alternativeCleanRegex, priority=3)
            themeDetailsList = self.mergeThemeLists(themeDetailsList, filteredAlternativeTracks)

        log("DefaultListing: Processing remaining themes found")
        themeDetailsList = self.mergeThemeLists(themeDetailsList, lowPriorityTracks)
        themeDetailsList = self.mergeThemeLists(themeDetailsList, lowPriorityAlternateTracks)

        # If there is a progress dialog, make sure it is closed
        progressDialog.closeProgress()

        return themeDetailsList

    # Common cleanup to do to automatic searches
    def commonTitleCleanup(self, name):
        # If performing the automated search, remove anything in brackets
        # Remove anything in square brackets
        cleanedName = re.sub(r'\[[^)]*\]', '', name)
        # Remove anything in rounded brackets
        cleanedName = re.sub(r'\([^)]*\)', '', cleanedName)
        # Remove double space
        cleanedName = cleanedName.replace("  ", " ")
        # Remove -'s from the name
        cleanedName = cleanedName.replace("-", " ")

        cleanedName = self.removePrepositions(cleanedName)
        # Remove white space from the start and end of the string
        cleanedName = cleanedName.strip()

        return cleanedName

    # Default set of appendices to use for searches
    def getSearchAppendices(self):
        return ["OST",           # English acronym for original soundtrack
                "theme",
                "title",
                "soundtrack",
                "score",
                "tv",
                "t\\.v",
                "movie",
                "tema",          # Spanish for theme
                "BSO",           # Spanish acronym for OST (banda sonora original)
                "B\\.S\\.O",     # variation for Spanish acronym BSO
                "banda sonora",  # Spanish for Soundtrack
                "pelicula",      # Spanish for movie
                "music",
                "overture",
                "finale",
                "prelude",
                "opening",
                "closing",
                "collection"]

    # Filters the list of tracks by a regular expression
    def getRegExMatchList(self, tracks, regex=None, priority=None, checkAlbumOnly=False):
        if (regex is None) or (regex == ""):
            return tracks

        filteredTrackList = []
        lowPriorityTracks = []

        for track in tracks:
            themeName = track.getName()

            if checkAlbumOnly:
                # Check the album name against the clean regex without the appended key words
                albumName = track.getAlbumName()
                if (albumName is not None) and (albumName != ""):
                    themeName = albumName
                else:
                    # No album name, skip this one
                    lowPriorityTracks.append(track)
                    continue

            themeNameMatch = self.isRegExMatch(regex, themeName)

            # Skip this one if the title does not have the regex in it
            if not themeNameMatch:
                lowPriorityTracks.append(track)
            else:
                # Flag this track with the supplied priority
                track.setPriority(priority)
                filteredTrackList.append(track)

        return filteredTrackList, lowPriorityTracks

    # Checks a name against a group of regular expressions
    def isRegExMatch(self, regex, nameToCheck):
        # We add a dot either side of the name we check, as it seems the regex is
        # having problems with start and end on line characters
        nameToCheck = ".%s." % nameToCheck

        # This is a bit strange, but the name we want to search we want filtered
        # to be without non-ascii characters as well as with, and with replacements
        try:
            asciiNameToCheck = re.sub(r'[^\x00-\x7F]', ' ', nameToCheck)
            asciiNameToCheck = asciiNameToCheck.replace('\ ', '')

            if asciiNameToCheck == nameToCheck:
                asciiNameToCheck = ""
        except:
            asciiNameToCheck = ""
        try:
            unicodeNameToCheck = unicodedata.normalize('NFD', nameToCheck).encode('ascii', 'ignore')

            if unicodeNameToCheck == nameToCheck:
                unicodeNameToCheck = ""
        except:
            unicodeNameToCheck = ""

        regexThemeName = "%s %s %s" % (nameToCheck, asciiNameToCheck, unicodeNameToCheck)

        # Check to see if the title contains the value that is being searched for
        titleMatch = regex.search(regexThemeName)
        # Skip this one if the title does not have the regex in it
        if not titleMatch:
            log("DefaultListing: Title %s not in regex %s" % (nameToCheck, regex.pattern))
            return False

        log("DefaultListing: Title matched %s to regex %s" % (nameToCheck, regex.pattern))
        return True

    # Remove anything like "the" "of" "a"
    def removePrepositions(self, showname):
        regexShowname = showname

        English = ['a', 'an', 'and', 'the', 'of', 'or', 'to']
        Spanish = ['el', 'los', 'las', 'de', 'del', 'y', 'u', 'o']
        French = ['à', 'la', 'le', 'les', 'du', 'des', 'et']
        Italian = ['ne', 'il', 'di', 'gli', 'lo', 'e']
        German = ['von', 'der', 'und', 'aus', 'zu']
        Swedish = ['av', 'i']

        prepositions = English + Spanish + French + Italian + German + Swedish

        for w in prepositions:
            removeWord = "(?i) %s " % w
            regexShowname = re.sub(removeWord, ' ', regexShowname)
            removeWord = "(?i)^%s " % w
            regexShowname = re.sub(removeWord, '', regexShowname)

        return regexShowname

    # Generates the regular expression that is used to filter results
    def getFilterRegex(self, showname, useAppendices=False):
        searchAppend = ""
        # If there are appendices to apply, then create the regex part
        if useAppendices:
            # Get all the appendices that we want to match
            searchAppendices = '|'.join(self.getSearchAppendices())
            searchAppend = "%s%s%s" % ('(?=.*[ ()\[\]"\'\.](', searchAppendices, ')[ ()\[\]"\'\.])')

        regexShowname = showname.decode("utf-8", 'ignore')

        regexShowname = self.removePrepositions(regexShowname)

        # Remove white space from the start and end of the string
        regexShowname = regexShowname.strip()
        regexShowname = regexShowname.replace('  ', ' ')

        log("DefaultListing: Before regex escape: %s" % regexShowname)

        # Need to escape any values in the show name that are used as
        # part of the regex formatting
        # Note: Thiswill also escape spaced, so if we replace
        # spaces later, we need it to be escaped
        beforeRegexEscape = regexShowname
        regexShowname = re.escape(regexShowname)

        log("DefaultListing: After regex escape: %s" % regexShowname)

        # Generate the regular expression that will be used to match the title
        regexCheck = "%s%s%s%s" % ('(?=.*', regexShowname.replace('\\ ', ')(?=.*'), ')', searchAppend)

        # Get the regex without and non-ascii characters
        asciiRegexCheck = None
        try:
            asciiRegexCheck = re.sub(r'[^\x00-\x7F]', ' ', regexCheck)
            asciiRegexCheck = asciiRegexCheck.replace('\ ', '')
            # Only want it if it is different from the one we have already
            if asciiRegexCheck == regexCheck:
                asciiRegexCheck = None
        except:
            log("DefaultListing: Failed to process asciiRegexCheck", True, xbmc.LOGERROR)
            asciiRegexCheck = None

        # Also get the string where we remove the non ascii characters and
        # replace them with the closest match
        unicodeRegex = None
        try:
            unicodeRegex = unicodedata.normalize('NFD', beforeRegexEscape).encode('ascii', 'ignore')
            unicodeRegex = re.escape(unicodeRegex)
            unicodeRegex = "%s%s%s%s" % ('(?=.*', unicodeRegex.replace('\\ ', ')(?=.*'), ')', searchAppend)
            # Only want it if it is different from the one we have already
            if unicodeRegex == regexCheck:
                unicodeRegex = None
        except:
            log("DefaultListing: Failed to process unicodeRegex", True, xbmc.LOGERROR)
            unicodeRegex = None

        if (asciiRegexCheck is not None) and (unicodeRegex is not None):
            regexCheck = "(%s)|(%s)|(%s)" % (regexCheck, asciiRegexCheck, unicodeRegex)
        elif (asciiRegexCheck is not None):
            regexCheck = "(%s)|(%s)" % (regexCheck, asciiRegexCheck)
        elif (unicodeRegex is not None):
            regexCheck = "(%s)|(%s)" % (regexCheck, unicodeRegex)
        # Default is just the one regex

        log("DefaultListing: Using regex: %s" % regexCheck)

        # Compile for case insensitive search
        regex = re.compile(regexCheck, re.IGNORECASE | re.UNICODE)
        return regex

    # Appends unique values from list 2 to list 1
    def mergeThemeLists(self, list1, list2):
        for item2 in list2:
            if not (item2 in list1):
                log("DefaultListing: Adding Theme = %s" % item2.getDisplayString())
                list1.append(item2)
            else:
                log("DefaultListing: Not Adding Theme = %s" % item2.getDisplayString())
        return list1


#################################################
# Searches www.televisiontunes.com for themes
#################################################
class TelevisionTunesListing(DefaultListing):
    # Television tunes just uses the default search
    def themeSearch(self, name, alternativeTitle=None, isTvShow=None, year=None, imdb=None, showProgressDialog=True):
        progressDialog = DummyProgressDialog(name)
        if showProgressDialog:
            percetageProgressDivisor = 1
            if alternativeTitle:
                percetageProgressDivisor = 2
            progressDialog = ProgressDialog(name, percetageProgressDivisor)

        # Default is to just do a normal search
        cleanTitle = self.commonTitleCleanup(name)
        cleanTitle = cleanTitle.replace("'", "")
        themeDetailsList = self._search(cleanTitle, progressDialog)

        # If there is an alternative title for this movie or show then
        # search for that as well and merge the results
        if (alternativeTitle is not None) and (alternativeTitle != ""):
            alternativeThemeDetailsList = self.search(alternativeTitle, progressDialog)
            themeDetailsList = self.mergeThemeLists(themeDetailsList, alternativeThemeDetailsList)

        # If there is a progress dialog, make sure it is closed
        progressDialog.closeProgress()

        return themeDetailsList

    # Perform the search for the theme
    def _search(self, showname, progressDialog):
        # Only Audio is supported by this scraper
        if not self.includeAudio:
            return []

        search_url = "http://www.televisiontunes.com/search.php?q=%s"

        log("TelevisionTunesListing: Search for %s" % showname)
        themeList = []
        url = search_url % urllib.quote_plus(showname)

        # We will only have progressed to at most 80%, so mark as completed at this point
        progressDialog.updateProgress(25)

        # Get the HTMl at the given URL
        data = TelevisionTunesListing.getHtmlSource(url)
        # Check for an error occuring in the fetch from the web
        if data is not None:
            # Need to use BeautifulSoup 3 as version 4 does not work with the data returned
            soup = BeautifulSoup(''.join(data))

            progressDialog.updateProgress(50)

            # Get the section that has all of the search matches in it
            searchResults = soup.findAll('div', {"class": "jp-title"})

            for entry in searchResults:
                # Get the link
                link = entry.find('a')
                trackName = link.string
                trackUrl = link['href']
                log("TelevisionTunesListing: found %s (%s)" % (trackName, trackUrl))
                themeScraperEntry = TelevisionTunesItemDetails(trackName, trackUrl)
                themeList.append(themeScraperEntry)
        else:
            log("TelevisionTunesListing: No data for %s" % search_url)

        if len(themeList) < 1:
            log("TelevisionTunesListing: no theme found for %s" % showname)

        # We will only have progressed to at most 80%, so mark as completed at this point
        progressDialog.updateProgress(100)

        return themeList

    # We don't add any appendices for Television Tunes search
    def getSearchAppendices(self):
        return []

    @staticmethod
    def getHtmlSource(url, save=False):
        req = urllib2.Request(url)
        req.add_header('User-Agent', ' Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')

        doc = None
        try:
            response = urllib2.urlopen(req)
            # Holds the webpage that was read via the response.read() command
            doc = response.read()
            # Closes the connection after we have read the webpage.
            try:
                response.close()
            except:
                log("TelevisionTunesListing: Failed to close connection for %s" % url)
        except:
            log("TelevisionTunesListing: ERROR opening page %s" % url, True, xbmc.LOGERROR)
            log("TelevisionTunesListing: %s" % traceback.format_exc(), True, xbmc.LOGERROR)
            xbmcgui.Dialog().ok(__language__(32101), __language__(32102))
            return None
        return doc


#########################################
# Custom TelevisionTunes.com Item Details
#########################################
class TelevisionTunesItemDetails(ThemeItemDetails):
    # Get the URL used to download the theme
    def getMediaURL(self):
        data = TelevisionTunesListing.getHtmlSource("http://www.televisiontunes.com" + ThemeItemDetails.getMediaURL(self))

        # Check for an error occuring in the fetch from the web
        if data is None:
            return None

        soup = BeautifulSoup(''.join(data))

        searchResults = soup.find('a', {"id": "download_song"})
        trackUrl = searchResults['href']

        if trackUrl is None:
            return None

        downloadURL = "http://www.televisiontunes.com" + trackUrl

        log("TelevisionTunesItemDetails: Download URL: %s" % downloadURL)

        return downloadURL


#################################################
# Searches www.goear.com for themes
#################################################
class GoearListing(DefaultListing):
    # Perform the search for the theme
    def _search(self, name, progressDialog):
        # Only Audio is supported by this scraper
        if not self.includeAudio:
            return []

        baseUrl = "http://www.goear.com/search/"
        # User - instead of spaces
        searchName = name.replace(" ", "-")
        # Remove double space
        searchName = searchName.replace("--", "-")

        fullUrl = "%s%s" % (baseUrl, urllib.quote_plus(searchName))

        # Now check if any non ascii characters exist in the name, if so
        # try the search with them converted
        unicodeFullUrl = None
        progressDivisor = 1
        try:
            unicodeSearchName = unicodedata.normalize('NFD', searchName.decode("utf-8", 'ignore')).encode('ascii', 'ignore')

            if unicodeSearchName != searchName:
                unicodeFullUrl = "%s%s" % (baseUrl, unicodeSearchName)
                progressDivisor = progressDivisor + 1
        except:
            log("GoearListing: Exception when converting to ascii %s" % traceback.format_exc(), True, xbmc.LOGERROR)

        # Perform the search using the supplied URL
        themeDetailsList = self._doSearch(fullUrl, progressDialog, progressDivisor)

        if unicodeFullUrl and not progressDialog.isUserCancelled(False):
            unicodeThemeList = self._doSearch(unicodeFullUrl, progressDialog, progressDivisor, startpercentage=50)
            themeDetailsList = self.mergeThemeLists(themeDetailsList, unicodeThemeList)

        return themeDetailsList

    # Perform the search for the theme
    def _doSearch(self, searchURL, progressDialog, progressDivisor=1, startpercentage=0):
        log("GoearListing: Performing doSearch for %s" % searchURL)

        themeList = []
        lastThemeBatch = ['dummy']
        nextPageIndex = 0

        # Loop until we do not get any entries for the given page
        while (len(lastThemeBatch) > 0) and (nextPageIndex < 40):
            # Check if the user has requested the operation to be cancelled
            if progressDialog.isUserCancelled():
                break

            progressDialog.updateProgress(((nextPageIndex * 2) / progressDivisor) + startpercentage)

            # Reset the themes to none
            lastThemeBatch = []

            thisSearchURL = searchURL
            if nextPageIndex > 0:
                thisSearchURL = "%s/%d" % (searchURL, nextPageIndex)

            # First search is page /0 anyway
            soup = self._getPageContents(thisSearchURL)

            if soup is not None:
                # Get the tracks for this page
                lastThemeBatch = self._getEntries(soup)
                # Now merge this batch with the existing entries
                themeList = self.mergeThemeLists(themeList, lastThemeBatch)

            nextPageIndex = nextPageIndex + 1

        # Make sure this searches progress is at 100%
        progressDialog.updateProgress((100 / progressDivisor) + startpercentage)

        return themeList

    # Reads a web page
    def _getPageContents(self, fullUrl):
        log("GoearListing: Loading page %s" % fullUrl)
        # Start by calling the search URL
        req = urllib2.Request(fullUrl)
        req.add_header('User-Agent', ' Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')

        requestFailed = True
        maxAttempts = 3
        is404error = False
        doc = None

        while requestFailed and (maxAttempts > 0):
            maxAttempts = maxAttempts - 1
            try:
                response = urllib2.urlopen(req)
                # Holds the webpage that was read via the response.read() command
                doc = response.read()
                # Closes the connection after we have read the webpage.
                try:
                    response.close()
                except:
                    log("GoearListing: Failed to close connection for %s" % fullUrl, True, xbmc.LOGERROR)
                requestFailed = False
            except urllib2.HTTPError, e:
                # Check for the case where we get a 404 as that means there are no more pages
                if e.code == 404:
                    log("GoearListing: 404 Error received, no more entries, attempt %d" % maxAttempts)
                    is404error = True
                else:
                    # If we get an exception we have failed to perform the http request
                    # we will try again before giving up
                    log("GoearListing: Request failed for %s" % fullUrl)
                    log("GoearListing: %s" % traceback.format_exc())
                    is404error = False

        if requestFailed:
            # pop up a notification, and then return than none were found
            if not is404error:
                xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (__language__(32105).encode('utf-8'), __language__(32994).encode('utf-8'), 3000, __icon__))
            return None

        # Load the output of the search request into Soup
        return BeautifulSoup(''.join(doc))

    # Reads the track entries from the page
    def _getEntries(self, soup):
        log("GoearListing: Getting Entries")
        # Get all the items in the search results
        searchResults = soup.find('ol', {"class": "board_list results_list"})
        themeList = []

        # Make sure the list is set to something
        if (searchResults is None) or (searchResults.contents is None):
            log("GoearListing: Unexpected return results of None")
            return themeList

        # Check out each item in the search results list
        for item in searchResults.contents:
            # Just in case there is a problem reading the page, or a single entry
            # make sure we don't fail everything
            try:
                # Skip the blank lines, just want the <li> elements
                if item == '\n':
                    continue

                # Get the name of the track
                trackNameTag = item.find('h4')
                if trackNameTag is None:
                    continue
                trackNameTag = trackNameTag.find('a')
                if trackNameTag is None:
                    continue
                trackName = trackNameTag.string

                # Get the name of the group, artist or album
                trackGroupNameTag = item.find('span', {"class": "group"})
                if trackGroupNameTag is not None:
                    groupName = trackGroupNameTag.string
                else:
                    groupName = None

                # Get the URL for the track
                trackUrl = trackNameTag['href']

                # Get the length of the track
                # e.g. <li class="length radius_3">3:36</li>
                trackLength = ""
                trackLengthTag = item.find('li', {"class": "length"})
                if trackLengthTag is not None:
                    trackLength = " [" + trackLengthTag.string + "]"

                # Get the quality of the track
                # e.g. <li class="kbps radius_3">128<abbr title="Kilobit por segundo">kbps</abbr></li>
                trackQuality = ""
                trackQualityTag = item.find('li', {"class": "kbps"})
                if trackQualityTag is not None:
                    trackQuality = " (" + trackQualityTag.contents[0] + "kbps)"

                themeScraperEntry = GoearThemeItemDetails(trackName, trackUrl, trackLength, trackQuality, groupName)
                themeList.append(themeScraperEntry)
                log("GoearListing: Theme Details = %s" % themeScraperEntry.getDisplayString())
                log("GoearListing: Theme URL = %s" % trackUrl)
            except:
                log("GoearListing: Failed when processing page %s" % traceback.format_exc(), True, xbmc.LOGERROR)

        return themeList


################################
# Custom Goear.com Item Details
################################
class GoearThemeItemDetails(ThemeItemDetails):
    # Get the URL used to download the theme
    def getMediaURL(self):
        # Before returning the Media URL, we want to call the listen URL
        # This is because if we do not call this first, then we only get a warning
        # message recording in the MP3
        try:
            req = urllib2.Request(ThemeItemDetails.getMediaURL(self))
            req.add_header('User-Agent', ' Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
            response = urllib2.urlopen(req)
            # read via the response.read() command (No need to save what was read)
            response.read()
            # Closes the connection after we have read the webpage.
            response.close()
        except:
            # If we get an exception we have failed to perform the http request
            log("GoearThemeItemDetails: Request failed for %s" % ThemeItemDetails.getMediaURL(self))
            log("GoearThemeItemDetails: %s" % traceback.format_exc())

        downloadURL = self._getDownloadURL(ThemeItemDetails.getMediaURL(self))

        log("GoearThemeItemDetails: Download URL: %s" % downloadURL)

        return downloadURL

    # Gets the URL to stream and download from
    def _getDownloadURL(self, themeURL):
        # The URL will be of the format:
        #  http://www.goear.com/listen/1ed51e2/together-the-firm
        # We want the ID out of the middle
        start_of_id = themeURL.find("listen/") + 7
        end_of_id = themeURL.find("/", start_of_id)
        audio_id = themeURL[start_of_id:end_of_id]

        download_url = "http://www.goear.com/action/sound/get/%s" % audio_id

        return download_url


#################################################
# Searches www.soundcloud.com for themes
#################################################
class SoundcloudListing(DefaultListing):
    # Perform the search for the theme
    def _search(self, showname, progressDialog):
        log("SoundcloudListing: Search for %s" % showname)

        # Only Audio is supported by this scraper
        if not self.includeAudio:
            return []

        theme_list = []

        numTracksInBatch = 200   # set it to a value to start the loop for the first time
        offset = 0
        while (numTracksInBatch == 200) and (offset < 1000):
            # Check if the user has reqested the operation to be cancelled
            if progressDialog.isUserCancelled():
                break

            # At most there will be 20 requests, so go up in batches of 20
            progressDialog.updateProgress(offset / 10)

            tracks = []
            client = soundcloud.Client(client_id='b45b1aa10f1ac2941910a7f0d10f8e28')
            try:
                # Max value for limit is 200 entries
                # That is more than enough - tried some cases to get more back - but the
                # ones later down the list really have very little similarity to what was
                # being searched for, will do a couple of loops but will not get everything
                normtitle = showname.decode("utf-8", 'ignore')
                tracks = client.get('/tracks', q=normtitle, filter="streamable", limit=200, offset=offset)
                numTracksInBatch = len(tracks)
                log("SoundcloudListing: Number of entries returned = %d, offset = %d" % (numTracksInBatch, offset))
                offset = offset + numTracksInBatch
            except:
                log("SoundcloudListing: Request failed for %s" % showname, True, xbmc.LOGERROR)
                log("SoundcloudListing: %s" % traceback.format_exc(), True, xbmc.LOGERROR)
                numTracksInBatch = 0

            # Loop over the tracks produced assigning it to the list
            for track in tracks:
                if track in [None, ""]:
                    continue

                try:
                    # another dictionary for holding all the results for a specific song
                    themeName = track.title
                    duration = self._convertTime(track.duration)
                    # Only allow the theme if it is streamable
                    if track.streamable:
                        id = track.id
                        # The file size makes no difference as the stream is always limited to 128kbps
                        filesize = ""  # self._convertSize(track.original_content_size)
                        # themeURL = track.download_url or track.permalink_url
                        # themeURL = self._getDownloadLinkFromWaveform(track.waveform_url)
                        themeURL = "https://api.soundcloud.com/tracks/%s/stream?client_id=22e566527758690e6feb2b5cb300cc43" % str(track.id)
                        log("SoundcloudListing: Found %s%s (%s) %s (%s)" % (themeName, duration, themeURL, str(id), track.waveform_url))
                        theme = ThemeItemDetails(themeName, themeURL, duration, filesize)
                        theme_list.append(theme)
                    else:
                        # As we filter for only streamable, this should never happen
                        log("SoundcloudListing: %s is not streamable" % themeName)
                except:
                    continue
        log("SoundcloudListing: Total entries returned from search = %d" % len(theme_list))

        # make sure the progress dialog has been set to 100%
        if offset != 1000:
            progressDialog.updateProgress(100)

        return theme_list

    # Generate the stream link from the waveform_url
#     def _getDownloadLinkFromWaveform(self, waveform_url):
#         regex = re.compile("\/([a-zA-Z0-9]+)_")
#         r = regex.search(waveform_url)
#         stream_id = r.groups()[0]
#         return "http://media.soundcloud.com/stream/%s" % str(stream_id)

    # this method converts the time in milliseconds to human readable format.
    def _convertTime(self, ms):
        x = ms / 1000
        seconds = x % 60
        x /= 60
        minutes = x % 60
        x /= 60
        hours = x % 24
        return " [%02d:%02d:%02d]" % (hours, minutes, seconds)

    def _convertSize(self, size):
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size, 1024)))
        p = math.pow(1024, i)
        s = round(size / p, 2)
        if (s > 0):
            return ' (%s %s)' % (s, size_name[i])
        else:
            return ""


#################################################
# Searches Theme Library for themes
#################################################
class ThemeLibraryListing(DefaultListing):
    def themeSearch(self, name, alternativeTitle=None, isTvShow=None, year=None, imdb=None, showProgressDialog=True):
        progressDialog = DummyProgressDialog(name)
        if showProgressDialog:
            progressDialog = ProgressDialog(name)

        # Get the details from the theme library
        themeLibrary = ThemeLibrary()
        progressDialog.updateProgress(25)

        themeDetails = themeLibrary.getThemes(name, isTvShow, year, imdb, self.includeAudio, self.includeVideo)
        del themeLibrary

        progressDialog.updateProgress(50)

        themeDetailsList = []
        audioThemeNum = 0
        videoThemeNum = 0
        if themeDetails is not None:
            for themeUrl in themeDetails.keys():
                title = ""
                if Settings.isVideoFile(themeUrl):
                    videoThemeNum = videoThemeNum + 1
                    title = "%s %d" % (__language__(32126), videoThemeNum)
                else:
                    audioThemeNum = audioThemeNum + 1
                    title = "%s %d" % (__language__(32124), audioThemeNum)

                # Get the size of the track
                sizeStr = self.getSizeString(themeDetails[themeUrl])

                theme = ThemeItemDetails(title, themeUrl, sizeStr)
                theme.setPriority(1)
                themeDetailsList.append(theme)
                progressDialog.updateProgress(75)

        # If there is a progress dialog, make sure it is closed
        progressDialog.updateProgress(100)
        progressDialog.closeProgress()

        return themeDetailsList

    # Perform the search for the theme
    def _search(self, showname, progressDialog):
        return []

    # We don't add any appendices for theme library search
    def getSearchAppendices(self):
        return []

    def getSizeString(self, sizeBytes):
        displayStr = ""
        try:
            if sizeBytes not in [None, "", "0", 0]:
                sizeStr = "{0:.2f}".format(float(sizeBytes) / 1048576.0)
                displayStr = "  [%sMB]" % sizeStr
        except:
            log("ThemeLibraryListing: Failed to convert size")

        return displayStr


#################################################
# Searches Plex Library for themes
#################################################
class PlexLibraryListing(DefaultListing):
    def themeSearch(self, name, alternativeTitle=None, isTvShow=None, year=None, imdb=None, showProgressDialog=True):
        progressDialog = DummyProgressDialog(name)
        if showProgressDialog:
            progressDialog = ProgressDialog(name)

        # Check the details that have been passed in for a match against the Database
        checkedId = self._getMetaHandlersID(isTvShow, name, year)
        progressDialog.updateProgress(25)

        # Get the details from the plex library
        log("PlexLibraryListing: Searching for theme with id: %s" % checkedId)
        themeUrls = []
        if checkedId not in [None, ""]:
            validURL = self._getValidUrl(checkedId)
            if validURL not in [None, ""]:
                themeUrls.append(validURL)

        progressDialog.updateProgress(50)

        # If the passed in imdb value is not the same as the one we found, try that as well
        if imdb not in [None, ""]:
            if checkedId != imdb:
                log("PlexLibraryListing: ID comparison, Original = %s, checked = %s" % (imdb, checkedId))
                validURL = self._getValidUrl(imdb)
                if validURL not in [None, ""]:
                    themeUrls.append(validURL)

        progressDialog.updateProgress(75)

        themeDetailsList = []
        themeNum = 0
        for themeUrl in themeUrls:
            title = ""
            themeNum = themeNum + 1
            title = "%s %d" % (__language__(32131), themeNum)

            theme = ThemeItemDetails(title, themeUrl)
            theme.setPriority(1)
            themeDetailsList.append(theme)

        # If there is a progress dialog, make sure it is closed
        progressDialog.updateProgress(100)
        progressDialog.closeProgress()

        return themeDetailsList

    # Perform the search for the theme
    def _search(self, showname, progressDialog):
        return []

    # We don't add any appendices for Plex Library search
    def getSearchAppendices(self):
        return []

    def _getValidUrl(self, videoId):
        if videoId in [None, ""]:
            return None

        url = "http://tvthemes.plexapp.com/%s.mp3" % videoId

        try:
            # Check to see if this is actually a link that exists
            request = urllib2.Request(url)
            request.get_method = lambda: 'HEAD'
            urllib2.urlopen(request)
            log("PlexLibraryListing: Theme exists at URL = %s" % url)
        except urllib2.HTTPError:
            log("PlexLibraryListing: No theme exists at URL = %s" % url)
            url = None

        return url

    # Uses metahandlers to get the TV ID
    def _getMetaHandlersID(self, isTvShow, title, year=""):
        idValue = ""
        if year in [None, 0, "0"]:
            year = ""
        # Does not seem to work correctly with the year at the moment
        year = ""
        metaget = None
        try:
            metaget = metahandlers.MetaData(preparezip=False)
            if isTvShow:
                idValue = metaget.get_meta('tvshow', title, year=str(year))['tvdb_id']
            else:
                idValue = metaget.get_meta('movie', title, year=str(year))['imdb_id']

            # Check if we have no id returned, and we added in a year
            if (idValue in [None, ""]) and (year not in [None, ""]):
                if isTvShow:
                    idValue = metaget.get_meta('tvshow', title)['tvdb_id']
                else:
                    idValue = metaget.get_meta('movie', title)['imdb_id']

            if not idValue:
                idValue = ""
        except Exception:
            idValue = ""
            log("PlexLibraryListing: Failed to get Metahandlers ID %s" % traceback.format_exc())

        if metaget is not None:
            del metaget

        return idValue
