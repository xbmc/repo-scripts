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

class User:
	def __init__(self):
		self.strUsername = ""
		self.Teams = ""
		self.Players = ""
		self.Leagues = ""
		self.Events = ""

	def setUsername(self,user):
		self.strUsername = user

	def setTeams(self,teams):
		self.Teams = teams

	def setPlayers(self,players):
		self.Players = players

	def setLeagues(self,leagues):
		self.Leagues = leagues

	def setEvents(self,events):
		self.Events = events
