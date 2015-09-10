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
import sys
import os
import urllib
from resources.lib import thecocktaildb
from resources.lib import ingredient_details
from resources.lib.common_cocktail import *

if addon.getSetting('ingredient-switch') == '0': switch_percentage = 20
elif addon.getSetting('ingredient-switch') == '1': switch_percentage = 10

#Window controls
drinklabel = 32603
drinkthumb = 32602
drinksublabel = 32604
drinkrecipe = 32606
INGREDIENT_PANEL_CONTROL = 32607
FICTIONAL_PANEL_CONTROL = 32608


class Screensaver(xbmcgui.WindowXMLDialog):
	def __init__( self, *args, **kwargs ):
		self.canceled = False
		self.mode = args[3]
		if self.mode:
			self.screensaver_mode = False
			self.cocktail_id = str(self.mode)
		else:
			self.screensaver_mode = True
	
	def onInit(self):
	
		#initiate fictional controler
		ingredient = xbmcgui.ListItem('scipt.screensaver.cocktail')
		self.getControl(FICTIONAL_PANEL_CONTROL).addItem(ingredient)
	
	
		self.drink_id = 0
		
		if self.screensaver_mode:
			if addon.getSetting('enable-instructions') == 'true':
				xbmc.executebuiltin("SetProperty(instructions,1,home)")
				wait_time = int(addon.getSetting('wait-time-instructions'))
				xbmc.sleep(wait_time*1000)
				
		next_random = int(addon.getSetting('next-time'))*1000
		
		if self.screensaver_mode:
			self.set_random()
			self.current_time = 0
			while not self.canceled:
				if self.current_time >= next_random:
					self.set_random()
					self.current_time = 0
				else:
					if ((float(self.current_time)/next_random)*100) % switch_percentage == 0.0 and ((float(self.current_time)/next_random)*100) != 0.0:
						if self.position == 0 and self.pages > 1:
							self.clear_ingredients()
							self.set_second_ingredients(self.cocktail_obj)
						elif self.position == 1:
							self.clear_ingredients()
							if self.pages == 3:
								self.set_third_ingredients(self.cocktail_obj)
							else:
								self.set_first_ingredients(self.cocktail_obj)
						elif self.position == 2:
							self.clear_ingredients()
							self.set_first_ingredients(self.cocktail_obj)
						xbmc.sleep(200)
						self.current_time += 200
					else:
						xbmc.sleep(200)
						self.current_time += 200
						
		else:
			xbmc.executebuiltin("SetProperty(loading,1,home)")
			cocktails_list = cocktailsdb_api.Lookup().cocktail(self.cocktail_id)
			xbmc.executebuiltin("ClearProperty(loading,Home)")
			if cocktails_list:
				self.set_cocktail(cocktails_list[0])
			else:
				xbmcgui.Dialog().ok(translate(32000),translate(32011))
				self.close()
			self.current_time = 0
			while not self.canceled:
				if ((float(self.current_time)/next_random)*100) % switch_percentage == 0.0 and ((float(self.current_time)/next_random)*100) != 0.0:
					if self.position == 0 and self.pages > 1:
						self.clear_ingredients()
						self.set_second_ingredients(self.cocktail_obj)
					elif self.position == 1:
						self.clear_ingredients()
						if self.pages == 3:
							self.set_third_ingredients(self.cocktail_obj)
						else:
							self.set_first_ingredients(self.cocktail_obj)
					elif self.position == 2:
						self.clear_ingredients()
						self.set_first_ingredients(self.cocktail_obj)
					xbmc.sleep(200)
					self.current_time += 200
				else:
					xbmc.sleep(200)
					self.current_time += 200
				

	def set_random(self):
		xbmc.executebuiltin("SetProperty(loading,1,home)")
		cocktails_list = cocktailsdb_api.Lookup().random()
		xbmc.sleep(200)
		xbmc.executebuiltin("ClearProperty(instructions,Home)")
		if int(cocktails_list[0].id) != self.drink_id:
			xbmc.sleep(200)
			xbmc.executebuiltin("ClearProperty(loading,Home)")
			self.drink_id = int(cocktails_list[0].id)
			self.set_cocktail(cocktails_list[0])
		else:	
			self.set_random()
		return
		
	def set_cocktail(self,cocktail):
		self.cocktail_obj = cocktail
		self.pages = 1
		self.clear_all()
		self.getControl(drinklabel).setLabel(cocktail.name)
		if cocktail.thumb: self.getControl(drinkthumb).setImage(cocktail.thumb)
		else: self.getControl(drinkthumb).setImage(os.path.join(addon_path,"resources","skins","default","media","cocktail.jpg"))
		self.getControl(drinkrecipe).setText(cocktail.recipe)
		self.getControl(drinksublabel).setText(cocktail.category + ' - ' + cocktail.alcoholic + ' - ' + cocktail.glass)
		self.set_first_ingredients(cocktail)
		return
		
	def set_first_ingredients(self,cocktail):
		self.position = 0
		
		ingredient_list = []
		
		if cocktail.ingredient1.rstrip():
			ingredient = xbmcgui.ListItem(cocktail.ingredient1)
			ingredient.setArt({ 'thumb': 'http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient1))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient1))+'.png')
			if cocktail.measure1.rstrip(): ingredient.setProperty('measure','('+cocktail.measure1.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if cocktail.ingredient2.rstrip():
			ingredient = xbmcgui.ListItem(cocktail.ingredient2)
			ingredient.setArt({ 'thumb': 'http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient2))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient2))+'.png')
			if cocktail.measure2.rstrip(): ingredient.setProperty('measure','('+cocktail.measure2.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if cocktail.ingredient3.rstrip():
			ingredient = xbmcgui.ListItem(cocktail.ingredient3)
			ingredient.setArt({ 'thumb': 'http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient3))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient3))+'.png')
			if cocktail.measure3.rstrip(): ingredient.setProperty('measure','('+cocktail.measure3.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
		
		if cocktail.ingredient4.rstrip():
			ingredient = xbmcgui.ListItem(cocktail.ingredient4)
			ingredient.setArt({ 'thumb': 'http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient4))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient4))+'.png')
			if cocktail.measure4.rstrip(): ingredient.setProperty('measure','('+cocktail.measure4.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if cocktail.ingredient5.rstrip():
			ingredient = xbmcgui.ListItem(cocktail.ingredient5)
			ingredient.setArt({ 'thumb': 'http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient5))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient5))+'.png')
			if cocktail.measure5.rstrip(): ingredient.setProperty('measure','('+cocktail.measure5.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if cocktail.ingredient6.rstrip():
			ingredient = xbmcgui.ListItem(cocktail.ingredient6)
			ingredient.setArt({ 'thumb': 'http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient6))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient6))+'.png')
			if cocktail.measure6.rstrip(): ingredient.setProperty('measure','('+cocktail.measure6.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
		
		
		self.getControl(INGREDIENT_PANEL_CONTROL).addItems(ingredient_list)
		if cocktail.ingredient7.rstrip(): self.pages = 2
		return
	
	def set_second_ingredients(self,cocktail):
		self.position = 1
		
		ingredient_list = []
		
		if cocktail.ingredient7.rstrip():
			ingredient = xbmcgui.ListItem(cocktail.ingredient7)
			ingredient.setArt({ 'thumb': 'http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient7))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient7))+'.png')
			if cocktail.measure7.rstrip(): ingredient.setProperty('measure','('+cocktail.measure7.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if cocktail.ingredient8.rstrip():
			ingredient = xbmcgui.ListItem(cocktail.ingredient8)
			ingredient.setArt({ 'thumb': 'http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient8))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient8))+'.png')
			if cocktail.measure8.rstrip(): ingredient.setProperty('measure','('+cocktail.measure8.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if cocktail.ingredient9.rstrip():
			ingredient = xbmcgui.ListItem(cocktail.ingredient9)
			ingredient.setArt({ 'thumb': 'http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient9))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient9))+'.png')
			if cocktail.measure9.rstrip(): ingredient.setProperty('measure','('+cocktail.measure9.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
		
		if cocktail.ingredient10.rstrip():
			ingredient = xbmcgui.ListItem(cocktail.ingredient10)
			ingredient.setArt({ 'thumb': 'http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient10))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient10))+'.png')
			if cocktail.measure10.rstrip(): ingredient.setProperty('measure','('+cocktail.measure10.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if cocktail.ingredient11.rstrip():
			ingredient = xbmcgui.ListItem(cocktail.ingredient11)
			ingredient.setArt({ 'thumb': 'http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient11))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient11))+'.png')
			if cocktail.measure11.rstrip(): ingredient.setProperty('measure','('+cocktail.measure11.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if cocktail.ingredient12.rstrip():
			ingredient = xbmcgui.ListItem(cocktail.ingredient12)
			ingredient.setArt({ 'thumb': 'http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient12))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient12))+'.png')
			if cocktail.measure12.rstrip(): ingredient.setProperty('measure','('+cocktail.measure12.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
		
		
		self.getControl(INGREDIENT_PANEL_CONTROL).addItems(ingredient_list)
		if cocktail.ingredient13.rstrip(): self.pages = 3
		return
		
	def set_third_ingredients(self,cocktail):
		self.position = 2
		
		if cocktail.ingredient13.rstrip():
			ingredient = xbmcgui.ListItem(cocktail.ingredient13)
			ingredient.setArt({ 'thumb': 'http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient13))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient13))+'.png')
			if cocktail.measure13.rstrip(): ingredient.setProperty('measure','('+cocktail.measure13.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if cocktail.ingredient14.rstrip():
			ingredient = xbmcgui.ListItem(cocktail.ingredient14)
			ingredient.setArt({ 'thumb': 'http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient14))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient14))+'.png')
			if cocktail.measure14.rstrip(): ingredient.setProperty('measure','('+cocktail.measure14.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if cocktail.ingredient15.rstrip():
			ingredient = xbmcgui.ListItem(cocktail.ingredient15)
			ingredient.setArt({ 'thumb': 'http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient15))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.thecocktaildb.com/images/ingredients/'+urllib.quote(removeNonAscii(cocktail.ingredient15))+'.png')
			if cocktail.measure15.rstrip(): ingredient.setProperty('measure','('+cocktail.measure15.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
		return
	
	def set_ingredient_description(self,ingredient_name,ingredient_thumb,ingredient_description):
		ingredient_details.start(ingredient_name,ingredient_thumb,ingredient_description)
		return
		
	def clear_all(self):
		self.getControl(drinklabel).setLabel('')
		self.getControl(drinkthumb).setImage('')
		self.getControl(drinkrecipe).setText('')
		self.getControl(drinksublabel).setText('')
		self.clear_ingredients()
		return
		
	def clear_ingredients(self):
		self.getControl(INGREDIENT_PANEL_CONTROL).reset()
		return
		
	def close_screensaver(self):
		self.canceled = True
		self.close()
		return
		
	def onAction(self,action):
		if action.getId() == ACTION_ENTER:
			
			if not xbmc.getCondVisibility("Control.HasFocus("+str(INGREDIENT_PANEL_CONTROL)+")"):
				size = self.getControl(INGREDIENT_PANEL_CONTROL).size()
				if size > 0:
					self.setFocusId(INGREDIENT_PANEL_CONTROL)
					self.getControl(INGREDIENT_PANEL_CONTROL).selectItem(0)
			else:
				ingredient_name = self.getControl(INGREDIENT_PANEL_CONTROL).getSelectedItem().getLabel()
				ingredient_thumb = self.getControl(INGREDIENT_PANEL_CONTROL).getSelectedItem().getProperty('ingredient_thumb')
				#TODO get ingredient description when available
				ingredient_description = translate(32029)
				self.set_ingredient_description(ingredient_name,ingredient_thumb,ingredient_description)
		
		if action.getId() == ACTION_RIGHT and not xbmc.getCondVisibility("Control.HasFocus("+str(INGREDIENT_PANEL_CONTROL)+")"):
			if self.position == 0 and self.pages > 1:
				self.clear_ingredients()
				self.set_second_ingredients(self.cocktail_obj)
			elif self.position == 1 and self.pages > 2:
				self.clear_ingredients()
				self.set_third_ingredients(self.cocktail_obj)
			else:
				if self.screensaver_mode:
					self.current_time = 0
					self.set_random()
		
		elif action.getId() == ACTION_LEFT and not xbmc.getCondVisibility("Control.HasFocus("+str(INGREDIENT_PANEL_CONTROL)+")"):
			if self.position == 2 and self.pages <= 3:
				self.clear_ingredients()
				self.set_second_ingredients(self.cocktail_obj)
			elif self.position == 1 and self.pages <= 2:
				self.clear_ingredients()
				self.set_first_ingredients(self.cocktail_obj)
			else:
				if self.screensaver_mode:
					self.current_time = 0
					self.set_random()
		
		elif action.getId() == ACTION_CONTEXT_MENU:
			keyb = xbmc.Keyboard('', translate(32009))
			keyb.doModal()
			if (keyb.isConfirmed()):
				search_parameter = urllib.quote_plus(keyb.getText())
				if not search_parameter: xbmcgui.Dialog().ok(translate(32000),translate(32010))
				else:
					cocktails_list = cocktailsdb_api.Search().cocktail(search_parameter)
					if not cocktails_list: xbmcgui.Dialog().ok(translate(32000),translate(32011))
					else:
						cocktails_name = []
						for cocktail in cocktails_list:
							cocktails_name.append(cocktail.name)
						if len(cocktails_name) == 1:
							self.set_cocktail(cocktails_list[0])
						else:
							choose = xbmcgui.Dialog().select(translate(32000),cocktails_name)
							if choose > -1:
								self.set_cocktail(cocktails_list[choose])
							
		else:
			if action.getId() != 7:
				if self.screensaver_mode:
					if not xbmc.getCondVisibility("Control.HasFocus("+str(INGREDIENT_PANEL_CONTROL)+")"):
						self.close_screensaver()
					else:
						if action.getId() == ACTION_RETURN or action.getId() == ACTION_ESCAPE:
							if xbmc.getCondVisibility("Control.HasFocus("+str(INGREDIENT_PANEL_CONTROL)+")"):
								self.setFocusId(FICTIONAL_PANEL_CONTROL)	
				else:
					if action.getId() == ACTION_RETURN or action.getId() == ACTION_ESCAPE:
						if xbmc.getCondVisibility("Control.HasFocus("+str(INGREDIENT_PANEL_CONTROL)+")"):
							self.setFocusId(FICTIONAL_PANEL_CONTROL)
						else:
							self.close_screensaver()
							
	def onClick(self,controlId):
		if controlId == INGREDIENT_PANEL_CONTROL:
			ingredient_name = self.getControl(INGREDIENT_PANEL_CONTROL).getSelectedItem().getLabel()
			ingredient_thumb = self.getControl(INGREDIENT_PANEL_CONTROL).getSelectedItem().getProperty('ingredient_thumb')
			#TODO get ingredient description when available
			ingredient_description = translate(32029)
			self.set_ingredient_description(ingredient_name,ingredient_thumb,ingredient_description)
			


if __name__ == '__main__':

	#note pass id of the drink to open a given cocktail
	
	screensaver = Screensaver(
		'script-cocktail-Cocktailplayer.xml',
		addon_path,
		'default',
		'',
	)
	screensaver.doModal()
	del screensaver
	sys.modules.clear()
