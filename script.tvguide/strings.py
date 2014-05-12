#
#      Copyright (C) 2012 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
import xbmcaddon

ADDON = xbmcaddon.Addon(id = 'script.tvguide')

NO_DESCRIPTION = 30000
CALCULATING_REMAINING_TIME = 30002
TIME_LEFT = 30003
BACKGROUND_UPDATE_IN_PROGRESS = 30004

NO_PROGRAM_AVAILABLE = 30009

NO_STREAM_AVAILABLE_TITLE = 30100
NO_STREAM_AVAILABLE_LINE1 = 30101
NO_STREAM_AVAILABLE_LINE2 = 30102

CLEAR_CACHE = 30104
CLEAR_NOTIFICATIONS = 30108
DONE = 30105

LOAD_ERROR_TITLE = 30150
LOAD_ERROR_LINE1 = 30151
LOAD_ERROR_LINE2 = 30152
CONFIGURATION_ERROR_LINE2 = 30153

SKIN_ERROR_LINE1 = 30154
SKIN_ERROR_LINE2 = 30155
SKIN_ERROR_LINE3 = 30156

NOTIFICATION_5_MINS = 30200
NOTIFICATION_NOW = 30201

WATCH_CHANNEL = 30300
REMIND_PROGRAM = 30301
DONT_REMIND_PROGRAM = 30302
CHOOSE_STRM_FILE = 30304
REMOVE_STRM_FILE = 30306

PREVIEW_STREAM = 30604
STOP_PREVIEW = 30607

WEEBTV_WEBTV_MISSING_1 = 30802
WEEBTV_WEBTV_MISSING_2 = 30803
WEEBTV_WEBTV_MISSING_3 = 30804

DATABASE_SCHEMA_ERROR_1 = 30157
DATABASE_SCHEMA_ERROR_2 = 30158
DATABASE_SCHEMA_ERROR_3 = 30159

def strings(id, replacements = None):
    string = ADDON.getLocalizedString(id)
    if replacements is not None:
        return string % replacements
    else:
        return string