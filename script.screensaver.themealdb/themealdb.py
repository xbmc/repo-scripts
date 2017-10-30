# -*- coding: utf-8 -*-
'''
    script.screensaver.meal - A random meal recipe screensaver for kodi 
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
from resources.lib import themealdb
from resources.lib import ingredient_details
from resources.lib.common_meal import *

if addon.getSetting('ingredient-switch') == '0': switch_percentage = 20
elif addon.getSetting('ingredient-switch') == '1': switch_percentage = 10

#Window controls
recipelabel = 32603
recipethumb = 32602
recipesublabel = 32604
reciperecipe = 32606
INGREDIENT_PANEL_CONTROL = 32607
FICTIONAL_PANEL_CONTROL = 32608
BACK_BACKGROUND_CONTROL = 32609
BACK_ICON_CONTROL = 32610


class Screensaver(xbmcgui.WindowXMLDialog):
	def __init__( self, *args, **kwargs ):
		self.canceled = False
		self.mode = args[3]
		if self.mode:
			self.screensaver_mode = False
			self.meal_id = str(self.mode)
		else:
			self.screensaver_mode = True
	
	def onInit(self):
		#Enable back button for touch devices
		if addon.getSetting('enable-back') == "false":
			self.getControl(BACK_BACKGROUND_CONTROL).setVisible(False)
			self.getControl(BACK_ICON_CONTROL).setVisible(False)
			
		#initiate fictional controler
		ingredient = xbmcgui.ListItem('scipt.screensaver.meal')
		self.getControl(FICTIONAL_PANEL_CONTROL).addItem(ingredient)
	
	
		self.recipe_id = 0
		
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
							self.set_second_ingredients(self.meal_obj)
						elif self.position == 1:
							self.clear_ingredients()
							if self.pages == 3:
								self.set_third_ingredients(self.meal_obj)
							else:
								self.set_first_ingredients(self.meal_obj)
						elif self.position == 2:
							self.clear_ingredients()
							self.set_first_ingredients(self.meal_obj)
						xbmc.sleep(200)
						self.current_time += 200
					else:
						xbmc.sleep(200)
						self.current_time += 200
						
		else:
			xbmc.executebuiltin("SetProperty(loading,1,home)")
			meals_list = mealsdb_api.Lookup().meal(self.meal_id)
			xbmc.executebuiltin("ClearProperty(loading,Home)")
			if meals_list:
				self.set_meal(meals_list[0])
			else:
				xbmcgui.Dialog().ok(translate(32000),translate(32011))
				self.close()
			self.current_time = 0
			while not self.canceled:
				if ((float(self.current_time)/next_random)*100) % switch_percentage == 0.0 and ((float(self.current_time)/next_random)*100) != 0.0:
					if self.position == 0 and self.pages > 1:
						self.clear_ingredients()
						self.set_second_ingredients(self.meal_obj)
					elif self.position == 1:
						self.clear_ingredients()
						if self.pages == 3:
							self.set_third_ingredients(self.meal_obj)
						else:
							self.set_first_ingredients(self.meal_obj)
					elif self.position == 2:
						self.clear_ingredients()
						self.set_first_ingredients(self.meal_obj)
					xbmc.sleep(200)
					self.current_time += 200
				else:
					xbmc.sleep(200)
					self.current_time += 200
				

	def set_random(self):
		xbmc.executebuiltin("SetProperty(loading,1,home)")
		meals_list = mealsdb_api.Lookup().random()
		xbmc.sleep(200)
		xbmc.executebuiltin("ClearProperty(instructions,Home)")
		if int(meals_list[0].id) != self.recipe_id:
			xbmc.sleep(200)
			xbmc.executebuiltin("ClearProperty(loading,Home)")
			self.recipe_id = int(meals_list[0].id)
			self.set_meal(meals_list[0])
		else:	
			self.set_random()
		return
		
	def set_meal(self,meal):
		self.meal_obj = meal
		self.pages = 1
		self.clear_all()
		self.getControl(recipelabel).setLabel(meal.name)
		if meal.thumb: self.getControl(recipethumb).setImage(meal.thumb)
		else: self.getControl(recipethumb).setImage(os.path.join(addon_path,"resources","skins","default","media","meal.jpg"))
		self.getControl(reciperecipe).setText(meal.recipe)
		self.getControl(recipesublabel).setText(meal.category + ' - ')
		self.set_first_ingredients(meal)
		return
		
	def set_first_ingredients(self,meal):
		self.position = 0
		
		ingredient_list = []
		
		if meal.ingredient1.rstrip():
			ingredient = xbmcgui.ListItem(meal.ingredient1)
			ingredient.setArt({ 'thumb': 'http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient1))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient1))+'.png')
			if meal.measure1.rstrip(): ingredient.setProperty('measure','('+meal.measure1.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if meal.ingredient2.rstrip():
			ingredient = xbmcgui.ListItem(meal.ingredient2)
			ingredient.setArt({ 'thumb': 'http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient2))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient2))+'.png')
			if meal.measure2.rstrip(): ingredient.setProperty('measure','('+meal.measure2.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if meal.ingredient3.rstrip():
			ingredient = xbmcgui.ListItem(meal.ingredient3)
			ingredient.setArt({ 'thumb': 'http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient3))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient3))+'.png')
			if meal.measure3.rstrip(): ingredient.setProperty('measure','('+meal.measure3.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
		
		if meal.ingredient4.rstrip():
			ingredient = xbmcgui.ListItem(meal.ingredient4)
			ingredient.setArt({ 'thumb': 'http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient4))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient4))+'.png')
			if meal.measure4.rstrip(): ingredient.setProperty('measure','('+meal.measure4.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if meal.ingredient5.rstrip():
			ingredient = xbmcgui.ListItem(meal.ingredient5)
			ingredient.setArt({ 'thumb': 'http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient5))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient5))+'.png')
			if meal.measure5.rstrip(): ingredient.setProperty('measure','('+meal.measure5.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if meal.ingredient6.rstrip():
			ingredient = xbmcgui.ListItem(meal.ingredient6)
			ingredient.setArt({ 'thumb': 'http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient6))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient6))+'.png')
			if meal.measure6.rstrip(): ingredient.setProperty('measure','('+meal.measure6.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
		
		
		self.getControl(INGREDIENT_PANEL_CONTROL).addItems(ingredient_list)
		if meal.ingredient7.rstrip(): self.pages = 2
		return
	
	def set_second_ingredients(self,meal):
		self.position = 1
		
		ingredient_list = []
		
		if meal.ingredient7.rstrip():
			ingredient = xbmcgui.ListItem(meal.ingredient7)
			ingredient.setArt({ 'thumb': 'http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient7))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient7))+'.png')
			if meal.measure7.rstrip(): ingredient.setProperty('measure','('+meal.measure7.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if meal.ingredient8.rstrip():
			ingredient = xbmcgui.ListItem(meal.ingredient8)
			ingredient.setArt({ 'thumb': 'http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient8))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient8))+'.png')
			if meal.measure8.rstrip(): ingredient.setProperty('measure','('+meal.measure8.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if meal.ingredient9.rstrip():
			ingredient = xbmcgui.ListItem(meal.ingredient9)
			ingredient.setArt({ 'thumb': 'http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient9))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient9))+'.png')
			if meal.measure9.rstrip(): ingredient.setProperty('measure','('+meal.measure9.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
		
		if meal.ingredient10.rstrip():
			ingredient = xbmcgui.ListItem(meal.ingredient10)
			ingredient.setArt({ 'thumb': 'http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient10))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient10))+'.png')
			if meal.measure10.rstrip(): ingredient.setProperty('measure','('+meal.measure10.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if meal.ingredient11.rstrip():
			ingredient = xbmcgui.ListItem(meal.ingredient11)
			ingredient.setArt({ 'thumb': 'http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient11))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient11))+'.png')
			if meal.measure11.rstrip(): ingredient.setProperty('measure','('+meal.measure11.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if meal.ingredient12.rstrip():
			ingredient = xbmcgui.ListItem(meal.ingredient12)
			ingredient.setArt({ 'thumb': 'http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient12))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient12))+'.png')
			if meal.measure12.rstrip(): ingredient.setProperty('measure','('+meal.measure12.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
		
		
		self.getControl(INGREDIENT_PANEL_CONTROL).addItems(ingredient_list)
		if meal.ingredient13.rstrip(): self.pages = 3
		return
		
	def set_third_ingredients(self,meal):
		self.position = 2
		
		if meal.ingredient13.rstrip():
			ingredient = xbmcgui.ListItem(meal.ingredient13)
			ingredient.setArt({ 'thumb': 'http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient13))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient13))+'.png')
			if meal.measure13.rstrip(): ingredient.setProperty('measure','('+meal.measure13.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if meal.ingredient14.rstrip():
			ingredient = xbmcgui.ListItem(meal.ingredient14)
			ingredient.setArt({ 'thumb': 'http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient14))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient14))+'.png')
			if meal.measure14.rstrip(): ingredient.setProperty('measure','('+meal.measure14.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
			
		if meal.ingredient15.rstrip():
			ingredient = xbmcgui.ListItem(meal.ingredient15)
			ingredient.setArt({ 'thumb': 'http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient15))+'.png' })
			ingredient.setProperty('ingredient_thumb','http://www.themealdb.com/images/ingredients/'+urllib.quote(removeNonAscii(meal.ingredient15))+'.png')
			if meal.measure15.rstrip(): ingredient.setProperty('measure','('+meal.measure15.rstrip()+')')
			else: ingredient.setProperty('measure','')
			ingredient_list.append(ingredient)
		return
	
	def set_ingredient_description(self,ingredient_name,ingredient_thumb,ingredient_description):
		ingredient_details.start(ingredient_name,ingredient_thumb,ingredient_description)
		return
		
	def clear_all(self):
		self.getControl(recipelabel).setLabel('')
		self.getControl(recipethumb).setImage('')
		self.getControl(reciperecipe).setText('')
		self.getControl(recipesublabel).setText('')
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
				self.set_second_ingredients(self.meal_obj)
			elif self.position == 1 and self.pages > 2:
				self.clear_ingredients()
				self.set_third_ingredients(self.meal_obj)
			else:
				if self.screensaver_mode:
					self.current_time = 0
					self.set_random()
		
		elif action.getId() == ACTION_LEFT and not xbmc.getCondVisibility("Control.HasFocus("+str(INGREDIENT_PANEL_CONTROL)+")"):
			if self.position == 2 and self.pages <= 3:
				self.clear_ingredients()
				self.set_second_ingredients(self.meal_obj)
			elif self.position == 1 and self.pages <= 2:
				self.clear_ingredients()
				self.set_first_ingredients(self.meal_obj)
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
					meals_list = mealsdb_api.Search().meal(search_parameter)
					if not meals_list: xbmcgui.Dialog().ok(translate(32000),translate(32011))
					else:
						meals_name = []
						for meal in meals_list:
							meals_name.append(meal.name)
						if len(meals_name) == 1:
							self.set_meal(meals_list[0])
						else:
							choose = xbmcgui.Dialog().select(translate(32000),meals_name)
							if choose > -1:
								self.set_meal(meals_list[choose])
							
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

	#note pass id of the meal to open a given meal
	
	screensaver = Screensaver(
		'script-themealdb-Mealplayer.xml',
		addon_path,
		'default',
		'',
	)
	screensaver.doModal()
	del screensaver
	sys.modules.clear()
