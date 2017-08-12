# -*- coding: utf-8 -*-
"""
    screensaver.atv4
    Copyright (C) 2015-2017 enen92

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
"""
import json
import urllib2
import xbmc
import xbmcgui
import os
import xbmcvfs
from commonatv import applefeed, applelocalfeed, addon, addon_path


class AtvPlaylist:
    def __init__(self, ):
        if not xbmc.getCondVisibility("Player.HasMedia"):
            try:
                response = urllib2.urlopen(applefeed)
                self.html = json.loads(response.read())
            except:
                with open(applelocalfeed, "r") as f:
                    self.html = json.loads(f.read())
        else:
            self.html = {}

    def getPlaylistJson(self, ):
        return self.html

    def getPlaylist(self, ):
        current_time = xbmc.getInfoLabel("System.Time")
        am_pm = xbmc.getInfoLabel("System.Time(xx)")
        current_hour = current_time.split(":")[0]
        if am_pm == "PM":
            if int(current_hour) < 12:
                current_hour = int(current_hour) + 12
            else:
                current_hour = int(current_hour)
        else:
            current_hour = int(current_hour)
        day_night = ''
        if current_hour < 19:
            if current_hour > 7:
                day_night = 'day'
            else:
                day_night = 'night'
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
                    item.setInfo('video', {'Title': label})
                    item.setArt({'thumb': os.path.join(addon_path, 'icon.png')})
                    url = video['url']
                    item.setPath(url)

                    # check if file exists on disk
                    movie = url.split("/")[-1]
                    localfilemov = os.path.join(addon.getSetting("download-folder"), movie)
                    if xbmcvfs.exists(localfilemov):
                        url = localfilemov

                    # check for existence of the trancoded file .mp4 only
                    localfilemp4 = os.path.join(addon.getSetting("download-folder"), movie.replace('.mov', '.mp4'))
                    if xbmcvfs.exists(localfilemp4):
                        url = localfilemp4

                    # build setting
                    thisvideosetting = "enable-" + video['accessibilityLabel'].lower().replace(" ", "")

                    if addon.getSetting(thisvideosetting) == "true":
                        if video['timeOfDay'] == 'day':
                            if addon.getSetting("time-of-day") == '0' or addon.getSetting("time-of-day") == '1':
                                self.playlist.add(url, item)
                            if addon.getSetting("time-of-day") == '3':
                                if day_night == 'day':
                                    self.playlist.add(url, item)
                        if video['timeOfDay'] == 'night':
                            if addon.getSetting("time-of-day") == '0' or addon.getSetting("time-of-day") == '2':
                                self.playlist.add(url, item)
                            if addon.getSetting("time-of-day") == '3':
                                if day_night == 'night':
                                    self.playlist.add(url, item)

            self.playlist.shuffle()
            return self.playlist
        else:
            return None
