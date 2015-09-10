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

import os
import xbmc
import thecocktaildb
from common_cocktail import *

def add_to_favourite_drinks(drink_name,drink_id,drink_image):
	content = drink_name + '|' + str(drink_id) + '|' + drink_image
	filename = os.path.join(favourite_drinks_folder,str(drink_id)+'.txt')
	save(filename,content)
	xbmc.executebuiltin("Notification(%s,%s,%i,%s)" % (translate(32000), translate(32022),1,os.path.join(addon_path,"icon.png")))
	return
	
def remove_from_favourites(drink_id):
	filename = os.path.join(favourite_drinks_folder,str(drink_id)+'.txt')
	if os.path.exists(filename):
		os.remove(filename)
		xbmc.executebuiltin("Notification(%s,%s,%i,%s)" % (translate(32000), translate(32023),1,os.path.join(addon_path,"icon.png")))
	else:
		xbmc.executebuiltin("Notification(%s,%s,%i,%s)" % (translate(32000), translate(32024),1,os.path.join(addon_path,"icon.png")))
	return

def has_favourites():
	drinks = os.listdir(favourite_drinks_folder)
	if drinks:
		return True
	else:
		xbmc.executebuiltin("Notification(%s,%s,%i,%s)" % (translate(32000), translate(32026),1,os.path.join(addon_path,"icon.png")))
		return False
		
def is_favourite(drink_id):
	filename = os.path.join(favourite_drinks_folder,str(drink_id) + '.txt')
	if os.path.exists(filename): return True
	else: return False	
	
def get_favourites():
	favourite_cocktails = []
	drinks = os.listdir(favourite_drinks_folder)
	if drinks:
		for drink in drinks:
			drink_file = os.path.join(favourite_drinks_folder,drink)
			drink_info = readfile(drink_file).split('|')
			drink_dict = { "idDrink" : drink_info[1], "strDrink" : drink_info[0], "strDrinkThumb": drink_info[2] }
			favourite_cocktails.append(thecocktaildb.Cocktail_lite(drink_dict ))
	return favourite_cocktails

def save(filename,contents):  
	fh = open(filename, 'w')
	fh.write(contents)  
	fh.close()
     
def readfile(filename):
	f = open(filename, "r")
	string = f.read()
	return string
