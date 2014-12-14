# -*- coding: utf-8 -*-
import os
import xbmc
import xbmcaddon
import xbmcvfs

__addon__ = xbmcaddon.Addon(id='screensaver.video')
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


# Get the contents of the directory
def list_dir(dirpath):
    # There is a problem with the afp protocol that means if a directory not ending
    # in a / is given, an error happens as it just appends the filename to the end
    # without actually checking there is a directory end character
    #    http://forum.xbmc.org/showthread.php?tid=192255&pid=1681373#pid1681373
    if dirpath.startswith('afp://') and (not dirpath.endswith('/')):
        dirpath = os_path_join(dirpath, '/')
    return xbmcvfs.listdir(dirpath)


##############################
# Stores Various Settings
##############################
class Settings():
    PRESET_VIDEOS = (
        [32101, "Aquarium001.mkv", "aHR0cHM6Ly9vbmVkcml2ZS5saXZlLmNvbS9kb3dubG9hZD9yZXNpZD04MEJEMTY5NjNGNUMyMUI1ITEyNyZhdXRoa2V5PSFBTGV4OFBrY3dWOExWSmc="],
        [32102, "Aquarium002-720p.mkv", "aHR0cHM6Ly9vbmVkcml2ZS5saXZlLmNvbS9kb3dubG9hZD9yZXNpZD04MEJEMTY5NjNGNUMyMUI1ITEyOCZhdXRoa2V5PSFBUG5OZkM4WUFDMjBVbUU="],
        [32103, "Fireplace001-720p.mkv", "aHR0cHM6Ly9vbmVkcml2ZS5saXZlLmNvbS9kb3dubG9hZD9yZXNpZD04MEJEMTY5NjNGNUMyMUI1ITEyOSZhdXRoa2V5PSFBR0VlekE2VFRHVV91ck0="],
        [32104, "Fireplace002.mkv", "aHR0cHM6Ly9vbmVkcml2ZS5saXZlLmNvbS9kb3dubG9hZD9yZXNpZD04MEJEMTY5NjNGNUMyMUI1ITEzMCZhdXRoa2V5PSFBT2ZfQ2xXbWp6cWtvdVE="],
        [32105, "Fireplace003-1080p.mkv", "aHR0cHM6Ly9vbmVkcml2ZS5saXZlLmNvbS9kb3dubG9hZD9yZXNpZD04MEJEMTY5NjNGNUMyMUI1ITEzMSZhdXRoa2V5PSFBQ1ptU0FlRFRVeGR6MjA="]
    )

    @staticmethod
    def getScreensaverVideo():
        return __addon__.getSetting("screensaverFile").decode("utf-8")

    @staticmethod
    def setScreensaverVideo(screensaverFile):
        __addon__.setSetting("useFolder", "false")
        __addon__.setSetting("screensaverFile", screensaverFile)
        __addon__.setSetting("screensaverFolder", "")

    @staticmethod
    def getScreensaverFolder():
        return __addon__.getSetting("screensaverFolder").decode("utf-8")

    @staticmethod
    def setScreensaverFolder(screensaverFolder):
        __addon__.setSetting("useFolder", "true")
        __addon__.setSetting("screensaverFolder", screensaverFolder)
        __addon__.setSetting("screensaverFile", "")

    @staticmethod
    def isFolderSelection():
        return __addon__.getSetting("useFolder") == "true"

    @staticmethod
    def setVideoSelectionPredefined():
        __addon__.setSetting("videoSelection", "0")

    @staticmethod
    def cleanAddonSettings():
        # We do this because this is a display field and if a user
        # 1) Selects the "Manual Define"
        # 2) Select a custom video
        # 3) Returns to "Built in Videos"
        # Then it will show the last built in video, which is not accurate
        if __addon__.getSetting("videoSelection") == "1":
            __addon__.setSetting("displaySelected", "")

    @staticmethod
    def setPresetVideoSelected(id):
        if id is not None:
            if id != -1:
                __addon__.setSetting("displaySelected", __addon__.getLocalizedString(Settings.PRESET_VIDEOS[id][0]))
            else:
                __addon__.setSetting("displaySelected", __addon__.getLocalizedString(32100))

    @staticmethod
    def isShowTime():
        return __addon__.getSetting("showTime") == "true"

    @staticmethod
    def isRandomStart():
        return __addon__.getSetting("randomStart") == 'true'
