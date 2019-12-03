# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Dag Wieers (@dagwieers) <dag@wieers.com>
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
''' This file implements the Kodi xbmcaddon module, either using stubs or alternative functionality '''

# pylint: disable=invalid-name

from __future__ import absolute_import, division, print_function, unicode_literals
from xbmc import getLocalizedString
from xbmcextra import ADDON_INFO, ADDON_ID, addon_settings, global_settings, import_language

GLOBAL_SETTINGS = global_settings()
ADDON_SETTINGS = addon_settings()
PO = import_language(language=GLOBAL_SETTINGS.get('locale.language'))


class Addon:
    ''' A reimplementation of the xbmcaddon Addon class '''

    def __init__(self, id=ADDON_ID):  # pylint: disable=redefined-builtin
        ''' A stub constructor for the xbmcaddon Addon class '''
        self.id = id

    def getAddonInfo(self, key):
        ''' A working implementation for the xbmcaddon Addon class getAddonInfo() method '''
        stub_info = dict(id=self.id, name=self.id, version='2.3.4', type='kodi.inputstream', profile='special://userdata', path='special://userdata')
        # Add stub_info values to ADDON_INFO when missing (e.g. path and profile)
        addon_info = dict(stub_info, **ADDON_INFO)
        return addon_info.get(self.id, stub_info).get(key)

    @staticmethod
    def getLocalizedString(msgctxt):
        ''' A working implementation for the xbmcaddon Addon class getLocalizedString() method '''
        return getLocalizedString(msgctxt)

    def getSetting(self, key):
        ''' A working implementation for the xbmcaddon Addon class getSetting() method '''
        return ADDON_SETTINGS.get(self.id, {}).get(key, '')

    @staticmethod
    def openSettings():
        ''' A stub implementation for the xbmcaddon Addon class openSettings() method '''

    def setSetting(self, key, value):
        ''' A stub implementation for the xbmcaddon Addon class setSetting() method '''
        if not ADDON_SETTINGS.get(self.id):
            ADDON_SETTINGS[self.id] = dict()
        ADDON_SETTINGS[self.id][key] = value
        # NOTE: Disable actual writing as it is no longer needed for testing
        # with open('test/userdata/addon_settings.json', 'w') as fd:
        #     json.dump(filtered_settings, fd, sort_keys=True, indent=4)
