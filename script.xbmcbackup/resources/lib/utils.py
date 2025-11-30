import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

__addon_id__ = 'script.xbmcbackup'
__Addon = xbmcaddon.Addon(__addon_id__)


def data_dir():
    return __Addon.getAddonInfo('profile')


def addon_dir():
    return __Addon.getAddonInfo('path')


def openSettings():
    __Addon.openSettings()


def log(message, loglevel=xbmc.LOGDEBUG):
    xbmc.log(__addon_id__ + "-" + __Addon.getAddonInfo('version') + ": " + message, level=loglevel)


def showNotification(message):
    xbmcgui.Dialog().notification(getString(30010), message, time=4000, icon=xbmcvfs.translatePath(__Addon.getAddonInfo('path') + "/resources/images/icon.png"))


def getSetting(name):
    return __Addon.getSetting(name)

def getSettingStringStripped(name):
    return __Addon.getSettingString(name).strip()

def getSettingBool(name):
    return bool(__Addon.getSettingBool(name))


def getSettingInt(name):
    return __Addon.getSettingInt(name)


def setSetting(name, value):
    __Addon.setSetting(name, value)


def getString(string_id):
    return __Addon.getLocalizedString(string_id)


def getRegionalTimestamp(date_time, dateformat=['dateshort']):
    result = ''

    for aFormat in dateformat:
        result = result + ("%s " % date_time.strftime(xbmc.getRegion(aFormat)))

    return result.strip()


def diskString(fSize):
    # convert a size in kilobytes to the best possible match and return as a string
    fSize = float(fSize)
    i = 0
    sizeNames = ['KB', 'MB', 'GB', 'TB']

    while(fSize > 1024):
        fSize = fSize / 1024
        i = i + 1

    return "%0.2f%s" % (fSize, sizeNames[i])
