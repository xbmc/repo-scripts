import xbmc
import xbmcaddon

import Utils as utils


class ClientInformation():
    def __init__(self):
        addonId = self.getAddonId()
        self.addon = xbmcaddon.Addon(id=addonId)

        self.className = self.__class__.__name__
        self.addonName = self.getAddonName()

    def logMsg(self, msg, lvl=1):
        utils.logMsg("%s %s" % (self.addonName, self.className), str(msg), int(lvl))

    def getAddonId(self):
        # To use when declaring xbmcaddon.Addon(id=addonId)
        return "service.nextup.notification"

    def getAddonName(self):
        # Useful for logging
        return self.addon.getAddonInfo('name').upper()

    def getVersion(self):
        return self.addon.getAddonInfo('version')

    def getPlatform(self):

        if xbmc.getCondVisibility('system.platform.osx'):
            return "OSX"
        elif xbmc.getCondVisibility('system.platform.atv2'):
            return "ATV2"
        elif xbmc.getCondVisibility('system.platform.ios'):
            return "iOS"
        elif xbmc.getCondVisibility('system.platform.windows'):
            return "Windows"
        elif xbmc.getCondVisibility('system.platform.linux'):
            return "Linux/RPi"
        elif xbmc.getCondVisibility('system.platform.android'):
            return "Linux/Android"

        return "Unknown"
