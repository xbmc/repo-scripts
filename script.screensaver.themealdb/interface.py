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
import themealdb as mealscreensaver
from resources.lib import themealdb
from resources.lib import ingredient_details
from resources.lib import youtube
from resources.lib import favourites
from resources.lib.common_meal import *

contextmenu_labels_recipe_original = [translate(32001),translate(32002)]
contextmenu_options_recipe_original = ['recipe','youtube']

INGREDIENT_recipe_PANEL_CONTROL = 32501
REGULAR_PANEL_CONTROL = 32500
BACK_BACKGROUND_CONTROL = 32502
BACK_ICON_CONTROL = 32503


class Main(xbmcgui.WindowXML):
	def __init__( self, *args, **kwargs ):
		self.status = None
		self.ingredient = None
		self.category = None
		self.area = None
		self.alcohol = None
	
	def onInit(self):
		if self.status == None:
			self.last_focused_mainmenu_item = 0
			self.last_focused_area_item = 0
			self.last_focused_category_item = 0
			self.last_focused_alchool_item = 0
			self.main_menu()
		#Enable back button for touch devices
		if addon.getSetting('enable-back') == "false":
			self.getControl(BACK_BACKGROUND_CONTROL).setVisible(False)
			self.getControl(BACK_ICON_CONTROL).setVisible(False)
		
	def main_menu(self):
		self.status = 'main_menu'
		self.last_focused_recipe = 0
		self.last_focused_ingredient = 0
		items = []
		menu_items = [(translate(32003),'categories',os.path.join(addon_path,"resources","skins","default","media","menuicons","categories.png")),(translate(32004),'area',os.path.join(addon_path,"resources","skins","default","media","menuicons","area.png")),(translate(32006),'ingredient',os.path.join(addon_path,"resources","skins","default","media","menuicons","ingredient.png")),(translate(32007),'search',os.path.join(addon_path,"resources","skins","default","media","menuicons","search.png")),(translate(32025),'favourites',os.path.join(addon_path,"resources","skins","default","media","menuicons","favourites.png")),(translate(32008),'screensaver',os.path.join(addon_path,"resources","skins","default","media","menuicons","screensaver.png"))]
		for label,identifier,icon in menu_items:
			item = xbmcgui.ListItem(label)
			item.setArt({ 'thumb': icon })
			item.setProperty('category',identifier)
			items.append(item)
		self.getControl(INGREDIENT_recipe_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).addItems(items)
		self.setFocusId(REGULAR_PANEL_CONTROL)
		self.getControl(REGULAR_PANEL_CONTROL).selectItem(self.last_focused_mainmenu_item)
		return
		
	def area_type(self):
		self.status = 'area_selection'
		self.last_focused_recipe = 0
		self.last_focused_ingredient = 0
		items = []
		xbmc.executebuiltin( "ActivateWindow(busydialog)" )
		categories = mealsdb_api.List().area()
		xbmc.executebuiltin( "Dialog.Close(busydialog)" )
		for label in categories:
			item = xbmcgui.ListItem(label)
			item.setArt({ 'thumb': os.path.join(addon_path,"resources","skins","default","media","area",urllib.quote(label).lower().replace('/','-')+".png") })
			item.setProperty('category','area_selection')
			items.append(item)
		self.getControl(INGREDIENT_recipe_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).addItems(items)
		self.setFocusId(REGULAR_PANEL_CONTROL)
		self.getControl(REGULAR_PANEL_CONTROL).selectItem(self.last_focused_area_item)
		return
		
	def categories(self):
		self.status = 'category_selection'
		self.last_focused_recipe = 0
		self.last_focused_ingredient = 0
		items = []
		xbmc.executebuiltin( "ActivateWindow(busydialog)" )
		categories = mealsdb_api.List().category()
		xbmc.executebuiltin( "Dialog.Close(busydialog)" )
		for label in categories:
			item = xbmcgui.ListItem(label)
			item.setArt({ 'thumb': os.path.join(addon_path,"resources","skins","default","media","category",urllib.quote(label).lower().replace('/','-')+".png") })
			item.setProperty('category','category_selection')
			items.append(item)
		self.getControl(INGREDIENT_recipe_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).addItems(items)
		self.setFocusId(REGULAR_PANEL_CONTROL)
		self.getControl(REGULAR_PANEL_CONTROL).selectItem(self.last_focused_category_item)
		return
		
	def ingredient_picker(self):
		self.status = 'ingredient_selection'
		self.last_focused_recipe = 0
		items = []
		xbmc.executebuiltin( "ActivateWindow(busydialog)" )
		categories = mealsdb_api.List().ingredient()
		for label in categories:
			item = xbmcgui.ListItem(label)
			item.setArt({ 'thumb': themealdb.API_INGREDIENT_URL + urllib.quote(removeNonAscii(label)) +'.png' })
			item.setProperty('category','ingredient_picker')
			item.setProperty('ingredient_thumb',themealdb.API_INGREDIENT_URL + urllib.quote(removeNonAscii(label)) +'.png' )
			item.setProperty('id','None')
			items.append(item)
		self.getControl(INGREDIENT_recipe_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).reset()
		self.getControl(INGREDIENT_recipe_PANEL_CONTROL).addItems(items)
		xbmc.executebuiltin( "Dialog.Close(busydialog)" )
		self.setFocusId(INGREDIENT_recipe_PANEL_CONTROL)
		self.getControl(INGREDIENT_recipe_PANEL_CONTROL).selectItem(self.last_focused_ingredient)
		return
		
	def search(self):
		keyb = xbmc.Keyboard('', translate(32009))
		keyb.doModal()
		if (keyb.isConfirmed()):
			search_parameter = urllib.quote_plus(keyb.getText())
			if not search_parameter: xbmcgui.Dialog().ok(translate(32000),translate(32010))
			else:
				xbmc.executebuiltin( "ActivateWindow(busydialog)" )
				meals_list = mealsdb_api.Search().meal(search_parameter)
				xbmc.executebuiltin( "Dialog.Close(busydialog)" )
				if not meals_list: xbmcgui.Dialog().ok(translate(32000),translate(32011))
				else:
					self.list_meals(meals_list)
					
	def reset_variables(self):
		self.ingredient = None
		self.category = None
		self.area = None
		self.alcohol = None
		return
		
	def list_favourites(self):
		has_favourites = favourites.has_favourites()
		if has_favourites:
			favourite_meals = favourites.get_favourites()
			self.list_meals(favourite_meals)
		return
		
	def list_meals(self,meals_list):
		self.status = 'meal_listing'
		if not meals_list:
			xbmcgui.Dialog().ok(translate(32000),translate(32012))
		else:
			items = []
			for meal in meals_list:
				item = xbmcgui.ListItem(meal.name)
				item.setArt({ 'thumb': meal.thumb })
				item.setProperty('recipe_thumb',meal.thumb)
				item.setProperty('id',str(meal.id))
				item.setProperty('category','meal_listing')
				items.append(item)
			self.meal_items = items
			self.getControl(INGREDIENT_recipe_PANEL_CONTROL).reset()
			self.getControl(REGULAR_PANEL_CONTROL).reset()
			self.getControl(INGREDIENT_recipe_PANEL_CONTROL).addItems(items)
			self.setFocusId(INGREDIENT_recipe_PANEL_CONTROL)
			self.getControl(INGREDIENT_recipe_PANEL_CONTROL).selectItem(0)
			return
			
	def set_youtube_videos(self,video_list):
		items = []
		self.status = 'video_listing'
		for label,thumb,video_id in video_list:
			item = xbmcgui.ListItem(label)
			item.setArt({ 'thumb': thumb })
			item.setProperty('video_id',video_id)
			item.setProperty('category','video_listing')
			items.append(item)
		self.youtube_videos = items
		self.getControl(INGREDIENT_recipe_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).addItems(items)
		return
		
	def meal_player(self,meal_id):
		screensaver = mealscreensaver.Screensaver(
			'script-themealdb-Mealplayer.xml',
			addon_path,
			'default',
			meal_id,
		)
		screensaver.doModal()
		del screensaver
		
	def set_ingredient_description(self,ingredient_name,ingredient_thumb,ingredient_description):
		ingredient_details.start(ingredient_name,ingredient_thumb,ingredient_description)
		return
			
	def onAction(self,action):
		if action.getId() == ACTION_RETURN or action.getId() == ACTION_ESCAPE:
			if self.status == 'main_menu': self.close()
			elif 'selection' in self.status: self.main_menu()
			elif self.status == 'video_listing':
				self.getControl(REGULAR_PANEL_CONTROL).reset()
				self.getControl(INGREDIENT_recipe_PANEL_CONTROL).reset()
				self.getControl(INGREDIENT_recipe_PANEL_CONTROL).addItems(self.meal_items)
				self.setFocusId(INGREDIENT_recipe_PANEL_CONTROL)
				self.getControl(INGREDIENT_recipe_PANEL_CONTROL).selectItem(self.last_focused_recipe)
				self.status = 'meal_listing'
			else:
				if self.category:
					self.reset_variables()
					self.categories()
				elif self.area:
					self.reset_variables()
					self.area_type()
				elif self.alcohol:
					self.reset_variables()
					self.alcoholic_type()
				elif self.ingredient:
					self.reset_variables()
					self.ingredient_picker()
				else:
					self.main_menu()
		
		elif action.getId() == ACTION_CONTEXT_MENU:

			#restart contextmenu			
			self.contextmenu_labels_recipe = []
			for item in contextmenu_labels_recipe_original:
				self.contextmenu_labels_recipe.append(item)
			self.contextmenu_options_recipe = []
			for item in contextmenu_options_recipe_original:
				self.contextmenu_options_recipe.append(item)
			
			
			if xbmc.getCondVisibility("Control.HasFocus("+str(INGREDIENT_recipe_PANEL_CONTROL)+")"):
				control = self.getControl(INGREDIENT_recipe_PANEL_CONTROL).getSelectedItem()
				self.last_focused_recipe = self.getControl(INGREDIENT_recipe_PANEL_CONTROL).getSelectedPosition()
				control_label = control.getLabel()
				control_thumb = control.getProperty('recipe_thumb')
				control_recipe_id = control.getProperty('id')
				if control.getProperty('id') != 'None':
				
					if favourites.is_favourite(control_recipe_id):
						self.contextmenu_labels_recipe.append(translate(32028))
						self.contextmenu_options_recipe.append('removefavourite')
					else:
						self.contextmenu_labels_recipe.append(translate(32027))
						self.contextmenu_options_recipe.append('addfavourite')
						
					choose = xbmcgui.Dialog().select(translate(32000),self.contextmenu_labels_recipe)
					if choose > - 1:
						if self.contextmenu_options_recipe[choose] == 'youtube':
							video_list = youtube.return_youtubevideos(control_label + ' recipe')
							if not video_list: xbmcgui.Dialog().ok(translate(32000),translate(32013))
							else:
								self.set_youtube_videos(video_list)
						elif self.contextmenu_options_recipe[choose] == 'recipe':
							meal_id = self.getControl(INGREDIENT_recipe_PANEL_CONTROL).getSelectedItem().getProperty('id')
							self.meal_player(meal_id)
							return
						elif self.contextmenu_options_recipe[choose] == 'addfavourite':
							favourites.add_to_favourite_recipes(control_label,control_recipe_id,control_thumb)
							return
						elif self.contextmenu_options_recipe[choose] == 'removefavourite':
							favourites.remove_from_favourites(control_recipe_id)
							items = []
							size = self.getControl(INGREDIENT_recipe_PANEL_CONTROL).size()
							if size > 0:
								for i in xrange(0,size):
									items.append(self.getControl(INGREDIENT_recipe_PANEL_CONTROL).getListItem(i))
							if items:
								refresh = True
								for recipe in items:
									if not favourites.is_favourite(recipe.getProperty('id')):
										if recipe.getProperty('id') != control_recipe_id:
											refresh = False
											break
								if refresh:
									self.list_favourites()
				else:
					#If here...we are in ingredient picker
					ingredient_name = self.getControl(INGREDIENT_recipe_PANEL_CONTROL).getSelectedItem().getLabel()
					ingredient_thumb = self.getControl(INGREDIENT_recipe_PANEL_CONTROL).getSelectedItem().getProperty('ingredient_thumb')
					#TODO get ingredient description when available
					ingredient_description = translate(32029)
					self.set_ingredient_description(ingredient_name,ingredient_thumb,ingredient_description)
				
			return
						 						
		
	def onClick(self,controlId):
		if controlId == REGULAR_PANEL_CONTROL:
			identifier = self.getControl(controlId).getSelectedItem().getProperty('category')
			self.focused_item = self.getControl(controlId).getSelectedPosition()
			if identifier == 'screensaver':
				self.reset_variables()
				xbmc.executescript(os.path.join(addon_path,'themealdb.py'))
			elif identifier == 'search':
				self.last_focused_mainmenu_item = self.focused_item
				self.reset_variables()
				self.search()
			elif identifier == 'alcohol':
				self.last_focused_mainmenu_item = self.focused_item
				self.reset_variables()
				self.alcoholic_type()
			elif identifier == 'area':
				self.last_focused_mainmenu_item = self.focused_item
				self.reset_variables()
				self.area_type()
			elif identifier == 'categories':
				self.last_focused_mainmenu_item = self.focused_item
				self.reset_variables()
				self.categories()
			elif identifier == 'ingredient':
				self.last_focused_mainmenu_item = self.focused_item
				self.reset_variables()
				self.ingredient_picker()
			elif identifier == 'favourites':
				self.last_focused_mainmenu_item = self.focused_item
				self.reset_variables()
				self.list_favourites()
			elif identifier == 'category_selection':
				category = self.getControl(controlId).getSelectedItem().getLabel()
				self.ingredient = None
				self.last_focused_category_item = self.focused_item
				self.category = category
				self.area = None
				self.alcohol = None
				xbmc.executebuiltin( "ActivateWindow(busydialog)" )
				meals = mealsdb_api.Filter().category(category)
				xbmc.executebuiltin( "Dialog.Close(busydialog)" )
				self.list_meals(meals)
			elif identifier == 'alcoholic_selection':
				tipo = self.getControl(controlId).getSelectedItem().getLabel()
				self.ingredient = None
				self.last_focused_alchool_item = self.focused_item
				self.category = None
				self.area = None
				self.alcohol = tipo
				xbmc.executebuiltin( "ActivateWindow(busydialog)" )
				meals = mealsdb_api.Filter().alcohol(tipo)
				xbmc.executebuiltin( "Dialog.Close(busydialog)" )
				self.list_meals(meals)
			elif identifier == 'area_selection':
				area = self.getControl(controlId).getSelectedItem().getLabel()
				self.last_focused_area_item = self.focused_item
				self.ingredient = None
				self.category = None
				self.area = area
				self.alcohol = None
				xbmc.executebuiltin( "ActivateWindow(busydialog)" )
				meals = mealsdb_api.Filter().area(area)
				xbmc.executebuiltin( "Dialog.Close(busydialog)" )
				self.list_meals(meals)
			elif identifier == 'video_listing':
				youtube_id = self.getControl(controlId).getSelectedItem().getProperty('video_id')
				player = xbmc.Player()
				player.play('plugin://plugin.video.youtube/play/?video_id='+youtube_id)
				while player.isPlaying():
					xbmc.sleep(200)
				xbmc.sleep(500)
				self.getControl(INGREDIENT_recipe_PANEL_CONTROL).reset()
				self.getControl(REGULAR_PANEL_CONTROL).reset()
				self.getControl(REGULAR_PANEL_CONTROL).addItems(self.youtube_videos)
				self.setFocusId(REGULAR_PANEL_CONTROL)
				self.getControl(REGULAR_PANEL_CONTROL).selectItem(self.focused_item)
		
		if controlId == INGREDIENT_recipe_PANEL_CONTROL:
			identifier = self.getControl(controlId).getSelectedItem().getProperty('category')
			if identifier == 'ingredient_picker':
				ingredient = self.getControl(controlId).getSelectedItem().getLabel()
				self.ingredient = ingredient
				self.last_focused_recipe = 0
				self.last_focused_ingredient = self.getControl(controlId).getSelectedPosition()
				self.category = None
				self.area = None
				self.alcohol = None
				xbmc.executebuiltin( "ActivateWindow(busydialog)" )
				meals = mealsdb_api.Filter().ingredient(ingredient)
				xbmc.executebuiltin( "Dialog.Close(busydialog)" )
				self.list_meals(meals)
			elif identifier == 'meal_listing':
				meal_id = self.getControl(controlId).getSelectedItem().getProperty('id')
				self.meal_player(meal_id)


if __name__ == '__main__':

	if len(sys.argv) <= 1:
		#Start interface
		main = Main(
			'script-meal-Main.xml',
			addon_path,
			'default',
			'',
		)
		main.doModal()
		del main
		sys.modules.clear()
	else:
		#Start screensaver
		xbmc.executescript(os.path.join(addon_path,'meal.py'))
