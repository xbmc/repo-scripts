#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Tristan Fischer (sphere@dersphere.de)
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

import os
import re
import sys
import urllib

import xbmc
import xbmcaddon
import xbmcgui

from thebigpictures import ScraperManager, ALL_SCRAPERS

addon = xbmcaddon.Addon()
addon_path = addon.getAddonInfo('path')
addon_name = addon.getAddonInfo('name')


class Downloader(object):

    def __init__(self, download_path):
        self.log('__init__ with path="%s"' % download_path)
        self.download_path = download_path
        self.pDialog = xbmcgui.DialogProgress()
        self.pDialog.create(addon.getAddonInfo('name'))
        self.pDialog.update(1, addon.getLocalizedString(32301))

    def download(self, photos):
        self.total_items = len(photos)
        album_title = photos[0]['album_title']
        album_title = re.sub('[^\w\- ]', '', album_title).replace(' ', '_')
        full_path = os.path.join(self.download_path, album_title)
        self.log('using full_path="%s"' % full_path)
        line3 = addon.getLocalizedString(32304) % full_path
        self.pDialog.update(2, '', '', line3)
        if not os.path.isdir(full_path):
            os.mkdir(full_path)
        for i, photo in enumerate(photos):
            self.current_item = i + 1
            url = photo['pic']
            self.current_file = '%d.%s' % (
                self.current_item, url.rsplit('.', 1)[-1]
            )
            filename = os.path.join(full_path, self.current_file)
            self.log('Downloading "%s" to "%s"' % (url, filename))
            try:
                urllib.urlretrieve(url, filename, self.update_progress)
            except IOError, e:
                self.log('ERROR: "%s"' % str(e))
                break
            self.log('Done')
            if self.pDialog.iscanceled():
                self.log('Canceled')
                break

    def update_progress(self, block_count, block_size, item_size):
        overall_percent = int(self.current_item * 100 / self.total_items)
        item_percent = int(block_count * block_size * 100 / item_size)
        line1 = addon.getLocalizedString(32302) % (
            self.current_item,
            self.total_items
        )
        line2 = addon.getLocalizedString(32303) % (
            self.current_file,
            item_percent
        )
        self.pDialog.update(overall_percent, line1, line2)

    def log(self, msg):
        xbmc.log('TheBigPictures Downloader: %s' % msg)

    def __del__(self):
        self.pDialog.close()


