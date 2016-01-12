# -*- coding: utf-8 -*-
import base64
import xml.etree.ElementTree as ET
import traceback
import urllib2
import xbmc
import xbmcaddon
import xbmcgui


__addon__ = xbmcaddon.Addon(id='script.tvtunes')
__addonid__ = __addon__.getAddonInfo('id')


from settings import log

try:
    from metahandler import metahandlers
except Exception:
    log("ThemeLibrary: metahandler Import Failed %s" % traceback.format_exc(), xbmc.LOGERROR)


# Class to handle the uploading of themes
class ThemeLibrary():
    def __init__(self):
        self.baseurl = None
        self.userlistFile = None
        self.libraryContentsFile = None
        self.libraryTvShowAudioContents = {}
        self.libraryMovieAudioContents = {}
        self.libraryTvShowVideoContents = {}
        self.libraryMovieVideoContents = {}

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
                    userlistElem = tvtunesLibraryET.find('userlist')
                    if userlistElem is not None:
                        self.userlistFile = userlistElem.text
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
                    tvShowId = elemItem.attrib['id']
                    # Now get the file name for the theme
                    themeElem = elemItem.find('audiotheme')
                    if themeElem is not None:
                        # Check if there is a size attribute
                        fileSize = themeElem.attrib['size']
                        details = {'file': themeElem.text, 'size': fileSize}
                        self.libraryTvShowAudioContents[tvShowId] = details

                    # Now get the file name for the video theme
                    vidThemeElem = elemItem.find('videotheme')
                    if vidThemeElem is not None:
                        # Check if there is a size attribute
                        fileSize = vidThemeElem.attrib['size']
                        details = {'file': vidThemeElem.text, 'size': fileSize}
                        self.libraryTvShowVideoContents[tvShowId] = details

            # Get the movies that are in the library
            movieElm = libraryContentsET.find('movies')
            if movieElm is not None:
                for elemItem in movieElm.findall('movie'):
                    movieId = elemItem.attrib['id']
                    # Now get the file name for the theme
                    themeElem = elemItem.find('audiotheme')
                    if themeElem is not None:
                        # Check if there is a size attribute
                        fileSize = themeElem.attrib['size']
                        details = {'file': themeElem.text, 'size': fileSize}
                        self.libraryMovieAudioContents[movieId] = details

                    # Now get the file name for the video theme
                    vidThemeElem = elemItem.find('videotheme')
                    if vidThemeElem is not None:
                        # Check if there is a size attribute
                        fileSize = vidThemeElem.attrib['size']
                        details = {'file': vidThemeElem.text, 'size': fileSize}
                        self.libraryMovieVideoContents[movieId] = details

        except:
            log("ThemeLibrary: Failed to read in library contents: %s" % traceback.format_exc(), xbmc.LOGERROR)
            return False

        return True

    def getThemes(self, title, isTvShow, year, imdb, includeAudio=True, includeVideo=True):
        if not self.loadLibraryContents():
            # Failed to load the library content
            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32101), __addon__.getLocalizedString(32123))
            return None

        # Check the details that have been passed in for a match against the Database
        checkedId = self._getMetaHandlersID(isTvShow, title, year)

        log("ThemeLibrary: Searching for theme with id: %s" % checkedId)

        themeUrls = {}
        if checkedId not in ["", None]:
            if includeAudio:
                (themeUrl, size) = self._getAudioTheme(checkedId, isTvShow)
                if themeUrl not in ["", None]:
                    themeUrls[themeUrl] = size
            # Only get the video theme if it is required
            if includeVideo:
                (vidThemeUrl, vidSize) = self._getVideoTheme(checkedId, isTvShow)
                if vidThemeUrl not in ["", None]:
                    themeUrls[vidThemeUrl] = vidSize

        if imdb not in [None, ""]:
            if checkedId != imdb:
                log("ThemeLibrary: ID comparison, Original = %s, checked = %s" % (imdb, checkedId))
                # Also get the theme for database ID
                if includeAudio:
                    (themeUrl, size) = self._getAudioTheme(imdb, isTvShow)
                    if themeUrl not in ["", None]:
                        themeUrls[themeUrl] = size
                # Only get the video theme if it is required
                if includeVideo:
                    (vidThemeUrl, vidSize) = self._getVideoTheme(imdb, isTvShow)
                    if vidThemeUrl not in ["", None]:
                        themeUrls[vidThemeUrl] = vidSize

        return themeUrls

    def _getAudioTheme(self, itemId, isTvShow):
        themeUrl = None
        details = None
        fileSize = None
        subDir = 'movies'
        # Check if it is in the library
        if isTvShow:
            subDir = 'tvshows'
            log("ThemeLibrary: Getting TV Show audio theme for %s" % itemId)
            details = self.libraryTvShowAudioContents.get(itemId, None)
        else:
            log("ThemeLibrary: Getting Movie audio theme for %s" % itemId)
            details = self.libraryMovieAudioContents.get(itemId, None)

        # Check if this theme exists
        if details not in [None, ""]:
            themeUrl = "%s%s/%s/%s" % (self.baseurl, subDir, itemId, details['file'])
            fileSize = details['size']
        return (themeUrl, fileSize)

    def _getVideoTheme(self, itemId, isTvShow):
        themeUrl = None
        details = None
        fileSize = None
        subDir = 'movies'
        # Check if it is in the library
        if isTvShow:
            subDir = 'tvshows'
            log("ThemeLibrary: Getting TV Show video theme for %s" % itemId)
            details = self.libraryTvShowVideoContents.get(itemId, None)
        else:
            log("ThemeLibrary: Getting Movie video theme for %s" % itemId)
            details = self.libraryMovieVideoContents.get(itemId, None)

        # Check if this theme exists
        if details not in [None, ""]:
            themeUrl = "%s%s/%s/%s" % (self.baseurl, subDir, itemId, details['file'])
            fileSize = details['size']
        return (themeUrl, fileSize)

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
            log("ThemeLibrary: Failed to get Metahandlers ID %s" % traceback.format_exc())

        if metaget is not None:
            del metaget

        return idValue
