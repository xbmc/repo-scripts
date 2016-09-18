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
import datetime
import thesportsdb
import ignoreleagues
import eventdetails
from resources.lib.utilities import positions
from resources.lib.utilities import ssutils
from resources.lib.utilities.cache import AddonCache
from resources.lib.utilities.common_addon import *

api = thesportsdb.Api("7723457519235")


class detailsDialog(xbmcgui.WindowXMLDialog):
		
	def __init__( self, *args, **kwargs ):
		self.teamid = kwargs["teamid"]
		self.teamObjs = {}
		self.eventObjs = {}
		self.cache_object = AddonCache()

	def onInit(self):
		self.setHistory(self.teamid)

	def updateCacheTimes(self):
		self.t2 = datetime.datetime.now()
		self.hoursList = [168, 336, 504, 672, 840]
		self.interval = int(addon.getSetting("new_request_interval"))
		return

	def setHistory(self,teamid):
		self.getControl(32540).setImage(os.path.join(addon_path,"resources","img","goal.png"))
		xbmc.executebuiltin("SetProperty(loading-script-matchcenter-history,1,home)")
		self.updateCacheTimes()
		if teamid:
			self.teamid = teamid
		panel_ids = [32502,32503]
		event_listall = [api.Schedules().Next().Team(teamid=self.teamid),api.Schedules().Last().Team(teamid=self.teamid)]
		
		#iterate either future or past events
		for i in xrange(0,len(event_listall)):
			items = []
			events = event_listall[i]
			if events:
				for event in events:
					id_teams = [event.idHomeTeam,event.idAwayTeam]
					index = 0
					for id_team in id_teams:
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
							event.setHomeTeamObj(obj=teamobject)
						else:
							event.setAwayTeamObj(obj=teamobject)
						index += 1

					#Append to event objects to move the event information between windows. Avoid making
					#another request
					self.eventObjs[event.idEvent] = event

	                #create listitem
					item = xbmcgui.ListItem(event.strHomeTeam + "|" + event.strAwayTeam)
					if event.HomeTeamObj and event.AwayTeamObj:
						if show_alternative == "true":
							item.setProperty('hometeamname',event.HomeTeamObj.AlternativeNameFirst)
							item.setProperty('awayteamname',event.AwayTeamObj.AlternativeNameFirst)
						else:
							item.setProperty('hometeamname',event.strHomeTeam)
							item.setProperty('awayteamname',event.strAwayTeam)

						item.setProperty('competitionandround',event.strLeague + " - " + "Round" + " " +  str(event.intRound))
						item.setProperty('hometeambadge',event.HomeTeamObj.strTeamBadge)
						item.setProperty('awayteambadge',event.AwayTeamObj.strTeamBadge)
						item.setProperty('eventid',event.idEvent)

						#Set event time
						try:
							db_time = pytz.timezone(str(pytz.timezone("Etc/UTC"))).localize(event.eventDateTime)
							my_location=pytz.timezone(pytz.all_timezones[int(my_timezone)])
							converted_time=db_time.astimezone(my_location)
							starttime=converted_time.strftime("%a, %d %b %Y %H:%M")
							item.setProperty('date',starttime)
						except: pass

						#Set score for past matches
						if i == 1:
							if event.intHomeScore and event.intAwayScore:
								result = str(event.intHomeScore) + "-" + str(event.intAwayScore)
								item.setProperty("result","[B]" + result + "[/B]")

					items.append(item)
			self.getControl(panel_ids[i]).addItems(items)

		xbmc.executebuiltin("ClearProperty(loading-script-matchcenter-history,Home)")
		xbmc.executebuiltin("SetProperty(has_history,1,home)")

	def onClick(self,controlId):
		if controlId == 32503:
			eventid = self.getControl(controlId).getSelectedItem().getProperty("eventid")
			eventdetails.showDetails(self.eventObjs[eventid])

def start(teamid=None):
	main = detailsDialog('script-matchcenter-MatchHistory.xml', addon_path, getskinfolder(), '', teamid=teamid)		
	main.doModal()
	del main