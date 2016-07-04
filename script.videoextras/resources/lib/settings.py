# -*- coding: utf-8 -*-
import os
import unicodedata
import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon(id='script.videoextras')
ADDON_ID = ADDON.getAddonInfo('id')


# Common logging module
def log(txt, loglevel=xbmc.LOGDEBUG):
    if (ADDON.getSetting("logEnabled") == "true") or (loglevel != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (ADDON_ID, txt)
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


# Remove characters that can not be used as directory path names
def normalize_string(text):
    try:
        text = text.replace(":", "")
        text = text.replace("/", "-")
        text = text.replace("\\", "-")
        text = text.replace("<", "")
        text = text.replace(">", "")
        text = text.replace("*", "")
        text = text.replace("?", "")
        text = text.replace('|', "")
        text = text.strip()
        # Remove dots from the last character as windows can not have directories
        # with dots at the end
        text = text.rstrip('.')
        text = unicodedata.normalize('NFKD', unicode(text, 'utf-8')).encode('ascii', 'ignore')
    except:
        pass
    return text


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
        return ADDON.getSetting("excludeFilesRegex")

    @staticmethod
    def getExtrasDirName():
        return ADDON.getSetting("extrasDirName")

    @staticmethod
    def getExtrasFileTag():
        if ADDON.getSetting("enableFileTag") != "true":
            return ""
        return ADDON.getSetting("extrasFileTag")

    @staticmethod
    def isSearchNested():
        return ADDON.getSetting("searchNested") == "true"

    @staticmethod
    def isDetailedListScreen():
        return ADDON.getSetting("detailedList") == "true"

    @staticmethod
    def isMenuReturnVideoSelection():
        settingsSelect = "extrasReturn"
        if Settings.isDetailedListScreen():
            settingsSelect = "detailedReturn"
        return ADDON.getSetting(settingsSelect) == ADDON.getLocalizedString(32007)

    @staticmethod
    def isMenuReturnHome():
        settingsSelect = "extrasReturn"
        if Settings.isDetailedListScreen():
            settingsSelect = "detailedReturn"
        return ADDON.getSetting(settingsSelect) == ADDON.getLocalizedString(32009)

    @staticmethod
    def isMenuReturnInformation():
        settingsSelect = "extrasReturn"
        if Settings.isDetailedListScreen():
            settingsSelect = "detailedReturn"
        return ADDON.getSetting(settingsSelect) == ADDON.getLocalizedString(32008)

    @staticmethod
    def isMenuReturnExtras():
        if Settings.isDetailedListScreen():
            return False
        return ADDON.getSetting("extrasReturn") == ADDON.getLocalizedString(32001)

    @staticmethod
    def isForceButtonDisplay():
        return ADDON.getSetting("forceButtonDisplay") == "true"

    @staticmethod
    def showOnContextMenu():
        return ADDON.getSetting("showOnContextMenu") == "true"

    @staticmethod
    def isServiceEnabled():
        return ADDON.getSetting("serviceEnabled") == "true"

    @staticmethod
    def getAddonVersion():
        return ADDON.getAddonInfo('version')

    @staticmethod
    def isDatabaseEnabled():
        return ADDON.getSetting("enableDB") == "true"

    @staticmethod
    def isCustomPathEnabled():
        return ADDON.getSetting("custom_path_enable") == 'true'

    @staticmethod
    def getCustomPath(subtype=None):
        if Settings.isCustomPathEnabled():
            subTypeDir = ""
            if subtype is not None:
                if subtype == Settings.MOVIES:
                    subTypeDir = ADDON.getSetting("custom_path_movies")
                elif subtype == Settings.TVSHOWS:
                    subTypeDir = ADDON.getSetting("custom_path_tvshows")
                elif subtype == Settings.MUSICVIDEOS:
                    subTypeDir = ADDON.getSetting("custom_path_musicvideos")

            return os_path_join(ADDON.getSetting("custom_path"), subTypeDir)
        else:
            return None

    @staticmethod
    def getCustomOverlayImage():
        if ADDON.getSetting("useCustomImages") != "true":
            return None
        return ADDON.getSetting('overlayImage')

    @staticmethod
    def getCustomListImage():
        if ADDON.getSetting("useCustomImages") != "true":
            return None
        return ADDON.getSetting('listImage')

    @staticmethod
    def isYouTubeSearchSupportEnabled():
        return ADDON.getSetting("enableYouTubeSearchSupport") == 'true'

    @staticmethod
    def disableYouTubeSearchSupport():
        ADDON.setSetting("enableYouTubeSearchSupport", "false")

    @staticmethod
    def isVimeoSearchSupportEnabled():
        return ADDON.getSetting("enableVimeoSearchSupport") == 'true'

    @staticmethod
    def disableVimeoSearchSupport():
        ADDON.setSetting("enableVimeoSearchSupport", "false")

    @staticmethod
    def showExtrasAfterMovie():
        return ADDON.getSetting("showExtrasAfterMovie") == 'true'
