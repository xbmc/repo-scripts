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
import matchhistory
from resources.lib.utilities.common_addon import *

api = thesportsdb.Api("7723457519235")

class detailsDialog(xbmcgui.WindowXMLDialog):
		
	def __init__( self, *args, **kwargs ):
		self.leagueid = kwargs["leagueid"]
		self.teamObjs = {}

	def onInit(self):
		self.getControl(32540).setImage(os.path.join(addon_path,"resources","img","goal.png"))
		xbmc.executebuiltin("SetProperty(loadingtables,1,home)")
		self.setTable()
		xbmc.executebuiltin("ClearProperty(loadingtables,Home)")

	def setTable(self):

		league = api.Lookups().League(leagueid=self.leagueid)[0]
		if league:
			self.getControl(32500).setLabel(league.strLeague)

		table = api.Lookups().Table(leagueid=self.leagueid,objects=True)
		if table:
			self.table = []
			position = 1
			for tableentry in table:
				try:
					if show_alternative == "false":
						item = xbmcgui.ListItem(tableentry.name)
					else:
						item = xbmcgui.ListItem(tableentry.Team.AlternativeNameFirst)
					item.setProperty('position','[B]'+str(position)+ ' - [/B]' )
					item.setProperty('teambadge',tableentry.Team.strTeamBadge)
					item.setProperty('teamid',tableentry.Team.idTeam)
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
				except: pass

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