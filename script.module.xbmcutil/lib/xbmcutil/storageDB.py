"""
	###################### xbmcutil.storageDB ######################
	Copyright: (c) 2013 William Forde (willforde+kodi@gmail.com)
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
	
	def close(self, sync=False):
		# Dumb dist out to Disk and Close Connection to File Object
		if sync is True: self._dump()
		if self._fileObj: self._fileObj.close()
	
	def getsize(self):
		# Return filesize of currently opened file
		return os.path.getsize(self._filename)
	
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
	def __init__(self, filename=u"metadata.json"):
		# Check if UserData Exists
		from xbmcutil import plugin
		systemMetaData = os.path.join(plugin.getLocalPath(), u"resources", filename)
		userMetaData = os.path.join(plugin.getProfile(), filename)
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

class SkinCodes(dictStorage):
	def __init__(self):
		from xbmcutil import plugin
		systemMetaData = os.path.join(plugin.getGlobalPath(), u"resources", u"data", u"skincodes.json")
		super(SkinCodes, self).__init__(systemMetaData)