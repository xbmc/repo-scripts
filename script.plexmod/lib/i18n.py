# coding=utf-8
from kodi_six import xbmcaddon


ADDON = xbmcaddon.Addon()


def T(ID, eng=''):
    return ADDON.getLocalizedString(ID)
