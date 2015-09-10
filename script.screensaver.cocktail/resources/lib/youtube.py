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

from common_cocktail import *
import urllib
import json
import re


def return_youtubevideos(query):
    foundAll = False
    ind = 1
    video_list = []
    inp = urllib.urlopen('https://www.googleapis.com/youtube/v3/search?part=snippet&q='+urllib.quote_plus(query)+'&maxResults='+str(addon.getSetting('youtube-max-results'))+'&key=AIzaSyAxaHJTQ5zgh86wk7geOwm-y0YyNMcEkSc')
    resp = json.load(inp)
    if resp and "items" in resp.keys():
        for item in resp["items"]:
            try:
                label = item["snippet"]["title"]
                thumb = item["snippet"]["thumbnails"]["high"]["url"]
                video = item["id"]["videoId"]
                video_item = (label,thumb,video)
                video_list.append(video_item)
            except: pass
    return video_list
