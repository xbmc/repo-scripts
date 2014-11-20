# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import xbmcaddon
import utils

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id').decode('utf-8')
REMOVAL_ENABLED = ADDON.getSetting('clean') == 'true'
POLLING = int(ADDON.getSetting('method'))
POLLING_INTERVAL = int("0"+ADDON.getSetting('pollinginterval')) or 4
RECURSIVE = ADDON.getSetting('recursivepolling') == 'true'
SCAN_DELAY = int("0"+ADDON.getSetting('delay')) or 1
STARTUP_DELAY = int("0"+ADDON.getSetting('startupdelay'))
PAUSE_ON_PLAYBACK = ADDON.getSetting('pauseonplayback') == 'true'
FORCE_GLOBAL_SCAN = ADDON.getSetting('forceglobalscan') == 'true'
SHOW_STATUS_DIALOG = ADDON.getSetting('showstatusdialog') == 'true'
CLEAN_ON_START = ADDON.getSetting('cleanonstart') == 'true'
SCAN_ON_START = ADDON.getSetting('scanonstart') == 'true'
PER_FILE_REMOVE = int(ADDON.getSetting('removalmethod')) == 1


if ADDON.getSetting('watchvideo') == 'true':
    VIDEO_SOURCES = utils.get_media_sources('video')
else:
    VIDEO_SOURCES = [_ for _ in set([
        ADDON.getSetting('videosource1').decode('utf-8'),
        ADDON.getSetting('videosource2').decode('utf-8'),
        ADDON.getSetting('videosource3').decode('utf-8'),
        ADDON.getSetting('videosource4').decode('utf-8'),
        ADDON.getSetting('videosource5').decode('utf-8')]) if _ != ""]

if ADDON.getSetting('watchmusic') == 'true':
    MUSIC_SOURCES = utils.get_media_sources('music')
else:
    MUSIC_SOURCES = [_ for _ in set([
        ADDON.getSetting('musicsource1').decode('utf-8'),
        ADDON.getSetting('musicsource2').decode('utf-8'),
        ADDON.getSetting('musicsource3').decode('utf-8'),
        ADDON.getSetting('musicsource4').decode('utf-8'),
        ADDON.getSetting('musicsource5').decode('utf-8')]) if _ != ""]
