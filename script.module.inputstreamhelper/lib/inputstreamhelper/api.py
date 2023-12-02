# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""This is the actual InputStream Helper API script"""

from __future__ import absolute_import, division, unicode_literals
from . import Helper
from .kodiutils import ADDON, log


def run(params):
    """Route to API method"""
    if 2 <= len(params) <= 4:
        if params[1] == 'widevine_install':
            if len(params) == 3:
                widevine_install(choose_version=params[2])
            else:
                widevine_install()
        elif params[1] == 'widevine_remove':
            widevine_remove()
        elif params[1] in ('rollback', 'widevine_rollback'):
            widevine_rollback()
        elif params[1] == 'check_inputstream':
            if len(params) == 3:
                check_inputstream(params[2])
            elif len(params) == 4:
                check_inputstream(params[2], drm=params[3])
        elif params[1] == 'info':
            info_dialog()
        elif params[1] == 'widevine_install_from':
            widevine_install_from()
        else:
            log(4, "Invalid API call method '{method}'", method=params[1])

    elif len(params) > 4:
        log(4, 'Invalid API call, too many parameters.')
    else:
        ADDON.openSettings()


def check_inputstream(protocol, drm=None):
    """The API interface to check inputstream"""
    Helper(protocol, drm=drm).check_inputstream()


def widevine_install(choose_version=False):
    """The API interface to install Widevine CDM"""
    choose_version = choose_version in ("True", "true")
    Helper('mpd', drm='widevine').install_widevine(choose_version=choose_version)


def widevine_install_from():
    """The API interface to install Widevine CDM from a given resource (URL or local ChromeOS image)."""
    Helper('mpd', drm='widevine').install_widevine_from()


def widevine_remove():
    """The API interface to remove Widevine CDM"""
    Helper('mpd', drm='widevine').remove_widevine()


def widevine_rollback():
    """The API interface to rollback Widevine CDM"""
    Helper('mpd', drm='widevine').rollback_libwv()


def info_dialog():
    """The API interface to show an info Dialog"""
    Helper('mpd', drm='widevine').info_dialog()
