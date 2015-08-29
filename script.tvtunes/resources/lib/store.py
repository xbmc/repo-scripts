# -*- coding: utf-8 -*-
import base64
import xml.etree.ElementTree as ET
import traceback
import urllib2
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui


__addon__ = xbmcaddon.Addon(id='script.tvtunes')
__addonid__ = __addon__.getAddonInfo('id')


from settings import Settings
from settings import log

try:
    from metahandler import metahandlers
except Exception:
    log("ThemeStore: metahandler Import Failed %s" % traceback.format_exc(), xbmc.LOGERROR)


# Class to handle the uploading of themes
class ThemeStore():
    def __init__(self):
        # Get the store settings file, this will be copied into this location my
        # the user so that the URLs are not public
        tvtunesRegFileName = xbmc.translatePath('special://profile/addon_data/%s/tvtunes-store-reg.xml' % __addonid__).decode("utf-8")

        self.baseurl = None
        self.userlistFile = None
        self.storeContentsFile = None
        self.storeTvShowAudioContents = {}
        self.storeMovieAudioContents = {}

        # Check if the file exists, if it does read it in
        if xbmcvfs.exists(tvtunesRegFileName):
            log("ThemeStore: Loading registration file %s" % tvtunesRegFileName)
            # Read the registration file for the store details
            try:
                tvtunesRegFile = xbmcvfs.File(tvtunesRegFileName, 'r')
                tvtunesRegStr = tvtunesRegFile.read()
                tvtunesRegFile.close()

                # Get the store configuration from the registration file
                tvtunesRegET = ET.ElementTree(ET.fromstring(base64.b64decode(tvtunesRegStr)))

                configElem = tvtunesRegET.find('config')
                if configElem is not None:
                    configLocation = configElem.text
                    if configLocation not in [None, ""]:
                        # Read in all the configuration details
                        tvtunesStoreConfig = urllib2.urlopen(configLocation)
                        tvtunesStoreConfigStr = tvtunesStoreConfig.read()
                        # Closes the connection after we have read the configuration
                        try:
                            tvtunesStoreConfig.close()
                        except:
                            log("ThemeStore: Failed to close connection for store config", xbmc.LOGERROR)

                        tvtunesStoreET = ET.ElementTree(ET.fromstring(base64.b64decode(tvtunesStoreConfigStr)))

                        baseUrlElem = tvtunesStoreET.find('baseurl')
                        if baseUrlElem is not None:
                            self.baseurl = baseUrlElem.text
                        userlistElem = tvtunesStoreET.find('userlist')
                        if userlistElem is not None:
                            self.userlistFile = userlistElem.text
                        storeContentsElem = tvtunesStoreET.find('storecontent')
                        if storeContentsElem is not None:
                            self.storeContentsFile = storeContentsElem.text
            except:
                log("ThemeStore: Failed to read in file %s" % tvtunesRegFileName, xbmc.LOGERROR)
                log("ThemeStore: %s" % traceback.format_exc(), xbmc.LOGERROR)

    # Make sure this user has access to the store
    def checkAccess(self):
        log("ThemeStore: Checking access")

        if self.baseurl is None or self.userlistFile is None:
            log("ThemeStore: Theme Store details not loaded correctly")
            return False

        # Get the machine we need to check
        machineId = Settings.getTvTunesId()
        log("ThemeStore: Unique machine ID is %s" % machineId)

        validUser = False
        try:
            # Get the user list
            remoteUserList = urllib2.urlopen(self.userlistFile)
            userListDetails = remoteUserList.read()
            # Closes the connection after we have read the remote user list
            try:
                remoteUserList.close()
            except:
                log("ThemeStore: Failed to close connection for remote user list", xbmc.LOGERROR)

            # Check all of the settings
            userListDetailsET = ET.ElementTree(ET.fromstring(base64.b64decode(userListDetails)))
            for useridElem in userListDetailsET.findall('userid'):
                if useridElem is not None:
                    useridStr = useridElem.text
                    if useridStr == machineId:
                        log("ThemeStore: Detected valid user")
                        validUser = True
        except:
            log("ThemesStore: Failed to read in user list: %s" % traceback.format_exc(), xbmc.LOGERROR)
            return False

        return validUser

    # Get the items that are in the theme store
    def loadStoreContents(self):
        # Make sure the config has been loaded
        if self.storeContentsFile in [None, ""]:
            return False

        # Need to get the contents list
        try:
            # Get the contents list from the store
            remoteStoreContents = urllib2.urlopen(self.storeContentsFile)
            storeContentsDetails = remoteStoreContents.read()
            # Closes the connection after we have read the remote user list
            try:
                remoteStoreContents.close()
            except:
                log("ThemesStore: Failed to close connection for remote store contents", xbmc.LOGERROR)

            storeContentsET = ET.ElementTree(ET.fromstring(storeContentsDetails))

            # Check if the store is currently disabled
            isEnabled = storeContentsET.find('enabled')
            if (isEnabled is None) or (isEnabled.text != 'true'):
                log("ThemesStore: Downloads disabled via online settings")
                # TODO: show a message dialog, or a notification
                return False

            # Get the tvshows that are in the store
            tvshowsElm = storeContentsET.find('tvshows')
            if tvshowsElm is not None:
                for elemItem in tvshowsElm.findall('tvshow'):
                    tvShowId = elemItem.attrib['id']
                    # Now get the file name for the theme
                    themeElem = elemItem.find('audiotheme')
                    if themeElem is not None:
                        self.storeTvShowAudioContents[tvShowId] = themeElem.text

            # Get the movies that are in the store
            movieElm = storeContentsET.find('movies')
            if movieElm is not None:
                for elemItem in movieElm.findall('movie'):
                    movieId = elemItem.attrib['id']
                    # Now get the file name for the theme
                    themeElem = elemItem.find('audiotheme')
                    if themeElem is not None:
                        self.storeMovieAudioContents[movieId] = themeElem.text

            # TODO: Add video theme content
        except:
            log("ThemesStore: Failed to read in store contents: %s" % traceback.format_exc(), xbmc.LOGERROR)
            return False

        return True

    def getThemeUrls(self, title, isTvShow, year, imdb):
        # First check that the user has access and load the store content
        if not self.checkAccess():
            # Display an error as this user is not registered
            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32101), __addon__.getLocalizedString(32122))
            return None

        if not self.loadStoreContents():
            # Failed to load the store content
            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32101), __addon__.getLocalizedString(32123))
            return None

        # Check the details that have been passed in for a match against the Database
        checkedId = self._getMetaHandlersID(isTvShow, title, year)

        log("ThemesStore: Searching for theme with id: %s" % checkedId)

        themeUrls = []
        if checkedId not in ["", None]:
            themeUrl = self._getThemeUrl(checkedId, isTvShow)
            if themeUrl not in ["", None]:
                themeUrls.append(themeUrl)

        if imdb not in [None, ""]:
            if checkedId != imdb:
                log("ThemesStore: ID comparison, Original = %s, checked = %s" % (imdb, checkedId))
                # Also get the theme for database ID
                themeUrl = self._getThemeUrl(imdb, isTvShow)
                if themeUrl not in ["", None]:
                    themeUrls.append(themeUrl)

        return themeUrls

    def _getThemeUrl(self, itemId, isTvShow):
        themeUrl = None
        filename = None
        subDir = 'movies'
        # Check if it is in the store
        if isTvShow:
            subDir = 'tvshows'
            log("ThemesStore: Getting TV Show theme for %s" % itemId)
            filename = self.storeTvShowAudioContents.get(itemId, None)
        else:
            log("ThemesStore: Getting Movie theme for %s" % itemId)
            filename = self.storeMovieAudioContents.get(itemId, None)

        # Check if this theme exists
        if filename not in [None, ""]:
            themeUrl = "%s%s/%s/%s" % (self.baseurl, subDir, itemId, filename)
        return themeUrl

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
            log("UploadThemes: Failed to get Metahandlers ID %s" % traceback.format_exc())

        if metaget is not None:
            del metaget

        return idValue
