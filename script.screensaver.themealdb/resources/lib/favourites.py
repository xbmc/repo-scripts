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

import os
import xbmc
import themealdb
from common_meal import *

def add_to_favourite_recipes(recipe_name,recipe_id,recipe_image):
	content = recipe_name + '|' + str(recipe_id) + '|' + recipe_image
	filename = os.path.join(favourite_recipes_folder,str(recipe_id)+'.txt')
	save(filename,content)
	xbmc.executebuiltin("Notification(%s,%s,%i,%s)" % (translate(32000), translate(32022),1,os.path.join(addon_path,"icon.png")))
	return
	
def remove_from_favourites(recipe_id):
	filename = os.path.join(favourite_recipes_folder,str(recipe_id)+'.txt')
	if os.path.exists(filename):
		os.remove(filename)
		xbmc.executebuiltin("Notification(%s,%s,%i,%s)" % (translate(32000), translate(32023),1,os.path.join(addon_path,"icon.png")))
	else:
		xbmc.executebuiltin("Notification(%s,%s,%i,%s)" % (translate(32000), translate(32024),1,os.path.join(addon_path,"icon.png")))
	return

def has_favourites():
	recipes = os.listdir(favourite_recipes_folder)
	if recipes:
		return True
	else:
		xbmc.executebuiltin("Notification(%s,%s,%i,%s)" % (translate(32000), translate(32026),1,os.path.join(addon_path,"icon.png")))
		return False
		
def is_favourite(recipe_id):
	filename = os.path.join(favourite_recipes_folder,str(recipe_id) + '.txt')
	if os.path.exists(filename): return True
	else: return False	
	
def get_favourites():
	favourite_meals = []
	recipes = os.listdir(favourite_recipes_folder)
	if recipes:
		for recipe in recipes:
			recipe_file = os.path.join(favourite_recipes_folder,recipe)
			recipe_info = readfile(recipe_file).split('|')
			recipe_dict = { "idMeal" : recipe_info[1], "strMeal" : recipe_info[0], "strMealThumb": recipe_info[2] }
			favourite_meals.append(themealdb.meal_lite(recipe_dict ))
	return favourite_meals

def save(filename,contents):  
	fh = open(filename, 'w')
	fh.write(contents)  
	fh.close()

def readfile(filename):
	f = open(filename, "r")
	string = f.read()
	return string
