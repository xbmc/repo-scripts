'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import xbmcaddon
import utils

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
CLEAN = ADDON.getSetting('clean') == 'true'
POLLING = int(ADDON.getSetting('method'))
POLLING_METHOD = int(ADDON.getSetting('pollingmethod'))
POLLING_INTERVAL = int("0"+ADDON.getSetting('pollinginterval')) or 4
RECURSIVE = not (ADDON.getSetting('nonrecursive') == 'true') or not POLLING
SCAN_DELAY = int("0"+ADDON.getSetting('delay')) or 1
PAUSE_ON_PLAYBACK = ADDON.getSetting('pauseonplayback') == 'true'
FORCE_GLOBAL_SCAN = ADDON.getSetting('forceglobalscan') == 'true'
SHOW_NOTIFICATIONS = ADDON.getSetting('notifications') == 'true'


if ADDON.getSetting('watchvideo') == 'true':
    VIDEO_SOURCES = utils.get_media_sources('video')
else:
    VIDEO_SOURCES = [_ for _ in set([
        ADDON.getSetting('videosource1'),
        ADDON.getSetting('videosource2'),
        ADDON.getSetting('videosource3'),
        ADDON.getSetting('videosource4'),
        ADDON.getSetting('videosource5')]) if _ != ""]

if ADDON.getSetting('watchmusic') == 'true':
    MUSIC_SOURCES = utils.get_media_sources('music')
else:
    MUSIC_SOURCES = [_ for _ in set([
        ADDON.getSetting('musicsource1'),
        ADDON.getSetting('musicsource2'),
        ADDON.getSetting('musicsource3'),
        ADDON.getSetting('musicsource4'),
        ADDON.getSetting('musicsource5')]) if _ != ""]
