# -*- coding: utf-8 -*-
'''
    script.screensaver.cocktail - A random cocktail recipe screensaver for kodi 
    Copyright (C) 2015 enen92,Zag

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
import xbmcaddon
import xbmcvfs
import thecocktaildb
import os

addon = xbmcaddon.Addon(id='script.screensaver.cocktail')
addon_path = addon.getAddonInfo('path')
addon_userdata = xbmc.translatePath(addon.getAddonInfo('profile')).decode('utf-8')
addon_name = addon.getAddonInfo('name')
cocktailsdb_api = thecocktaildb.Api('1352')
favourite_drinks_folder = os.path.join(addon_userdata,'favourites')

if not os.path.exists(addon_userdata): xbmcvfs.mkdir(addon_userdata)
if not os.path.exists(favourite_drinks_folder): xbmcvfs.mkdir(favourite_drinks_folder)


ACTION_CONTEXT_MENU = 117
ACTION_LEFT = 1
ACTION_RIGHT = 2
ACTION_ESCAPE = 10
ACTION_RETURN = 92
ACTION_ENTER = 7


def removeNonAscii(s):
	return "".join(filter(lambda x: ord(x)<128, s))

def translate(text):
	return addon.getLocalizedString(text).encode('utf-8')
