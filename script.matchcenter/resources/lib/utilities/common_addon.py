# -*- coding: utf-8 -*-
'''
    script.matchcenter - Football information for Kodi
    A program addon that can be mapped to a key on your remote to display football information.
    Livescores, Event details, Line-ups, League tables, next and previous matches by team. Follow what
    others are saying about the match in twitter.
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

addon = xbmcaddon.Addon(id='script.matchcenter')
addon_path = addon.getAddonInfo('path')
addon_userdata = xbmc.translatePath(addon.getAddonInfo('profile')).decode('utf-8')
addon_name = addon.getAddonInfo('name')

#cache folders
addon_userdata_cached_leagues = os.path.join(addon_userdata,"leagues")
addon_userdata_cached_leagueteams = os.path.join(addon_userdata,"leagueteams")
addon_userdata_cached_teams = os.path.join(addon_userdata,"teams")

ignored_league_list_file = os.path.join(addon_userdata,"ignored.txt") 
livescores_update_time = int(addon.getSetting("livescores-update-time"))
twitter_update_time = int(addon.getSetting("twitter-update-time"))
save_hashes_during_playback = addon.getSetting("save_hashes_during_playback")
twitter_history_enabled = addon.getSetting("twitter_history_enabled")
my_timezone = addon.getSetting("timezone")
my_location = pytz.timezone(pytz.all_timezones[int(my_timezone)])
hide_notstarted = addon.getSetting("hide-notstarted")
hide_finished = addon.getSetting("hide-finished")
show_alternative = addon.getSetting("use-alternative-name")
json_formations = os.path.join(addon_path,"resources","formations.dict")
tweet_file = os.path.join(addon_userdata,"twitter.txt")
twitter_history_file = os.path.join(addon_userdata,"twitter_history.txt")


def getskinfolder():
    #if "skin.aeon.nox" in xbmc.getSkinDir(): return "skin.aeon.nox.5"
    #else: 
    return "default"

def removeNonAscii(s):
	return "".join(filter(lambda x: ord(x)<128, s))

def translate(text):
	return addon.getLocalizedString(text).encode('utf-8')
