#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2013 Tristan Fischer (sphere@dersphere.de)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import random

import xbmcaddon
import xbmcgui
import xbmc

from thebigpictures import ScraperManager, ALL_SCRAPERS

addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo('name')
addon_path = addon.getAddonInfo('path')


class Screensaver(xbmcgui.WindowXMLDialog):

    class ExitMonitor(xbmc.Monitor):

        def __init__(self, exit_callback):
            self.exit_callback = exit_callback

        def onScreensaverDeactivated(self):
            self.exit_callback()

    def onInit(self):
        self.abort_requested = False
        self.started = False
        self.exit_monitor = self.ExitMonitor(self.exit)

        self.picture_control = self.getControl(30001)
        self.loader_control = self.getControl(30002)
        self.source_control = self.getControl(30003)
        self.title_control = self.getControl(30004)
        self.description_control = self.getControl(30005)
        self.next_picture_control = self.getControl(30006)

        self.picture_duration = (
            int(addon.getSetting('picture_duration')) * 1000
        )

        self.get_scrapers()
        self.slideshow()

    def get_scrapers(self):
        enabled_scrapers = []
        for scraper in ALL_SCRAPERS:
            if addon.getSetting('enable_%s' % scraper) == 'true':
                enabled_scrapers.append(scraper)
        self.scraper_manager = ScraperManager(enabled_scrapers)

    def slideshow(self):
        self.scraper_manager.shuffle()
        while not self.abort_requested:
            self.scraper_manager.next()
            albums = self.scraper_manager.get_albums()
            random.shuffle(albums)
            for album in albums:
                photos = self.scraper_manager.get_photos(album['album_url'])
                random.shuffle(photos)
                for i, photo in enumerate(photos):
                    photo['source'] = (
                        self.scraper_manager.current_scraper.title
                    )
                    self.set_photo(photo)
                    if i + 1 < len(photos):
                        next_photo = photos[i + 1]
                        self.preload_next_photo(next_photo)
                    for i in xrange(self.picture_duration / 500):
                        #self.log('check abort %d' % (i + 1))
                        if self.abort_requested:
                            self.log('slideshow abort_requested')
                            self.exit()
                            return
                        xbmc.sleep(500)

    def set_photo(self, photo):
        if not self.started:
            self.loader_control.setVisible(False)
            self.started = True
        picture_url = photo['pic']
        #self.log('photo: %s' % picture_url)
        self.picture_control.setImage(picture_url)
        self.source_control.setLabel(photo['source'])
        self.title_control.setLabel(photo['title'])
        self.description_control.setText(photo['description'])

    def preload_next_photo(self, photo):
        picture_url = photo['pic']
        self.next_picture_control.setImage(picture_url)

    def exit(self):
        self.abort_requested = True
        self.exit_monitor = None
        self.log('exit')
        self.close()

    def log(self, msg):
        xbmc.log(u'TheBigPictures Screensaver: %s' % msg)


if __name__ == '__main__':
    screensaver = Screensaver(
        'script-%s-main.xml' % addon_name,
        addon_path,
        'default',
    )
    screensaver.doModal()
    del screensaver
    sys.modules.clear()
