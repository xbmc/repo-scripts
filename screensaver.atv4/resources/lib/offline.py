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
import playlist
import downloader
from commonatv import *


def offline():
    if addon.getSetting("download-folder") != "":
    	places = ["All", "London", "Hawaii", "New York City", "San Francisco", "China"]
    	choose=dialog.select(translate(32014),places)
    	if choose > -1:
    		atvPlaylist = playlist.AtvPlaylist()
    		playlistDictionary = atvPlaylist.getPlaylistJson()
    		downloadList = []
    		if playlistDictionary:
    			for block in playlistDictionary:
    				for video in block['assets']:
    					if places[choose].lower() == "all":
    						downloadList.append(video['url'])
    					else:
    						if places[choose].lower() == video['accessibilityLabel'].lower():
    							downloadList.append(video['url'])
    		#call downloader
    		if downloadList:
    			down = downloader.Downloader()
    			down.downloadall(downloadList)
    		else:
    			dialog.ok(translate(32000), translate(32012))
    else:
    	dialog.ok(translate(32000), translate(32013))


