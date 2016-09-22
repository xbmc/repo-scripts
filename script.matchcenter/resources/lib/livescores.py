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
import sys
import thesportsdb
import random
import threading
import pytz
import datetime
import eventdetails
import ignoreleagues
import mainmenu
from utilities import ssutils
from utilities.addonfileio import FileIO
from utilities.cache import AddonCache
from utilities.common_addon import *

api = thesportsdb.Api("7723457519235")

class Main(xbmcgui.WindowXMLDialog):
	
	def __init__( self, *args, **kwargs ):
		self.isRunning = True
		self.standalone = kwargs["standalone"]
		self.teamObjs = {}
		self.cache_object = AddonCache()

	def onInit(self):
		xbmc.log(msg="[Match Center] Script started", level=xbmc.LOGDEBUG)
		if os.path.exists(ignored_league_list_file):
			self.ignored_leagues = [league.lower() for league in eval(FileIO.fileread(ignored_league_list_file)) if league] 
		else:
			self.ignored_leagues = []
		xbmc.executebuiltin("ClearProperty(no-games,Home)")
		self.getControl(32540).setImage(os.path.join(addon_path,"resources","img","goal.png"))
		xbmc.executebuiltin("SetProperty(loading-script-matchcenter-livescores,1,home)")
		self.livescoresThread()
		xbmc.executebuiltin("ClearProperty(loading-script-matchcenter-livescores,Home)")
		i = 0
		while self.isRunning:
			if (float(i*200)/(livescores_update_time*60*1000)).is_integer() and ((i*200)/(3*60*1000)) != 0:
				self.livescoresThread()
			xbmc.sleep(200)
			i += 1
		xbmc.log(msg="[Match Center] Script stopped", level=xbmc.LOGDEBUG)

	def updateCacheTimes(self):
		self.t2 = datetime.datetime.now()
		self.hoursList = [168, 336, 504, 672, 840]
		self.interval = int(addon.getSetting("new_request_interval"))
		return

	def livescoresThread(self):
		self.getLivescores()
		self.updateCacheTimes()
		self.setLivescores()
		return

	def getLivescores(self):
		self.livescoresdata = api.Livescores().Soccer()
		return

	def set_no_games(self):
		xbmc.executebuiltin("ClearProperty(loading-script-matchcenter-livescores,Home)")
		self.getControl(32541).setImage(os.path.join(addon_path,"resources","img","baliza.png"))
		xbmc.executebuiltin("SetProperty(no-games,1,home)")
		return
		
	def setLivescores(self):
		items = []
		self.livecopy = []
		if self.livescoresdata:
			for livegame in self.livescoresdata:
				if removeNonAscii(livegame.League).strip().lower() not in str(self.ignored_leagues):

					#decide to add the match or not
					if (livegame.Time.lower() != "not started") and (livegame.Time.lower() != "finished") and (livegame.Time.lower() != "postponed"):
						add = True
					else:
						if livegame.Time.lower() == "not started" and hide_notstarted == "true":
							add = False
						elif livegame.Time.lower() == "postponed" and hide_notstarted == "true":
							add = False
						elif livegame.Time.lower() == "finished" and hide_finished == "true":
							add = False
						else:
							add = True
					if not livegame.HomeGoals.strip() and not livegame.AwayGoals.strip():
						add = False
					
					#Get only the team objects for the games that will be added (avoid unecessary requests)
					#Append to self.teamObjs	
					if add == True:
						id_teams = []
						if livegame.HomeTeam_Id:
							id_teams.append(livegame.HomeTeam_Id)
						else:
							id_teams.append(None)

						if livegame.AwayTeam_Id:
							id_teams.append(livegame.AwayTeam_Id)
						else:
							id_teams.append(None)
	
						index = 0 #To distinguish home (0) from away team (1)
						for id_team in id_teams:
							if id_team:
								update_team_data = True
								if self.cache_object.isCachedTeam(id_team):
									update_team_data = abs(self.t2 - self.cache_object.getCachedTeamTimeStamp(id_team)) > datetime.timedelta(hours=self.hoursList[self.interval])
			                    
								if update_team_data:
									try:
										teamobject = api.Lookups().Team(teamid=id_team)[0]
										self.cache_object.cacheTeam(teamid=id_team,team_obj=teamobject)
										xbmc.log(msg="[Match Center] Timedelta was reached for team %s new request to be made..." % (str(id_team)), level=xbmc.LOGDEBUG)
									except: 
										teamobject = None
								else:
									teamobject = self.cache_object.getcachedTeam(id_team)
									xbmc.log(msg="[Match Center] Used cached data for team %s..." % (str(id_team)), level=xbmc.LOGDEBUG)
			                    
								if index == 0:
									livegame.setHomeTeamObj(obj=teamobject)
								else:
									livegame.setAwayTeamObj(obj=teamobject)
							index += 1

						#if livegame.HomeTeamObj and livegame.AwayTeamObj:
						item = xbmcgui.ListItem(livegame.HomeTeam+livegame.AwayTeam)
						item.setProperty('result',str(livegame.HomeGoals)+"-"+str(livegame.AwayGoals))
							
						#Set team name label
						hometeamName = livegame.HomeTeam
						awayteamName = livegame.AwayTeam
						if show_alternative == "true":
							if livegame.HomeTeamObj:
								hometeamName = livegame.HomeTeamObj.AlternativeNameFirst
							if livegame.AwayTeamObj:
								awayteamName = livegame.AwayTeamObj.AlternativeNameFirst							

						#Choose between textbox (long names) or label (short names)
						if len(hometeamName) >= 14 and " " in hometeamName:
							item.setProperty('hometeam_long',hometeamName)
						else:
							item.setProperty('hometeam_short',hometeamName)

						if len(awayteamName) >= 14 and " " in awayteamName:
							item.setProperty('awayteam_long',awayteamName)
						else:
							item.setProperty('awayteam_short',awayteamName)

						#set team badge
						if livegame.HomeTeamObj and livegame.HomeTeamObj.strTeamBadge:
							item.setProperty('home_team_logo',livegame.HomeTeamObj.strTeamBadge)
						else: 
							item.setProperty('home_team_logo',os.path.join(addon_path,"resources","img","nobadge_placeholder.png"))
						if livegame.AwayTeamObj and livegame.AwayTeamObj.strTeamBadge:
							item.setProperty('away_team_logo',livegame.AwayTeamObj.strTeamBadge)
						else: 
							item.setProperty('away_team_logo',os.path.join(addon_path,"resources","img","nobadge_placeholder.png"))

						if livegame.HomeGoals and bool(int(livegame.HomeGoals)>0):
							item.setProperty('has_home_goals',os.path.join(addon_path,"resources","img","goal.png"))
						if livegame.AwayGoals and bool(int(livegame.AwayGoals)>0):
							item.setProperty('has_away_goals',os.path.join(addon_path,"resources","img","goal.png"))
						if livegame.HomeGoalDetails: item.setProperty('home_goal_details',livegame.HomeGoalDetails)
						if livegame.AwayGoalDetails: item.setProperty('away_goal_details',livegame.AwayGoalDetails)
						item.setProperty('league_and_round',livegame.League+' - ' + translate(32017) + ' '+livegame.Round)
							
						#red cards
						if livegame.HomeTeamRedCardDetails:
							home_redcards = livegame.HomeTeamRedCardDetails.split(";")
							for redcard in home_redcards:
								if not redcard: home_redcards.remove(redcard)
							if len(home_redcards) == 1: item.setProperty('home_redcard1',os.path.join(addon_path,"resources","img","redcard.png"))
							elif len(home_redcards) > 1:
								item.setProperty('home_redcard1',os.path.join(addon_path,"resources","img","redcard.png"))
								item.setProperty('home_redcard2',os.path.join(addon_path,"resources","img","redcard.png"))
						if livegame.AwayTeamRedCardDetails:
							away_redcards = livegame.AwayTeamRedCardDetails.split(";")
							for redcard in away_redcards:
								if not redcard: away_redcards.remove(redcard)
							if len(away_redcards) == 1: item.setProperty('away_redcard2',os.path.join(addon_path,"resources","img","redcard.png"))
							elif len(away_redcards) > 1:
								item.setProperty('away_redcard1',os.path.join(addon_path,"resources","img","redcard.png"))
								item.setProperty('away_redcard2',os.path.join(addon_path,"resources","img","redcard.png"))
							
						#Convert event time to user timezone
						if livegame.Time.lower() == "not started":
							try:
								db_time = pytz.timezone(str(pytz.timezone("Etc/UTC"))).localize(livegame.DateTime)
								my_location=pytz.timezone(pytz.all_timezones[int(my_timezone)])
								converted_time=db_time.astimezone(my_location)
								starttime=converted_time.strftime("%H:%M")
								item.setProperty('starttime',starttime)
							except Exception, e:
								xbmc.log(msg="[Match Center] Exception: %s" % (str(e)), level=xbmc.LOGDEBUG)

						#set match progress
						matchpercent = "0"
						if "'" in livegame.Time.lower():
							try:
								matchpercent = str(int((float(livegame.Time.replace("'",""))/90)*100))
							except: pass
						else:
							if livegame.Time.lower() == "halftime":
								matchpercent = "50"
							elif livegame.Time.lower() == "postponed" or livegame.Time.lower() == "not started":
								matchpercent = "0"
							elif livegame.Time.lower() == "finished":
								matchpercent = "100" 
						item.setProperty("matchpercent",matchpercent)

						#check match status
						item.setProperty('minute',str(ssutils.translatematch(livegame.Time)))
						if livegame.Time.lower() == "finished": status = os.path.join(addon_path,"resources","img","redstatus.png")
						elif "'" in livegame.Time.lower(): status = os.path.join(addon_path,"resources","img","greenstatus.png")
						else: status = os.path.join(addon_path,"resources","img","yellowstatus.png")
						item.setProperty('status',status)
						items.append(item)
						
						self.livecopy.append(livegame)

		
		if items:
			#grab items selected first to select the one selected later
			match_identifier = None
			if self.getControl(32500).size() > 0:
				current_focused_item = self.getControl(32500).getSelectedItem()
				match_identifier = current_focused_item.getLabel()
			
			self.getControl(32500).reset()
			xbmc.executebuiltin("ClearProperty(no-games,Home)")
			self.items = items
			self.getControl(32500).addItems(items)
			#Resize dialog if no scrollbar is showing
			if len(items) <= 4:
				self.getControl(32502).setWidth(955)
			self.setFocusId(32500)
			#Set focus on previously focused match
			if match_identifier:
				index = 0
				for item in items:
					if item.getLabel() == match_identifier:
						self.getControl(32500).selectItem(index)
						break
					index += 1

		else:
			self.getControl(32500).reset()
			self.set_no_games()
		return

	def stopRunning(self):
		self.isRunning = False
		self.close()
		if not self.standalone:
			mainmenu.start()

	def onAction(self,action):
		if action.getId() == 92 or action.getId() == 10:
			self.stopRunning()
		elif action.getId() == 117:
			choose = xbmcgui.Dialog().select("Choose an option",["Ignore this league"])
			if choose > -1:
				panel = self.getControl(32500)
				league = panel.getSelectedItem().getProperty("league_and_round").split(" - ")
				if len(league) > 1 and league[0]:
					items = []
					events_list = []
					i = 0
					for item in self.items:
						if league[0].lower() not in item.getProperty("league_and_round").lower():
							items.append(item)
							events_list.append(self.livecopy[i])
						i += 1
					panel.reset()
					panel.addItems(items)
					self.items = items
					self.livecopy = events_list
					self.already_ignored = eval(FileIO.fileread(ignored_league_list_file))
					self.already_ignored.append(league[0])
					FileIO.filewrite(ignored_league_list_file,str(self.already_ignored))

	def onClick(self,controlId):
		if controlId == 32500:
			selectedItem = self.getControl(32500).getSelectedPosition()
			eventdetails.showDetails(self.livecopy[selectedItem])

def start(standalone=False):
	main = Main(
			'script-matchcenter-Livescores.xml',
			addon_path,
			getskinfolder(),
			'',
			standalone=standalone
			)
	main.doModal()
	del main