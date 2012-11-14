import os
import re
import urllib

import xbmcgui

from addon import Addon, log


class Downloader(object):

    def __init__(self, photos, download_path):
        self.len = len(photos)
        log('downloader.__init__ with %d items and path=%s' % (self.len,
                                                               download_path))
        self.pDialog = xbmcgui.DialogProgress()
        self.pDialog.create(Addon.getAddonInfo('name'))
        s = Addon.getLocalizedString(32301)  # Gathering Data...
        self.pDialog.update(0, s)
        album_title = photos[0]['album_title']
        self.sub_folder = re.sub('[^\w\- ]', '', album_title).replace(' ', '_')
        self.full_path = os.path.join(download_path, self.sub_folder)
        log('script.download_album using full_path="%s"' % self.full_path)
        self.__create_folder(self.full_path)
        for i, photo in enumerate(photos):
            self.current_item = i + 1
            url = photo['pic']
            self.current_file = photo['pic'].split('/')[-1].split('?')[0]
            filename = os.path.join(self.full_path, self.current_file)
            log('downloader: Downloading "%s" to "%s"' % (url, filename))
            try:
                urllib.urlretrieve(url, filename, self.update_progress)
            except IOError, e:
                log('downloader: ERROR: "%s"' % str(e))
                break
            log('downloader: Done')
            if self.pDialog.iscanceled():
                log('downloader: Canceled')
                break

    def update_progress(self, count, block_size, total_size):
        percent = int(self.current_item * 100 / self.len)
        item_percent = int(count * block_size * 100 / total_size)
        line1 = Addon.getLocalizedString(32302) % (self.current_item,
                                                   self.len)
        line2 = Addon.getLocalizedString(32303) % (self.current_file,
                                                   item_percent)
        line3 = Addon.getLocalizedString(32304) % self.sub_folder
        self.pDialog.update(percent, line1, line2, line3)

    def __create_folder(self, full_path):
        if not os.path.isdir(full_path):
            os.mkdir(full_path)

    def __del__(self):
        self.pDialog.close()
