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

import xbmcaddon
import xbmcgui
import xbmc
import os

from resources.lib.common_cocktail import *

#Window controls
ingredientlabel = 32609
ingredientthumb = 32610
ingredientdescription = 32611



class Ingredientdetails(xbmcgui.WindowXMLDialog):
	def __init__( self, *args, **kwargs ):
		self.info = eval(args[3])
		
		self.ingredient_title = self.info[0]
		self.ingredient_thumb = self.info[1]
		self.ingredient_description = self.info[2]
	
	def onInit(self):
		self.getControl(ingredientlabel).setLabel(self.ingredient_title)
		self.getControl(ingredientthumb).setImage(self.ingredient_thumb)
		self.getControl(ingredientdescription).setText(self.ingredient_description)
		
	def onAction(self,action):
		if action.getId() == ACTION_RETURN or action.getId() == ACTION_ESCAPE:
			self.close()


def start(name,thumb,description):
	argm = str([name,thumb,description]) 
	ingrdts = Ingredientdetails(
		'script-cocktail-ingredientdetails.xml',
		addon_path,
		'default',
		argm,
	)
	ingrdts.doModal()
	del ingrdts
