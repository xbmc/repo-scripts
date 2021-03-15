"""
   Copyright (C) 2015- enen92
   This file is part of screensaver.atv4 - https://github.com/enen92/screensaver.atv4

   SPDX-License-Identifier: GPL-2.0-only
   See LICENSE for more information.
"""

import json
import xbmc
import os
import xbmcvfs
from random import shuffle
from .commonatv import applefeed, applelocalfeed, addon

from urllib.request import Request, urlopen


class AtvPlaylist:
    def __init__(self, ):
        if not xbmc.getCondVisibility("Player.HasMedia"):
            if not addon.getSettingBool("force-offline"):
                try:
                    req = Request(applefeed)
                    with urlopen(req) as response:
                        self.html = json.loads(response.read())
                except Exception:
                    self.local_feed()
            else:
                self.local_feed()
        else:
            self.html = {}

    def local_feed(self):
        with open(applelocalfeed, "r") as f:
            self.html = json.loads(f.read())

    def getPlaylistJson(self):
        return self.html

    def getPlaylist(self):
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

        self.playlist = []
        if self.html:
            for block in self.html:
                for video in block['assets']:

                    url = video['url']

                    exists_on_disk = False

                    # check if file exists on disk
                    movie = url.split("/")[-1]
                    localfilemov = os.path.join(addon.getSetting("download-folder"), movie)
                    if xbmcvfs.exists(localfilemov):
                        url = localfilemov
                        exists_on_disk = True

                    # check for existence of the trancoded file .mp4 only
                    localfilemp4 = os.path.join(addon.getSetting("download-folder"), movie.replace('.mov', '.mp4'))
                    if xbmcvfs.exists(localfilemp4):
                        url = localfilemp4
                        exists_on_disk = True

                    # Continue to next item if the file is not in disk and the
                    # setting refuse-stream is enabled
                    if not exists_on_disk and addon.getSettingBool("force-offline"):
                        continue

                    # build setting
                    thisvideosetting = "enable-" + video['accessibilityLabel'].lower().replace(" ", "")

                    if addon.getSetting(thisvideosetting) == "true":
                        if video['timeOfDay'] == 'day':
                            if addon.getSetting("time-of-day") == '0' or addon.getSettingInt("time-of-day") == 1:
                                self.playlist.append(url)
                            if addon.getSettingInt("time-of-day") == 3:
                                if day_night == 'day':
                                    self.playlist.append(url)
                        if video['timeOfDay'] == 'night':
                            if addon.getSetting("time-of-day") == '0' or addon.getSettingInt("time-of-day") == 2:
                                self.playlist.append(url)
                            if addon.getSettingInt("time-of-day") == 3:
                                if day_night == 'night':
                                    self.playlist.append(url)

            shuffle(self.playlist)
            return self.playlist
        else:
            return None
