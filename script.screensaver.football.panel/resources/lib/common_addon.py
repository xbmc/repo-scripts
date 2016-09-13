# -*- coding: utf-8 -*-
'''
    script.screensaver.football.panel - A Football Panel for Kodi
    RSS Feeds, Livescores and League tables as a screensaver or
    program addon 
    Copyright (C) 2016 enen92

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

import xbmc
import xbmcaddon
import xbmcvfs
import os
import pytz

addon = xbmcaddon.Addon(id='script.screensaver.football.panel')
addon_path = addon.getAddonInfo('path')
addon_userdata = xbmc.translatePath(addon.getAddonInfo('profile')).decode('utf-8')
addon_name = addon.getAddonInfo('name')

addon_userdata_cached_leagues = os.path.join(addon_userdata,"leagues")
addon_userdata_cached_leagueteams = os.path.join(addon_userdata,"leagueteams")
addon_userdata_cached_teams = os.path.join(addon_userdata,"teams")

ignored_league_list_file = os.path.join(addon_userdata,"ignored.txt") 
livescores_update_time = int(addon.getSetting("livescores-update-time"))
tables_update_time = int(addon.getSetting("tables-update-time"))
rss_update_time = int(addon.getSetting("rss-update-time"))
my_timezone = addon.getSetting("timezone")
my_location = pytz.timezone(pytz.all_timezones[int(my_timezone)])
hide_notstarted = addon.getSetting("hide-notstarted")
hide_finished = addon.getSetting("hide-finished")
show_alternative = addon.getSetting("use-alternative-name")
 
LIVESCORES_PANEL_CONTROL_1 = 32500
LIVESCORES_PANEL_CONTROL_2 = 32501
LEAGUETABLES_LIST_CONTROL = 32552
LEAGUETABLES_CLEARART = 32503
OPTIONS_PANEL = 6
OPTIONS_OK = 5
OPTIONS_CANCEL = 7
RSS_FEEDS = 32504
NO_GAMES = 32505
ACTION_LEFT = 1
ACTION_BACK1 = 10
ACTION_BACK2 = 92


def removeNonAscii(s):
	return "".join(filter(lambda x: ord(x)<128, s))

def translate(text):
	return addon.getLocalizedString(text).encode('utf-8')

