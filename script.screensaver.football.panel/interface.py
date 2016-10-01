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

import xbmcgui
import xbmc
import sys
import thesportsdb
import random
import threading
import feedparser
import pytz
import datetime
from resources.lib import ignoreleagues
from resources.lib import ssutils
from resources.lib.addonfileio import FileIO
from resources.lib.cache import AddonCache
from resources.lib.common_addon import *

api = thesportsdb.Api("7723457519235")

class Main(xbmcgui.WindowXMLDialog):

	class ExitMonitor(xbmc.Monitor):

		def __init__(self, exit_callback):
			self.exit_callback = exit_callback

		def onAbortRequested(self):
			self.exit_callback()

		def onScreensaverDeactivated(self):
			self.exit_callback()
	
	def __init__( self, *args, **kwargs ):
		self.exit_monitor = self.ExitMonitor(self.stopRunning)
		if os.path.exists(ignored_league_list_file):
			self.ignored_leagues = eval(FileIO.fileread(ignored_league_list_file))
		else:
			self.ignored_leagues = []
		
		self.tables = ssutils.get_league_tables_ids()
		random.shuffle(self.tables)
		
		self.table_index = -1
		self.teamObjs = {}
		self.cache_object = AddonCache()

	def onInit(self):
		xbmc.log(msg="[Football Panel] Script started", level=xbmc.LOGDEBUG)
		self.isRunning = True
		xbmc.executebuiltin("ClearProperty(no-games,Home)")
		xbmc.executebuiltin("ClearProperty(has-tables,Home)")
		xbmc.executebuiltin("ClearProperty(has-rss,Home)")
		xbmc.executebuiltin("SetProperty(loading,1,home)")
		
		t1 = threading.Thread(target=self.livescoresThread)
		t2 = threading.Thread(target=self.tablesThread)
		t3 = threading.Thread(target=self.rssThread)
		t1.start()
		t2.start()
		t3.start()
		t1.join()
		t2.join()
		t3.join()
		xbmc.executebuiltin("ClearProperty(loading,Home)")
		i = 0
		while self.isRunning:
			if (float(i*200)/(livescores_update_time*60*1000)).is_integer() and i != 0:
				self.livescoresThread()
			if (float(i*200)/(tables_update_time*60*1000)).is_integer() and i != 0:
				self.tablesThread()
			if (float(i*200)/(rss_update_time*60*1000)).is_integer() and i != 0:
				self.rssThread()
			xbmc.sleep(200)
			i += 1
		xbmc.log(msg="[Football Panel] Script stopped", level=xbmc.LOGDEBUG)

	def livescoresThread(self):
		self.getLivescores()
		self.setLivescores()
		return

	def tablesThread(self):
		self.getLeagueTable()
		return

	def rssThread(self):
		self.setRss()
		return

	def setRss(self):
		feed = feedparser.parse(addon.getSetting("rss-url"))
		rss_line = ''
		for entry in feed['entries']:
			rss_line = rss_line + entry['summary_detail']['value'] + " | "
		if rss_line:
			#cleanup html code from the rss line
			htmlstriper = ssutils.HTMLStripper()
			htmlstriper.feed(rss_line)
			rss_line = htmlstriper.get_data()
			self.getControl(RSS_FEEDS).setLabel("")
			self.getControl(RSS_FEEDS).setLabel(rss_line)
			xbmc.executebuiltin("SetProperty(has-rss,1,home)")

	def getLivescores(self):
		self.livescoresdata = api.Livescores().Soccer()
		return

	def set_no_games(self):
		images = []
		self.updateCacheTimes()
		league_id = ssutils.get_league_id_no_games()

		update_team_data = True
		if self.cache_object.isCachedLeagueTeams(league_id):
			update_team_data = abs(self.t2 - self.cache_object.getCachedLeagueTeamsTimeStamp(league_id)) > datetime.timedelta(hours=self.hoursList[self.interval])

		if update_team_data:
			xbmc.log(msg="[Football Panel] Timedelta was reached for teams in league %s new request to be made..." % (str(league_id)), level=xbmc.LOGDEBUG)
			teams_in_league = api.Lookups().Team(leagueid=league_id)
			self.cache_object.cacheLeagueTeams(leagueid=league_id,team_obj_list=teams_in_league)
		else:
			xbmc.log(msg="[Football Panel] Using cached object for teams in league %s" % (str(league_id)), level=xbmc.LOGDEBUG)
			teams_in_league = self.cache_object.getcachedLeagueTeams(league_id)

		for team in teams_in_league:
			if team.strTeamFanart3: images.append(team.strTeamFanart3)
			if team.strTeamFanart4: images.append(team.strTeamFanart4)
		
		if images:
			random_photo = images[random.randint(0,len(images)-1)]
			self.getControl(NO_GAMES).setImage(random_photo)
		xbmc.executebuiltin("SetProperty(no-games,1,home)")
		return

	def updateCacheTimes(self):
		self.t2 = datetime.datetime.now()
		self.hoursList = [24, 48, 96, 168, 336]
		self.interval = int(addon.getSetting("new_request_interval"))
		return

	def getLeagueTable(self):
		
		self.table_index += 1
		if self.table_index > (len(self.tables)-1):
			self.table_index = 0

		leagueid = self.tables[self.table_index]
		table = api.Lookups().Table(leagueid)

		#Look for cached data first
		self.updateCacheTimes()

		#league data
		update_league_data = True
		if self.cache_object.isCachedLeague(leagueid):
			update_league_data = abs(self.t2 - self.cache_object.getCachedLeagueTimeStamp(leagueid)) > datetime.timedelta(hours=self.hoursList[self.interval])

		if update_league_data:
			xbmc.log(msg="[Football Panel] Timedelta was reached for league %s new request to be made..." % (str(leagueid)), level=xbmc.LOGDEBUG)
			league = api.Lookups().League(self.tables[self.table_index])[0]
			self.cache_object.cacheLeague(leagueid=leagueid,league_obj=league)
		else:
			xbmc.log(msg="[Football Panel] Using cached object for league %s" % (str(leagueid)), level=xbmc.LOGDEBUG)
			league = self.cache_object.getcachedLeague(leagueid)

		#team data
		update_team_data = True
		if self.cache_object.isCachedLeagueTeams(leagueid):
			update_team_data = abs(self.t2 - self.cache_object.getCachedLeagueTeamsTimeStamp(leagueid)) > datetime.timedelta(hours=self.hoursList[self.interval])

		if update_team_data:
			xbmc.log(msg="[Football Panel] Timedelta was reached for teams in league %s new request to be made..." % (str(leagueid)), level=xbmc.LOGDEBUG)
			teams_in_league = api.Lookups().Team(leagueid=self.tables[self.table_index])
			self.cache_object.cacheLeagueTeams(leagueid=leagueid,team_obj_list=teams_in_league)
		else:
			xbmc.log(msg="[Football Panel] Using cached object for teams in league %s" % (str(leagueid)), level=xbmc.LOGDEBUG)
			teams_in_league = self.cache_object.getcachedLeagueTeams(leagueid)
		
		#Finnaly set the table

		self.table = []
		for tableentry in table:
			try:
				item = xbmcgui.ListItem(tableentry.name)
				for team in teams_in_league:
					if tableentry.teamid == team.idTeam:
						item.setArt({ 'thumb': team.strTeamBadge })
						if show_alternative == "true":
							item.setLabel(team.AlternativeNameFirst)

				item.setProperty('points',str(tableentry.total))
				self.table.append(item)
			except Exception, e:
				xbmc.log(msg="[Football Panel] Exception: %s" % (str(e)), level=xbmc.LOGDEBUG)

		
		self.getControl(LEAGUETABLES_LIST_CONTROL).reset()
		if league.strLogo:
			self.getControl(LEAGUETABLES_CLEARART).setImage(league.strLogo)
		self.getControl(LEAGUETABLES_LIST_CONTROL).addItems(self.table)
		xbmc.executebuiltin("SetProperty(has-tables,1,home)")
		return
		
	def setLivescores(self):
		items = []
		self.updateCacheTimes()
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
					
					#Avoid adding matches that have no score defined
					if not livegame.HomeGoals.strip() and not livegame.AwayGoals.strip():
						add = False
						
					if add == True:

						#Get only the team objects for the games that will be added (avoid unecessary requests)
						#Append to self.teamObjs

						id_teams = [livegame.HomeTeam_Id,livegame.AwayTeam_Id]
						index = 0 #To distinguish home (0) from away team (1)
						for id_team in id_teams:
							update_team_data = True
							if self.cache_object.isCachedTeam(id_team):
								update_team_data = abs(self.t2 - self.cache_object.getCachedTeamTimeStamp(id_team)) > datetime.timedelta(hours=self.hoursList[self.interval])
		                    
							if update_team_data:
								try:
									teamobject = api.Lookups().Team(teamid=id_team)[0]
									self.cache_object.cacheTeam(teamid=id_team,team_obj=teamobject)
									xbmc.log(msg="[Football Panel] Timedelta was reached for team %s new request to be made..." % (str(id_team)), level=xbmc.LOGDEBUG)
								except: 
									teamobject = None
							else:
								teamobject = self.cache_object.getcachedTeam(id_team)
								xbmc.log(msg="[Football Panel] Used cached data for team %s..." % (str(id_team)), level=xbmc.LOGDEBUG)
		                    
							if index == 0:
								livegame.setHomeTeamObj(obj=teamobject)
							else:
								livegame.setAwayTeamObj(obj=teamobject)
							index += 1

						if livegame.HomeTeamObj and livegame.AwayTeamObj:
							item = xbmcgui.ListItem(livegame.HomeTeam+livegame.AwayTeam)
							item.setProperty('result',str(livegame.HomeGoals)+"-"+str(livegame.AwayGoals))
							item.setProperty('home_team_logo',livegame.HomeTeamObj.strTeamBadge)
							item.setProperty('away_team_logo',livegame.AwayTeamObj.strTeamBadge)
							if livegame.HomeGoals and bool(int(livegame.HomeGoals)>0):
								item.setProperty('has_home_goals',"goal.png")
							if livegame.AwayGoals and bool(int(livegame.AwayGoals)>0):
								item.setProperty('has_away_goals',"goal.png")
							if livegame.HomeGoalDetails: item.setProperty('home_goal_details',livegame.HomeGoalDetails)
							if livegame.AwayGoalDetails: item.setProperty('away_goal_details',livegame.AwayGoalDetails)
							item.setProperty('league_and_round',livegame.League+' - Round '+livegame.Round)
							
							#red cards
							if livegame.HomeTeamRedCardDetails:
								home_redcards = livegame.HomeTeamRedCardDetails.split(";")
								if home_redcards:
									for redcard in home_redcards:
										if not redcard: home_redcards.remove(redcard)
								if len(home_redcards) == 1: item.setProperty('home_redcard1',"redcard.png")
								elif len(home_redcards) > 1:
									item.setProperty('home_redcard1',"redcard.png")
									item.setProperty('home_redcard2',"redcard.png")
							if livegame.AwayTeamRedCardDetails:
								away_redcards = livegame.AwayTeamRedCardDetails.split(";")
								if away_redcards:
									for redcard in away_redcards:
										if not redcard: away_redcards.remove(redcard)
								if len(away_redcards) == 1: item.setProperty('away_redcard1',"redcard.png")
								elif len(away_redcards) > 1:
									item.setProperty('away_redcard1',"redcard.png")
									item.setProperty('away_redcard2',"redcard.png")
							
							#Convert event time to user timezone
							if livegame.Time.lower() == "not started":
								try:
									db_time = pytz.timezone(str(pytz.timezone("Etc/UTC"))).localize(livegame.DateTime)
									my_location=pytz.timezone(pytz.all_timezones[int(my_timezone)])
									converted_time=db_time.astimezone(my_location)
									starttime=converted_time.strftime("%H:%M")
									item.setProperty('starttime',starttime)
								except: pass

							#check match status
							item.setProperty('minute',str(livegame.Time))
							if livegame.Time.lower() == "finished": status = "redstatus.png"
							elif "'" in livegame.Time.lower(): status = "greenstatus.png"
							else: status = "yellowstatus.png"
							item.setProperty('status',status)
							items.append(item)

		self.getControl(LIVESCORES_PANEL_CONTROL_1).reset()
		self.getControl(LIVESCORES_PANEL_CONTROL_2).reset()
		if items:
			xbmc.executebuiltin("ClearProperty(no-games,Home)")
			if len(items) < 3:
				self.getControl(LIVESCORES_PANEL_CONTROL_1).addItems(items)
			else:
				self.getControl(LIVESCORES_PANEL_CONTROL_1).addItems(items[0:int(round(len(items)/2))])
				self.getControl(LIVESCORES_PANEL_CONTROL_2).addItems(items[int(round(len(items)/2))+1:])
		else:
			self.set_no_games()
		return

	def stopRunning(self):
		self.isRunning = False
		self.close()

	def onAction(self,action):
		if action.getId() == 92 or action.getId() == 10:
			self.stopRunning()

def get_params():
    pairsofparams = []
    if len(sys.argv) >= 2:
        params=sys.argv[1]
        pairsofparams=params.split('/')
        pairsofparams = [parm for parm in pairsofparams if parm]
    return pairsofparams

params=get_params()

if not params:
	main = Main(
			'script-livescores-Main.xml',
			addon_path,
			'default',
			'',
			)
	main.doModal()
	del main

else:
	if "ignoreleagues" in params:
		ignoreWindow = ignoreleagues.Select(
				'DialogSelect.xml',
				addon_path,
				'default',
				'',
				)
		ignoreWindow.doModal()
		del ignoreWindow
	elif "removecache" in params:
		AddonCache.removeCachedData()
