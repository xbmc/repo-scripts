# -*- coding: utf-8 -*-
''' This is the actual InputStream Helper API script '''

from __future__ import absolute_import, division, unicode_literals
from inputstreamhelper import Helper
from .kodiutils import ADDON, log


def run(params):
    ''' Route to API method '''
    if 2 <= len(params) <= 4:
        if params[1] == 'widevine_install':
            widevine_install()
        elif params[1] == 'widevine_remove':
            widevine_remove()
        elif params[1] == 'check_inputstream':
            if len(params) == 3:
                check_inputstream(params[2])
            elif len(params) == 4:
                check_inputstream(params[2], drm=params[3])
        elif params[1] == 'info':
            info_dialog()
    elif len(params) > 4:
        log('invalid API call, too many parameters')
    else:
        ADDON.openSettings()


def check_inputstream(protocol, drm=None):
    ''' The API interface to check inputstream '''
    Helper(protocol, drm=drm).check_inputstream()


def widevine_install():
    ''' The API interface to install Widevine CDM '''
    Helper('mpd', drm='widevine').install_widevine()


def widevine_remove():
    ''' The API interface to remove Widevine CDMs '''
    Helper('mpd', drm='widevine').remove_widevine()


def info_dialog():
    ''' The API interface to show an info Dialog '''
    Helper('mpd', drm='widevine').info_dialog()
