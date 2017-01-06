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

    def getPlatform(self):

        if xbmc.getCondVisibility('system.platform.osx'):
            return "OSX"
        elif xbmc.getCondVisibility('system.platform.atv2'):
            return "ATV2"
        elif xbmc.getCondVisibility('system.platform.ios'):
            return "iOS"
        elif xbmc.getCondVisibility('system.platform.windows'):
            return "Windows"
        elif xbmc.getCondVisibility('system.platform.android'):
            return "Linux/Android"
        elif xbmc.getCondVisibility('system.platform.linux.raspberrypi'):
            return "Linux/RPi"
        elif xbmc.getCondVisibility('system.platform.linux'):
            return "Linux"
        else:
            return "Unknown"

    def get_device_name(self):

        # Use Kodi's deviceName
        device_name = xbmc.getInfoLabel('System.FriendlyName').decode('utf-8')
        return device_name


    def get_device_id(self, reset=False):
        WINDOW = xbmcgui.Window(10000)
        client_id = WINDOW.getProperty('kodi_deviceId')
        if client_id:
            return client_id

        kodiguid = xbmc.translatePath("special://temp/guid").decode('utf-8')

        ###$ Begin migration $###
        if not xbmcvfs.exists(kodiguid):
            addon_path = self.addon.getAddonInfo('path').decode('utf-8')
            if os.path.supports_unicode_filenames:
                path = os.path.join(addon_path, "machine_guid")
            else:
                path = os.path.join(addon_path.encode('utf-8'), "machine_guid")

            guid_file = xbmc.translatePath(path).decode('utf-8')
            if xbmcvfs.exists(guid_file):
                xbmcvfs.copy(guid_file, kodiguid)
        ###$ End migration $###

        if reset and xbmcvfs.exists(kodiguid):
            # Reset the file
            xbmcvfs.delete(kodiguid)

        guid = xbmcvfs.File(kodiguid)
        client_id = guid.read()
        if not client_id:
            client_id = str("%012X" % uuid4())
            guid = xbmcvfs.File(kodiguid, 'w')
            guid.write(client_id)

        guid.close()

        WINDOW.setProperty('kodi_deviceId',client_id)

        return client_id
