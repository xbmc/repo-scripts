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

import json
import urllib
import urllib2

API_BASE_URL = 'http://www.thecocktaildb.com/api/json/v1'
API_INGREDIENT_URL = 'http://www.thecocktaildb.com/images/ingredients/'


class Api:
	
	def __init__(self,API_KEY=None):
		global APIKEY
		APIKEY = API_KEY
		if APIKEY != None and type(APIKEY) == str:
			print "Module initiated with API key " + str(API_KEY)
		else:
			print "API Key not valid or with the wrong type"
	
		
	class Search:
	
		def cocktail(self,name=None):
			if name == None:
				print "Error: cocktail name not provided"
				return None
			else:				
				url = '%s/%s/search.php?s=%s' % (API_BASE_URL,APIKEY,str(name))
				print url
				data = json.load(urllib2.urlopen(url))["drinks"]
				if not data:
					print "No cocktails found"
					return None
				else:
					cocktails = []
					for dict_ in data:
						cocktails.append(Cocktail(dict_))
					return cocktails
				
	class List:
		
		def alcoholic(self):
			return_list = []
			url = '%s/%s/list.php?a=list' % (API_BASE_URL,APIKEY)
			data = json.load(urllib2.urlopen(url))["drinks"]
			if data:
				for item in data:
					if item["strAlcoholic"]: return_list.append(item["strAlcoholic"])
			return return_list
		
		def glass(self):
			return_list = []
			url = '%s/%s/list.php?g=list' % (API_BASE_URL,APIKEY)
			data = json.load(urllib2.urlopen(url))["drinks"]
			if data:
				for item in data:
					if item["strGlass"]: return_list.append(item["strGlass"])
			return return_list
			
		def category(self):
			return_list = []
			url = '%s/%s/list.php?c=list' % (API_BASE_URL,APIKEY)
			data = json.load(urllib2.urlopen(url))["drinks"]
			if data:
				for item in data:
					if item["strCategory"]: return_list.append(item["strCategory"])
			return return_list
			
		def ingredient(self):
			return_list = []
			url = '%s/%s/list.php?i=list' % (API_BASE_URL,APIKEY)
			data = json.load(urllib2.urlopen(url))["drinks"]
			if data:
				for item in data:
					if item["strIngredient1"]: return_list.append(item["strIngredient1"])
			return return_list
			
	class Filter:
		
		def glass(self,glass):
			cocktails = []
			url = '%s/%s/filter.php?g=%s' % (API_BASE_URL,APIKEY,glass.replace(' ','_'))
			data = json.load(urllib2.urlopen(url))["drinks"]
			if data:
				for dict_ in data:
					cocktails.append(Cocktail_lite(dict_))
			return cocktails
			
		def category(self,category):
			cocktails = []
			url = '%s/%s/filter.php?c=%s' % (API_BASE_URL,APIKEY,category.replace(' ','_'))
			data = json.load(urllib2.urlopen(url))["drinks"]
			if data:
				for dict_ in data:
					cocktails.append(Cocktail_lite(dict_))
			return cocktails
			
		def alcohol(self,alcool):
			cocktails = []
			url = '%s/%s/filter.php?a=%s' % (API_BASE_URL,APIKEY,alcool.replace(' ','_'))
			data = json.load(urllib2.urlopen(url))["drinks"]
			if data:
				for dict_ in data:
					cocktails.append(Cocktail_lite(dict_))
			return cocktails
			
		def ingredient(self,ingredient):
			cocktails = []
			url = '%s/%s/filter.php?i=%s' % (API_BASE_URL,APIKEY,ingredient.replace(' ','_'))
			data = json.load(urllib2.urlopen(url))["drinks"]
			if data:
				for dict_ in data:
					cocktails.append(Cocktail_lite(dict_))
			return cocktails
			
	class Lookup:
		
		def cocktail(self,cocktail_id):
			cocktails = []
			url = '%s/%s/lookup.php?i=%s' % (API_BASE_URL,APIKEY,str(cocktail_id))
			data = json.load(urllib2.urlopen(url))["drinks"]
			if data:
				for dict_ in data:
					cocktails.append(Cocktail(dict_))
			return cocktails
			
		def random(self):
			cocktails = []
			url = '%s/%s/random.php' % (API_BASE_URL,APIKEY)
			data = json.load(urllib2.urlopen(url))["drinks"]
			if data:
				for dict_ in data:
					cocktails.append(Cocktail(dict_))
				return cocktails
			
					
			
					
class Cocktail:

	def __init__(self,cocktail_dict):
		self.id = cocktail_dict["idDrink"]
		self.name = cocktail_dict["strDrink"]
		self.category = cocktail_dict["strCategory"]
		self.alcoholic = cocktail_dict["strAlcoholic"]
		self.glass = cocktail_dict["strGlass"]
		self.recipe = cocktail_dict["strInstructions"]
		self.thumb = cocktail_dict["strDrinkThumb"]
		self.ingredient1 = cocktail_dict["strIngredient1"]
		self.ingredient2 = cocktail_dict["strIngredient2"]
		self.ingredient3 = cocktail_dict["strIngredient3"]
		self.ingredient4 = cocktail_dict["strIngredient4"]
		self.ingredient5 = cocktail_dict["strIngredient5"]
		self.ingredient6 = cocktail_dict["strIngredient6"]
		self.ingredient7 = cocktail_dict["strIngredient7"]
		self.ingredient8 = cocktail_dict["strIngredient8"]
		self.ingredient9 = cocktail_dict["strIngredient9"]
		self.ingredient10 = cocktail_dict["strIngredient10"]
		self.ingredient11 = cocktail_dict["strIngredient11"]
		self.ingredient12 = cocktail_dict["strIngredient12"]
		self.ingredient13 = cocktail_dict["strIngredient13"]
		self.ingredient14 = cocktail_dict["strIngredient14"]
		self.ingredient15 = cocktail_dict["strIngredient15"]
		self.measure1 = cocktail_dict["strMeasure1"]
		self.measure2 = cocktail_dict["strMeasure2"]
		self.measure3 = cocktail_dict["strMeasure3"]
		self.measure4 = cocktail_dict["strMeasure4"]
		self.measure5 = cocktail_dict["strMeasure5"]
		self.measure6 = cocktail_dict["strMeasure6"]
		self.measure7 = cocktail_dict["strMeasure7"]
		self.measure8 = cocktail_dict["strMeasure8"]
		self.measure9 = cocktail_dict["strMeasure9"]
		self.measure10 = cocktail_dict["strMeasure10"]
		self.measure11 = cocktail_dict["strMeasure11"]
		self.measure12 = cocktail_dict["strMeasure12"]
		self.measure13 = cocktail_dict["strMeasure13"]
		self.measure14 = cocktail_dict["strMeasure14"]
		self.measure15 = cocktail_dict["strMeasure15"]
		
class Cocktail_lite:

	def __init__(self,cocktail_dict):
		self.id = cocktail_dict["idDrink"]
		self.name = cocktail_dict["strDrink"]
		self.thumb = cocktail_dict["strDrinkThumb"]
		
		
		
		
		
		
		
		
