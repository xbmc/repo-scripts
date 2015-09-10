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
import cocktail as cocktailscreensaver
from resources.lib import thecocktaildb
from resources.lib import ingredient_details
from resources.lib import youtube
from resources.lib import favourites
from resources.lib.common_cocktail import *

contextmenu_labels_drink_original = [translate(32001),translate(32002)]
contextmenu_options_drink_original = ['recipe','youtube']

INGREDIENT_DRINK_PANEL_CONTROL = 32501
REGULAR_PANEL_CONTROL = 32500


class Main(xbmcgui.WindowXML):
	def __init__( self, *args, **kwargs ):
		self.status = None
		self.ingredient = None
		self.category = None
		self.glass = None
		self.alcohol = None
	
	def onInit(self):
		if self.status == None:
			self.last_focused_mainmenu_item = 0
			self.last_focused_glass_item = 0
			self.last_focused_category_item = 0
			self.last_focused_alchool_item = 0
			self.main_menu()
		
	def main_menu(self):
		self.status = 'main_menu'
		self.last_focused_drink = 0
		self.last_focused_ingredient = 0
		items = []
		menu_items = [(translate(32003),'categories',os.path.join(addon_path,"resources","skins","default","media","menuicons","categories.png")),(translate(32004),'glass',os.path.join(addon_path,"resources","skins","default","media","menuicons","glass.png")),(translate(32005),'alcohol',os.path.join(addon_path,"resources","skins","default","media","menuicons","alcohol.png")),(translate(32006),'ingredient',os.path.join(addon_path,"resources","skins","default","media","menuicons","ingredient.png")),(translate(32007),'search',os.path.join(addon_path,"resources","skins","default","media","menuicons","search.png")),(translate(32025),'favourites',os.path.join(addon_path,"resources","skins","default","media","menuicons","favourites.png")),(translate(32008),'screensaver',os.path.join(addon_path,"resources","skins","default","media","menuicons","screensaver.png"))]
		for label,identifier,icon in menu_items:
			item = xbmcgui.ListItem(label)
			item.setArt({ 'thumb': icon })
			item.setProperty('category',identifier)
			items.append(item)
		self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).addItems(items)
		self.setFocusId(REGULAR_PANEL_CONTROL)
		self.getControl(REGULAR_PANEL_CONTROL).selectItem(self.last_focused_mainmenu_item)
		return
		
	def alcoholic_type(self):
		self.status = 'alcoholic_selection'
		self.last_focused_drink = 0
		self.last_focused_ingredient = 0
		items = []
		xbmc.executebuiltin( "ActivateWindow(busydialog)" )
		categories = cocktailsdb_api.List().alcoholic()
		xbmc.executebuiltin( "Dialog.Close(busydialog)" )
		for label in categories:
			item = xbmcgui.ListItem(label)
			item.setArt({ 'thumb': os.path.join(addon_path,"resources","skins","default","media","menuicons",urllib.quote(label).lower()+".png") })
			item.setProperty('category','alcoholic_selection')
			items.append(item)
		self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).addItems(items)
		self.setFocusId(REGULAR_PANEL_CONTROL)
		self.getControl(REGULAR_PANEL_CONTROL).selectItem(self.last_focused_alchool_item)
		return
		
	def glass_type(self):
		self.status = 'glass_selection'
		self.last_focused_drink = 0
		self.last_focused_ingredient = 0
		items = []
		xbmc.executebuiltin( "ActivateWindow(busydialog)" )
		categories = cocktailsdb_api.List().glass()
		xbmc.executebuiltin( "Dialog.Close(busydialog)" )
		for label in categories:
			item = xbmcgui.ListItem(label)
			item.setArt({ 'thumb': os.path.join(addon_path,"resources","skins","default","media","glasses",urllib.quote(label).lower().replace('/','-')+".png") })
			item.setProperty('category','glass_selection')
			items.append(item)
		self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).addItems(items)
		self.setFocusId(REGULAR_PANEL_CONTROL)
		self.getControl(REGULAR_PANEL_CONTROL).selectItem(self.last_focused_glass_item)
		return
		
	def categories(self):
		self.status = 'category_selection'
		self.last_focused_drink = 0
		self.last_focused_ingredient = 0
		items = []
		xbmc.executebuiltin( "ActivateWindow(busydialog)" )
		categories = cocktailsdb_api.List().category()
		xbmc.executebuiltin( "Dialog.Close(busydialog)" )
		for label in categories:
			item = xbmcgui.ListItem(label)
			item.setArt({ 'thumb': os.path.join(addon_path,"resources","skins","default","media","category",urllib.quote(label).lower().replace('/','-')+".png") })
			item.setProperty('category','category_selection')
			items.append(item)
		self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).addItems(items)
		self.setFocusId(REGULAR_PANEL_CONTROL)
		self.getControl(REGULAR_PANEL_CONTROL).selectItem(self.last_focused_category_item)
		return
		
	def ingredient_picker(self):
		self.status = 'ingredient_selection'
		self.last_focused_drink = 0
		items = []
		xbmc.executebuiltin( "ActivateWindow(busydialog)" )
		categories = cocktailsdb_api.List().ingredient()
		for label in categories:
			item = xbmcgui.ListItem(label)
			item.setArt({ 'thumb': thecocktaildb.API_INGREDIENT_URL + urllib.quote(removeNonAscii(label)) +'.png' })
			item.setProperty('category','ingredient_picker')
			item.setProperty('ingredient_thumb',thecocktaildb.API_INGREDIENT_URL + urllib.quote(removeNonAscii(label)) +'.png' )
			item.setProperty('id','None')
			items.append(item)
		self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).reset()
		self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).addItems(items)
		xbmc.executebuiltin( "Dialog.Close(busydialog)" )
		self.setFocusId(INGREDIENT_DRINK_PANEL_CONTROL)
		self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).selectItem(self.last_focused_ingredient)
		return
		
	def search(self):
		keyb = xbmc.Keyboard('', translate(32009))
		keyb.doModal()
		if (keyb.isConfirmed()):
			search_parameter = urllib.quote_plus(keyb.getText())
			if not search_parameter: xbmcgui.Dialog().ok(translate(32000),translate(32010))
			else:
				xbmc.executebuiltin( "ActivateWindow(busydialog)" )
				cocktails_list = cocktailsdb_api.Search().cocktail(search_parameter)
				xbmc.executebuiltin( "Dialog.Close(busydialog)" )
				if not cocktails_list: xbmcgui.Dialog().ok(translate(32000),translate(32011))
				else:
					self.list_cocktails(cocktails_list)
					
	def reset_variables(self):
		self.ingredient = None
		self.category = None
		self.glass = None
		self.alcohol = None
		return
		
	def list_favourites(self):
		has_favourites = favourites.has_favourites()
		if has_favourites:
			favourite_cocktails = favourites.get_favourites()
			self.list_cocktails(favourite_cocktails)
		return
		
	def list_cocktails(self,cocktails_list):
		self.status = 'cocktail_listing'
		if not cocktails_list:
			xbmcgui.Dialog().ok(translate(32000),translate(32012))
		else:
			items = []
			for cocktail in cocktails_list:
				item = xbmcgui.ListItem(cocktail.name)
				item.setArt({ 'thumb': cocktail.thumb })
				item.setProperty('drink_thumb',cocktail.thumb)
				item.setProperty('id',str(cocktail.id))
				item.setProperty('category','cocktail_listing')
				items.append(item)
			self.cocktail_items = items
			self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).reset()
			self.getControl(REGULAR_PANEL_CONTROL).reset()
			self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).addItems(items)
			self.setFocusId(INGREDIENT_DRINK_PANEL_CONTROL)
			self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).selectItem(0)
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
		self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).reset()
		self.getControl(REGULAR_PANEL_CONTROL).addItems(items)
		return
		
	def cocktail_player(self,cocktail_id):
		screensaver = cocktailscreensaver.Screensaver(
			'script-cocktail-Cocktailplayer.xml',
			addon_path,
			'default',
			cocktail_id,
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
				self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).reset()
				self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).addItems(self.cocktail_items)
				self.setFocusId(INGREDIENT_DRINK_PANEL_CONTROL)
				self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).selectItem(self.last_focused_drink)
				self.status = 'cocktail_listing'
			else:
				if self.category:
					self.reset_variables()
					self.categories()
				elif self.glass:
					self.reset_variables()
					self.glass_type()
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
			self.contextmenu_labels_drink = []
			for item in contextmenu_labels_drink_original:
				self.contextmenu_labels_drink.append(item)
			self.contextmenu_options_drink = []
			for item in contextmenu_options_drink_original:
				self.contextmenu_options_drink.append(item)
			
			
			if xbmc.getCondVisibility("Control.HasFocus("+str(INGREDIENT_DRINK_PANEL_CONTROL)+")"):
				control = self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).getSelectedItem()
				self.last_focused_drink = self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).getSelectedPosition()
				control_label = control.getLabel()
				control_thumb = control.getProperty('drink_thumb')
				control_drink_id = control.getProperty('id')
				if control.getProperty('id') != 'None':
				
					if favourites.is_favourite(control_drink_id):
						self.contextmenu_labels_drink.append(translate(32028))
						self.contextmenu_options_drink.append('removefavourite')
					else:
						self.contextmenu_labels_drink.append(translate(32027))
						self.contextmenu_options_drink.append('addfavourite')
						
					choose = xbmcgui.Dialog().select(translate(32000),self.contextmenu_labels_drink)
					if choose > - 1:
						if self.contextmenu_options_drink[choose] == 'youtube':
							video_list = youtube.return_youtubevideos(control_label + ' drink')
							if not video_list: xbmcgui.Dialog().ok(translate(32000),translate(32013))
							else:
								self.set_youtube_videos(video_list)
						elif self.contextmenu_options_drink[choose] == 'recipe':
							cocktail_id = self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).getSelectedItem().getProperty('id')
							self.cocktail_player(cocktail_id)
							return
						elif self.contextmenu_options_drink[choose] == 'addfavourite':
							favourites.add_to_favourite_drinks(control_label,control_drink_id,control_thumb)
							return
						elif self.contextmenu_options_drink[choose] == 'removefavourite':
							favourites.remove_from_favourites(control_drink_id)
							items = []
							size = self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).size()
							if size > 0:
								for i in xrange(0,size):
									items.append(self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).getListItem(i))
							if items:
								refresh = True
								for drink in items:
									if not favourites.is_favourite(drink.getProperty('id')):
										if drink.getProperty('id') != control_drink_id:
											refresh = False
											break
								if refresh:
									self.list_favourites()
				else:
					#If here...we are in ingredient picker
					ingredient_name = self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).getSelectedItem().getLabel()
					ingredient_thumb = self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).getSelectedItem().getProperty('ingredient_thumb')
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
				xbmc.executescript(os.path.join(addon_path,'cocktail.py'))
			elif identifier == 'search':
				self.last_focused_mainmenu_item = self.focused_item
				self.reset_variables()
				self.search()
			elif identifier == 'alcohol':
				self.last_focused_mainmenu_item = self.focused_item
				self.reset_variables()
				self.alcoholic_type()
			elif identifier == 'glass':
				self.last_focused_mainmenu_item = self.focused_item
				self.reset_variables()
				self.glass_type()
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
				self.glass = None
				self.alcohol = None
				xbmc.executebuiltin( "ActivateWindow(busydialog)" )
				cocktails = cocktailsdb_api.Filter().category(category)
				xbmc.executebuiltin( "Dialog.Close(busydialog)" )
				self.list_cocktails(cocktails)
			elif identifier == 'alcoholic_selection':
				tipo = self.getControl(controlId).getSelectedItem().getLabel()
				self.ingredient = None
				self.last_focused_alchool_item = self.focused_item
				self.category = None
				self.glass = None
				self.alcohol = tipo
				xbmc.executebuiltin( "ActivateWindow(busydialog)" )
				cocktails = cocktailsdb_api.Filter().alcohol(tipo)
				xbmc.executebuiltin( "Dialog.Close(busydialog)" )
				self.list_cocktails(cocktails)
			elif identifier == 'glass_selection':
				glass = self.getControl(controlId).getSelectedItem().getLabel()
				self.last_focused_glass_item = self.focused_item
				self.ingredient = None
				self.category = None
				self.glass = glass
				self.alcohol = None
				xbmc.executebuiltin( "ActivateWindow(busydialog)" )
				cocktails = cocktailsdb_api.Filter().glass(glass)
				xbmc.executebuiltin( "Dialog.Close(busydialog)" )
				self.list_cocktails(cocktails)
			elif identifier == 'video_listing':
				youtube_id = self.getControl(controlId).getSelectedItem().getProperty('video_id')
				player = xbmc.Player()
				player.play('plugin://plugin.video.youtube/play/?video_id='+youtube_id)
				while player.isPlaying():
					xbmc.sleep(200)
				xbmc.sleep(500)
				self.getControl(INGREDIENT_DRINK_PANEL_CONTROL).reset()
				self.getControl(REGULAR_PANEL_CONTROL).reset()
				self.getControl(REGULAR_PANEL_CONTROL).addItems(self.youtube_videos)
				self.setFocusId(REGULAR_PANEL_CONTROL)
				self.getControl(REGULAR_PANEL_CONTROL).selectItem(self.focused_item)
		
		if controlId == INGREDIENT_DRINK_PANEL_CONTROL:
			identifier = self.getControl(controlId).getSelectedItem().getProperty('category')
			if identifier == 'ingredient_picker':
				ingredient = self.getControl(controlId).getSelectedItem().getLabel()
				self.ingredient = ingredient
				self.last_focused_drink = 0
				self.last_focused_ingredient = self.getControl(controlId).getSelectedPosition()
				self.category = None
				self.glass = None
				self.alcohol = None
				xbmc.executebuiltin( "ActivateWindow(busydialog)" )
				cocktails = cocktailsdb_api.Filter().ingredient(ingredient)
				xbmc.executebuiltin( "Dialog.Close(busydialog)" )
				self.list_cocktails(cocktails)
			elif identifier == 'cocktail_listing':
				cocktail_id = self.getControl(controlId).getSelectedItem().getProperty('id')
				self.cocktail_player(cocktail_id)


if __name__ == '__main__':

	main = Main(
		'script-cocktail-Main.xml',
		addon_path,
		'default',
		'',
	)
	main.doModal()
	del main
	sys.modules.clear()
