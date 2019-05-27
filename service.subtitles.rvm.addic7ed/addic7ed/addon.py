# coding: utf-8

from __future__ import unicode_literals
import os
from kodi_six import xbmc, xbmcaddon

__all__ = ['ADDON_ID', 'addon', 'path', 'profile', 'icon', 'get_ui_string']

ADDON_ID = 'service.subtitles.rvm.addic7ed'
addon = xbmcaddon.Addon(ADDON_ID)
path = xbmc.translatePath(addon.getAddonInfo('path'))
profile = xbmc.translatePath(addon.getAddonInfo('profile'))
icon = os.path.join(path, 'icon.png')


def get_ui_string(string_id):
    """
    Get language string by ID

    :param string_id: UI string ID
    :return: UI string
    """
    return addon.getLocalizedString(string_id)
