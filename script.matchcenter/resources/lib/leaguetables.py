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

import xbmcgui
import xbmc
import thesportsdb
import datetime
import matchhistory
from resources.lib.utilities.cache import AddonCache
from resources.lib.utilities.common_addon import *

api = thesportsdb.Api("7723457519235")

class detailsDialog(xbmcgui.WindowXMLDialog):
		
	def __init__( self, *args, **kwargs ):
		self.leagueid = kwargs["leagueid"]
		self.teamObjs = {}
		self.cache_object = AddonCache()

	def onInit(self):
		self.getControl(32540).setImage(os.path.join(addon_path,"resources","img","goal.png"))
		xbmc.executebuiltin("SetProperty(loading-script-matchcenter-tables,1,home)")
		self.setTable()
		xbmc.executebuiltin("ClearProperty(loading-script-matchcenter-tables,Home)")

	def updateCacheTimes(self):
		self.t2 = datetime.datetime.now()
		self.hoursList = [168, 336, 504, 672, 840]
		self.interval = int(addon.getSetting("new_request_interval"))
		return

	def setTable(self):
		self.updateCacheTimes()

		#league data
		update_league_data = True
		if self.cache_object.isCachedLeague(self.leagueid):
			update_league_data = abs(self.t2 - self.cache_object.getCachedLeagueTimeStamp(self.leagueid)) > datetime.timedelta(hours=self.hoursList[self.interval])

		if update_league_data:
			xbmc.log(msg="[Match Center] Timedelta was reached for league %s new request to be made..." % (str(self.leagueid)), level=xbmc.LOGDEBUG)
			league = api.Lookups().League(self.leagueid)[0]
			self.cache_object.cacheLeague(leagueid=self.leagueid,league_obj=league)
		else:
			xbmc.log(msg="[Match Center] Using cached object for league %s" % (str(self.leagueid)), level=xbmc.LOGDEBUG)
			league = self.cache_object.getcachedLeague(self.leagueid)

		if league:
			self.getControl(32500).setLabel(league.strLeague)

		table = api.Lookups().Table(leagueid=self.leagueid)

		if table:
			#team data
			update_team_data = True
			if self.cache_object.isCachedLeagueTeams(self.leagueid):
				update_team_data = abs(self.t2 - self.cache_object.getCachedLeagueTeamsTimeStamp(self.leagueid)) > datetime.timedelta(hours=self.hoursList[self.interval])

			if update_team_data:
				xbmc.log(msg="[Match Center] Timedelta was reached for teams in league %s new request to be made..." % (str(self.leagueid)), level=xbmc.LOGDEBUG)
				teams_in_league = api.Lookups().Team(leagueid=self.leagueid)
				self.cache_object.cacheLeagueTeams(leagueid=self.leagueid,team_obj_list=teams_in_league)
			else:
				xbmc.log(msg="[Match Center] Using cached object for teams in league %s" % (str(self.leagueid)), level=xbmc.LOGDEBUG)
				teams_in_league = self.cache_object.getcachedLeagueTeams(self.leagueid)


			self.table = []
			position = 1
			for tableentry in table:
				try:
					item = xbmcgui.ListItem(tableentry.name)
					for team in teams_in_league:
						if tableentry.teamid == team.idTeam:
							item.setArt({ 'thumb': team.strTeamBadge })

							if show_alternative == "true":
								item.setLabel(team.AlternativeNameFirst)
							item.setProperty('teamid',team.idTeam)
					
					item.setProperty('position','[B]'+str(position)+ ' - [/B]' )		
					item.setProperty('totalgames',str(tableentry.played))
					item.setProperty('totalwins',str(tableentry.win))
					item.setProperty('totaldraws',str(tableentry.draw))
					item.setProperty('totallosts',str(tableentry.loss))
					item.setProperty('goalsscored',str(tableentry.goalsfor))
					item.setProperty('goalsconceeded',str(tableentry.goalsagainst))
					item.setProperty('goaldifference',str(tableentry.goalsdifference))
					item.setProperty('points',str(tableentry.total))
					position += 1
					self.table.append(item)
				except Exception, e:
					xbmc.log(msg="[Match Center] Exception: %s" % (str(e)), level=xbmc.LOGDEBUG)

			self.getControl(32501).addItems(self.table)
			self.setFocusId(32501)
		return


	def onClick(self,controlId):
		if controlId == 32501:
			teamid = self.getControl(controlId).getSelectedItem().getProperty("teamid")
			matchhistory.start(teamid)


def start_table(leagueid=None):
	main = detailsDialog('script-matchcenter-LeagueTables.xml', addon_path, getskinfolder(), '', leagueid=leagueid)
	main.doModal()
	del main