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
import datetime

class Player:
    def __init__(self):
        self.idPlayer = ""
        self.idTeam = ""
        self.idSoccerXML = ""
        self.idPlayerManager = ""
        self.strNationality = ""
        self.strPlayer = ""
        self.strTeam = ""
        self.strSport = ""
        self.intSoccerXMLTeamID = ""
        self.dateBorn = ""
        self.dateSigned = ""
        self.strSigning = ""
        self.strWage = ""
        self.strBirthLocation = ""
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
        self.strPosition = ""
        self.strCollege = ""
        self.strFacebook = ""
        self.strWebsite = ""
        self.strTwitter = ""
        self.strInstagram = ""
        self.strYoutube = ""
        self.strHeight = ""
        self.strWeight = ""
        self.intLoved = ""
        self.strThumb = ""
        self.strCutout = ""
        self.strFanart1 = ""
        self.strFanart2 = ""
        self.strFanart3 = ""
        self.strFanart4 = ""
        self.strLocked = ""


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
    def dateBornAsDatetime(self):
        if self.dateBorn:
            return datetime.datetime.strptime(self.dateBorn, "%Y-%m-%d").date()
        else:
            return None

    @property
    def dateSignedAsDatetime(self):
        if self.dateSigned:
            return datetime.datetime.strptime(self.dateSigned, "%Y-%m-%d").date()
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

def as_player(d):
    p = Player()
    p.__dict__.update(d)
    return p