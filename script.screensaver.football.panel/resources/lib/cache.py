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

import thesportsdb
import os
import datetime
import xbmc
from addonfileio import FileIO
from common_addon import *


class AddonCache:

	def __init__(self):
		#setup cache folders on object instantiation
		folders = [addon_userdata,addon_userdata_cached_leagues,addon_userdata_cached_leagueteams,addon_userdata_cached_teams]
		for folder in folders:
			if not os.path.exists(folder):
				os.mkdir(folder)

	def isCachedLeague(self,leagueid):
		return os.path.exists(os.path.join(addon_userdata_cached_leagues,"%s.txt" % (str(leagueid))))

	def isCachedLeagueTeams(self,leagueid):
		return os.path.exists(os.path.join(addon_userdata_cached_leagueteams,"%s.txt" % (str(leagueid))))

	def isCachedTeam(self,teamid):
		return os.path.exists(os.path.join(addon_userdata_cached_teams,"%s.txt" % (str(teamid))))

	def getCachedLeagueTimeStamp(self,leagueid):
		return datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(addon_userdata_cached_leagues,"%s.txt" % (str(leagueid)))))

	def getCachedLeagueTeamsTimeStamp(self,leagueid):
		return datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(addon_userdata_cached_leagueteams,"%s.txt" % (str(leagueid)))))

	def getCachedTeamTimeStamp(self,teamid):
		return datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(addon_userdata_cached_teams,"%s.txt" % (str(teamid)))))

	def cacheLeague(self,leagueid,league_obj):
		league_dict = league_obj.__dict__
		FileIO.filewrite(os.path.join(os.path.join(addon_userdata_cached_leagues,"%s.txt" % (str(leagueid)))),str(league_dict))
		return

	def getcachedLeague(self,leagueid):
		league_str = FileIO.fileread(os.path.join(os.path.join(addon_userdata_cached_leagues,"%s.txt" % (str(leagueid)))))
		league = thesportsdb.league.as_league(eval(league_str))
		return league

	def cacheLeagueTeams(self,leagueid,team_obj_list):
		team_list = []
		for team in team_obj_list:
			team_list.append(team.__dict__)
		FileIO.filewrite(os.path.join(os.path.join(addon_userdata_cached_leagueteams,"%s.txt" % (str(leagueid)))),str(team_list))
		return

	def getcachedLeagueTeams(self,leagueid):
		team_list_str = FileIO.fileread(os.path.join(os.path.join(addon_userdata_cached_leagueteams,"%s.txt" % (str(leagueid)))))
		teams_list = [thesportsdb.team.as_team(team) for team in eval(team_list_str)]
		return teams_list

	def cacheTeam(self,teamid,team_obj):
		team_dict = team_obj.__dict__
		FileIO.filewrite(os.path.join(os.path.join(addon_userdata_cached_teams,"%s.txt" % (str(teamid)))),str(team_dict))
		return

	def getcachedTeam(self,teamid):
		team = FileIO.fileread(os.path.join(os.path.join(addon_userdata_cached_teams,"%s.txt" % (str(teamid)))))
		return thesportsdb.team.as_team(eval(team))

	@staticmethod
	def removeCachedData():
		has_removed_files = False
		cache_folders = [addon_userdata_cached_leagues,addon_userdata_cached_leagueteams,addon_userdata_cached_teams]
		for folder in cache_folders:
			cached_objects = os.listdir(folder)
			if cached_objects:
				for file_ in cached_objects:
					os.remove(os.path.join(folder,file_))
					if not has_removed_files:
						has_removed_files = True

		if has_removed_files:
			xbmc.executebuiltin("XBMC.Notification(%s,%s,3000,%s)" % (translate(32000),translate(32021),os.path.join(addon_path,"icon.png")))
		else:
			xbmc.executebuiltin("XBMC.Notification(%s,%s,3000,%s)" % (translate(32000),translate(32022),os.path.join(addon_path,"icon.png")))





