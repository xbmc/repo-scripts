# -*- coding: utf-8 -*-
"""
  Copyright (C) 2017-2020 enen92
  Copyright (C) 2026-2026 guss77
  This file is part of kaster

  SPDX-License-Identifier: GPL-2.0-or-later
  See LICENSE for more information.
"""
import xbmc
import os
import json
import time
import requests
import xbmcgui
import xbmcaddon
import xbmcvfs
from . import kodiutils
from random import randint, shuffle
from .screensaverutils import ScreenSaverUtils

PATH = xbmcaddon.Addon().getAddonInfo("path")

IMAGE_FILE = os.path.join(PATH, "resources", "images", "chromecast.json")

# Additional URLs from periodic scraping of the Chromecast ambient home page
ADDITIONAL_IMAGE_LIST_URL = ("https://raw.githubusercontent.com/guss77/"
                             "chromecast-ambient-scapper/refs/heads/main/chromecast.json")

# Stop probing google images after repeated network failures, so an unreachable
# network cannot stall the slideshow once per picture.
GOOGLE_CHECK_MAX_FAILURES = 10

# How long Google stays disabled before the loop gives it another chance: the
# network may have recovered without a Kodi restart.
GOOGLE_DISABLE_RECHECK_INTERVAL = 15 * 60


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
        self.google_check_failures = 0
        self.google_checks_disabled = False
        self.google_disabled_at = 0.0
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
                # Google was disabled earlier; give it another chance after
                # the interval, so a network blip does not need a Kodi
                # restart to recover.
                if (self.google_checks_disabled and
                        time.time() - self.google_disabled_at >=
                        GOOGLE_DISABLE_RECHECK_INTERVAL):
                    self.google_checks_disabled = False
                    self.get_images()
                    if not self.images:
                        continue
                # Failed google pictures are dropped from the list, so it can
                # become empty in the middle of a round. Reload it, or wait if
                # there is nothing left to show.
                if not self.images:
                    self.get_images()
                    if not self.images:
                        self.exit_monitor.waitForAbort(5)
                        continue
                rand_index = randint(0, len(self.images) - 1)

                # if it is a google image....
                if "private" not in self.images[rand_index]:
                    if self.google_check_failures < GOOGLE_CHECK_MAX_FAILURES:
                        image_url = self.images[rand_index]["url"]
                        failure = None
                        try:
                            # Follow redirects (Google image URLs often 302
                            # to the actual image); without this the check
                            # reports the redirect status itself.
                            req = requests.head(
                                url=image_url, timeout=10, allow_redirects=True)
                        except requests.exceptions.RequestException as error:
                            req = None
                            failure = "%s: %s" % (type(error).__name__, error)
                        if req is not None and req.status_code == 429:
                            # Too many requests, not a broken picture: the
                            # server is reachable and only asks us to slow
                            # down. Back off, keep the picture for a later
                            # attempt and do not count this as a failure.
                            self.google_check_failures = 0
                            self.exit_monitor.waitForAbort(5)
                            continue
                        if req is None or req.status_code != 200:
                            # Drop an unreachable or broken picture instead of
                            # retrying it forever, which would prevent the list
                            # from draining and the local pictures from loading.
                            del self.images[rand_index]
                            self.google_check_failures += 1
                            if failure is None:
                                failure = "HTTP %s" % req.status_code
                            remaining = (GOOGLE_CHECK_MAX_FAILURES -
                                         self.google_check_failures)
                            if remaining:
                                kodiutils.log(
                                    "google image check failed for %s (%s); "
                                    "%d strike(s) left" % (image_url, failure,
                                                           remaining),
                                    xbmc.LOGDEBUG)
                            else:
                                kodiutils.log(
                                    "google image check failed for %s (%s); "
                                    "disabling google images"
                                    % (image_url, failure),
                                    xbmc.LOGDEBUG)
                            if self.google_check_failures >= GOOGLE_CHECK_MAX_FAILURES:
                                # The network looks unreachable. Stop using
                                # google pictures for now; the loop re-enables
                                # them after GOOGLE_DISABLE_RECHECK_INTERVAL.
                                self.google_checks_disabled = True
                                self.google_disabled_at = time.time()
                                self.images = [image for image in self.images
                                               if "private" in image]
                            continue
                        self.google_check_failures = 0

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
                    # Logic for user owned photos - custom information and
                    # photographer credits read from the image metadata
                    self.set_user_picture_info(self.images[rand_index])
                # Insert photo
                self.backgroud.setImage(self.images[rand_index]["url"])
                # Pop image and wait
                del self.images[rand_index]
                # Sleep for the configured time in one-second slices so that a
                # screensaver deactivation interrupts the wait promptly: the
                # monitor's abort event only signals script abort, not
                # screensaver deactivation.
                wait_time = kodiutils.get_setting_as_int("wait-time-before-changing-image")
                wait_end = time.time() + wait_time
                while True:
                    left = wait_end - time.time()
                    if left <= 0 or not self._isactive or self.exit_monitor.abortRequested():
                        break
                    self.exit_monitor.waitForAbort(min(left, 1))
                if not self._isactive or self.exit_monitor.abortRequested():
                    break
                # Check if images dict is empty, if so read the file again
                if not self.images:
                    self.get_images()

    def set_user_picture_info(self, image):
        """Show a local photo's caption and photographer on the info lines."""
        line1 = image.get("line1", "")
        line2 = image.get("line2", "")
        if "photographer" in image:
            photo_by = "%s %s" % (kodiutils.get_string(32001),
                                  image["photographer"])
            # Use the same layout as the google photos: the credit moves to
            # line two when line one already holds a caption.
            if line1:
                line2 = photo_by
            else:
                line1 = photo_by
        self.metadata_line2.setLabel(line1)
        self.metadata_line3.setLabel(line2)

    def get_images(self, override=False):
        self.google_check_failures = 0
        # Read google images from json file
        self.images = []
        if not self.google_checks_disabled and (kodiutils.get_setting_as_int("screensaver-mode") == 0 or kodiutils.get_setting_as_int("screensaver-mode") == 2 or override):
            try:
                with open(IMAGE_FILE, "r") as f:
                    images = f.read()
            except:
                with open(IMAGE_FILE, "r", encoding="utf-8") as f:
                    images = f.read()
            self.images = json.loads(images)
            self._merge_additional_images()
        # Check if we have images to append
        if kodiutils.get_setting_as_int("screensaver-mode") == 1 or kodiutils.get_setting_as_int("screensaver-mode") == 2 and not override:
            if kodiutils.get_setting("my-pictures-folder") and xbmcvfs.exists(kodiutils.translate_path(kodiutils.get_setting("my-pictures-folder"))):
                for image in self.utils.get_own_pictures(kodiutils.get_setting("my-pictures-folder")):
                    self.images.append(image)
            else:
                if not override: # do not go into recursion loop
                    return self.get_images(override=True)
        shuffle(self.images)
        return

    def _merge_additional_images(self):
        """Merge the additional image list into the list loaded from disk.

        ADDITIONAL_IMAGE_LIST_URL should return JSON compatible with our local
        image list file.
        """
        try:
            response = requests.get(ADDITIONAL_IMAGE_LIST_URL, timeout=10)
            if response.status_code != 200:
                return
            entries = response.json()
        except Exception:
            return
        if not isinstance(entries, list):
            return
        existing = {e.get("url") for e in self.images if isinstance(e, dict)}
        for entry in entries:
            if (isinstance(entry, dict) and entry.get("url")
                    and entry["url"] not in existing):
                self.images.append(entry)
                existing.add(entry["url"])

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
