# -*- coding: utf-8 -*-
import os
import time
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


# There has been problems with calling isfile with non ascii characters,
# so we have this method to try and do the conversion for us
def os_path_isfile(workingPath,):
    # Convert each argument - if an error, then it will use the default value
    # that was passed in
    try:
        workingPath = workingPath.decode("utf-8")
    except:
        pass
    try:
        return os.path.isfile(workingPath)
    except:
        return False


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
    SCHEDULE_OFF = 0
    SCHEDULE_SETTINGS = 1
    SCHEDULE_FILE = 2

    EVERY_DAY = -1
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

    # Locations:
    # ozibox.com
    #    Aquarium001.mkv
    #    Aquarium004-720p.mp4
    #    Beach002-720p.mp4
    #    Christmas001-1080p.mp4
    #    Clock001-720p.mp4
    #    Clock002-360p.mp4
    #    Fireplace001-720p.mkv
    #    Fireplace002.mkv
    #    JohnnyCastaway001-480.mp4
    #    Matrix001-720.mp4
    #    Ocean001-720p.mp4
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
    #
    # copy.com
    #    Aquarium002-720p.mkv
    #    Aquarium003-720p.mp4
    #    Aquarium005-720p.mkv
    #    Beach001-720p.mp4
    #    Beach003-720p.mp4
    #    Fireplace003-1080p.mkv
    #    Fireplace004-720p.mp4
    #    Space003-720p.mkv
    #    Waterfall003-720p.mp4
    PRESET_VIDEOS = (
        [32101, "Aquarium001.mkv", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD03QTcyNTkyQTNBNUE0QTVRUVdFMjAxMTY2N0VXUVM="],
        [32102, "Aquarium002-720p.mkv", "aHR0cDovL2NvcHkuY29tL2NlbXZGQ213M016SVhOMU8/ZG93bmxvYWQ9MQ=="],
        [32106, "Aquarium003-720p.mp4", "aHR0cDovL2NvcHkuY29tLzFkaUJkN3Z6SWt3ZFpDdVQ/ZG93bmxvYWQ9MQ=="],
        [32124, "Aquarium004-720p.mp4", "aHR0cDovLzE3OC4zMy42My42OC9wdXRzdG9yYWdlL0Rvd25sb2FkRmlsZUhhc2gvQ0NCNDY2NDEzQTVBNEE1UVFXRTEzMDY2OTlFV1FTL0FxdWFyaXVtMDA0LTcyMHAubXA0"],
        [32128, "Aquarium005-720p.mkv", "aHR0cDovL2NvcHkuY29tL0Y4NnRrUU9kR3hRVEVBR1Q/ZG93bmxvYWQ9MQ=="],
        [32109, "Beach001-720p.mp4", "aHR0cDovL2NvcHkuY29tL1VvRE1OZ0JWajBmTVFxeFY/ZG93bmxvYWQ9MQ=="],
        [32110, "Beach002-720p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD1CN0U5RjZDRTNBNUE0QTVRUVdFMjEwMzI1MUVXUVM="],
        [32119, "Beach003-720p.mp4", "aHR0cDovL2NvcHkuY29tL0t0OVFsNlVlVEVLR09vZXU/ZG93bmxvYWQ9MQ=="],
        [32125, "Christmas001-1080p.mp4", "aHR0cDovLzE3OC4zMy42My42OC9wdXRzdG9yYWdlL0Rvd25sb2FkRmlsZUhhc2gvQjE0NEQ1MDIzQTVBNEE1UVFXRTEzMDY3MDJFV1FTL0NocmlzdG1hczAwMS0xMDgwcC5tcDQ="],
        [32130, "Clock001-720p.mp4", "aHR0cDovLzE3OC4zMy42My42OC9wdXRzdG9yYWdlL0Rvd25sb2FkRmlsZUhhc2gvRDZBRjc2MEEzQTVBNEE1UVFXRTE1MDM1OTRFV1FTL0Nsb2NrMDAxLTcyMHAubXA0"],
        [32131, "Clock002-360p.mp4", "aHR0cDovLzE3OC4zMy42My42OC9wdXRzdG9yYWdlL0Rvd25sb2FkRmlsZUhhc2gvQjFDMjJCNTMzQTVBNEE1UVFXRTE1MDM1OThFV1FTL0Nsb2NrMDAyLTM2MHAubXA0"],
        [32103, "Fireplace001-720p.mkv", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD1ENzMwODE2OTNBNUE0QTVRUVdFMjAxMTcyOUVXUVM="],
        [32104, "Fireplace002.mkv", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD05QkRBRDdDODNBNUE0QTVRUVdFMjAxMTY4OUVXUVM="],
        [32105, "Fireplace003-1080p.mkv", "aHR0cDovL2NvcHkuY29tL1dzZEcwdmZ0cWl2V3NqWUQ/ZG93bmxvYWQ9MQ=="],
        [32107, "Fireplace004-720p.mp4", "aHR0cDovL2NvcHkuY29tL2I2VlJ6UTFYeEVmSXhwU0g/ZG93bmxvYWQ9MQ=="],
        [32126, "JohnnyCastaway001-480.mp4", "aHR0cDovLzE3OC4zMy42My42OC9wdXRzdG9yYWdlL0Rvd25sb2FkRmlsZUhhc2gvODU1RDlBMDQzQTVBNEE1UVFXRTEzMDY2ODhFV1FTL0pvaG5ueUNhc3Rhd2F5MDAxLTQ4MC5tcDQ="],
        [32111, "Matrix001-720p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD05RTczMTM0QjNBNUE0QTVRUVdFMjEwMzMyN0VXUVM="],
        [32127, "Ocean001-720p.mp4", "aHR0cDovLzE3OC4zMy42My42OC9wdXRzdG9yYWdlL0Rvd25sb2FkRmlsZUhhc2gvMjI2NzJBNzczQTVBNEE1UVFXRTEzMTg1NDlFV1FTL09jZWFuMDAxLTcyMHAubXA0"],
        [32115, "RetroSciFi-001-1080p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD02QjVCNzREQzNBNUE0QTVRUVdFMjEwNDA4N0VXUVM="],
        [32120, "Snow001-720p.mp4", "aHR0cDovLzE3OC4zMy42My42OC9wdXRzdG9yYWdlL0Rvd25sb2FkRmlsZUhhc2gvRjI5QkZFQzIzQTVBNEE1UVFXRTk0MTMzN0VXUVMvU25vdzAwMS03MjBwLm1wNA=="],
        [32121, "Snow002-1080p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlSGFzaC85MEE1NjhDRDNBNUE0QTVRUVdFMjc3ODg4N0VXUVMvU25vdzAwMi0xMDgwcC5tcDQ="],
        [32122, "Snow003-720p.mp4", "aHR0cDovLzE3OC4zMy42My42OC9wdXRzdG9yYWdlL0Rvd25sb2FkRmlsZUhhc2gvQjE0RUE1NDYzQTVBNEE1UVFXRTk0MTQ3MkVXUVMvU25vdzAwMy03MjBwLm1wNA=="],
        [32108, "Space001-720p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD1EQ0E4OTFEMTNBNUE0QTVRUVdFMjAxMTc3NkVXUVM="],
        [32112, "Space002-1080p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD00NDQxQ0JCNTNBNUE0QTVRUVdFMjEwMzA4OUVXUVM="],
        [32129, "Space003-720p.mp4", "aHR0cDovL2NvcHkuY29tL3NEZDByM0gxRldZVGptUjk/ZG93bmxvYWQ9MQ=="],
        [32114, "StarTrekTNG-001-720p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD1FM0VFRTkyNzNBNUE0QTVRUVdFMjEwNDA4NEVXUVM="],
        [32116, "Waterfall001-720p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD0wNDk1NDU5RTNBNUE0QTVRUVdFMjExNTk2N0VXUVM="],
        [32117, "Waterfall002-720p.mp4", "aHR0cDovLzE3OC4zMy42MS42L3B1dHN0b3JhZ2UvRG93bmxvYWRGaWxlLmFzaHg/RG93bmxvYWRGaWxlSGFzaD0wQTRGQjAxMjNBNUE0QTVRUVdFMjExNTk4NUVXUVM="],
        [32118, "Waterfall003-720p.mp4", "aHR0cDovL2NvcHkuY29tL20xcnNFVXhjVXlBTWVOaGM/ZG93bmxvYWQ9MQ=="],
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

    DAY_TYPE = (
        EVERY_DAY,
        MONDAY,
        TUESDAY,
        WEDNESDAY,
        THURSDAY,
        FRIDAY,
        SATURDAY,
        SUNDAY
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
    def isFolderNested():
        nested = False
        if Settings.isFolderSelection():
            nested = __addon__.getSetting("screensaverFolderNested") == "true"
        return nested

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

        # Set the default values for the schedule screensaver folders
        defaultFolder = Settings.getScreensaverFolder()
        if defaultFolder not in [None, ""]:
            # Make sure the directory path ends with a seperator, otherwise it
            # will show the parent path
            if (not defaultFolder.endswith("/")) and (not defaultFolder.endswith("\\")):
                dirSep = "/"
                if "\\" in defaultFolder:
                    dirSep = "\\"
                defaultFolder = "%s%s" % (defaultFolder, dirSep)
            ruleNum = 1
            while ruleNum < 6:
                videoFileTag = "rule%dVideoFile" % ruleNum
                if __addon__.getSetting(videoFileTag) in [None, ""]:
                    __addon__.setSetting(videoFileTag, defaultFolder)
                ruleNum = ruleNum + 1

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
    def isLaunchOnStartup():
        return __addon__.getSetting("launchOnStartup") == 'true'

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
    def isShutdownAfterTimeout():
        return __addon__.getSetting("stopAutomaticShutdown") == 'true'

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

    @staticmethod
    def isUseAudioSuspend():
        if Settings.getVolume() == 0:
            return __addon__.getSetting("useAudioSuspend") == 'true'
        return False

    @staticmethod
    def getTimeForClock(filenameAndPath, duration):
        startTime = 0
        justFilename = os_path_split(filenameAndPath)[-1]
        # Check if we are dealing with a clock
        if 'clock' in justFilename.lower():
            # Get the current time, we need to convert
            localTime = time.localtime()
            startTime = (((localTime.tm_hour * 60) + localTime.tm_min) * 60) + localTime.tm_sec

            # Check if the video is the 12 hour or 24 hour clock
            if duration < 46800:
                # 12 hour clock
                log("12 hour clock detected for %s" % justFilename)
                if startTime > 43200:
                    startTime = startTime - 43200
            else:
                log("24 hour clock detected for %s" % justFilename)

        # Just make sure that the start time is not larger than the duration
        if startTime > duration:
            log("Start time %d later than duration %d" % (startTime, duration))
            startTime = 0

        return startTime

    @staticmethod
    def getScheduleSetting():
        return int(__addon__.getSetting("scheduleSource"))

    @staticmethod
    def getScheduleFile():
        if Settings.getScheduleSetting() == Settings.SCHEDULE_FILE:
            return __addon__.getSetting("scheduleFile")
        return None

    @staticmethod
    def getNumberOfScheduleRules():
        if Settings.getScheduleSetting() == Settings.SCHEDULE_SETTINGS:
            return int(__addon__.getSetting("numberOfSchuleRules"))
        return 0

    @staticmethod
    def getRuleVideoFile(ruleId):
        videoFileTag = "rule%dVideoFile" % ruleId
        return __addon__.getSetting(videoFileTag)

    @staticmethod
    def getRuleOverlayFile(ruleId):
        overlayImageTag = "rule%dOverlayImage" % ruleId

        if __addon__.getSetting(overlayImageTag):
            overlayId = int(__addon__.getSetting(overlayImageTag))
            # Check if this is is the manual defined option, so the last in the selection
            if overlayId >= len(Settings.OVERLAY_IMAGES):
                overlayFileTag = "rule%dOverlayFile" % ruleId
                return __addon__.getSetting(overlayFileTag).decode("utf-8")
            else:
                return Settings.OVERLAY_IMAGES[overlayId]
        return None

    @staticmethod
    def getRuleStartTime(ruleId):
        startTimeTag = "rule%dStartTime" % ruleId
        # Get the start time
        startTimeStr = __addon__.getSetting(startTimeTag)
        startTimeSplit = startTimeStr.split(':')
        startTime = (int(startTimeSplit[0]) * 60) + int(startTimeSplit[1])
        return startTime

    @staticmethod
    def getRuleEndTime(ruleId):
        endTimeTag = "rule%dEndTime" % ruleId
        # Get the end time
        endTimeStr = __addon__.getSetting(endTimeTag)
        endTimeSplit = endTimeStr.split(':')
        endTime = (int(endTimeSplit[0]) * 60) + int(endTimeSplit[1])
        return endTime

    @staticmethod
    def getRuleDay(ruleId):
        dayTag = "rule%dDay" % ruleId

        if __addon__.getSetting(dayTag):
            dayId = int(__addon__.getSetting(dayTag))
            if dayId >= len(Settings.DAY_TYPE):
                return Settings.EVERY_DAY
            else:
                return Settings.DAY_TYPE[dayId]
        return Settings.EVERY_DAY

    @staticmethod
    def getNextDay(currentDay):
        nextDay = Settings.MONDAY
        # We know the days are sequential so we can just add one to the value
        # If we were at Sunday (The end of the list), then we need to go to the Monday
        if currentDay != Settings.SUNDAY:
            nextDay = currentDay + 1
        return nextDay
