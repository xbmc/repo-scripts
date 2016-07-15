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
import eventdetails
import ignoreleagues
import mainmenu
from utilities import ssutils
from utilities.common_addon import *

api = thesportsdb.Api("7723457519235")

class Main(xbmcgui.WindowXMLDialog):
	
	def __init__( self, *args, **kwargs ):
		self.isRunning = True
		self.standalone = kwargs["standalone"]
		self.teamObjs = {}

	def onInit(self):
		xbmc.log(msg="[Match Center] Script started", level=xbmc.LOGDEBUG)
		if os.path.exists(ignored_league_list_file):
			self.ignored_leagues = eval(ssutils.read_file(ignored_league_list_file))
		else:
			self.ignored_leagues = []
		xbmc.executebuiltin("ClearProperty(no-games,Home)")
		self.getControl(32540).setImage(os.path.join(addon_path,"resources","img","goal.png"))
		xbmc.executebuiltin("SetProperty(loading,1,home)")
		self.livescoresThread()
		xbmc.executebuiltin("ClearProperty(loading,Home)")
		i = 0
		while self.isRunning:
			if (float(i*200)/(livescores_update_time*60*1000)).is_integer() and ((i*200)/(3*60*1000)) != 0:
				self.livescoresThread()
			xbmc.sleep(200)
			i += 1
		xbmc.log(msg="[Match Center] Script stopped", level=xbmc.LOGDEBUG)

	def livescoresThread(self):
		self.getLivescores()
		self.setLivescores()
		return

	def getLivescores(self):
		self.livescoresdata = api.Livescores().Soccer()
		return

	def set_no_games(self):
		xbmc.executebuiltin("ClearProperty(loading,Home)")
		self.getControl(32541).setImage(os.path.join(addon_path,"resources","img","baliza.png"))
		xbmc.executebuiltin("SetProperty(no-games,1,home)")
		return
		
	def setLivescores(self):
		items = []
		self.livecopy = []
		if self.livescoresdata:
			for livegame in self.livescoresdata:
				if removeNonAscii(livegame.League) not in str(self.ignored_leagues):
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
						
					if add == True:
						#Get only the team objects for the games that will be added (avoid unecessary requests)
						#Append to self.teamObjs
						if not livegame.HomeTeam in self.teamObjs.keys():
							try:
								hometeamobj = api.Lookups().Team(teamid=livegame.HomeTeam_Id)[0]
								livegame.setHomeTeamObj(hometeamobj)
								self.teamObjs[livegame.HomeTeam] = hometeamobj
							except:
								hometeamobj = None
						else:
							hometeamobj = self.teamObjs[livegame.HomeTeam]
							livegame.setHomeTeamObj(hometeamobj)
						if not livegame.AwayTeam in self.teamObjs.keys():
							try:
								awayteamobj = api.Lookups().Team(teamid=livegame.AwayTeam_Id)[0]
								livegame.setAwayTeamObj(awayteamobj)
								self.teamObjs[livegame.AwayTeam] = awayteamobj
							except:
								awayteamobj = None
						else:
							awayteamobj = self.teamObjs[livegame.AwayTeam]
							livegame.setAwayTeamObj(awayteamobj)


						if awayteamobj and hometeamobj:
							item = xbmcgui.ListItem(livegame.HomeTeam+livegame.AwayTeam)
							item.setProperty('result',str(livegame.HomeGoals)+"-"+str(livegame.AwayGoals))
							
							#Set team name label
							if show_alternative == "true":
								hometeamName = livegame.HomeTeamObj.AlternativeNameFirst
								awayteamName = livegame.AwayTeamObj.AlternativeNameFirst
							else:
								hometeamName = livegame.HomeTeam
								awayteamName = livegame.AwayTeam

							#Choose between textbox (long names) or label (short names)
							if len(hometeamName) >= 14 and " " in hometeamName:
								item.setProperty('hometeam_long',hometeamName)
							else:
								item.setProperty('hometeam_short',hometeamName)

							if len(awayteamName) >= 14 and " " in awayteamName:
								item.setProperty('awayteam_long',awayteamName)
							else:
								item.setProperty('awayteam_short',awayteamName)

							item.setProperty('home_team_logo',livegame.HomeTeamObj.strTeamBadge)
							item.setProperty('away_team_logo',livegame.AwayTeamObj.strTeamBadge)
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
								except: pass

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

		self.getControl(32500).reset()
		if items:
			xbmc.executebuiltin("ClearProperty(no-games,Home)")
			self.getControl(32500).addItems(items)
			self.setFocusId(32500)
		else:
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