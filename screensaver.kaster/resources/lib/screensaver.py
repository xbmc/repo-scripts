# -*- coding: utf-8 -*-
"""
  Copyright (C) 2017-2020 enen92
  This file is part of kaster

  SPDX-License-Identifier: GPL-2.0-or-later
  See LICENSE for more information.
"""
import xbmc
import os
import json
import requests
import xbmcgui
import xbmcaddon
import xbmcvfs
from . import kodiutils
from random import randint, shuffle
from .screensaverutils import ScreenSaverUtils

PATH = xbmcaddon.Addon().getAddonInfo("path")

if not kodiutils.get_setting_as_bool("enable-hq"):
    IMAGE_FILE = os.path.join(PATH, "resources", "images", "chromecast.json")
else:
    IMAGE_FILE = os.path.join(PATH, "resources", "images", "chromecast-hq.json")


class Kaster(xbmcgui.WindowXMLDialog):

    class ExitMonitor(xbmc.Monitor):

        def __init__(self, exit_callback):
            self.exit_callback = exit_callback

        def onScreensaverDeactivated(self):
            try:
                self.exit_callback()
            except AttributeError:
                xbmc.log(
                    msg="exit_callback method not yet available",
                    level=xbmc.LOGWARNING
                )


    def __init__(self, *args, **kwargs):
        self.exit_monitor = None
        self.images = []
        self.set_property()
        self.utils = ScreenSaverUtils()

    def onInit(self):
        self._isactive = True
        # Register screensaver deactivate callback function
        self.exit_monitor = self.ExitMonitor(self.exit)
        # Init controls
        self.backgroud = self.getControl(32500)
        self.metadata_line2 = self.getControl(32503)
        self.metadata_line3 = self.getControl(32504)

        # Grab images
        self.get_images()

        # Start Image display loop
        if self.images and self.exit_monitor:
            while self._isactive and not self.exit_monitor.abortRequested():
                rand_index = randint(0, len(self.images) - 1)

                # if it is a google image....
                if "private" not in self.images[rand_index]:
                    req = requests.head(url=self.images[rand_index]["url"])
                    if req.status_code != 200:
                        # sleep for a bit to avoid 429 (too many requests)
                        if req.status_code == 429:
                            self.exit_monitor.waitForAbort(5)
                        continue

                    # photo metadata
                    if "location" in list(self.images[rand_index].keys()) and "photographer" in list(self.images[rand_index].keys()):
                        self.metadata_line2.setLabel(self.images[rand_index]["location"])
                        self.metadata_line3.setLabel("%s %s" % (kodiutils.get_string(32001),
                                                                self.utils.remove_unknown_author(self.images[rand_index]["photographer"])))
                    elif "location" in list(self.images[rand_index].keys()) and "photographer" not in list(self.images[rand_index].keys()):
                        self.metadata_line2.setLabel(self.images[rand_index]["location"])
                        self.metadata_line3.setLabel("")
                    elif "location" not in list(self.images[rand_index].keys()) and "photographer" in list(self.images[rand_index].keys()):
                        self.metadata_line2.setLabel("%s %s" % (kodiutils.get_string(32001),
                                                                self.utils.remove_unknown_author(self.images[rand_index]["photographer"])))
                        self.metadata_line3.setLabel("")
                    else:
                        self.metadata_line2.setLabel("")
                        self.metadata_line3.setLabel("")
                else:
                    # Logic for user owned photos - custom information
                    if "line1" in self.images[rand_index]:
                        self.metadata_line2.setLabel(self.images[rand_index]["line1"])
                    else:
                        self.metadata_line2.setLabel("")
                    if "line2" in self.images[rand_index]:
                        self.metadata_line3.setLabel(self.images[rand_index]["line2"])
                    else:
                        self.metadata_line2.setLabel("")
                # Insert photo
                self.backgroud.setImage(self.images[rand_index]["url"])
                # Pop image and wait
                del self.images[rand_index]
                # sleep for the configured time
                wait_time = kodiutils.get_setting_as_int("wait-time-before-changing-image")
                self.exit_monitor.waitForAbort(wait_time)
                if not self._isactive or self.exit_monitor.abortRequested():
                    break
                # Check if images dict is empty, if so read the file again
                if not self.images:
                    self.get_images()

    def get_images(self, override=False):
        # Read google images from json file
        self.images = []
        if kodiutils.get_setting_as_int("screensaver-mode") == 0 or kodiutils.get_setting_as_int("screensaver-mode") == 2 or override:
            try:
                with open(IMAGE_FILE, "r") as f:
                    images = f.read()
            except:
                with open(IMAGE_FILE, "r", encoding="utf-8") as f:
                    images = f.read()
            self.images = json.loads(images)
        # Check if we have images to append
        if kodiutils.get_setting_as_int("screensaver-mode") == 1 or kodiutils.get_setting_as_int("screensaver-mode") == 2 and not override:
            if kodiutils.get_setting("my-pictures-folder") and xbmcvfs.exists(xbmc.translatePath(kodiutils.get_setting("my-pictures-folder"))):
                for image in self.utils.get_own_pictures(kodiutils.get_setting("my-pictures-folder")):
                    self.images.append(image)
            else:
                return self.get_images(override=True)
        shuffle(self.images)
        return

    def set_property(self):
        # Kodi does not yet allow scripts to ship font definitions
        skin = xbmc.getSkinDir()
        if "estuary" in skin:
            self.setProperty("clockfont", "fontclock")
        elif "zephyr" in skin:
            self.setProperty("clockfont", "fontzephyr")
        elif "eminence" in skin:
            self.setProperty("clockfont", "fonteminence")
        elif "aura" in skin:
            self.setProperty("clockfont", "fontaura")
        elif "box" in skin:
            self.setProperty("clockfont", "box")
        else:
            self.setProperty("clockfont", "fontmainmenu")
        # Set skin properties as settings
        for setting in ["hide-clock-info", "hide-kodi-logo", "hide-weather-info", "hide-pic-info", "hide-overlay", "show-blackbackground"]:
            self.setProperty(setting, kodiutils.get_setting(setting))
        # Set animations
        if kodiutils.get_setting_as_int("animation") == 1:
            self.setProperty("animation","panzoom")
        return


    def exit(self):
        self._isactive = False
        # Delete the monitor from memory so we can gracefully remove
        # the screensaver window from memory too
        if self.exit_monitor:
            del self.exit_monitor
        # Finally call close so doModal returns
        self.close()
