import os

import xbmc
import xbmcplugin
import xbmcaddon
import xbmcgui
import uuid
import sys

from utils import debug

SETTING_KODI_ID = 'kodi_id'
SETTING_IS_PAIRED = 'is_paired'
KODI_ADDON_ID = ''


def get_plugin_id():
    global KODI_ADDON_ID
    if not KODI_ADDON_ID:
        KODI_ADDON_ID = xbmcaddon.Addon().getAddonInfo('id')
    return KODI_ADDON_ID

PLUGIN_ID = get_plugin_id()
DATA_PATH = 'special://profile/addon_data/%s' % (PLUGIN_ID)

debug('PLUGIN_ID = %s' % PLUGIN_ID)


def get_random_kodi_id():
    return str(uuid.uuid4())


def get_should_pair_file_path():
    return xbmc.translatePath('%s/%s' % (DATA_PATH, 'should_pair'))


class Conf(object):
    def __init__(self):
        addon = xbmcaddon.Addon(PLUGIN_ID)
        self._kodi_id = addon.getSetting(SETTING_KODI_ID)
        self._is_paired = addon.getSetting(SETTING_IS_PAIRED)

        if not self.has_kodi_id:
            self.set_random_kodi_id()

        debug('Loaded Kodi ID = %s, is_paired = %s' % (self.get_kodi_id(), self.is_paired))

    def set_random_kodi_id(self):
        self.set_kodi_id(get_random_kodi_id())
        debug('New random Kodi ID is %s' % self.get_kodi_id())

    @property
    def has_kodi_id(self):
        return len(self.get_kodi_id()) > 0

    @property
    def is_paired(self):
        debug('is_paired = %s' % str(self._is_paired != 'false'))
        return self._is_paired != 'false'

    @is_paired.setter
    def is_paired(self, value):
        addon = xbmcaddon.Addon(id=PLUGIN_ID)
        value = 'false' if not value else 'true'
        debug('Setting is_paired = %s' % str(value))
        addon.setSetting(SETTING_IS_PAIRED, value)
        self._is_paired = value

    def get_kodi_id(self):
        return self._kodi_id

    def set_kodi_id(self, value):
        addon = xbmcaddon.Addon(id=PLUGIN_ID)
        debug('Setting kodi_id = %s' % value)
        addon.setSetting(id=SETTING_KODI_ID, value=value)
        self._kodi_id = value

    # @kodi_id.setter
    # def kodi_id(self, value):
    #     self.set_kodi_id(value)

    @property
    def repair_asked(self):
        return xbmcgui.Window(10000).getProperty(get_plugin_id() + '_pair') == 'True'

    @staticmethod
    def close_repair_request():
        xbmcgui.Window(10000).setProperty(get_plugin_id() + '_pair', 'False')

    @staticmethod
    def ask_repair():
        xbmcgui.Window(10000).setProperty(get_plugin_id() + '_pair', 'True')
