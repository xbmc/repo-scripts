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
import xbmcgui
import thesportsdb
from utilities.addonfileio import FileIO
from utilities.common_addon import *

api = thesportsdb.Api("7723457519235")

class Select(xbmcgui.WindowXMLDialog):
	
	def __init__( self, *args, **kwargs ):
		if os.path.exists(ignored_league_list_file):
			self.already_ignored = eval(FileIO.fileread(ignored_league_list_file))
		else:
			self.already_ignored = []

	def onInit(self):
		self.getControl(1).setLabel(translate(32003))
		self.getControl(3).setVisible(False)
		leagues = api.Search().Leagues(sport="Soccer")
		ignored_through_context_menu = self.already_ignored
		if leagues:
			items = []
			for league in leagues:
				if removeNonAscii(league.strLeague) in self.already_ignored:
					item = xbmcgui.ListItem("[COLOR selected]" + league.strLeague + "[/COLOR]")
					item.setProperty("isIgnored","true")
					ignored_through_context_menu.remove(removeNonAscii(league.strLeague))
				else:
					item = xbmcgui.ListItem(league.strLeague)
					item.setProperty("isIgnored","false")
				item.setArt({"thumb":league.strBadge})
				items.append(item)
			
			#ignore the ones ignored through context menu
			if ignored_through_context_menu:
				for league_ign in ignored_through_context_menu:
					item = xbmcgui.ListItem("[COLOR selected]" + league_ign + "[/COLOR]")
					item.setProperty("isIgnored","true")
					item.setArt({"thumb":os.path.join(addon_path,"resources","img","nobadge_placeholder.png")})
					items.append(item)

			self.getControl(6).addItems(items)
			self.setFocusId(6)
			#Krypton
			if int(xbmc.getInfoLabel("System.BuildVersion")[0:2]) >= 17:
				self.getControl(5).setLabel(translate(32052))
				self.getControl(7).setLabel(translate(32053))

	def onAction(self,action):
		if action.getId() == 10 or action.getId() == 92:
			self.close()
		elif action.getId() == 1:
			self.setFocusId(6)

	def onClick(self,controlId):
		#list
		if controlId == 6:
			is_ignored = self.getControl(controlId).getSelectedItem().getProperty("isIgnored")
			league_name = self.getControl(controlId).getSelectedItem().getLabel().replace("[COLOR selected]","").replace("[/COLOR]","")
			if is_ignored == "false":
				self.getControl(controlId).getSelectedItem().setProperty("isIgnored","true")
				self.getControl(controlId).getSelectedItem().setLabel("[COLOR selected]" + league_name + "[/COLOR]")
			else:
				self.getControl(controlId).getSelectedItem().setProperty("isIgnored","false")
				self.getControl(controlId).getSelectedItem().setLabel(league_name)
		#ok
		elif controlId == 5:
			ignored_items = []
			total_items = self.getControl(6).size()
			for i in xrange(0,total_items):
				item = self.getControl(6).getListItem(i)
				if item.getProperty("isIgnored") == "true":
					ignored_items.append(removeNonAscii(item.getLabel().replace("[COLOR selected]","").replace("[/COLOR]","")))
					addon.setSetting("manually-ignored-leagues",addon.getSetting("manually-ignored-leagues").replace("<league>"+removeNonAscii(item.getLabel().replace("[COLOR selected]","").replace("[/COLOR]",""))+"</league>",""))
			
			FileIO.filewrite(ignored_league_list_file,str(ignored_items))
			self.close()
			xbmcgui.Dialog().ok(translate(32000),translate(32009))

		elif controlId == 7:
			self.close()

def start():
	ignoreWindow = Select(
		'DialogSelect.xml',
		addon_path,
		'default',
		'',
	)
	ignoreWindow.doModal()
	del ignoreWindow
	