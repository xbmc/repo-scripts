# -*- coding: utf-8 -*-
''' This is the actual InputStream Helper plugin entry point '''

from __future__ import absolute_import, division, unicode_literals
import sys
from routing import Plugin
from inputstreamhelper import ADDON, Helper

# NOTE: Work around an issue in script.module.routing
#       https://github.com/tamland/kodi-plugin-routing/pull/16
if len(sys.argv) < 1:
    sys.argv.append('addon.py')
if len(sys.argv) < 2:
    sys.argv.append('-1')

plugin = Plugin()


@plugin.route('addon.py')  # This is the entry point from the addon menu
@plugin.route('/')
@plugin.route('/settings')
def settings():
    ''' Entry point to open the plugin settings '''
    ADDON.openSettings()


@plugin.route('/check/<protocol>')
@plugin.route('/check/<protocol>/<drm>')
def check_inputstream(protocol, drm=None):
    ''' The API interface to check inputstream '''
    Helper(protocol, drm=drm).check_inputstream()


@plugin.route('/widevine/install')
@plugin.route('/widevine/install/latest')
def widevine_install():
    ''' The API interface to install Widevine CDM '''
    Helper('mpd', drm='widevine').install_widevine()


@plugin.route('/widevine/remove')
def widevine_remove():
    ''' The API interface to remove Widevine CDMs '''
    Helper('mpd', drm='widevine').remove_widevine()


if __name__ == '__main__':
    plugin.run(sys.argv)
