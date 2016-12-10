# -*- coding: utf8 -*-

# Copyright (C) 2016 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmcaddon
import xbmc
import os
import xbmcgui
import base64
import uuid
import hashlib
HOME = xbmcgui.Window(10000)


class Addon(object):

    def __init__(self, *args, **kwargs):
        self.addon = xbmcaddon.Addon(*args)
        self.ID = self.addon.getAddonInfo('id').decode("utf-8")
        self.ICON = self.addon.getAddonInfo('icon').decode("utf-8")
        self.NAME = self.addon.getAddonInfo('name').decode("utf-8")
        self.FANART = self.addon.getAddonInfo('fanart').decode("utf-8")
        self.AUTHOR = self.addon.getAddonInfo('author').decode("utf-8")
        self.CHANGELOG = self.addon.getAddonInfo('changelog').decode("utf-8")
        self.DESCRIPTION = self.addon.getAddonInfo('description').decode("utf-8")
        self.DISCLAIMER = self.addon.getAddonInfo('disclaimer').decode("utf-8")
        self.VERSION = self.addon.getAddonInfo('version').decode("utf-8")
        self.PATH = self.addon.getAddonInfo('path').decode("utf-8")
        self.PROFILE = self.addon.getAddonInfo('profile').decode("utf-8")
        self.SUMMARY = self.addon.getAddonInfo('summary').decode("utf-8")
        self.TYPE = self.addon.getAddonInfo('type').decode("utf-8")
        self.MEDIA_PATH = os.path.join(self.PATH, "resources", "skins", "Default", "media")
        self.DATA_PATH = xbmc.translatePath("special://profile/addon_data/%s" % self.ID).decode("utf-8")

    def setting(self, setting_name):
        return self.addon.getSetting(setting_name)

    def set_setting(self, setting_name, string):
        self.addon.setSetting(str(setting_name), str(string))

    def set_password_prompt(self, setting_name):
        password = xbmcgui.Dialog().input(self.LANG(12326), option=xbmcgui.ALPHANUM_HIDE_INPUT)
        if password:
            self.set_password(setting_name, password)

    def set_password(self, setting_name, string):
        self.addon.setSetting(setting_name, encode_string(string))

    def get_password(self, setting_name):
        mac = str(uuid.getnode())
        mac_hash = hashlib.md5(mac).hexdigest()
        if not self.addon.getSetting("mac_hash"):
            self.addon.setSetting("mac_hash", mac_hash)
        elif self.addon.getSetting("mac_hash") != mac_hash:
            xbmcgui.Dialog().notification("Error", "MAC id changed. Please enter password again in settings.")
            self.addon.setSetting("mac_hash", mac_hash)
            return None
        setting = self.addon.getSetting(setting_name)
        if setting:
            return decode_string(setting)

    def bool_setting(self, setting_name):
        return self.addon.getSetting(setting_name) == "true"

    def reload_addon(self):
        self.addon = xbmcaddon.Addon(self.ID)

    def LANG(self, id_):
        return self.addon.getLocalizedString(id_) if 31000 <= id_ <= 33000 else xbmc.getLocalizedString(id_)

    def set_global(self, setting_name, setting_value):
        HOME.setProperty(setting_name, setting_value)

    def get_global(self, setting_name):
        return HOME.getProperty(setting_name)

    def clear_global(self, setting_name):
        HOME.clearProperty(setting_name)

    def clear_globals(self):
        HOME.clearProperties()


def encode_string(clear):
    enc = []
    key = str(uuid.getnode())
    for i in range(len(clear)):
        key_c = key[i % len(key)]
        enc_c = chr((ord(clear[i]) + ord(key_c)) % 256)
        enc.append(enc_c)
    return base64.urlsafe_b64encode("".join(enc))


def decode_string(enc):
    dec = []
    key = str(uuid.getnode())
    enc = base64.urlsafe_b64decode(enc)
    for i in range(len(enc)):
        key_c = key[i % len(key)]
        dec_c = chr((256 + ord(enc[i]) - ord(key_c)) % 256)
        dec.append(dec_c)
    return "".join(dec)
