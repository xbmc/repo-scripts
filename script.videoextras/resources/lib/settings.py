# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import os
import xbmcvfs

__addon__ = xbmcaddon.Addon(id='script.videoextras')
__addonid__ = __addon__.getAddonInfo('id')


# Common logging module
def log(txt, loglevel=xbmc.LOGDEBUG):
    if (__addon__.getSetting("logEnabled") == "true") or (loglevel != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode("utf-8"), level=loglevel)


# There has been problems with calling join with non ascii characters,
# so we have this method to try and do the conversion for us
def os_path_join(dir, file):
    # Convert each argument - if an error, then it will use the default value
    # that was passed in
    try:
        dir = dir.decode("utf-8")
    except:
        pass
    try:
        file = file.decode("utf-8")
    except:
        pass
    return os.path.join(dir, file)


# Splits a path the same way as os.path.split but supports paths of a different
# OS than that being run on
def os_path_split(fullpath):
    # Check if it ends in a slash
    if fullpath.endswith("/") or fullpath.endswith("\\"):
        # Remove the slash character
        fullpath = fullpath[:-1]

    try:
        slash1 = fullpath.rindex("/")
    except:
        slash1 = -1

    try:
        slash2 = fullpath.rindex("\\")
    except:
        slash2 = -1

    # Parse based on the last type of slash in the string
    if slash1 > slash2:
        return fullpath.rsplit("/", 1)

    return fullpath.rsplit("\\", 1)


# Checks if a directory exists (Do not use for files)
def dir_exists(dirpath):
    directoryPath = dirpath
    # The xbmcvfs exists interface require that directories end in a slash
    # It used to be OK not to have the slash in Gotham, but it is now required
    if (not directoryPath.endswith("/")) and (not directoryPath.endswith("\\")):
        dirSep = "/"
        if "\\" in directoryPath:
            dirSep = "\\"
        directoryPath = "%s%s" % (directoryPath, dirSep)
    return xbmcvfs.exists(directoryPath)


##############################
# Stores Various Settings
##############################
class Settings():
    # Flags to show which section something is in
    MOVIES = 'movies'
    TVSHOWS = 'tvshows'
    MUSICVIDEOS = 'musicvideos'

    @staticmethod
    def getExcludeFiles():
        return __addon__.getSetting("excludeFilesRegex")

    @staticmethod
    def getExtrasDirName():
        return __addon__.getSetting("extrasDirName")

    @staticmethod
    def getExtrasFileTag():
        if __addon__.getSetting("enableFileTag") != "true":
            return ""
        return __addon__.getSetting("extrasFileTag")

    @staticmethod
    def isSearchNested():
        return __addon__.getSetting("searchNested") == "true"

    @staticmethod
    def isDetailedListScreen():
        return __addon__.getSetting("detailedList") == "true"

    @staticmethod
    def isMenuReturnVideoSelection():
        settingsSelect = "extrasReturn"
        if Settings.isDetailedListScreen():
            settingsSelect = "detailedReturn"
        return __addon__.getSetting(settingsSelect) == __addon__.getLocalizedString(32007)

    @staticmethod
    def isMenuReturnHome():
        settingsSelect = "extrasReturn"
        if Settings.isDetailedListScreen():
            settingsSelect = "detailedReturn"
        return __addon__.getSetting(settingsSelect) == __addon__.getLocalizedString(32009)

    @staticmethod
    def isMenuReturnInformation():
        settingsSelect = "extrasReturn"
        if Settings.isDetailedListScreen():
            settingsSelect = "detailedReturn"
        return __addon__.getSetting(settingsSelect) == __addon__.getLocalizedString(32008)

    @staticmethod
    def isMenuReturnExtras():
        if Settings.isDetailedListScreen():
            return False
        return __addon__.getSetting("extrasReturn") == __addon__.getLocalizedString(32001)

    @staticmethod
    def isForceButtonDisplay():
        return __addon__.getSetting("forceButtonDisplay") == "true"

    @staticmethod
    def isServiceEnabled():
        return __addon__.getSetting("serviceEnabled") == "true"

    @staticmethod
    def getAddonVersion():
        return __addon__.getAddonInfo('version')

    @staticmethod
    def isDatabaseEnabled():
        return __addon__.getSetting("enableDB") == "true"

    @staticmethod
    def isCustomPathEnabled():
        return __addon__.getSetting("custom_path_enable") == 'true'

    @staticmethod
    def getCustomPath(subtype=None):
        if Settings.isCustomPathEnabled():
            subTypeDir = ""
            if subtype is not None:
                if subtype == Settings.MOVIES:
                    subTypeDir = __addon__.getSetting("custom_path_movies")
                elif subtype == Settings.TVSHOWS:
                    subTypeDir = __addon__.getSetting("custom_path_tvshows")
                elif subtype == Settings.MUSICVIDEOS:
                    subTypeDir = __addon__.getSetting("custom_path_musicvideos")

            return os_path_join(__addon__.getSetting("custom_path"), subTypeDir)
        else:
            return None

    @staticmethod
    def getCustomOverlayImage():
        if __addon__.getSetting("useCustomImages") != "true":
            return None
        return __addon__.getSetting('overlayImage')

    @staticmethod
    def getCustomListImage():
        if __addon__.getSetting("useCustomImages") != "true":
            return None
        return __addon__.getSetting('listImage')
