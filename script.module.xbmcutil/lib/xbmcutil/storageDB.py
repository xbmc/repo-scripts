"""
	###################### xbmcutil.storageDB ######################
	Copyright: (c) 2013 William Forde (willforde+xbmc@gmail.com)
	License: GPLv3, see LICENSE for more details
	
	This file is part of xbmcutil
	
	xbmcutil is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.
	
	xbmcutil is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.
	
	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
# Call Imports
import os

class _BaseStorage(object):
	def __init__(self, filename, *args, **kwargs):
		# Update Internal Dict with Arguments
		if args or kwargs: self._update(*args, **kwargs)
		
		# Load and set serializer object
		self._filename = filename
		self._serializerObj = __import__("fastjson")
		
		# Load Store Dict from Disk if Available
		if os.path.exists(filename):
			self._fileObj = open(filename, "rb+")
			self._load()
		else:
			self._fileObj = None
	
	def sync(self):
		# Dumb Dict out to Disk
		self._dump()
	
	def close(self):
		# Dumb dist out to Disk and Close Connection to File Object
		if self._fileObj: self._fileObj.close()
	
	def _dump(self):
		# Check if FileObj Needs Creating First
		if self._fileObj:
			self._fileObj.seek(0)
			self._fileObj.truncate(0)
		else:
			self._fileObj = open(self._filename, "wb+")
		
		# Dumb Data to Disk
		self._serializerObj.dump(self._serialize(), self._fileObj, indent=4, separators=(",", ":"))
		
		# Flush Data out to Disk
		self._fileObj.flush()
	
	def _load(self):
		# Load Data from Disk
		self._fileObj.seek(0)
		self._update(self._serializerObj.load(self._fileObj))
	
	# Methods to add support for with statement
	def __enter__(self): return self
	def __exit__(self, *exc_info): self.close()

class dictStorage(_BaseStorage, dict):
	def _serialize(self):
		return self.copy()
	
	def _update(self, *args, **kwargs):
		self.update(*args, **kwargs)

class listStorage(_BaseStorage, list):
	def _serialize(self):
		return list(self)
	
	def _update(self, *args, **kwargs):
		self.extend(*args, **kwargs)

class setStorage(_BaseStorage, set):
	def _serialize(self):
		return list(self)
	
	def _update(self, *args, **kwargs):
		self.update(*args, **kwargs)

class Metadata(dictStorage):
	def __init__(self):
		# Check if UserData Exists
		from xbmcutil import plugin
		systemMetaData = os.path.join(plugin.getLocalPath(), u"resources", u"metadata.json")
		userMetaData = os.path.join(plugin.getProfile(), u"metadata.json")
		if os.path.isfile(systemMetaData) and not os.path.isfile(userMetaData):
			import shutil
			shutil.move(systemMetaData, userMetaData)
			super(Metadata, self).__init__(userMetaData)
		else:
			super(Metadata, self).__init__(userMetaData)

class SavedSearch(setStorage):
	def __init__(self):
		# Create and set saved searches data path
		from xbmcutil import plugin
		savedSearches = os.path.join(plugin.getProfile(), u"savedsearches.json")
		super(SavedSearch, self).__init__(savedSearches)

from xbmcutil import listitem, plugin
class SavedSearches(listitem.VirtualFS):
	@plugin.error_handler
	def scraper(self):
		# Fetch list of current saved searches
		self.searches = SavedSearch()
				
		# Call Search Dialog if Required
		if "remove" in plugin and plugin["remove"] in self.searches:
			self.searches.remove(plugin.pop("remove"))
			self.searches.sync()
		elif "search" in plugin:
			self.search_dialog(plugin["url"])
			del plugin["search"]
		elif not self.searches:
			self.search_dialog(plugin["url"])
		
		# Add Extra Items
		params = plugin._Params.copy()
		params["search"] = "true"
		params["updatelisting"] = "true"
		params["cachetodisc"] = "true"
		self.add_item(label=u"-%s" % plugin.getuni(137), url=params, isPlayable=False) # 137 = Search
		
		# Set Content Properties
		self.set_sort_methods(self.sort_method_video_title)
		self.set_content("files")
		
		# Display list of searches if any
		try:
			if self.searches: return self.list_searches()
			else: return True
		finally:
			self.searches.close()
	
	def search_dialog(self, urlString):
		# Add searchTerm to database
		self.searches.add(plugin.dialogSearch())
		self.searches.sync()
	
	def list_searches(self):
		# Create Speed vars
		results = []
		additem = results.append
		localListitem = listitem.ListItem
		
		# Fetch Forwarding url string & action
		baseUrl = plugin["url"]
		baseAction = plugin["forwarding"]
		
		# Create Context Menu item Params
		strRemove = plugin.getuni(1210) # 1210 = Remove
		params = plugin._Params.copy()
		params["updatelisting"] = "true"
		
		# Loop earch Search item
		for searchTerm in self.searches:
			# Create listitem of Data
			item = localListitem()
			item.setLabel(searchTerm.title())
			item.setParamDict(action=baseAction, url=baseUrl % searchTerm)
			
			# Creatre Context Menu item to remove search item
			params["remove"] = searchTerm
			item.addContextMenuItem(strRemove, "XBMC.Container.Update", **params)
			
			# Store Listitem data
			additem(item.getListitemTuple(isPlayable=False))
		
		# Return list of listitems
		return results