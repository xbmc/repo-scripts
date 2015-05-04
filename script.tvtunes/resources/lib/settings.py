# -*- coding: utf-8 -*-
import unicodedata
import xbmc
import xbmcaddon
import os
import xbmcvfs

__addon__ = xbmcaddon.Addon(id='script.tvtunes')
__addonid__ = __addon__.getAddonInfo('id')


# Common logging module
def log(txt, debug_logging_enabled=True, loglevel=xbmc.LOGDEBUG):
    if ((__addon__.getSetting("logEnabled") == "true") and debug_logging_enabled) or (loglevel != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode("utf-8"), level=loglevel)


def normalize_string(text):
    try:
        text = text.replace(":", "")
        text = text.replace("/", "-")
        text = text.replace("\\", "-")
        text = text.strip()
        # Remove dots from the last character as windows can not have directories
        # with dots at the end
        text = text.rstrip('.')
        text = unicodedata.normalize('NFKD', unicode(text, 'utf-8')).encode('ascii', 'ignore')
    except:
        pass
    return text


# There has been problems with calling join with non ascii characters,
# so we have this method to try and do the conversion for us
def os_path_join(dir, file):
    # Check if it ends in a slash
    if dir.endswith("/") or dir.endswith("\\"):
        # Remove the slash character
        dir = dir[:-1]

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


# Get the contents of the directory
def list_dir(dirpath):
    # There is a problem with the afp protocol that means if a directory not ending
    # in a / is given, an error happens as it just appends the filename to the end
    # without actually checking there is a directory end character
    #    http://forum.xbmc.org/showthread.php?tid=192255&pid=1681373#pid1681373
    if dirpath.startswith('afp://') and (not dirpath.endswith('/')):
        dirpath = os_path_join(dirpath, '/')
    return xbmcvfs.listdir(dirpath)


