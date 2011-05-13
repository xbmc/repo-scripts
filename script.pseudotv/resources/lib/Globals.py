#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import os
import xbmcaddon, xbmc
import Settings



def log(msg, level = xbmc.LOGDEBUG):
    xbmc.log(ADDON_ID + '-' + msg, level)


def migrate():
    log("migration")
    curver = "0.0.0"

    try:
        curver = ADDON_SETTINGS.getSetting("Version")
    except:
        pass

    if compareVersions(curver, VERSION) < 0:
        if compareVersions(curver, "1.0.2") < 0:
            log("Migrating to 1.0.2")

            # Migrate to 1.0.2
            for i in range(200):
                if os.path.exists(xbmc.translatePath('special://profile/playlists/video') + '/Channel_' + str(i + 1) + '.xsp'):
                    ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_type", "0")
                    ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_1", "special://profile/playlists/video/Channel_" + str(i + 1) + ".xsp")
                elif os.path.exists(xbmc.translatePath('special://profile/playlists/mixed') + '/Channel_' + str(i + 1) + '.xsp'):
                    ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_type", "0")
                    ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_1", "special://profile/playlists/mixed/Channel_" + str(i + 1) + ".xsp")

            currentpreset = 0

            for i in range(TOTAL_FILL_CHANNELS):
                chantype = 9999

                try:
                    chantype = int(ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_type"))
                except:
                    pass

                if chantype == 9999:
                    addPreset(i + 1, currentpreset)
                    currentpreset += 1

    ADDON_SETTINGS.setSetting("Version", VERSION)

    
def addPreset(channel, presetnum):
    networks = ['ABC', 'AMC', 'Bravo', 'CBS', 'Comedy Central', 'Food Network', 'FOX', 'FX', 'HBO', 'NBC', 'SciFi', 'The WB']
    genres = ['Animation', 'Comedy', 'Documentary', 'Drama', 'Fantasy']
    studio = ['Brandywine Productions Ltd.', 'Fox 2000 Pictures', 'GK Films', 'Legendary Pictures', 'Universal Pictures']
    
    if presetnum < len(networks):
        ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_type", "1")
        ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_1", networks[presetnum])
    elif presetnum - len(networks) < len(genres):
        ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_type", "5")
        ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_1", genres[presetnum - len(networks)])
    elif presetnum - len(networks) - len(genres) < len(studio):
        ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_type", "2")
        ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_1", studio[presetnum - len(networks) - len(genres)])


def compareVersions(version1, version2):
    retval = 0
    ver1 = version1.split('.')
    ver2 = version2.split('.')

    for i in range(min(len(ver1), len(ver2))):
        if ver1[i] < ver2[i]:
            retval = -1
            break

        if ver1[i] > ver2[i]:
            retval = 1
            break

    if retval == 0:
        if len(ver1) > len(ver2):
            retval = 1
        elif len(ver2) > len(ver1):
            retval = -1

    return retval



ADDON_ID = 'script.pseudotv'
ADDON_SETTINGS = Settings.Settings()
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_INFO = REAL_SETTINGS.getAddonInfo('path')

VERSION = "1.2.0"

TIMEOUT = 15 * 1000
TOTAL_FILL_CHANNELS = 20
PREP_CHANNEL_TIME = 60 * 60 * 24 * 5
ALLOW_CHANNEL_HISTORY_TIME = 60 * 60 * 24 * 1

MODE_RESUME = 1
MODE_ALWAYSPAUSE = 2
MODE_ORDERAIRDATE = 4
MODE_RANDOM = 8
MODE_REALTIME = 16
MODE_SERIAL = MODE_RESUME | MODE_ALWAYSPAUSE | MODE_ORDERAIRDATE
MODE_STARTMODES = MODE_RANDOM | MODE_REALTIME | MODE_RESUME

IMAGES_LOC = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'images')) + '/'
PRESETS_LOC = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'presets')) + '/'
CHANNELS_LOC = xbmc.translatePath('special://profile/addon_data/' + ADDON_ID + '/cache/')
GEN_CHAN_LOC = os.path.join(CHANNELS_LOC, 'generated') + '/'

TIME_BAR = 'pstvTimeBar.png'
BUTTON_FOCUS = 'pstvButtonFocus.png'
BUTTON_NO_FOCUS = 'pstvButtonNoFocus.png'

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_PAGEUP = 5
ACTION_PAGEDOWN = 6
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = 10
ACTION_SHOW_INFO = 11
ACTION_PAUSE = 12
ACTION_STOP = 13
ACTION_NEXT_ITEM = 14
ACTION_PREV_ITEM = 15
ACTION_STEP_FOWARD = 17
ACTION_STEP_BACK = 18
ACTION_BIG_STEP_FORWARD = 19
ACTION_BIG_STEP_BACK = 20
ACTION_OSD = 122
ACTION_NUMBER_0 = 58
ACTION_NUMBER_1 = 59
ACTION_NUMBER_2 = 60
ACTION_NUMBER_3 = 61
ACTION_NUMBER_4 = 62
ACTION_NUMBER_5 = 63
ACTION_NUMBER_6 = 64
ACTION_NUMBER_7 = 65
ACTION_NUMBER_8 = 66
ACTION_NUMBER_9 = 67
ACTION_PLAYER_FORWARD = 73
ACTION_PLAYER_REWIND = 74
ACTION_PLAYER_PLAY = 75
ACTION_PLAYER_PLAYPAUSE = 76
#ACTION_MENU = 117
ACTION_MENU = 7
ACTION_INVALID = 999
