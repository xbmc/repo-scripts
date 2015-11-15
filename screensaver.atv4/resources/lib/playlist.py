# -*- coding: utf-8 -*-
'''
    screensaver.atv4
    Copyright (C) 2015 enen92

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
import urllib2
import xbmc
import xbmcaddon
import xbmcgui
import os

addon = xbmcaddon.Addon(id='screensaver.atv4')
addon_path = addon.getAddonInfo('path')



class AtvPlaylist:

	def __init__(self,):
		url = 'http://a1.phobos.apple.com/us/r1000/000/Features/atv/AutumnResources/videos/entries.json'
		try:
			response = urllib2.urlopen(url)
			self.html = json.loads(response.read())
		except: self.html = {}

	def getPlaylist(self,):
		self.playlist = xbmc.PlayList(1)
		if self.html:
			for i in range(1,11):
				for j in range(1,5):
					for block in self.html:
							for video in block['assets']:
								try:
									if video["id"] == 'b'+str(i)+'-'+str(j) and addon.getSetting('b'+str(i)+'-'+str(j)) == 'true':
										label = video['accessibilityLabel'] + ' by ' + str(video['timeOfDay'])
										item = xbmcgui.ListItem(label)
										item.setLabel(label)
										item.setInfo('video', {'Title': label })
										item.setArt({'thumb': os.path.join(addon_path,'icon.png')})
										url = video['url']
										item.setPath(url)
										self.playlist.add(url,item)
								except: pass
			return self.playlist
		else:
			return None
