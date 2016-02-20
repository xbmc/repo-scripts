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
import random

class League:
    def __init__(self):
        self.idLeague = ""
        self.idSoccerXML = ""
        self.strSport = ""
        self.strLeague = ""
        self.strLeagueAlternate = ""
        self.intFormedYear = ""
        self.dateFirstEvent = ""
        self.strGender = ""
        self.strCountry = ""
        self.strWebsite = ""
        self.strFacebook = ""
        self.strTwitter = ""
        self.strYoutube = ""
        self.strRSS = ""
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
        self.strFanart1 = ""
        self.strFanart2 = ""
        self.strFanart3 = ""
        self.strFanart4 = ""
        self.strBanner = ""
        self.strBadge = ""
        self.strLogo = ""
        self.strPoster = ""
        self.strTrophy = ""
        self.strNaming = ""
        self.strLocked = ""

    @property
    def AlternativeNameFirst(self):
        if self.strLeagueAlternate: return self.strLeagueAlternate
        else: return self.strLeague

    @property
    def FanartList(self):
        fanartlist = []
        if self.strFanart1: fanartlist.append(self.strFanart1)
        if self.strFanart2: fanartlist.append(self.strFanart2)
        if self.strFanart3: fanartlist.append(self.strFanart3)
        if self.strFanart4: fanartlist.append(self.strFanart4)
        return fanartlist

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

def as_league(d):
    l = League()
    l.__dict__.update(d)
    return l