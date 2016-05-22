# -*- coding: utf-8 -*-
import base64
import xml.etree.ElementTree as ET
import traceback
import urllib2
import xbmc
import xbmcaddon
import xbmcgui

from settings import log
from idLookup import IdLookup

ADDON = xbmcaddon.Addon(id='script.tvtunes')


# Class to handle the uploading of themes
class ThemeLibrary():
    def __init__(self):
        self.baseurl = None
        self.libraryContentsFile = None

        self.tvShowList = []
        self.movieList = []

        # Read the registration file for the library details
        try:
            tvtunesRegStr = "PHR2dHVuZXNTdG9yZVJlZz4gICAgPGNvbmZpZz5odHRwOi8vc2l0ZXMuZ29vZ2xlLmNvbS9zaXRlL3JvYndlYnNldC90dnR1bmVzLXN0b3JlLWNvbmZpZy54bWw8L2NvbmZpZz48L3R2dHVuZXNTdG9yZVJlZz4="

            # Get the library configuration from the registration file
            tvtunesRegET = ET.ElementTree(ET.fromstring(base64.b64decode(tvtunesRegStr)))

            configElem = tvtunesRegET.find('config')
            if configElem is not None:
                configLocation = configElem.text
                if configLocation not in [None, ""]:
                    # Read in all the configuration details
                    tvtunesLibraryConfig = urllib2.urlopen(configLocation)
                    tvtunesLibraryConfigStr = tvtunesLibraryConfig.read()
                    # Closes the connection after we have read the configuration
                    try:
                        tvtunesLibraryConfig.close()
                    except:
                        log("ThemeLibrary: Failed to close connection for library config", xbmc.LOGERROR)

                    tvtunesLibraryET = ET.ElementTree(ET.fromstring(base64.b64decode(tvtunesLibraryConfigStr)))

                    baseUrlElem = tvtunesLibraryET.find('baseurl')
                    if baseUrlElem is not None:
                        self.baseurl = baseUrlElem.text
                    storeContentsElem = tvtunesLibraryET.find('storecontent')
                    if storeContentsElem is not None:
                        self.libraryContentsFile = storeContentsElem.text
        except:
            log("ThemeLibrary: %s" % traceback.format_exc(), xbmc.LOGERROR)

    # Get the items that are in the theme library
    def loadLibraryContents(self):
        # Make sure the config has been loaded
        if self.libraryContentsFile in [None, ""]:
            return False

        # Check if the file has already been loaded
        if (len(self.tvShowList) > 0) or (len(self.movieList) > 0):
            return True

        # Need to get the contents list
        try:
            # Get the contents list from the library
            remoteLibraryContents = urllib2.urlopen(self.libraryContentsFile)
            libraryContentsDetails = remoteLibraryContents.read()
            # Closes the connection after we have read the remote user list
            try:
                remoteLibraryContents.close()
            except:
                log("ThemeLibrary: Failed to close connection for remote library contents", xbmc.LOGERROR)

            libraryContentsET = ET.ElementTree(ET.fromstring(libraryContentsDetails))

            # Check if the library is currently disabled
            isEnabled = libraryContentsET.find('enabled')
            if (isEnabled is None) or (isEnabled.text != 'true'):
                log("ThemeLibrary: Downloads disabled via online settings")
                # TODO: show a message dialog, or a notification
                return False

            # Get the tvshows that are in the library
            tvshowsElm = libraryContentsET.find('tvshows')
            if tvshowsElm is not None:
                for elemItem in tvshowsElm.findall('tvshow'):
                    themeDetails = {'id': None, 'audio': None, 'video': None, 'tvdb': None, 'imdb': None}

                    themeDetails['id'] = elemItem.attrib.get('id', None)
                    themeDetails['tvdb'] = elemItem.attrib.get('tvdb', None)
                    themeDetails['imdb'] = elemItem.attrib.get('imdb', None)

                    # Now get the file name for the theme
                    themeElem = elemItem.find('audiotheme')
                    if themeElem is not None:
                        # Check if there is a size attribute
                        fileSize = themeElem.attrib.get('size', None)
                        themeDetails['audio'] = {'file': themeElem.text, 'size': fileSize}

                    # Now get the file name for the video theme
                    vidThemeElem = elemItem.find('videotheme')
                    if vidThemeElem is not None:
                        # Check if there is a size attribute
                        fileSize = vidThemeElem.get('size', None)
                        themeDetails['video'] = {'file': vidThemeElem.text, 'size': fileSize}

                    self.tvShowList.append(themeDetails)

            # Get the movies that are in the library
            movieElm = libraryContentsET.find('movies')
            if movieElm is not None:
                for elemItem in movieElm.findall('movie'):
                    themeDetails = {'id': None, 'audio': None, 'video': None, 'tmdb': None, 'imdb': None}

                    themeDetails['id'] = elemItem.attrib.get('id', None)
                    themeDetails['tmdb'] = elemItem.attrib.get('tmdb', None)
                    themeDetails['imdb'] = elemItem.attrib.get('imdb', None)

                    # Now get the file name for the theme
                    themeElem = elemItem.find('audiotheme')
                    if themeElem is not None:
                        # Check if there is a size attribute
                        fileSize = themeElem.attrib.get('size', None)
                        themeDetails['audio'] = {'file': themeElem.text, 'size': fileSize}

                    # Now get the file name for the video theme
                    vidThemeElem = elemItem.find('videotheme')
                    if vidThemeElem is not None:
                        # Check if there is a size attribute
                        fileSize = vidThemeElem.get('size', None)
                        themeDetails['video'] = {'file': vidThemeElem.text, 'size': fileSize}

                    self.movieList.append(themeDetails)
        except:
            log("ThemeLibrary: Failed to read in library contents: %s" % traceback.format_exc(), xbmc.LOGERROR)
            return False

        return True

    def getThemes(self, title, isTvShow, year, imdb, includeAudio=True, includeVideo=True):
        log("ThemeLibrary: Getting themes for %s" % title)
        if not self.loadLibraryContents():
            # Failed to load the library content
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32101), ADDON.getLocalizedString(32123))
            return None

        # Check the details that have been passed in for a match against the Database
        # This will try and match the name
        idLookup = IdLookup()
        checkedIdDetails = idLookup.getIds(title, year, isTvShow)
        del idLookup

        log("ThemeLibrary: Searching for theme with id: %s" % str(checkedIdDetails))

        # Get together all the Ids we are going to search for
        ids = []
        if imdb not in [None, ""]:
            ids.append(imdb)
        if checkedIdDetails['imdb'] not in [None, ""]:
            ids.append(checkedIdDetails['imdb'])
        if checkedIdDetails['tmdb'] not in [None, ""]:
            ids.append(checkedIdDetails['tmdb'])
        if checkedIdDetails['tvdb'] not in [None, ""]:
            ids.append(checkedIdDetails['tvdb'])
        # Make sure the  items are unique
        ids = list(set(ids))

        themeUrls = {}
        for id in ids:
            themeDetail = self._getThemes(id, isTvShow)
            if themeDetail not in [None, ""]:
                if includeAudio and (themeDetail.get('audio', None) not in [None, ""]):
                    (themeUrl, fileSize) = self._getThemeLink(themeDetail['id'], themeDetail['audio'], isTvShow)
                    themeUrls[themeUrl] = fileSize
                if includeVideo and (themeDetail.get('video', None) not in [None, ""]):
                    (themeUrl, fileSize) = self._getThemeLink(themeDetail['id'], themeDetail['video'], isTvShow)
                    themeUrls[themeUrl] = fileSize

        return themeUrls

    # Read the theme details from the library storage
    def _getThemes(self, itemId, isTvShow):
        if itemId in [None, ""]:
            return None

        details = None
        # Check if it is in the library
        if isTvShow:
            log("ThemeLibrary: Getting TV Show theme for %s" % itemId)
            for tvTheme in self.tvShowList:
                if (tvTheme['id'] == itemId) or (tvTheme['imdb'] == itemId) or (tvTheme['tvdb'] == itemId):
                    details = tvTheme
                    # Only need one entry
                    break
        else:
            log("ThemeLibrary: Getting Movie theme for %s" % itemId)
            for movieTheme in self.movieList:
                if (movieTheme['id'] == itemId) or (movieTheme['imdb'] == itemId) or (movieTheme['tmdb'] == itemId):
                    details = movieTheme
                    # Only need one entry
                    break

        return details

    # Get the link and file size for the theme
    def _getThemeLink(self, itemId, detail, isTvShow):
        themeUrl = None
        fileSize = None
        subDir = 'movies'
        # Check if it is in the library
        if isTvShow:
            subDir = 'tvshows'

        # Check if this theme exists
        if detail not in [None, ""]:
            themeUrl = "%s%s/%s/%s" % (self.baseurl, subDir, itemId, detail['file'])
            fileSize = detail['size']

        return (themeUrl, fileSize)