# Checks if a directory exists (Do not use for files)
def dir_exists(dirpath):
    # There is an issue with password protected smb shares, in that they seem to
    # always return false for a directory exists call, so if we have a smb with
    # a password and user name, then we return true
    if Settings.isSmbEnabled() and ('@' in dirpath):
        return True

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
    ALL_ENGINES = 'All'
    TELEVISION_TUNES = 'televisiontunes.com'
    SOUNDCLOUD = 'soundcloud.com'
    GROOVESHARK = 'grooveshark.com'
    GOEAR = 'goear.com'
    PROMPT_ENGINE = 'Prompt User'

    # Settings for Automatically Downloading
    AUTO_DOWNLOAD_SINGLE_ITEM = 1
    AUTO_DOWNLOAD_PRIORITY_1 = 2
    AUTO_DOWNLOAD_PRIORITY_1_OR_2 = 2

    @staticmethod
    def isCustomPathEnabled():
        return __addon__.getSetting("custom_path_enable") == 'true'

    @staticmethod
    def getCustomPath():
        return __addon__.getSetting("custom_path").decode("utf-8")

    @staticmethod
    def getDownVolume():
        return int(float(__addon__.getSetting("downvolume")))

    @staticmethod
    def isLoop():
        return __addon__.getSetting("loop") == 'true'

    @staticmethod
    def isFadeOut():
        return __addon__.getSetting("fadeOut") == 'true'

    @staticmethod
    def isFadeIn():
        return __addon__.getSetting("fadeIn") == 'true'

    @staticmethod
    def isSmbEnabled():
        return __addon__.getSetting("smb_share") == 'true'

    @staticmethod
    def getSmbUser():
        if __addon__.getSetting("smb_login"):
            return __addon__.getSetting("smb_login")
        else:
            return "guest"

    @staticmethod
    def getSmbPassword():
        if __addon__.getSetting("smb_psw"):
            return __addon__.getSetting("smb_psw")
        else:
            return "guest"

    # Calculates the regular expression to use to search for theme files
    @staticmethod
    def getThemeFileRegEx(searchDir=None, extensionOnly=False):
        fileTypes = "mp3"  # mp3 is the default that is always supported
        if(__addon__.getSetting("wma") == 'true'):
            fileTypes = fileTypes + "|wma"
        if(__addon__.getSetting("flac") == 'true'):
            fileTypes = fileTypes + "|flac"
        if(__addon__.getSetting("m4a") == 'true'):
            fileTypes = fileTypes + "|m4a"
        if(__addon__.getSetting("wav") == 'true'):
            fileTypes = fileTypes + "|wav"
        themeRegEx = '(theme[ _A-Za-z0-9.-]*.(' + fileTypes + ')$)'
        # If using the directory method then remove the requirement to have "theme" in the name
        if (searchDir is not None) and Settings.isThemeDirEnabled():
            # Make sure this is checking the theme directory, not it's parent
            if searchDir.endswith(Settings.getThemeDirectory()):
                extensionOnly = True
        # See if we do not want the theme keyword
        if extensionOnly:
            themeRegEx = '(.(' + fileTypes + ')$)'
        return themeRegEx

    @staticmethod
    def isShuffleThemes():
        return __addon__.getSetting("shuffle") == 'true'

    @staticmethod
    def isRandomStart():
        return __addon__.getSetting("random") == 'true'

    @staticmethod
    def isPlayMovieList():
        return __addon__.getSetting("movielist") == 'true'

    @staticmethod
    def isPlayTvShowList():
        return __addon__.getSetting("tvlist") == 'true'

    @staticmethod
    def isPlayMusicVideoList():
        return __addon__.getSetting("musicvideolist") == 'true'

    @staticmethod
    def getPlayDurationLimit():
        return int(float(__addon__.getSetting("endafter")))

    @staticmethod
    def getTrackLengthLimit():
        return int(float(__addon__.getSetting("trackLengthLimit")))

    # Check if the video info button should be hidden
    @staticmethod
    def hideVideoInfoButton():
        return __addon__.getSetting("showVideoInfoButton") != 'true'

    # Check the delay start value
    @staticmethod
    def getStartDelaySeconds():
        return int(float(__addon__.getSetting("delayStart")))

    @staticmethod
    def isThemeDirEnabled():
        # Theme sub directory only supported when not using a custom path
        if Settings.isCustomPathEnabled():
            return False
        return __addon__.getSetting("searchSubDir") == 'true'

    @staticmethod
    def getThemeDirectory():
        # Load the information about storing themes in sub-directories
        # Only use the Theme dir if custom path is not used
        return __addon__.getSetting("subDirName")

    @staticmethod
    def getAutoDownloadSetting():
        return int(__addon__.getSetting("auto_download"))

    @staticmethod
    def isAutoDownloadPromptUser():
        # If no auto select is set, then always prompt the user
        if Settings.getAutoDownloadSetting() == 0:
            return True
        return __addon__.getSetting("auto_prompt_user_if_required") == 'true'

    @staticmethod
    def isMultiThemesSupported():
        return __addon__.getSetting("multiThemeDownload") == 'true'

    @staticmethod
    def isMovieDownloadEnabled():
        return __addon__.getSetting("searchMovieDownload") == 'true'

    @staticmethod
    def getSearchEngine():
        index = int(__addon__.getSetting("searchSource"))
        if index == 0:
            return Settings.ALL_ENGINES
        elif index == 1:
            return Settings.TELEVISION_TUNES
        elif index == 2:
            return Settings.SOUNDCLOUD
        elif index == 3:
            return Settings.GROOVESHARK
        elif index == 4:
            return Settings.GOEAR
        # Default is to prompt the user
        return Settings.PROMPT_ENGINE

    @staticmethod
    def getStartupVolume():
        # Check to see if the volume needs to be changed when the system starts
        if __addon__.getSetting("resetVolumeOnStartup") == 'true':
            return int(float(__addon__.getSetting("resetStartupVolumeValue")))
        return -1


