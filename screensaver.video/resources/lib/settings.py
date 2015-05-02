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
    # Locations:
    # ozibox.com
    #    Aquarium001.mkv
    #    Beach002-720p.mp4
    #    Fireplace001-720p.mkv
    #    Fireplace002.mkv
    #    Matrix001-720.mp4
    #    RetroSciFi-001-1080p.mp4
    #    Snow001-720p.mp4
    #    Snow002-1080p.mp4
    #    Snow003-1080p.mp4
    #    Space001-720p.mp4
    #    Space002-1080p.mp4
    #    StarTrekTNG-001-720p.mp4
    #    Woodland001-720p.mp4
    #    Waterfall001-720p.mp4
    #    Waterfall002-720p.mp4
    #    Watermill001-1080p.mp4
    # copy.com
    #    Aquarium002-720p.mkv
    #    Aquarium003-720p.mp4
    #    Beach001-720p.mp4
    #    Beach003-720p.mp4
    #    Fireplace003-1080p.mkv
    #    Fireplace004-720p.mp4
    #    Waterfall003-720p.mp4
    PRESET_VIDEOS = (
        [32101, "Aquarium001.mkv", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD03QTcyNTkyQTNBNUE0QTVRUVdFMjAxMTY2N0VXUVM="],
        [32102, "Aquarium002-720p.mkv", "aHR0cDovL2NvcHkuY29tL2NlbXZGQ213M016SVhOMU8vQXF1YXJpdW0wMDItNzIwcC5ta3Y="],
        [32106, "Aquarium003-720p.mp4", "aHR0cDovL2NvcHkuY29tLzFkaUJkN3Z6SWt3ZFpDdVQvQXF1YXJpdW0wMDMtNzIwcC5tcDQ="],
        [32109, "Beach001-720p.mp4", "aHR0cDovL2NvcHkuY29tL1VvRE1OZ0JWajBmTVFxeFYvQmVhY2gwMDEtNzIwcC5tcDQ="],
        [32110, "Beach002-720p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD1CN0U5RjZDRTNBNUE0QTVRUVdFMjEwMzI1MUVXUVM="],
        [32119, "Beach003-720p.mp4", "aHR0cDovL2NvcHkuY29tL0t0OVFsNlVlVEVLR09vZXUvQmVhY2gwMDMtNzIwcC5tcDQ="],
        [32103, "Fireplace001-720p.mkv", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD1ENzMwODE2OTNBNUE0QTVRUVdFMjAxMTcyOUVXUVM="],
        [32104, "Fireplace002.mkv", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD05QkRBRDdDODNBNUE0QTVRUVdFMjAxMTY4OUVXUVM="],
        [32105, "Fireplace003-1080p.mkv", "aHR0cDovL2NvcHkuY29tL1dzZEcwdmZ0cWl2V3NqWUQvRmlyZXBsYWNlMDAzLTEwODBwLm1rdg=="],
        [32107, "Fireplace004-720p.mp4", "aHR0cDovL2NvcHkuY29tL2I2VlJ6UTFYeEVmSXhwU0gvRmlyZXBsYWNlMDA0LTcyMHAubXA0"],
        [32111, "Matrix001-720p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD05RTczMTM0QjNBNUE0QTVRUVdFMjEwMzMyN0VXUVM="],
        [32115, "RetroSciFi-001-1080p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD02QjVCNzREQzNBNUE0QTVRUVdFMjEwNDA4N0VXUVM="],
        [32120, "Snow001-720p.mp4", "aHR0cDovLzE3OC4zMy42My42OC9wdXRzdG9yYWdlL0Rvd25sb2FkRmlsZUhhc2gvRjI5QkZFQzIzQTVBNEE1UVFXRTk0MTMzN0VXUVMvU25vdzAwMS03MjBwLm1wNA=="],
        [32121, "Snow002-1080p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlSGFzaC85MEE1NjhDRDNBNUE0QTVRUVdFMjc3ODg4N0VXUVMvU25vdzAwMi0xMDgwcC5tcDQ="],
        [32122, "Snow003-720p.mp4", "aHR0cDovLzE3OC4zMy42My42OC9wdXRzdG9yYWdlL0Rvd25sb2FkRmlsZUhhc2gvQjE0RUE1NDYzQTVBNEE1UVFXRTk0MTQ3MkVXUVMvU25vdzAwMy03MjBwLm1wNA=="],
        [32108, "Space001-720p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD1EQ0E4OTFEMTNBNUE0QTVRUVdFMjAxMTc3NkVXUVM="],
        [32112, "Space002-1080p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD00NDQxQ0JCNTNBNUE0QTVRUVdFMjEwMzA4OUVXUVM="],
        [32114, "StarTrekTNG-001-720p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD1FM0VFRTkyNzNBNUE0QTVRUVdFMjEwNDA4NEVXUVM="],
        [32116, "Waterfall001-720p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD0wNDk1NDU5RTNBNUE0QTVRUVdFMjExNTk2N0VXUVM="],
        [32117, "Waterfall002-720p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD0wQTRGQjAxMjNBNUE0QTVRUVdFMjExNTk4NUVXUVM="],
        [32118, "Waterfall003-720p.mp4", "aHR0cDovL2NvcHkuY29tL20xcnNFVXhjVXlBTWVOaGMvV2F0ZXJmYWxsMDAzLTcyMHAubXA0"],
        [32123, "Watermill001-1080p.mp4", "aHR0cDovLzE3OC4zMy42My42OC9wdXRzdG9yYWdlL0Rvd25sb2FkRmlsZUhhc2gvQTRDNzMxNkYzQTVBNEE1UVFXRTk0MTQ0OEVXUVMvV2F0ZXJtaWxsMDAxLTEwODBwLm1wNA=="],
        [32113, "Woodland001-720p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD0xODFDMjE1QjNBNUE0QTVRUVdFMjEwMzMyOUVXUVM="]
    )

    DIM_LEVEL = (
        '00000000',
        '11000000',
        '22000000',
        '33000000',
        '44000000',
        '55000000',
        '66000000',
        '77000000',
        '88000000',
        '99000000',
        'AA000000',
        'BB000000',
        'CC000000',
        'DD000000',
        'EE000000'
    )

    REPEAT_TYPE = (
        'RepeatAll',
        'RepeatOne'
    )

    OVERLAY_IMAGES = (
        None,
        'PictureFrame1.png',
        'WindowFrame1.png',
        'WindowFrame2.png',
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

    @staticmethod
    def isBlockScreensaverIfMediaPlaying():
        return __addon__.getSetting("mediaPlayingBlock") == 'true'

    @staticmethod
    def getVolume():
        if __addon__.getSetting("alterVolume") == 'false':
            return -1
        return int(float(__addon__.getSetting("screensaverVolume")))

    @staticmethod
    def getDimValue():
        # The actual dim level (Hex) is one of
        # Where 00000000 is not changed
        # So that is a total of 15 different options
        # FF000000 would be completely black, so we do not use that one
        if __addon__.getSetting("dimLevel"):
            return Settings.DIM_LEVEL[int(__addon__.getSetting("dimLevel"))]
        else:
            return '00000000'

    @staticmethod
    def screensaverTimeout():
        timoutSetting = 0
        if __addon__.getSetting("stopAutomatic") == 'true':
            timoutSetting = int(float(__addon__.getSetting("stopAfter")))
        return timoutSetting

    @staticmethod
    def getFolderRepeatType():
        repeatType = Settings.REPEAT_TYPE[0]
        if __addon__.getSetting("videoSelection") == "1":
            if Settings.isFolderSelection() and __addon__.getSetting("folderRepeatType"):
                repeatType = Settings.REPEAT_TYPE[int(__addon__.getSetting("folderRepeatType"))]
        return repeatType

    @staticmethod
    def getOverlayImage():
        if __addon__.getSetting("overlayImage"):
            overlayId = int(__addon__.getSetting("overlayImage"))
            # Check if this is is the manual defined option, so the last in the selection
            if overlayId >= len(Settings.OVERLAY_IMAGES):
                return __addon__.getSetting("overlayImageFile").decode("utf-8")
            else:
                return Settings.OVERLAY_IMAGES[overlayId]
        else:
            return None

    @staticmethod
    def getStartupVolume():
        # Check to see if the volume needs to be changed when the system starts
        if __addon__.getSetting("resetVolumeOnStartup") == 'true':
            return int(float(__addon__.getSetting("resetStartupVolumeValue")))
        return -1