class GUI(xbmcgui.WindowXML):

    CONTROL_MAIN_IMAGE = 100
    CONTROL_VISIBLE = 102
    CONTROL_ASPECT_KEEP = 103
    CONTROL_ARROWS = 104
    CONTROL_BG = 105
    ACTION_CONTEXT_MENU = [117]
    ACTION_PREVIOUS_MENU = [9, 92, 10]
    ACTION_SHOW_INFO = [11]
    ACTION_EXIT_SCRIPT = [13]
    ACTION_DOWN = [4]
    ACTION_UP = [3]
    ACTION_0 = [58, 18]
    ACTION_PLAY = [79]

    def __init__(self, skin_file, addon_path):
        self.log('__init__')
        self.getScrapers()

    def getScrapers(self):
        enabled_scrapers = []
        for scraper in ALL_SCRAPERS:
            if addon.getSetting('enable_%s' % scraper) == 'true':
                enabled_scrapers.append(scraper)
        self.scraper_manager = ScraperManager(enabled_scrapers)

    def onInit(self):
        self.log('onInit')
        self.show_info = True
        self.aspect_keep = True
        self.last_seen_album_id = 0

        self.getControls()

        if addon.getSetting('show_arrows') == 'false':
            self.arrows_controller.setVisible(False)
        if addon.getSetting('aspect_ratio2') == '0':
            self.aspect_controller.setVisible(False)
        if addon.getSetting('black_background') == 'true':
            if self.bg_controller:
                self.bg_controller.setVisible(False)

        self.showHelp()
        self.showAlbums()

        self.setFocus(self.image_list)
        self.log('onInit finished')

    def getControls(self):
        self.window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
        self.image_list = self.getControl(self.CONTROL_MAIN_IMAGE)
        self.arrows_controller = self.getControl(self.CONTROL_ARROWS)
        self.aspect_controller = self.getControl(self.CONTROL_ASPECT_KEEP)
        self.info_controller = self.getControl(self.CONTROL_VISIBLE)
        try:
            self.bg_controller = self.getControl(self.CONTROL_BG)
        except RuntimeError:
            # catch exception with skins which override the xml
            # but are not up2date like Aeon Nox
            self.bg_controller = None

    def onAction(self, action):
        action_id = action.getId()
        if action_id in self.ACTION_SHOW_INFO:
            self.toggleInfo()
        elif action_id in self.ACTION_CONTEXT_MENU:
            self.download_album()
        elif action_id in self.ACTION_PREVIOUS_MENU:
            if self.getWindowProperty('Category') == 'Album':
                self.close()
            elif self.getWindowProperty('Category') == 'Photo':
                self.showAlbums(self.last_seen_album_id)
        elif action_id in self.ACTION_EXIT_SCRIPT:
            self.close()
        elif action_id in self.ACTION_DOWN:
            if self.getWindowProperty('Category') == 'Album':
                self.scraper_manager.next()
                self.showAlbums()
        elif action_id in self.ACTION_UP:
            if self.getWindowProperty('Category') == 'Album':
                self.scraper_manager.previous()
                self.showAlbums()
        elif action_id in self.ACTION_0:
            self.toggleAspect()
        elif action_id in self.ACTION_PLAY:
            self.startSlideshow()

    def onClick(self, controlId):
        if controlId == self.CONTROL_MAIN_IMAGE:
            if self.getWindowProperty('Category') == 'Album':
                self.showPhotos()
            elif self.getWindowProperty('Category') == 'Photo':
                self.toggleInfo()

    def showPhotos(self):
        self.log('showPhotos')
        self.last_seen_album_id = int(self.getItemProperty('album_id'))
        album_url = self.getItemProperty('album_url')
        self.addItems(self.scraper_manager.get_photos(album_url))
        self.setWindowProperty('Category', 'Photo')
        self.log('showPhotos finished')

    def showAlbums(self, switch_to_album_id=0):
        self.log('showAlbums started with switch to album_id: %s'
                 % switch_to_album_id)
        self.addItems(self.scraper_manager.get_albums())
        if switch_to_album_id:
            self.image_list.selectItem(switch_to_album_id)
        self.setWindowProperty('Category', 'Album')
        self.log('showAlbums finished')

    def addItems(self, items):
        self.log('addItems')
        self.image_list.reset()
        for item in items:
            li = xbmcgui.ListItem(
                label=item['title'],
                label2=item['description'],
                iconImage=item['pic']
            )
            li.setProperty(
                'album_title',
                self.scraper_manager.current_scraper.title
            )
            li.setProperty('album_url', item.get('album_url'))
            li.setProperty('album_id', str(item.get('album_id')))
            self.image_list.addItem(li)

    def getItemProperty(self, key):
        return self.image_list.getSelectedItem().getProperty(key)

    def getWindowProperty(self, key):
        return self.window.getProperty(key)

    def setWindowProperty(self, key, value):
        return self.window.setProperty(key, value)

    def toggleInfo(self):
        self.show_info = not self.show_info
        self.info_controller.setVisible(self.show_info)

    def toggleAspect(self):
        self.aspect_keep = not self.aspect_keep
        self.aspect_controller.setVisible(self.aspect_keep)

    def startSlideshow(self):
        self.log('startSlideshow')
        params = {
            'scraper_id': self.scraper_manager._current_index,
            'album_url': self.getItemProperty('album_url')
        }
        if addon.getSetting('random_slideshow') == 'true':
            random = 'random'
        else:
            random = 'notrandom'
        url = 'plugin://%s/?%s' % (addon.getAddonInfo('id'),
                                   urllib.urlencode(params))
        self.log('startSlideshow using url=%s' % url)
        xbmc.executebuiltin('Slideshow(%s, recursive, %s)'
                            % (url, random))
        self.log('startSlideshow finished')

    def download_album(self):
        self.log('download_album')
        download_path = addon.getSetting('download_path')
        if not download_path:
            s = addon.getLocalizedString(32300)  # Choose default download path
            new_path = xbmcgui.Dialog().browse(3, s, 'pictures')
            if not new_path:
                return
            else:
                download_path = new_path
                addon.setSetting('download_path', download_path)
        self.log('download_album using download_path="%s"' % download_path)
        downloader = Downloader(download_path)
        album_url = self.getItemProperty('album_url')
        items = self.scraper_manager.get_photos(album_url)
        downloader.download(items)
        del downloader
        self.log('download_album finished')

    def showHelp(self):
        if not addon.getSetting('dont_show_help') == 'true':
            addon.openSettings()

    def log(self, msg):
        xbmc.log('TheBigPictures GUI: %s' % msg)


if __name__ == '__main__':
    gui = GUI(u'script-%s-main.xml' % addon_name, addon_path).doModal()
    del gui
    sys.modules.clear()
