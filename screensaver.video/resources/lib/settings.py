# -*- coding: utf-8 -*-
import os
import time
import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon(id='screensaver.video')
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
    # It used to be OK not to have the slash in Gothan, but it is now required
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
    def isFolderSelection():
        return ADDON.getSetting("useFolder") == "true"

    @staticmethod
    def getScreensaverVideo():
        return ADDON.getSetting("screensaverFile").decode("utf-8")

    @staticmethod
    def getScreensaverFolder():
        screenFolder = ADDON.getSetting("screensaverFolder").decode("utf-8")

        # If the screensaver folder has not been set yet, then set it to default
        if screenFolder in [None, ""]:
            addonRootDir = xbmc.translatePath('special://profile/addon_data/%s' % ADDON_ID).decode("utf-8")
            screenFolder = os_path_join(addonRootDir, 'videos')
            ADDON.setSetting("screensaverFolder", screenFolder)

            # Make sure the screensaver folder exists, if not, createe it
            if not dir_exists(addonRootDir):
                xbmcvfs.mkdir(addonRootDir)
            if not dir_exists(screenFolder):
                xbmcvfs.mkdir(screenFolder)

        return screenFolder

    @staticmethod
    def getTempFolder():
        addonRootDir = xbmc.translatePath('special://profile/addon_data/%s' % ADDON_ID).decode("utf-8")
        tempDir = os_path_join(addonRootDir, 'temp')

        # Make sure the screensaver folder exists, if not, createe it
        if not dir_exists(addonRootDir):
            xbmcvfs.mkdir(addonRootDir)
        if not dir_exists(tempDir):
            xbmcvfs.mkdir(tempDir)

        return tempDir

    @staticmethod
    def getCustomFolder():
        addonRootDir = xbmc.translatePath('special://profile/addon_data/%s' % ADDON_ID).decode("utf-8")
        customDir = os_path_join(addonRootDir, 'custom')

        # Make sure the screensaver folder exists, if not, createe it
        if not dir_exists(addonRootDir):
            xbmcvfs.mkdir(addonRootDir)
        if not dir_exists(customDir):
            xbmcvfs.mkdir(customDir)

        return customDir

    @staticmethod
    def isFolderNested():
        nested = False
        if Settings.isFolderSelection():
            nested = ADDON.getSetting("screensaverFolderNested") == "true"
        return nested

    @staticmethod
    def isLimitSessionToSingleCollection():
        limitSessionToSingleCollection = False
        if Settings.isFolderSelection():
            limitSessionToSingleCollection = ADDON.getSetting("limitSessionToSingleCollection") == "true"
        return limitSessionToSingleCollection

    @staticmethod
    def cleanAddonSettings():
        # Set the default values for the schedule screensaver folders
        defaultFolder = Settings.getScreensaverFolder()
        if defaultFolder not in [None, ""]:
            # Make sure the directory path ends with a separator, otherwise it
            # will show the parent path
            if (not defaultFolder.endswith("/")) and (not defaultFolder.endswith("\\")):
                dirSep = "/"
                if "\\" in defaultFolder:
                    dirSep = "\\"
                defaultFolder = "%s%s" % (defaultFolder, dirSep)
            ruleNum = 1
            while ruleNum < 6:
                videoFileTag = "rule%dVideoFile" % ruleNum
                if ADDON.getSetting(videoFileTag) in [None, ""]:
                    ADDON.setSetting(videoFileTag, defaultFolder)
                ruleNum = ruleNum + 1

    @staticmethod
    def isShowTime():
        return ADDON.getSetting("showTime") == "true"

    @staticmethod
    def isRandomStart():
        return ADDON.getSetting("randomStart") == 'true'

    @staticmethod
    def isBlockScreensaverIfMediaPlaying():
        return ADDON.getSetting("mediaPlayingBlock") == 'true'

    @staticmethod
    def isLaunchOnStartup():
        return ADDON.getSetting("launchOnStartup") == 'true'

    @staticmethod
    def getVolume():
        if ADDON.getSetting("alterVolume") == 'false':
            return -1
        return int(float(ADDON.getSetting("screensaverVolume")))

    @staticmethod
    def getDimValue():
        # The actual dim level (Hex) is one of
        # Where 00000000 is not changed
        # So that is a total of 15 different options
        # FF000000 would be completely black, so we do not use that one
        if ADDON.getSetting("dimLevel"):
            return Settings.DIM_LEVEL[int(ADDON.getSetting("dimLevel"))]
        else:
            return '00000000'

    @staticmethod
    def screensaverTimeout():
        timoutSetting = 0
        if ADDON.getSetting("stopAutomatic") == 'true':
            timoutSetting = int(float(ADDON.getSetting("stopAfter")))
        return timoutSetting

    @staticmethod
    def isShutdownAfterTimeout():
        return ADDON.getSetting("stopAutomaticShutdown") == 'true'

    @staticmethod
    def getFolderRepeatType():
        repeatType = Settings.REPEAT_TYPE[0]
        if ADDON.getSetting("videoSelection") == "1":
            if Settings.isFolderSelection() and ADDON.getSetting("folderRepeatType"):
                repeatType = Settings.REPEAT_TYPE[int(ADDON.getSetting("folderRepeatType"))]
        return repeatType

    @staticmethod
    def getOverlayImage():
        if ADDON.getSetting("overlayImage"):
            overlayId = int(ADDON.getSetting("overlayImage"))
            # Check if this is is the manual defined option, so the last in the selection
            if overlayId >= len(Settings.OVERLAY_IMAGES):
                return ADDON.getSetting("overlayImageFile").decode("utf-8")
            else:
                return Settings.OVERLAY_IMAGES[overlayId]
        else:
            return None

    @staticmethod
    def getStartupVolume():
        # Check to see if the volume needs to be changed when the system starts
        if ADDON.getSetting("resetVolumeOnStartup") == 'true':
            return int(float(ADDON.getSetting("resetStartupVolumeValue")))
        return -1

    @staticmethod
    def isUseAudioSuspend():
        if Settings.getVolume() == 0:
            return ADDON.getSetting("useAudioSuspend") == 'true'
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
        return int(ADDON.getSetting("scheduleSource"))

    @staticmethod
    def getScheduleFile():
        if Settings.getScheduleSetting() == Settings.SCHEDULE_FILE:
            return ADDON.getSetting("scheduleFile")
        return None

    @staticmethod
    def getNumberOfScheduleRules():
        if Settings.getScheduleSetting() == Settings.SCHEDULE_SETTINGS:
            return int(ADDON.getSetting("numberOfSchuleRules"))
        return 0

    @staticmethod
    def getRuleVideoFile(ruleId):
        videoFileTag = "rule%dVideoFile" % ruleId
        return ADDON.getSetting(videoFileTag)

    @staticmethod
    def getRuleOverlayFile(ruleId):
        overlayImageTag = "rule%dOverlayImage" % ruleId

        if ADDON.getSetting(overlayImageTag):
            overlayId = int(ADDON.getSetting(overlayImageTag))
            # Check if this is is the manual defined option, so the last in the selection
            if overlayId >= len(Settings.OVERLAY_IMAGES):
                overlayFileTag = "rule%dOverlayFile" % ruleId
                return ADDON.getSetting(overlayFileTag).decode("utf-8")
            else:
                return Settings.OVERLAY_IMAGES[overlayId]
        return None

    @staticmethod
    def getRuleStartTime(ruleId):
        startTimeTag = "rule%dStartTime" % ruleId
        # Get the start time
        startTimeStr = ADDON.getSetting(startTimeTag)
        startTimeSplit = startTimeStr.split(':')
        startTime = (int(startTimeSplit[0]) * 60) + int(startTimeSplit[1])
        return startTime

    @staticmethod
    def getRuleEndTime(ruleId):
        endTimeTag = "rule%dEndTime" % ruleId
        # Get the end time
        endTimeStr = ADDON.getSetting(endTimeTag)
        endTimeSplit = endTimeStr.split(':')
        endTime = (int(endTimeSplit[0]) * 60) + int(endTimeSplit[1])
        return endTime

    @staticmethod
    def getRuleDay(ruleId):
        dayTag = "rule%dDay" % ruleId

        if ADDON.getSetting(dayTag):
            dayId = int(ADDON.getSetting(dayTag))
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

    @staticmethod
    def getWeatherAddon():
        weatherAddon = None
        if ADDON.getSetting("showWeather") == 'true':
            weatherAddon = ADDON.getSetting("weatherAddon")
        return weatherAddon
