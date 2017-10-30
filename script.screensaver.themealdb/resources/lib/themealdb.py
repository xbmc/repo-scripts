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

import json
import urllib
import urllib2

API_BASE_URL = 'http://www.themealdb.com/api/json/v1'
API_INGREDIENT_URL = 'http://www.themealdb.com/images/ingredients/'


class Api:
	
	def __init__(self,API_KEY=None):
		global APIKEY
		APIKEY = API_KEY
		if APIKEY != None and type(APIKEY) == str:
			print "Module initiated with API key " + str(API_KEY)
		else:
			print "API Key not valid or with the wrong type"
	
		
	class Search:
	
		def meal(self,name=None):
			if name == None:
				print "Error: meal name not provided"
				return None
			else:				
				url = '%s/%s/search.php?s=%s' % (API_BASE_URL,APIKEY,str(name))
				print url
				data = json.load(urllib2.urlopen(url))["meals"]
				if not data:
					print "No meals found"
					return None
				else:
					meals = []
					for dict_ in data:
						meals.append(meal(dict_))
					return meals

		def ingredient(self,name=None):
			if name == None:
				print "Error: ingredient not found"
				return None
			else:
				url = '%s/%s/search.php?i=%s' % (API_BASE_URL,APIKEY,urllib.quote_plus(str(name)))
				data = json.load(urllib2.urlopen(url))["ingredients"]
				if not data:
					print "No ingredients found"
					return None
				else:
					return data[0]["strDescription"]

	class List:
		
		def alcoholic(self):
			return_list = []
			url = '%s/%s/list.php?a=list' % (API_BASE_URL,APIKEY)
			data = json.load(urllib2.urlopen(url))["meals"]
			if data:
				for item in data:
					if item["strAlcoholic"]: return_list.append(item["strAlcoholic"])
			return return_list
		
		def glass(self):
			return_list = []
			url = '%s/%s/list.php?g=list' % (API_BASE_URL,APIKEY)
			data = json.load(urllib2.urlopen(url))["meals"]
			if data:
				for item in data:
					if item["strGlass"]: return_list.append(item["strGlass"])
			return return_list
			
		def area(self):
			return_list = []
			url = '%s/%s/list.php?a=list' % (API_BASE_URL,APIKEY)
			data = json.load(urllib2.urlopen(url))["meals"]
			if data:
				for item in data:
					if item["strArea"]: return_list.append(item["strArea"])
			return return_list
			
		def category(self):
			return_list = []
			url = '%s/%s/list.php?c=list' % (API_BASE_URL,APIKEY)
			data = json.load(urllib2.urlopen(url))["meals"]
			if data:
				for item in data:
					if item["strCategory"]: return_list.append(item["strCategory"])
			return return_list
			
		def ingredient(self):
			return_list = []
			url = '%s/%s/list.php?i=list' % (API_BASE_URL,APIKEY)
			data = json.load(urllib2.urlopen(url))["meals"]
			if data:
				for item in data:
					if item["strIngredient1"]: return_list.append(item["strIngredient1"])
			return return_list
			
	class Filter:
		
		def area(self,glass):
			meals = []
			url = '%s/%s/filter.php?a=%s' % (API_BASE_URL,APIKEY,glass.replace(' ','_'))
			data = json.load(urllib2.urlopen(url))["meals"]
			if data:
				for dict_ in data:
					meals.append(meal_lite(dict_))
			return meals
			
		def category(self,category):
			meals = []
			url = '%s/%s/filter.php?c=%s' % (API_BASE_URL,APIKEY,category.replace(' ','_'))
			data = json.load(urllib2.urlopen(url))["meals"]
			if data:
				for dict_ in data:
					meals.append(meal_lite(dict_))
			return meals
			
		def alcohol(self,alcool):
			meals = []
			url = '%s/%s/filter.php?a=%s' % (API_BASE_URL,APIKEY,alcool.replace(' ','_'))
			data = json.load(urllib2.urlopen(url))["meals"]
			if data:
				for dict_ in data:
					meals.append(meal_lite(dict_))
			return meals
			
		def ingredient(self,ingredient):
			meals = []
			url = '%s/%s/filter.php?i=%s' % (API_BASE_URL,APIKEY,ingredient.replace(' ','_'))
			data = json.load(urllib2.urlopen(url))["meals"]
			if data:
				for dict_ in data:
					meals.append(meal_lite(dict_))
			return meals
			
	class Lookup:
		
		def meal(self,meal_id):
			meals = []
			url = '%s/%s/lookup.php?i=%s' % (API_BASE_URL,APIKEY,str(meal_id))
			data = json.load(urllib2.urlopen(url))["meals"]
			if data:
				for dict_ in data:
					meals.append(meal(dict_))
			return meals
			
		def random(self):
			meals = []
			url = '%s/%s/random.php' % (API_BASE_URL,APIKEY)
			data = json.load(urllib2.urlopen(url))["meals"]
			if data:
				for dict_ in data:
					meals.append(meal(dict_))
				return meals
			
					
			
					
