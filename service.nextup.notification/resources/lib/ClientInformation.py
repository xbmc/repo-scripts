import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

import os
from uuid import uuid4 as uuid4

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

    def getPlayMode(self):
        if self.addon.getSetting("showPostPlay") == "true":
            return "PostPlay"
        else:
            return "PrePlay"

    def getVersion(self):
        return self.addon.getAddonInfo('version')

