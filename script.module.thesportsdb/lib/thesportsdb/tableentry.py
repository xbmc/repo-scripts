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

class Tableentry:
    def __init__(self):
        self.name = ""
        self.teamid = ""
        self.played = ""
        self.goalsfor = ""
        self.goalsagainst = ""
        self.goalsdifference = ""
        self.win = ""
        self.draw = ""
        self.loss = ""
        self.total = ""
        self.Team = ""

    def setTeamObject(self,obj):
        self.Team = obj

def as_tableentry(d):
    t = Tableentry()
    t.__dict__.update(d)
    return t
