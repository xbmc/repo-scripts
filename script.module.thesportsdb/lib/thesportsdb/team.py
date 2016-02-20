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
import xbmc
import random

class Team:
    def __init__(self):
        self.idTeam = ""
        self.idSoccerXML = ""
        self.intLoved = ""
        self.strTeam = ""
        self.strTeamShort = ""
        self.strAlternate = ""
        self.intFormedYear = ""
        self.strSport = ""
        self.strLeague = ""
        self.idLeague = ""
        self.strDivision = ""
        self.strManager = ""
        self.strStadium = ""
        self.strKeywords = ""
        self.strRSS = ""
        self.strStadiumThumb = ""
        self.strStadiumDescription = ""
        self.strStadiumLocation = ""
        self.strWebsite = ""
        self.strFacebook = ""
        self.strTwitter = ""
        self.strInstagram = ""
        self.strDescriptionEN = ""
        self.strDescriptionDE = ""
        self.strDescriptionFR = ""
        self.strDescriptionCN = ""
        self.strDescriptionIT = ""
        self.strDescriptionJP = ""
        self.strDescriptionRU = ""
        self.strDescriptionES = ""
        self.strDescriptionPT = ""
        self.strDescriptionSE = ""
        self.strDescriptionNL = ""
        self.strDescriptionHU = ""
        self.strDescriptionNO = ""
        self.strDescriptionIL = ""
        self.strDescriptionPL = ""
        self.strGender = ""
        self.strCountry = ""
        self.strTeamBadge = ""
        self.strTeamJersey = ""
        self.strTeamLogo = ""
        self.strTeamFanart1 = ""
        self.strTeamFanart2 = ""
        self.strTeamFanart3 = ""
        self.strTeamFanart4 = ""
        self.strTeamBanner = ""
        self.strYoutube = ""
        self.strLocked = ""

    @property
    def AlternativeNameFirst(self):
        if self.strAlternate: return self.strAlternate
        else: return self.strTeam

    @property
    def FanartList(self):
        fanartlist = []
        if self.strTeamFanart1: fanartlist.append(self.strTeamFanart1)
        if self.strTeamFanart2: fanartlist.append(self.strTeamFanart2)
        if self.strTeamFanart3: fanartlist.append(self.strTeamFanart3)
        if self.strTeamFanart4: fanartlist.append(self.strTeamFanart4)
        return fanartlist

    @property
    def FanFanart(self):
        if self.strTeamFanart4: return self.strTeamFanart4
        else: return self.RandomFanart

    @property
    def PlayerFanart(self):
        if self.strTeamFanart3: return self.strTeamFanart3
        else: return self.RandomFanart

    @property
    def RandomFanart(self):
        if self.FanartList:
            return self.FanartList[random.randint(0,len(self.FanartList)-1)]
        else:
            return None

    @property
    def strDescription(self):
        description = self.strDescriptionEN
        xbmcLanguage = xbmc.getInfoLabel("System.Language")
        if "portuguese" in xbmcLanguage.lower():
            if self.strDescriptionPT: description = self.strDescriptionPT
        elif "german" in xbmcLanguage.lower():
            if self.strDescriptionDE: description = self.strDescriptionDE
        elif "french" in xbmcLanguage.lower():
            if self.strDescriptionFR: description = self.strDescriptionFR
        elif "chinese" in xbmcLanguage.lower():
            if self.strDescriptionCN: description = self.strDescriptionCN
        elif "italian" in xbmcLanguage.lower():
            if self.strDescriptionIT: description = self.strDescriptionIT
        elif "japanese" in xbmcLanguage.lower():
            if self.strDescriptionJP: description = self.strDescriptionJP
        elif "russian" in xbmcLanguage.lower():
            if self.strDescriptionRU: description = self.strDescriptionRU
        elif "spanish" in xbmcLanguage.lower():
            if self.strDescriptionES: description = self.strDescriptionES
        elif "swedish" in xbmcLanguage.lower():
            if self.strDescriptionSE: description = self.strDescriptionSE
        elif "dutch" in xbmcLanguage.lower():
            if self.strDescriptionNL: description = self.strDescriptionNL
        elif "hungarian" in xbmcLanguage.lower():
            if self.strDescriptionHU: description = self.strDescriptionHU
        elif "norwegian" in xbmcLanguage.lower():
            if self.strDescriptionNO: description = self.strDescriptionNO
        elif "hebrew" in xbmcLanguage.lower():
            if self.strDescriptionIL: description = self.strDescriptionIL
        elif "polish" in xbmcLanguage.lower():
            if self.strDescriptionPL: description = self.strDescriptionPL
        return description

def as_team(d):
    t = Team()
    t.__dict__.update(d)
    return t