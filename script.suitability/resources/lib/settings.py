# -*- coding: utf-8 -*-
import os
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon(id='script.suitability')
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


##############################
# Stores Various Settings
##############################
class Settings():
    # Note: The following values match the string values for each type
    # This makes it easier to display text to the user based on these types
    COMMON_SENSE_MEDIA = 32008
    KIDS_IN_MIND = 32009
    DOVE_FOUNDATION = 32024
    MOVIE_GUIDE_ORG = 32025

    VIEWER_SUMMARY = 1
    VIEWER_DETAILED = 2

    @staticmethod
    def getDefaultSource():
        index = int(ADDON.getSetting("defaultSource"))
        if index == 0:
            return Settings.COMMON_SENSE_MEDIA
        elif index == 1:
            return Settings.KIDS_IN_MIND
        elif index == 2:
            return Settings.DOVE_FOUNDATION
        elif index == 2:
            return Settings.MOVIE_GUIDE_ORG

        return Settings.COMMON_SENSE_MEDIA

    @staticmethod
    def getDefaultViewer():
        index = int(ADDON.getSetting("defaultViewer"))
        if index == 0:
            return Settings.VIEWER_SUMMARY
        elif index == 1:
            return Settings.VIEWER_DETAILED

        return Settings.VIEWER_SUMMARY

    @staticmethod
    def showOnContextMenu():
        return ADDON.getSetting("showOnContextMenu") == "true"

    @staticmethod
    def getNextSource(currentSource):
        # Read the setting to see which order they should be in
        order = [None, None, None, None]

        index = int(ADDON.getSetting("commonSenseMediaPosition"))
        if (index > 0) and (index < 5):
            if order[index - 1] is None:
                order[index - 1] = Settings.COMMON_SENSE_MEDIA
            else:
                order.append(Settings.COMMON_SENSE_MEDIA)
        index = int(ADDON.getSetting("kidsInMindPosition"))
        if (index > 0) and (index < 5):
            if order[index - 1] is None:
                order[index - 1] = Settings.KIDS_IN_MIND
            else:
                order.append(Settings.KIDS_IN_MIND)
        index = int(ADDON.getSetting("doveFoundationPosition"))
        if (index > 0) and (index < 5):
            if order[index - 1] is None:
                order[index - 1] = Settings.DOVE_FOUNDATION
            else:
                order.append(Settings.DOVE_FOUNDATION)
        index = int(ADDON.getSetting("movieGuideOrgPosition"))
        if (index > 0) and (index < 5):
            if order[index - 1] is None:
                order[index - 1] = Settings.MOVIE_GUIDE_ORG
            else:
                order.append(Settings.MOVIE_GUIDE_ORG)

        # Now remove any of the None elements
        order = [x for x in order if x is not None]

        # Check for the case where the default value is not in the
        # ordered list, we will automatically add it to the end
        if currentSource not in order:
            order.append(currentSource)

        # Check for the case where there is only one search provider
        # in which case there is no "next"
        if len(order) < 2:
            return None

        # Get the current index of the source
        currentSourceIdx = order.index(currentSource)
        nextIdx = currentSourceIdx + 1
        if nextIdx >= len(order):
            nextIdx = 0
        return order[nextIdx]
