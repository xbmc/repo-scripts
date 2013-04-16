'''
    ISY Event Engine for XBMC (log)
    Copyright (C) 2012 Ryan M. Kraus

    LICENSE:
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
    
    DESCRIPTION:
    This Python Module logs messages for the XBMC addon, ISY Events.
    
    WRITTEN:    11/2012
'''

# imports
# xbmc
import xbmcaddon

# get translator function
self = xbmcaddon.Addon('service.script.isyevents')
translator = self.getLocalizedString

# function to record messages to log
def log(msg):
    print translator(33001) + msg