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
import os
import xbmcgui
import thesportsdb
from resources.lib import ssutils
from resources.lib.addonfileio import FileIO
from resources.lib.common_addon import *

api = thesportsdb.Api("7723457519235")

class Select(xbmcgui.WindowXMLDialog):
	
	def __init__( self, *args, **kwargs ):
		if os.path.exists(ignored_league_list_file):
			self.already_ignored = eval(FileIO.fileread(ignored_league_list_file))
		else:
			self.already_ignored = []

	def onInit(self):
		self.getControl(1).setLabel(translate(32002))
		#Krypton
		if int(xbmc.getInfoLabel("System.BuildVersion")[0:2]) >= 17:
			self.getControl(OPTIONS_OK).setLabel(translate(32016))
			self.getControl(OPTIONS_CANCEL).setLabel(translate(32017))

		leagues = api.Search().Leagues(sport="Soccer")
		if leagues:
			items = []

			for league in leagues:
				if removeNonAscii(league.strLeague) in self.already_ignored:
					item = xbmcgui.ListItem("[COLOR selected]" + league.strLeague + "[/COLOR]")
					item.setProperty("isIgnored","true")
				else:
					item = xbmcgui.ListItem(league.strLeague)
					item.setProperty("isIgnored","false")
				item.setArt({"thumb":league.strBadge})
				items.append(item)
			self.getControl(6).addItems(items)
			self.setFocusId(6)

	def onAction(self,action):
		if action.getId() == ACTION_BACK1 or action.getId() == ACTION_BACK2:
			self.close()
		elif action.getId() == ACTION_LEFT:
			self.setFocusId(6)

	def onClick(self,controlId):
		#list
		if controlId == OPTIONS_PANEL:
			is_ignored = self.getControl(controlId).getSelectedItem().getProperty("isIgnored")
			league_name = self.getControl(controlId).getSelectedItem().getLabel().replace("[COLOR selected]","").replace("[/COLOR]","")
			if is_ignored == "false":
				self.getControl(controlId).getSelectedItem().setProperty("isIgnored","true")
				self.getControl(controlId).getSelectedItem().setLabel("[COLOR selected]" + league_name + "[/COLOR]")
			else:
				self.getControl(controlId).getSelectedItem().setProperty("isIgnored","false")
				self.getControl(controlId).getSelectedItem().setLabel(league_name)
		#ok
		elif controlId == OPTIONS_OK:
			ignored_items = []
			total_items = self.getControl(OPTIONS_PANEL).size()
			for i in xrange(0,total_items):
				item = self.getControl(OPTIONS_PANEL).getListItem(i)
				if item.getProperty("isIgnored") == "true":
					ignored_items.append(removeNonAscii(item.getLabel().replace("[COLOR selected]","").replace("[/COLOR]","")))
			
			if not os.path.exists(addon_userdata):
				os.mkdir(addon_userdata)

			FileIO.filewrite(ignored_league_list_file,str(ignored_items))
			
			self.close()
			xbmcgui.Dialog().ok(translate(32000),translate(32009))

		elif controlId == OPTIONS_CANCEL:
			self.close()
	