# Class to handle all the screen saver settings
class ScreensaverSettings():
    MODES = (
        'TableDrop',
        'StarWars',
        'RandomZoomIn',
        'AppleTVLike',
        'GridSwitch',
        'Random',
        'Slider',
        'Crossfade'
    )
    SOURCES = (
        ['movies', 'tvshows'],
        ['movies'],
        ['tvshows'],
        ['image_folder']
    )
    IMAGE_TYPES = (
        ['fanart', 'thumbnail', 'cast'],
        ['fanart', 'thumbnail'],
        ['thumbnail', 'cast'],
        ['fanart'],
        ['thumbnail'],
        ['cast']
    )
    DIM_LEVEL = (
        'FFFFFFFF',
        'FFEEEEEE',
        'FFEEEEEE',
        'FFDDDDDD',
        'FFCCCCCC',
        'FFBBBBBB',
        'FFAAAAAA',
        'FF999999',
        'FF888888',
        'FF777777',
        'FF666666',
        'FF555555',
        'FF444444',
        'FF333333',
        'FF222222',
        'FF111111'
    )
    SLIDE_FROM = (
        'Left',
        'Right',
        'Top',
        'Bottom'
    )

    @staticmethod
    def getMode():
        if __addon__.getSetting("screensaver_mode"):
            return ScreensaverSettings.MODES[int(__addon__.getSetting("screensaver_mode"))]
        else:
            return 'Random'

    @staticmethod
    def getSource():
        selectedSource = __addon__.getSetting("screensaver_source")
        sourceId = 0
        if selectedSource:
            sourceId = int(selectedSource)
        return ScreensaverSettings.SOURCES[sourceId]

    @staticmethod
    def getImageTypes():
        imageTypes = __addon__.getSetting("screensaver_image_type")
        # If dealing with a custom folder, then no image type defined
        if ScreensaverSettings.getSource() == ['image_folder']:
            return []
        imageTypeId = 0
        if imageTypes:
            imageTypeId = int(imageTypes)
        return ScreensaverSettings.IMAGE_TYPES[imageTypeId]

    @staticmethod
    def getImagePath():
        return __addon__.getSetting("screensaver_image_path").decode("utf-8")

    @staticmethod
    def isRecursive():
        return __addon__.getSetting("screensaver_recursive") == 'true'

    @staticmethod
    def getWaitTime():
        return int(float(__addon__.getSetting('screensaver_wait_time')) * 1000)

    @staticmethod
    def getSpeed():
        return float(__addon__.getSetting('screensaver_speed'))

    @staticmethod
    def getEffectTime():
        return int(float(__addon__.getSetting('screensaver_effect_time')) * 1000)

    @staticmethod
    def getAppletvlikeConcurrency():
        return float(__addon__.getSetting('screensaver_appletvlike_concurrency'))

    @staticmethod
    def getGridswitchRowsColumns():
        return int(__addon__.getSetting('screensaver_gridswitch_columns'))

    @staticmethod
    def isGridswitchRandom():
        return __addon__.getSetting("screensaver_gridswitch_random") == 'true'

    @staticmethod
    def isPlayThemes():
        return __addon__.getSetting("screensaver_playthemes") == 'true'

    @staticmethod
    def isOnlyIfThemes():
        return __addon__.getSetting("screensaver_onlyifthemes") == 'true'

    @staticmethod
    def isRepeatTheme():
        return __addon__.getSetting("screensaver_themeControl") == '1'

    @staticmethod
    def isSkipAfterThemeOnce():
        return __addon__.getSetting("screensaver_themeControl") == '2'

    @staticmethod
    def getDimValue():
        # The actual dim level (Hex) is one of
        # FF111111, FF222222 ... FFEEEEEE, FFFFFFFF
        # Where FFFFFFFF is not changed
        # So that is a total of 15 different options
        if __addon__.getSetting("screensaver_dimlevel"):
            return ScreensaverSettings.DIM_LEVEL[int(__addon__.getSetting("screensaver_dimlevel"))]
        else:
            return 'FFFFFFFF'

    @staticmethod
    def getSlideFromOrigin():
        selectedOrigin = __addon__.getSetting("screensaver_slide_from")
        originId = 0
        if selectedOrigin:
            originId = int(selectedOrigin)
        return ScreensaverSettings.SLIDE_FROM[originId]

    @staticmethod
    def includeArtworkDownloader():
        # Make sure that the fanart is actually selected to be used, otherwise there is no
        # point in searching for it
        if 'fanart' in ScreensaverSettings.getImageTypes():
            return __addon__.getSetting("screensaver_artworkdownloader") == 'true'
        else:
            return False
