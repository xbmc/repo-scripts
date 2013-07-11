
#/*
# *      Copyright (C) 2010 lzoubek
# *
# *
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with this program; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
# */

import simplejson as json
import os,xbmc,time

class MPDCache:

	def __init__(self,addon,profile):
		self.addon = addon
		self.profile=profile

	def clear(self):
		local = xbmc.translatePath(self.addon.getAddonInfo('profile'))
		if not os.path.exists(local):
			os.makedirs(local)
		local = os.path.join(local,'cache.'+self.profile)
		os.remove(local)

	def _load(self):
		local = xbmc.translatePath(self.addon.getAddonInfo('profile'))
		if not os.path.exists(local):
			os.makedirs(local)
		local = os.path.join(local,'cache.'+self.profile)
		if not os.path.exists(local):
			return {}
		# keep cache for a week
		if (time.time() - os.path.getctime(local)) > (3600*24*7):
			return {}
		f = open(local,'r')
		data = f.read()
		cache = json.loads(unicode(data.decode('utf-8','ignore')))
		f.close()
		return cache

	def _save(self,cache):
		local = xbmc.translatePath(self.addon.getAddonInfo('profile'))
		if not os.path.exists(local):
			os.makedirs(local)
		local = os.path.join(local,'cache')
		f = open(local,'w')
		f.write(json.dumps(cache,ensure_ascii=True))
		f.close()

	def getArtists(self):
		cache = self._load()
		if 'artists' in cache.keys():
			return cache['artists']
		return []
	
	def putArtists(self,artists):
		cache = self._load()
		cache['artists'] = artists
		self._save(cache)
		
