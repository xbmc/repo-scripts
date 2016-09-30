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
import re
import ignoreleagues
from resources.lib.utilities import positions
from resources.lib.utilities import ssutils
from resources.lib.utilities.addonfileio import FileIO
from resources.lib.utilities.common_addon import *

api = thesportsdb.Api("7723457519235")


class detailsDialog(xbmcgui.WindowXMLDialog):
		
	def __init__( self, *args, **kwargs ):
		self.isRunning = True
		self.match = kwargs["item"]
		self.controls = []

	def onInit(self):
		self.setEventDetails()

	def setEventDetails(self):
		xbmc.executebuiltin("ClearProperty(has_lineups,Home)")
		xbmc.executebuiltin("SetProperty(has_details,1,home)")

		#livematch
		if 'idEvent' not in self.match.__dict__.keys():
			header = self.match.League + " - " + translate(32017) + " " + str(self.match.Round)
			matchTime = ssutils.translatematch(self.match.Time)
			matchHomeGoals = self.match.HomeGoals
			matchAwayGoals = self.match.AwayGoals
			matchpercent = 0.0
			#match time
			if "'" in self.match.Time.lower():
				try:
					matchpercent = float(int((float(self.match.Time.replace("'",""))/90)*100))
				except: pass
			else:
				if self.match.Time.lower() == "halftime":
					matchpercent = 50.0
				elif self.match.Time.lower() == "postponed" or self.match.Time.lower() == "not started":
					matchpercent = 0.0
				elif self.match.Time.lower() == "finished":
					matchpercent = 100.0
			#match status
			if self.match.Time.lower() == "finished": status = os.path.join(addon_path,"resources","img","redstatus.png")
			elif "'" in self.match.Time.lower(): status = os.path.join(addon_path,"resources","img","greenstatus.png")
			else: status = os.path.join(addon_path,"resources","img","yellowstatus.png")
			stadium = self.match.Stadium
			matchReferee = self.match.Referee
			matchSpectators = self.match.Spectators
			matchHomeGoalDetails = self.match.HomeGoalDetails
			matchHomeTeamRedCardDetails = self.match.HomeTeamRedCardDetails
			matchHomeTeamYellowCardDetails = self.match.HomeTeamYellowCardDetails
			matchHomeSubDetails = self.match.HomeSubDetails
			matchAwayGoalDetails = self.match.AwayGoalDetails
			matchAwayTeamRedCardDetails = self.match.AwayTeamRedCardDetails
			matchAwayTeamYellowCardDetails = self.match.AwayTeamYellowCardDetails
			matchAwaySubDetails = self.match.AwaySubDetails

		#past match
		else:
			header = self.match.strLeague + " - " + translate(32017) + " " + str(self.match.intRound)
			matchTime = ssutils.translatematch("Finished")
			matchHomeGoals = self.match.intHomeScore
			matchAwayGoals = self.match.intAwayScore
			status = os.path.join(addon_path,"resources","img","redstatus.png")
			matchpercent = 100.0
			stadium = self.match.HomeTeamObj.strStadium
			matchReferee = ""
			matchSpectators = self.match.intSpectators
			matchHomeGoalDetails = self.match.strHomeGoalDetails
			matchHomeTeamRedCardDetails = self.match.strHomeRedCards
			matchHomeTeamYellowCardDetails = self.match.strHomeYellowCards
			matchHomeSubDetails = ""
			matchAwayGoalDetails = self.match.strAwayGoalDetails
			matchAwayTeamRedCardDetails = self.match.strAwayRedCards
			matchAwayTeamYellowCardDetails = self.match.strAwayYellowCards
			matchAwaySubDetails = ""

		self.getControl(32500).setLabel(header)
		
		if self.match.HomeTeamObj:
			if self.match.HomeTeamObj.strTeamBadge:
				self.getControl(32501).setImage(self.match.HomeTeamObj.strTeamBadge)
			else:
				self.getControl(32501).setImage(os.path.join(addon_path,"resources","img","nobadge_placeholder.png"))
			if self.match.HomeTeamObj.strTeamJersey:
				self.getControl(32502).setImage(self.match.HomeTeamObj.strTeamJersey)
			else:
				self.getControl(32502).setImage(os.path.join(addon_path,"resources","img","nokit_placeholder.png"))
		else:
			self.getControl(32501).setImage(os.path.join(addon_path,"resources","img","nobadge_placeholder.png"))
			self.getControl(32502).setImage(os.path.join(addon_path,"resources","img","nokit_placeholder.png"))

		#Default values for team names. It depends if it is a live object or simple a past event
		if ("HomeTeam" in self.match.__dict__.keys() and "AwayTeam" in self.match.__dict__.keys()):
			self.getControl(32503).setLabel(self.match.HomeTeam)
			self.getControl(32506).setLabel(self.match.AwayTeam)
		else:
			self.getControl(32503).setLabel(self.match.strHomeTeam)
			self.getControl(32506).setLabel(self.match.strAwayTeam)

		if show_alternative == "true":
			if self.match.HomeTeamObj: self.getControl(32503).setLabel(self.match.HomeTeamObj.AlternativeNameFirst)
			if self.match.AwayTeamObj: self.getControl(32506).setLabel(self.match.AwayTeamObj.AlternativeNameFirst)			

		if self.match.AwayTeamObj:
			if self.match.AwayTeamObj.strTeamBadge:
				self.getControl(32504).setImage(self.match.AwayTeamObj.strTeamBadge)
			else:
				self.getControl(32504).setImage(os.path.join(addon_path,"resources","img","nobadge_placeholder.png"))
			if self.match.AwayTeamObj.strTeamJersey:
				self.getControl(32505).setImage(self.match.AwayTeamObj.strTeamJersey)
			else:
				self.getControl(32505).setImage(os.path.join(addon_path,"resources","img","nokit_placeholder.png"))
		else:
			self.getControl(32504).setImage(os.path.join(addon_path,"resources","img","nobadge_placeholder.png"))
			self.getControl(32505).setImage(os.path.join(addon_path,"resources","img","nokit_placeholder.png"))
		
		if matchHomeGoals and matchAwayGoals:
			self.getControl(32507).setLabel(str(matchHomeGoals)+"-"+str(matchAwayGoals))
		
		if matchTime:
			self.getControl(32508).setLabel(matchTime)

		#Match Status (yellow,green,red)
		self.getControl(32509).setImage(status)

		#Match progress bar
		self.getControl(32510).setPercent(matchpercent)

		#Stadium and location
		self.getControl(32511).setLabel(stadium)

		#Spectators and Referee
		if matchReferee:
			self.getControl(32512).setLabel("[COLOR selected]" + translate(32023) + ": [/COLOR]" + matchReferee)
		if matchSpectators:
			self.getControl(32513).setLabel(matchSpectators + " " + translate(32024))

		#Home Team Event Details
		vars = [("goal",matchHomeGoalDetails),("redcard",matchHomeTeamRedCardDetails),("yellowcard",matchHomeTeamYellowCardDetails),("sub",matchHomeSubDetails)]
		hometeamevents = {}
		home_subs = {}
		for key,var in vars:
			if key and var:
				if ";" in var:
					events = var.split(";")
					if events:
						for event in events:
							stringregex = re.findall("(\d+)'\:(.*)", event)
							if stringregex:
								for time,strevent in stringregex:
									if key == "sub":
										if time in home_subs.keys():
											if strevent.strip().startswith("in"):
												home_subs[time]["in"] = strevent
												if "out" in home_subs[time].keys():
													if not int(time) in hometeamevents.keys():
														hometeamevents[int(time)] = [(key,home_subs[time]["out"] + " |" + home_subs[time]["in"])]
													else:
														hometeamevents[int(time)].append((key,home_subs[time]["out"] + " |" + home_subs[time]["in"]))				
													#Remove item from dict (we might have more than one sub associated to a given minute)
													home_subs.pop(time, None)
													
											elif strevent.strip().startswith("out"):
												home_subs[time]["out"] = strevent
												if "in" in home_subs[time].keys():
													if not int(time) in hometeamevents.keys():
														hometeamevents[int(time)] = [(key,home_subs[time]["out"] + " |" + home_subs[time]["in"])]
													else:
														hometeamevents[int(time)].append((key,home_subs[time]["out"] + " |" + home_subs[time]["in"]))
													#Remove item from dict (we might have more than one sub associated to a given minute)
													home_subs.pop(time, None)
										else:
											home_subs[time] = {}
											if strevent.strip().startswith("in"):
												home_subs[time]["in"] = strevent
											elif strevent.strip().startswith("out"):
												home_subs[time]["out"] = strevent
									else:
										if not int(time) in hometeamevents.keys():
											hometeamevents[int(time)] = [(key,strevent)]
										else:
											hometeamevents[int(time)].append((key,strevent))
		#Away Team Event Details
		vars = [("goal",matchAwayGoalDetails),("redcard",matchAwayTeamRedCardDetails),("yellowcard",matchAwayTeamYellowCardDetails),("sub",matchAwaySubDetails)]
		awayteamevents = {}
		away_subs = {}
		for key,var in vars:
			if key and var:
				if ";" in var:
					events = var.split(";")
					if events:
						for event in events:
							stringregex = re.findall("(\d+)'\:(.*)", event)
							if stringregex:
								for time,strevent in stringregex:
									if key == "sub":
										if time in away_subs.keys():
											if strevent.strip().startswith("in"):
												away_subs[time]["in"] = strevent
												if "out" in away_subs[time].keys():
													if not int(time) in awayteamevents.keys():
														awayteamevents[int(time)] = [(key,away_subs[time]["out"] + " |" + away_subs[time]["in"])]
													else:
														awayteamevents[int(time)].append((key,away_subs[time]["out"] + " |" + away_subs[time]["in"]))				
													#Remove item from dict (we might have more than one sub associated to a given minute)
													away_subs.pop(time, None)
													
											elif strevent.strip().startswith("out"):
												away_subs[time]["out"] = strevent
												if "in" in away_subs[time].keys():
													if not int(time) in awayteamevents.keys():
														awayteamevents[int(time)] = [(key,away_subs[time]["out"] + " |" + away_subs[time]["in"])]
													else:
														awayteamevents[int(time)].append((key,away_subs[time]["out"] + " |" + away_subs[time]["in"]))
													#Remove item from dict (we might have more than one sub associated to a given minute)
													away_subs.pop(time, None)													
										else:
											away_subs[time] = {}
											if strevent.strip().startswith("in"):
												away_subs[time]["in"] = strevent	
											elif strevent.strip().startswith("out"):
												away_subs[time]["out"] = strevent
									else:
										if not strevent: strevent = translate(32025)
										if not int(time) in awayteamevents.keys():
											awayteamevents[int(time)] = [(key,strevent.strip())]
										else:
											awayteamevents[int(time)].append((key,strevent.strip()))

		#set home and away event details
		#set home
		self.getControl(32516).reset()
		if hometeamevents:
			items = []
			ordered_times = reversed(sorted(hometeamevents.keys()))
			for time in ordered_times:
				eventlist = hometeamevents[time]
				for eventtype,eventlabel in eventlist:
					item = xbmcgui.ListItem(str(eventtype) + str(eventlabel))
					item.setProperty("eventlabel",eventlabel)
					item.setProperty("eventimg",os.path.join(addon_path,"resources","img",str(eventtype)+".png"))
					item.setProperty("eventtime",str(time) + "':")
					items.append(item)
			if items:
				self.getControl(32516).addItems(items)
		
		#set home and away event details
		#set away
		self.getControl(32517).reset()
		if awayteamevents:
			items = []
			ordered_times = reversed(sorted(awayteamevents.keys()))
			for time in ordered_times:
				eventlist = awayteamevents[time]
				for eventtype,eventlabel in eventlist:
					item = xbmcgui.ListItem(str(eventtype) + str(eventlabel))
					item.setProperty("eventlabel",eventlabel)
					item.setProperty("eventimg",os.path.join(addon_path,"resources","img",str(eventtype)+".png"))
					item.setProperty("eventtime",str(time) + "':")
					items.append(item)
			if items:
				self.getControl(32517).addItems(items)
		self.setFocusId(32514)

	def setLineUps(self,team):
		xbmc.executebuiltin("ClearProperty(has_details,Home)")
		self.getControl(32519).setImage(os.path.join(addon_path,"resources","img","pitch.png"))
		xbmc.executebuiltin("SetProperty(has_lineups,1,home)")

		self.current_lineup = team
		
		if team == "home":
			if 'idEvent' not in self.match.__dict__.keys():
				if self.match.HomeTeamObj: self.LineUpTeamObj = self.match.HomeTeamObj
				else: self.LineUpTeamObj = None
				self.teamname = self.match.HomeTeam
				self.formationlabel = self.match.HomeTeamFormation
				self.lineupgoalkeeper = self.match.HomeLineupGoalkeeper
				self.lineupdefenders = self.match.HomeLineupDefense
				self.lineupmidfielders = self.match.HomeLineupMidfield
				self.lineupforwarders = self.match.HomeLineupForward
				self.lineupsubs = self.match.HomeLineupSubstitutes
				if self.match.HomeLineupCoach:
					self.lineupcoach = self.match.HomeLineupCoach.replace(";","")
				else: self.lineupcoach = {}
			else:
				self.teamname = self.match.strHomeTeam
				self.LineUpTeamObj = self.match.HomeTeamObj
				self.formationlabel = self.match.strHomeFormation
				self.lineupgoalkeeper = self.match.strHomeLineupGoalkeeper
				self.lineupdefenders = self.match.strHomeLineupDefense
				self.lineupmidfielders = self.match.strHomeLineupMidfield
				self.lineupforwarders = self.match.strHomeLineupForward
				self.lineupsubs = self.match.strHomeLineupSubstitutes
				self.lineupcoach = {}

			self.getControl(32527).setLabel(translate(32027))
		else:
			if 'idEvent' not in self.match.__dict__.keys():
				if self.match.AwayTeamObj: self.LineUpTeamObj = self.match.AwayTeamObj
				else: self.LineUpTeamObj = None
				self.teamname = self.match.AwayTeam
				self.formationlabel = self.match.AwayTeamFormation
				self.lineupgoalkeeper = self.match.AwayLineupGoalkeeper
				self.lineupdefenders = self.match.AwayLineupDefense
				self.lineupmidfielders = self.match.AwayLineupMidfield
				self.lineupforwarders = self.match.AwayLineupForward
				self.lineupsubs = self.match.AwayLineupSubstitutes
				if self.match.AwayLineupCoach:
					self.lineupcoach = self.match.AwayLineupCoach.replace(";","")
				else: self.lineupcoach = {}
			else:
				self.teamname = self.match.strAwayTeam
				self.LineUpTeamObj = self.match.AwayTeamObj
				self.formationlabel = self.match.strAwayFormation
				self.lineupgoalkeeper = self.match.strAwayLineupGoalkeeper
				self.lineupdefenders = self.match.strAwayLineupDefense
				self.lineupmidfielders = self.match.strAwayLineupMidfield
				self.lineupforwarders = self.match.strAwayLineupForward
				self.lineupsubs = self.match.strAwayLineupSubstitutes
				self.lineupcoach = {}

			self.getControl(32527).setLabel(translate(32028))

		#Set Labels for the panel
		self.getControl(32522).setLabel(translate(32029) + ":")
		self.getControl(32523).setLabel(translate(32030) + ":")

		#Set team information
		#Name
		self.getControl(32521).setLabel(self.teamname)
		if self.LineUpTeamObj:
			if show_alternative == "true":
				self.getControl(32521).setLabel(self.LineUpTeamObj.AlternativeNameFirst)
			
			#Set team Badge
			if self.LineUpTeamObj.strTeamBadge:
				self.getControl(32520).setImage(self.LineUpTeamObj.strTeamBadge)
			else:
				self.getControl(32520).setImage(os.path.join(addon_path,"resources","img","nobadge_placeholder.png"))
		else:
			self.getControl(32520).setImage(os.path.join(addon_path,"resources","img","nobadge_placeholder.png"))

		#Set team formation label
		if self.formationlabel:
			self.getControl(32518).setLabel(self.formationlabel)
		#Set coach
		if self.lineupcoach:
			self.getControl(32526).setLabel("[COLOR selected]" + translate(32026) + ":[/COLOR] " + self.lineupcoach)

		#Set Lineup
		starters = []

		if self.lineupgoalkeeper:
			self.lineupgoalkeeper = self.lineupgoalkeeper.replace(";","")
			starters.append(self.lineupgoalkeeper)
		
		defenders = []
		if self.lineupdefenders:
			for player in self.lineupdefenders.split(";"):
				if player:
					defenders.append(player.strip())
					starters.append(player.strip())
			self.lineupdefenders = defenders
			del defenders
		
		midfielders = []
		if self.lineupmidfielders:
			for player in self.lineupmidfielders.split(";"):
				if player:
					midfielders.append(player.strip())
					starters.append(player.strip())
			self.lineupmidfielders = midfielders
			del midfielders
		
		forwarders = []
		if self.lineupforwarders:
			for player in self.lineupforwarders.split(";"):
				if player:
					forwarders.append(player.strip())
					starters.append(player.strip())

		self.getControl(32524).reset()
		self.getControl(32524).addItems(starters)
		self.lineupforwarders = forwarders

		#Set Subs
		subs = []
		if self.lineupsubs:
			for player in self.lineupsubs.split(";"):
				if player: subs.append(player.strip())
		self.getControl(32525).reset()
		self.getControl(32525).addItems(subs)

		#Players on pitch
		pitch = self.getControl(32519)
		pitchPosition = pitch.getPosition()
		pitchHeight = pitch.getHeight()
		pitchWidth = pitch.getWidth()

		if self.formationlabel:
			formationsjson = eval(FileIO.fileread(json_formations))
			formation = formationsjson[self.formationlabel]
		else:
			formation = None

		if formation:
			#goalkeeper
			goalkeeper = formation["goalkeeper"]
			image_size = positions.getShirtHeight(pitchHeight,goalkeeper[1])
			image_x = int(goalkeeper[0]*float(pitchWidth))+int(0.15*image_size)
			image_y =  int(goalkeeper[1]*float(pitchHeight))+int(0.15*image_size)
			if self.LineUpTeamObj and self.LineUpTeamObj.strTeamJersey:
				image = xbmcgui.ControlImage(image_x,image_y,image_size,image_size, self.LineUpTeamObj.strTeamJersey )
				self.controls.append(image)
			else:
				image = xbmcgui.ControlImage(image_x,image_y,image_size,image_size, os.path.join(addon_path,"resources","img","nokit_placeholder.png") )
				self.controls.append(image)
			label = positions.getLabel(image, "[B]" + self.lineupgoalkeeper + "[/B]")
			self.controls.append(label)
			#defenders
			defenders = formation["defenders"]
			if defenders:
				i = 0
				for defender in defenders:
					image_size = positions.getShirtHeight(pitchHeight,defender[1])
					image_x = int(defender[0]*float(pitchWidth))+int(0.15*image_size)
					image_y =  int(defender[1]*float(pitchHeight))+int(0.15*image_size)
					if self.LineUpTeamObj and self.LineUpTeamObj.strTeamJersey:
						image = xbmcgui.ControlImage(image_x,image_y,image_size,image_size, self.LineUpTeamObj.strTeamJersey)
						self.controls.append(image)
					else:
						image = xbmcgui.ControlImage(image_x,image_y,image_size,image_size, os.path.join(addon_path,"resources","img","nokit_placeholder.png") )
						self.controls.append(image)
					label = positions.getLabel(image,"[B]" + self.lineupdefenders[i] + "[/B]")
					self.controls.append(label)
					i += 1
			#midfielders
			midfielders = formation["midfielders"]
			if midfielders:
				i = 0
				for midfielder in midfielders:
					image_size = positions.getShirtHeight(pitchHeight,midfielder[1])
					image_x = int(midfielder[0]*float(pitchWidth))+int(0.15*image_size)
					image_y =  int(midfielder[1]*float(pitchHeight))+int(0.15*image_size)
					if self.LineUpTeamObj and self.LineUpTeamObj.strTeamJersey:
						image = xbmcgui.ControlImage(image_x,image_y,image_size,image_size, self.LineUpTeamObj.strTeamJersey)
						self.controls.append(image)
					else:
						image = xbmcgui.ControlImage(image_x,image_y,image_size,image_size, os.path.join(addon_path,"resources","img","nokit_placeholder.png") )
						self.controls.append(image)
					label = positions.getLabel(image,"[B]" + self.lineupmidfielders[i] + "[/B]")
					self.controls.append(label)
					i += 1
			#forwarders
			forwarders = formation["forwarders"]
			if forwarders:
				i = 0
				for forwarder in forwarders:
					image_size = positions.getShirtHeight(pitchHeight,forwarder[1])
					image_x = int(forwarder[0]*float(pitchWidth))+int(0.15*image_size)
					image_y =  int(forwarder[1]*float(pitchHeight))+int(0.15*image_size)
					if self.LineUpTeamObj and self.LineUpTeamObj.strTeamJersey:
						image = xbmcgui.ControlImage(image_x,image_y,image_size,image_size, self.LineUpTeamObj.strTeamJersey)
						self.controls.append(image)
					else:
						image = xbmcgui.ControlImage(image_x,image_y,image_size,image_size, os.path.join(addon_path,"resources","img","nokit_placeholder.png") )
						self.controls.append(image)
					label = positions.getLabel(image,"[B]" + self.lineupforwarders[i] + "[/B]")
					self.controls.append(label)
					i += 1

			self.addControls(self.controls)
		self.setFocusId(32527)

	def resetControls(self):
		self.removeControls(self.controls)
		self.controls = []


	def stopRunning(self):
		self.isRunning = False
		xbmc.executebuiltin("ClearProperty(has_lineups,Home)")
		xbmc.executebuiltin("ClearProperty(has_details,Home)")
		self.close()

	def onAction(self,action):
		if action.getId() == 92 or action.getId() == 10:
			self.stopRunning()

	def onClick(self,controlId):
		if controlId == 32514:
			if self.controls:
				self.resetControls()
			self.setLineUps("home")
		elif controlId == 32515:
			if self.controls:
				self.resetControls()
			self.setLineUps("away")
		elif controlId == 32528:
			if self.controls: 
				self.resetControls()
			self.setEventDetails()
		elif controlId == 32527:
			if self.controls: 
				self.resetControls()
			if self.current_lineup == "home":
				self.setLineUps("away")
			else:
				self.setLineUps("home")

def showDetails(match, matchid = None):
	if not match and matchid:
		match = api.Lookups().Event(eventid=matchid)
		if match: 
			match = match[0]
			match.setHomeTeamObj(api.Lookups().Team(teamid=match.idHomeTeam)[0])
			match.setAwayTeamObj(api.Lookups().Team(teamid=match.idAwayTeam)[0])
		else:
			xbmcgui.Dialog().ok(translate(32000), translate(32064))
			sys.exit(0)

	main = detailsDialog('script-matchcenter-EventDetails.xml', addon_path,getskinfolder(),'', item=match )
	main.doModal()
	del main