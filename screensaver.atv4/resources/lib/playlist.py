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
from commonatv import *

class AtvPlaylist:

	def __init__(self,):
		if not xbmc.getCondVisibility("Player.HasMedia"):
			url = 'http://a1.phobos.apple.com/us/r1000/000/Features/atv/AutumnResources/videos/entries.json'
			try:
				response = urllib2.urlopen(url)
				self.html = json.loads(response.read())
			except: 
				f = open(os.path.join(addon_path,"resources","entries.json"),"r")
				self.html = json.loads(f.read())
				f.close()
		else: self.html = {}

	def getPlaylistJson(self,):
		return self.html

	def getPlaylist(self,):
		current_time = xbmc.getInfoLabel("System.Time")
		am_pm = xbmc.getInfoLabel("System.Time(xx)")
		current_hour = current_time.split(":")[0]
		if am_pm == "PM": 
			if int(current_hour) < 12: current_hour = int(current_hour) + 12
			else: current_hour = int(current_hour)
		else: current_hour = int(current_hour)
		day_night = ''
		if current_hour < 19:
			if current_hour > 7: day_night = 'day'
			else: day_night = 'night'
		if current_hour > 19:
			day_night = 'night'
	

		self.playlist = xbmc.PlayList(1)
		self.playlist.clear()
		if self.html:
			for block in self.html:
				for video in block['assets']:

					label = video['accessibilityLabel'] + ' by ' + str(video['timeOfDay'])
					item = xbmcgui.ListItem(label)
					item.setLabel(label)
					item.setInfo('video', {'Title': label })
					item.setArt({'thumb': os.path.join(addon_path,'icon.png')})
					url = video['url']
					item.setPath(url)

					#check if file exists on disk
					movie = url.split("/")[-1]
					localfile = os.path.join(addon.getSetting("download-folder"),movie)
					if os.path.exists(localfile):
						url = localfile

					if video['accessibilityLabel'].lower() == "hawaii" and addon.getSetting("enable-hawaii") == "true":
						if video['timeOfDay'] == 'day':
							if addon.getSetting("time-of-day") == '0' or addon.getSetting("time-of-day") == '1':
								self.playlist.add(url,item)
							if addon.getSetting("time-of-day") == '3':
								if day_night == 'day':
									self.playlist.add(url,item)
						if video['timeOfDay'] == 'night':
							if addon.getSetting("time-of-day") == '0' or addon.getSetting("time-of-day") == '2':
								self.playlist.add(url,item)
							if addon.getSetting("time-of-day") == '3':
								if day_night=='night':
									self.playlist.add(url,item)

					elif video['accessibilityLabel'].lower() == "london" and addon.getSetting("enable-london") == "true":
						if video['timeOfDay'] == 'day':
							if addon.getSetting("time-of-day") == '0' or addon.getSetting("time-of-day") == '1':
								self.playlist.add(url,item)
							if addon.getSetting("time-of-day") == '3':
								if day_night=='day':
									self.playlist.add(url,item)
						if video['timeOfDay'] == 'night':
							if addon.getSetting("time-of-day") == '0' or addon.getSetting("time-of-day") == '2':
								self.playlist.add(url,item)
							if addon.getSetting("time-of-day") == '3':
								if day_night=='night':
									self.playlist.add(url,item)

					elif video['accessibilityLabel'].lower() == "new york city" and addon.getSetting("enable-nyork") == "true":
						if video['timeOfDay'] == 'day':
							if addon.getSetting("time-of-day") == '0' or addon.getSetting("time-of-day") == '1':
								self.playlist.add(url,item)
							if addon.getSetting("time-of-day") == '3':
								if day_night == 'day':
									self.playlist.add(url,item)
						if video['timeOfDay'] == 'night':
							if addon.getSetting("time-of-day") == '0' or addon.getSetting("time-of-day") == '2':
								self.playlist.add(url,item)
							if addon.getSetting("time-of-day") == '3':
								if day_night=='night':
									self.playlist.add(url,item)

					elif video['accessibilityLabel'].lower() == "san francisco" and addon.getSetting("enable-sfrancisco") == "true":
						if video['timeOfDay'] == 'day':
							if addon.getSetting("time-of-day") == '0' or addon.getSetting("time-of-day") == '1':
								self.playlist.add(url,item)
							if addon.getSetting("time-of-day") == '3':
								if day_night == 'day':
									self.playlist.add(url,item)
						if video['timeOfDay'] == 'night':
							if addon.getSetting("time-of-day") == '0' or addon.getSetting("time-of-day") == '2':
								self.playlist.add(url,item)
							if addon.getSetting("time-of-day") == '3':
								if day_night == 'night':
									self.playlist.add(url,item)

					elif video['accessibilityLabel'].lower() == "china" and addon.getSetting("enable-china") == "true":
						if video['timeOfDay'] == 'day':
							if addon.getSetting("time-of-day") == '0' or addon.getSetting("time-of-day") == '1':
								self.playlist.add(url,item)
							if addon.getSetting("time-of-day") == '3':
								if day_night == 'day':
									self.playlist.add(url,item)
						if video['timeOfDay'] == 'night':
							if addon.getSetting("time-of-day") == '0' or addon.getSetting("time-of-day") == '2':
								self.playlist.add(url,item)
							if addon.getSetting("time-of-day") == '3':
								if day_night == 'night':
									self.playlist.add(url,item)
				
			self.playlist.shuffle()
			return self.playlist
		else:
			return None
