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
import leaguetables
import mainmenu
from utilities import ssutils
from utilities.common_addon import *

api = thesportsdb.Api("7723457519235")

class Main(xbmcgui.WindowXMLDialog):
	
	def __init__( self, *args, **kwargs ):
		self.standalone = kwargs["standalone"]

	def onInit(self):
		self.getControl(32540).setImage(os.path.join(addon_path,"resources","img","goal.png"))
		xbmc.executebuiltin("SetProperty(loading-script-matchcenter-leagueselection,1,home)")
		leagues = api.Search().Leagues(sport="Soccer")
		leagues_to_be_shown = ssutils.get_league_tables_ids()
		items = []
		if leagues:
			for league in leagues:
				if str(league.idLeague) in str(leagues_to_be_shown):
					item = xbmcgui.ListItem(league.strLeague)
					item.setProperty("thumb",str(league.strBadge))
					item.setProperty("identifier",str(league.idLeague))
					items.append(item)
		xbmc.executebuiltin("ClearProperty(loading-script-matchcenter-leagueselection,Home)")
		self.getControl(32500).addItems(items)
		if len(items) <= 9:
			self.getControl(32541).setWidth(962)
			self.getControl(32542).setWidth(962)

	def onAction(self,action):
		if action.getId() == 10 or action.getId() == 92:
			self.close()
			if not self.standalone:
				mainmenu.start()

	def onClick(self,controlId):
		if controlId == 32500:
			identifier = self.getControl(32500).getSelectedItem().getProperty("identifier")
			leaguetables.start_table(leagueid=int(identifier))

def start(standalone=False):
	main = Main(
			'script-matchcenter-LeagueSelection.xml',
			addon_path,
			getskinfolder(),
			'',
			standalone=standalone
			)
	main.doModal()
	del main