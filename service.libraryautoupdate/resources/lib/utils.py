from kodi_six import xbmc, xbmcgui, xbmcaddon, xbmcvfs

__addon_id__ = 'service.libraryautoupdate'
__Addon = xbmcaddon.Addon(__addon_id__)


def check_data_dir():
    if(not xbmcvfs.exists(xbmcvfs.translatePath(data_dir()))):
        xbmcvfs.mkdir(xbmcvfs.translatePath(data_dir()))


def data_dir():
    return __Addon.getAddonInfo('profile')


def addon_dir():
    return __Addon.getAddonInfo('path')


def log(message, loglevel=xbmc.LOGDEBUG):
    xbmc.log(__addon_id__ + "-" + __Addon.getAddonInfo('version') + " : " + message, level=loglevel)


def showNotification(title, message):
    xbmcgui.Dialog().notification(getString(30000), message, time=5000, icon=xbmcvfs.translatePath(__Addon.getAddonInfo('path') + "/resources/media/icon.png"), sound=False)


def setSetting(name, value):
    __Addon.setSettingString(name, value)


def getSetting(name):
    return __Addon.getSetting(name)


def getSettingBool(name):
    return bool(__Addon.getSettingBool(name))


def getSettingInt(name):
    return __Addon.getSettingInt(name)


def getString(string_id):
    return __Addon.getLocalizedString(string_id)
