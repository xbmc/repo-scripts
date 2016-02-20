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

def CheckDateString(datestring):
	datelist = datestring.split("-")
	if len(datelist) == 3:
		if len(datelist[0]) == 4:
			if len(datelist[1]) >= 1 and len(datelist[1]) <= 2:
				if len(datelist[2]) >= 1 and len(datelist[2]) <= 2:
					return True
			else: return False
		else:
			return False
	else:
		return False

def CheckDateTime(datetimedate):
	if "datetime.date" in str(type(datetimedate)): return True
	else: return False
