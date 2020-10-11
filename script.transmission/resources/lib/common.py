# -*- coding: utf-8 -*-
# Copyright (c) 2013 Artem Glebov

from kodi_six import xbmcaddon
from resources.lib import transmissionrpc

__addon__ = xbmcaddon.Addon(id='script.transmission')
get_localized_string = __addon__.getLocalizedString


def get_addon_info(name):
    return __addon__.getAddonInfo(name)


def get_settings():
    params = {
        'address': __addon__.getSetting('rpc_host'),
        'port': __addon__.getSetting('rpc_port'),
        'user': __addon__.getSetting('rpc_user'),
        'password': __addon__.getSetting('rpc_password'),
        'stop_all_on_playback': __addon__.getSetting('stop_all_on_playback')
    }
    return params


def get_params():
    params = {
        'address': __addon__.getSetting('rpc_host'),
        'port': __addon__.getSetting('rpc_port'),
        'user': __addon__.getSetting('rpc_user'),
        'password': __addon__.getSetting('rpc_password'),
    }
    return params


def get_rpc_client():
    params = get_params()
    return transmissionrpc.Client(**params)


def open_settings():
    __addon__.openSettings()


def set_setting(name, value):
    __addon__.setSetting(name, value)
