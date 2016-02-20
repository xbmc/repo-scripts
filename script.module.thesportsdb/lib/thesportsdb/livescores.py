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
import time

class Livescore:
    def __init__(self):
        self.Date = ""
        self.League = ""
        self.Round = ""
        self.Spectators = ""
        self.HomeTeam = ""
        self.HomeTeam_Id = ""
        self.AwayTeam = ""
        self.AwayTeam_Id = ""
        self.Time = ""
        self.HomeGoals = ""
        self.AwayGoals = ""
        self.HomeGoalDetails = ""
        self.AwayGoalDetails = ""
        self.HomeLineupGoalkeeper = ""
        self.AwayLineupGoalkeeper = ""
        self.HomeLineupDefense = ""
        self.AwayLineupDefense = ""
        self.HomeLineupMidfield = ""
        self.AwayLineupMidfield = ""
        self.HomeLineupForward = ""
        self.AwayLineupForward = ""
        self.HomeLineupSubstitutes = ""
        self.AwayLineupSubstitutes = ""
        self.HomeLineupCoach = ""
        self.AwayLineupCoach = ""
        self.HomeSubDetails = ""
        self.AwaySubDetails =  ""
        self.HomeTeamFormation = ""
        self.AwayTeamFormation = ""
        self.Location = ""
        self.Stadium = ""
        self.Referee = ""
        self.HomeSubDetails = ""
        self.AwaySubDetails = ""
        self.HomeTeamYellowCardDetails = ""
        self.AwayTeamYellowCardDetails = ""
        self.HomeTeamRedCardDetails = ""
        self.AwayTeamRedCardDetails = ""
        self.HomeLineupCoach = ""
        self.AwayLineupCoach = ""
        self.HomeTeamObj = ""
        self.AwayTeamObj = ""

    def setHomeTeamObj(self,obj):
        self.HomeTeamObj = obj

    def setAwayTeamObj(self,obj):
        self.AwayTeamObj = obj

    @property 
    def DateTime(self):
        if self.Date:
            try:
                date = self.Date.split("+")[0]
                return datetime.datetime.fromtimestamp(time.mktime(time.strptime(date, "%Y-%m-%dT%H:%M:%S")))
            except: return None
        else:
            return None


def as_event(d):
    e = Livescore()
    e.__dict__.update(d)
    return e
