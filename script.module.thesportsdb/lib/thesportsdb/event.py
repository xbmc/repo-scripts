# -*- coding: utf-8 -*-
'''
    script.module.thesportsdb - A python module to wrap the main thesportsdb
    API methods
    Copyright (C) 2016 enen92,Zag

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
import datetime

class Event:
    def __init__(self):
        self.idEvent = ""
        self.idSoccerXML = ""
        self.strEvent = ""
        self.strFilename = ""
        self.strSport = ""
        self.idLeague = ""
        self.strLeague = ""
        self.strSeason = ""
        self.strDescriptionEN = ""
        self.strHomeTeam = ""
        self.strAwayTeam = ""
        self.intHomeScore = ""
        self.intRound = ""
        self.intAwayScore = ""
        self.intSpectators = ""
        self.strHomeGoalDetails = ""
        self.strHomeRedCards = ""
        self.strHomeYellowCards = ""
        self.strHomeLineupGoalkeeper = ""
        self.strHomeLineupDefense = ""
        self.strHomeLineupMidfield = ""
        self.strHomeLineupForward = ""
        self.strHomeLineupSubstitutes = ""
        self.strHomeFormation = ""
        self.strAwayRedCards = ""
        self.strAwayYellowCards = ""
        self.strAwayGoalDetails = ""
        self.strAwayLineupGoalkeeper = ""
        self.strAwayLineupDefense = ""
        self.strAwayLineupMidfield = ""
        self.strAwayLineupForward = ""
        self.strAwayLineupSubstitutes = ""
        self.strAwayFormation = ""
        self.intHomeShots = ""
        self.intAwayShots = ""
        self.dateEvent = ""
        self.strDate = ""
        self.strTime = ""
        self.strTVStation = ""
        self.idHomeTeam = ""
        self.idAwayTeam = ""
        self.strResult = ""
        self.strCircuit = ""
        self.strCountry = ""
        self.strCity = ""
        self.strPoster = ""
        self.strFanart = ""
        self.strThumb = ""
        self.strBanner = ""
        self.strMap = ""
        self.strLocked = ""

    @property
    def strDescription(self):
        return self.strDescriptionEN

    @property
    def eventDateTime(self):
        try:
            datelist = self.dateEvent.split("-")
            year = int(datelist[0])
            month = int(datelist[1])
            day = int(datelist[2])
            if self.strTime:
                timelist = self.strTime.split("+")[0].split(":")
                hour = int(timelist[0])
                minute = int(timelist[1])
                seconds = int(timelist[2])
            else:
                hour = 0
                minute = 0
                hour = 0
            return datetime.datetime(year=year,month=month,day=day,hour=hour,minute=minute,second=seconds)
        except: return None
    
    def setHomeTeamObj(self,obj=None):
        if obj:
            self.HomeTeamObj = obj

    def setAwayTeamObj(self,obj=None):
        if obj:
            self.AwayTeamObj = obj

def as_event(d):
    e = Event()
    e.__dict__.update(d)
    return e
