# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon(id='screensaver.tvtunes')
ADDON_ID = ADDON.getAddonInfo('id')


# Common logging module
def log(txt, debug_logging_enabled=True, loglevel=xbmc.LOGDEBUG):
    if ((ADDON.getSetting("logEnabled") == "true") and debug_logging_enabled) or (loglevel != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (ADDON_ID, txt)
        xbmc.log(msg=message.encode("utf-8"), level=loglevel)


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
        if ADDON.getSetting("screensaver_mode"):
            return ScreensaverSettings.MODES[int(ADDON.getSetting("screensaver_mode"))]
        else:
            return 'Random'

    @staticmethod
    def getSource():
        selectedSource = ADDON.getSetting("screensaver_source")
        sourceId = 0
        if selectedSource:
            sourceId = int(selectedSource)
        return ScreensaverSettings.SOURCES[sourceId]

    @staticmethod
    def getImageTypes():
        imageTypes = ADDON.getSetting("screensaver_image_type")
        # If dealing with a custom folder, then no image type defined
        if ScreensaverSettings.getSource() == ['image_folder']:
            return []
        imageTypeId = 0
        if imageTypes:
            imageTypeId = int(imageTypes)
        return ScreensaverSettings.IMAGE_TYPES[imageTypeId]

    @staticmethod
    def getImagePath():
        return ADDON.getSetting("screensaver_image_path").decode("utf-8")

    @staticmethod
    def isRecursive():
        return ADDON.getSetting("screensaver_recursive") == 'true'

    @staticmethod
    def getWaitTime():
        return int(float(ADDON.getSetting('screensaver_wait_time')) * 1000)

    @staticmethod
    def getSpeed():
        return float(ADDON.getSetting('screensaver_speed'))

    @staticmethod
    def getEffectTime():
        return int(float(ADDON.getSetting('screensaver_effect_time')) * 1000)

    @staticmethod
    def getAppletvlikeConcurrency():
        return float(ADDON.getSetting('screensaver_appletvlike_concurrency'))

    @staticmethod
    def getGridswitchRowsColumns():
        return int(ADDON.getSetting('screensaver_gridswitch_columns'))

    @staticmethod
    def isGridswitchRandom():
        return ADDON.getSetting("screensaver_gridswitch_random") == 'true'

    @staticmethod
    def isPlayThemes():
        return ADDON.getSetting("screensaver_playthemes") == 'true'

    @staticmethod
    def isOnlyIfThemes():
        return ADDON.getSetting("screensaver_onlyifthemes") == 'true'

    @staticmethod
    def isRepeatTheme():
        return ADDON.getSetting("screensaver_themeControl") == '1'

    @staticmethod
    def isSkipAfterThemeOnce():
        return ADDON.getSetting("screensaver_themeControl") == '2'

    @staticmethod
    def getDimValue():
        # The actual dim level (Hex) is one of
        # FF111111, FF222222 ... FFEEEEEE, FFFFFFFF
        # Where FFFFFFFF is not changed
        # So that is a total of 15 different options
        if ADDON.getSetting("screensaver_dimlevel"):
            return ScreensaverSettings.DIM_LEVEL[int(ADDON.getSetting("screensaver_dimlevel"))]
        else:
            return 'FFFFFFFF'

    @staticmethod
    def getSlideFromOrigin():
        selectedOrigin = ADDON.getSetting("screensaver_slide_from")
        originId = 0
        if selectedOrigin:
            originId = int(selectedOrigin)
        return ScreensaverSettings.SLIDE_FROM[originId]

    @staticmethod
    def includeArtworkDownloader():
        # Make sure that the fanart is actually selected to be used, otherwise there is no
        # point in searching for it
        if 'fanart' in ScreensaverSettings.getImageTypes():
            return ADDON.getSetting("screensaver_artworkdownloader") == 'true'
        else:
            return False
