# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon(id='screensaver.random')
ADDON_ID = ADDON.getAddonInfo('id')


# Common logging module
def log(txt, loglevel=xbmc.LOGDEBUG):
    if (ADDON.getSetting("logEnabled") == "true") or (loglevel != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (ADDON_ID, txt)
        xbmc.log(msg=message.encode("utf-8"), level=loglevel)


##############################
# Stores Various Settings
##############################
class Settings():
    MODE_RANDOM = 0
    MODE_SCHEDULE = 1

    @staticmethod
    def getExcludedScreensavers():
        excludes = ADDON.getSetting("excludedScreensavers")
        if excludes in [None, ""]:
            return []
        return excludes.split(',')

    @staticmethod
    def isRandomMode():
        if int(ADDON.getSetting("mode")) != Settings.MODE_SCHEDULE:
            return True
        return False

    @staticmethod
    def isScheduleMode():
        if int(ADDON.getSetting("mode")) == Settings.MODE_SCHEDULE:
            return True
        return False

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
    def getRuleScreensaver(ruleId):
        screensaverTag = "rule%dScreensaver" % ruleId
        return ADDON.getSetting(screensaverTag)

    @staticmethod
    def getNumberOfScheduleRules():
        return int(ADDON.getSetting("numberOfSchuleRules"))

    @staticmethod
    def getScheduledScreensaver(currentTime):
        i = 1
        while i <= Settings.getNumberOfScheduleRules():
            if (currentTime >= Settings.getRuleStartTime(i)) and (currentTime <= Settings.getRuleEndTime(i)):
                return Settings.getRuleScreensaver(i)
            i = i + 1
        return None