class meal:

	def __init__(self,meal_dict):
		self.id = meal_dict["idMeal"]
		self.name = meal_dict["strMeal"]
		self.category = meal_dict["strCategory"]
		self.recipe = meal_dict["strInstructions"]
		self.thumb = meal_dict["strMealThumb"]
		self.ingredient1 = meal_dict["strIngredient1"]
		self.ingredient2 = meal_dict["strIngredient2"]
		self.ingredient3 = meal_dict["strIngredient3"]
		self.ingredient4 = meal_dict["strIngredient4"]
		self.ingredient5 = meal_dict["strIngredient5"]
		self.ingredient6 = meal_dict["strIngredient6"]
		self.ingredient7 = meal_dict["strIngredient7"]
		self.ingredient8 = meal_dict["strIngredient8"]
		self.ingredient9 = meal_dict["strIngredient9"]
		self.ingredient10 = meal_dict["strIngredient10"]
		self.ingredient11 = meal_dict["strIngredient11"]
		self.ingredient12 = meal_dict["strIngredient12"]
		self.ingredient13 = meal_dict["strIngredient13"]
		self.ingredient14 = meal_dict["strIngredient14"]
		self.ingredient15 = meal_dict["strIngredient15"]
		self.ingredient16 = meal_dict["strIngredient16"]
		self.ingredient17 = meal_dict["strIngredient17"]
		self.ingredient18 = meal_dict["strIngredient18"]
		self.ingredient19 = meal_dict["strIngredient19"]
		self.ingredient20 = meal_dict["strIngredient20"]
		self.measure1 = meal_dict["strMeasure1"]
		self.measure2 = meal_dict["strMeasure2"]
		self.measure3 = meal_dict["strMeasure3"]
		self.measure4 = meal_dict["strMeasure4"]
		self.measure5 = meal_dict["strMeasure5"]
		self.measure6 = meal_dict["strMeasure6"]
		self.measure7 = meal_dict["strMeasure7"]
		self.measure8 = meal_dict["strMeasure8"]
		self.measure9 = meal_dict["strMeasure9"]
		self.measure10 = meal_dict["strMeasure10"]
		self.measure11 = meal_dict["strMeasure11"]
		self.measure12 = meal_dict["strMeasure12"]
		self.measure13 = meal_dict["strMeasure13"]
		self.measure14 = meal_dict["strMeasure14"]
		self.measure15 = meal_dict["strMeasure15"]
		self.measure16 = meal_dict["strMeasure16"]
		self.measure17 = meal_dict["strMeasure17"]
		self.measure18 = meal_dict["strMeasure18"]
		self.measure19 = meal_dict["strMeasure19"]
		self.measure20 = meal_dict["strMeasure20"]
		
class meal_lite:

	def __init__(self,meal_dict):
		self.id = meal_dict["idMeal"]
		self.name = meal_dict["strMeal"]
		self.thumb = meal_dict["strMealThumb"]
		
		
		
		
		
		
		
		
