import urllib

import xbmc
import xbmcgui
import downloader

from addon import Addon, log, SCRAPERS_PATH
from resources.lib.scrapers.scraper import ScraperManager


class GUI(xbmcgui.WindowXML):

    CONTROL_MAIN_IMAGE = 100
    CONTROL_VISIBLE = 102
    CONTROL_ASPECT_KEEP = 103
    CONTROL_ARROWS = 104
    ACTION_CONTEXT_MENU = [117]
    ACTION_PREVIOUS_MENU = [9, 92, 10]
    ACTION_SHOW_INFO = [11]
    ACTION_EXIT_SCRIPT = [13]
    ACTION_DOWN = [4]
    ACTION_UP = [3]
    ACTION_0 = [58, 18]
    ACTION_PLAY = [79]

    def __init__(self, skin_file, addon_path):
        log('script.__init__ started')
        self.ScraperManager = ScraperManager(SCRAPERS_PATH)

    def onInit(self):
        log('script.onInit started')
        self.show_info = True
        self.aspect_keep = True
        self.last_seen_album_id = 0
        if Addon.getSetting('show_arrows') == 'false':
            self.getControl(self.CONTROL_ARROWS).setVisible(False)
        if Addon.getSetting('aspect_ratio2') == '0':
            self.getControl(self.CONTROL_ASPECT_KEEP).setVisible(False)
        self.showHelp()
        self.showAlbums()
        self.setFocus(self.getControl(self.CONTROL_MAIN_IMAGE))
        log('script.onInit finished')

    def onAction(self, action):
        action_id = action.getId()
        if action_id in self.ACTION_SHOW_INFO:
            self.toggleInfo()
        elif action_id in self.ACTION_CONTEXT_MENU:
            self.download_album()
        elif action_id in self.ACTION_PREVIOUS_MENU:
            if self.current_mode == 'albums':
                self.close()
            elif self.current_mode == 'photos':
                self.showAlbums(self.last_seen_album_id)
        elif action_id in self.ACTION_EXIT_SCRIPT:
            self.close()
        elif action_id in self.ACTION_DOWN and self.current_mode == 'albums':
            self.ScraperManager.switch_to_next()
            self.showAlbums()
        elif action_id in self.ACTION_UP and self.current_mode == 'albums':
            self.ScraperManager.switch_to_previous()
            self.showAlbums()
        elif action_id in self.ACTION_0:
            self.toggleAspect()
        elif action_id in self.ACTION_PLAY:
            self.startSlideshow()

    def onClick(self, controlId):
        if controlId == self.CONTROL_MAIN_IMAGE:
            if self.current_mode == 'albums':
                self.showPhotos()
            elif self.current_mode == 'photos':
                self.toggleInfo()

    def showPhotos(self):
        log('script.showPhotos started')
        self.last_seen_album_id = int(self.getProperty('album_id'))
        self.current_mode = 'photos'
        w = xbmcgui.Window(xbmcgui.getCurrentWindowId())
        w.setProperty('Category', 'Photo')
        album_url = self.getProperty('album_url')
        self.getControl(self.CONTROL_MAIN_IMAGE).reset()
        photos = self.ScraperManager.get_photos(album_url)
        self.addItems(photos)
        log('script.showPhotos finished')

    def showAlbums(self, switch_to_album_id=0):
        log('script.showAlbums started with switch to album_id: %s'
            % switch_to_album_id)
        self.current_mode = 'albums'
        w = xbmcgui.Window(xbmcgui.getCurrentWindowId())
        w.setProperty('Category', 'Album')
        self.getControl(self.CONTROL_MAIN_IMAGE).reset()
        albums = self.ScraperManager.get_albums()
        self.addItems(albums)
        if switch_to_album_id:
            c = self.getControl(self.CONTROL_MAIN_IMAGE)
            c.selectItem(switch_to_album_id)
        log('script.showAlbums finished')

    def addItems(self, items):
        log('script.addItems started')
        for item in items:
            li = xbmcgui.ListItem(label=item['title'],
                                  label2=item['description'],
                                  iconImage=item['pic'])
            li.setProperty('album', self.ScraperManager.scraper_title)
            if 'album_url' in item.keys():
                li.setProperty('album_url', item['album_url'])
            if 'album_id' in item.keys():
                li.setProperty('album_id', str(item['album_id']))
            self.getControl(self.CONTROL_MAIN_IMAGE).addItem(li)

    def getProperty(self, property):
        c = self.getControl(self.CONTROL_MAIN_IMAGE)
        return c.getSelectedItem().getProperty(property)

    def toggleInfo(self):
        c = self.getControl(self.CONTROL_VISIBLE)
        self.show_info = not self.show_info
        c.setVisible(self.show_info)

    def toggleAspect(self):
        c = self.getControl(self.CONTROL_ASPECT_KEEP)
        self.aspect_keep = not self.aspect_keep
        c.setVisible(self.aspect_keep)

    def startSlideshow(self):
        log('script.startSlideshow started')
        params = {}
        params['scraper_id'] = self.ScraperManager.scraper_id
        params['mode'] = 'photos'
        params['album_url'] = self.getProperty('album_url')
        if Addon.getSetting('random_slideshow') == 'true':
            random = 'random'
        else:
            random = 'notrandom'
        url = 'plugin://%s/?%s' % (Addon.getAddonInfo('id'),
                                   urllib.urlencode(params))
        log('script.startSlideshow using url=%s' % url)
        xbmc.executebuiltin('Slideshow(%s, recursive, %s)'
                            % (url, random))
        log('script.startSlideshow finished')

    def download_album(self):
        log('script.download_album started')
        download_path = Addon.getSetting('download_path')
        if not download_path:
            s = Addon.getLocalizedString(32300)  # Choose default download path
            new_path = xbmcgui.Dialog().browse(3, s, 'pictures')
            if not new_path:
                return
            else:
                download_path = new_path
                Addon.setSetting('download_path', download_path)
        log('script.download_album using download_path="%s"' % download_path)
        album_url = self.getProperty('album_url')
        items = self.ScraperManager.get_photos(album_url)
        downloader.Downloader(items, download_path)
        log('script.download_album finished')

    def showHelp(self):
        if not Addon.getSetting('dont_show_help') == 'true':
            Addon.openSettings()
