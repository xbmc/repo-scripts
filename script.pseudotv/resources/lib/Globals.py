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


from FileAccess import FileLock



def log(msg, level = xbmc.LOGDEBUG):
    try:
        xbmc.log(ADDON_ID + '-' + msg, level)
    except:
        pass


ADDON_ID = 'script.pseudotv'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_INFO = REAL_SETTINGS.getAddonInfo('path')

VERSION = "2.0.0"

TIMEOUT = 15 * 1000
TOTAL_FILL_CHANNELS = 20
PREP_CHANNEL_TIME = 60 * 60 * 24 * 5
ALLOW_CHANNEL_HISTORY_TIME = 60 * 60 * 24 * 1
NOTIFICATION_CHECK_TIME = 5
NOTIFICATION_TIME_BEFORE_END = 90
NOTIFICATION_DISPLAY_TIME = 8

MODE_RESUME = 1
MODE_ALWAYSPAUSE = 2
MODE_ORDERAIRDATE = 4
MODE_RANDOM = 8
MODE_REALTIME = 16
MODE_SERIAL = MODE_RESUME | MODE_ALWAYSPAUSE | MODE_ORDERAIRDATE
MODE_STARTMODES = MODE_RANDOM | MODE_REALTIME | MODE_RESUME

SETTINGS_LOC = ''
CHANNEL_SHARING = False

if REAL_SETTINGS.getSetting('ChannelSharing') == "true":
    CHANNEL_SHARING = True
    SETTINGS_LOC = REAL_SETTINGS.getSetting('SettingsFolder')

IMAGES_LOC = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'images')) + '/'
PRESETS_LOC = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'presets')) + '/'

if len(SETTINGS_LOC) == 0:
    SETTINGS_LOC = 'special://profile/addon_data/' + ADDON_ID

CHANNELS_LOC = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'cache')) + '/'
GEN_CHAN_LOC = os.path.join(CHANNELS_LOC, 'generated') + '/'
MADE_CHAN_LOC = os.path.join(CHANNELS_LOC, 'stored') + '/'

GlobalFileLock = FileLock()
ADDON_SETTINGS = Settings.Settings()

USING_EDEN = True

try:
    import xbmcvfs
    log("Globals - Eden")
except:
    USING_EDEN = False
    log("Globals - Dharma")

TIME_BAR = 'pstvTimeBar.png'
BUTTON_FOCUS = 'pstvButtonFocus.png'
BUTTON_NO_FOCUS = 'pstvButtonNoFocus.png'

RULES_ACTION_START = 1
RULES_ACTION_JSON = 2
RULES_ACTION_LIST = 4
RULES_ACTION_BEFORE_CLEAR = 8
RULES_ACTION_BEFORE_TIME = 16
RULES_ACTION_FINAL_MADE = 32
RULES_ACTION_FINAL_LOADED = 64

# Maximum is 10 for this
RULES_PER_PAGE = 7

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
