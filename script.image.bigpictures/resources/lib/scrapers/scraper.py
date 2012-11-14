import os
import simplejson as json
import sys
import time
import urllib2

from BeautifulSoup import BeautifulSoup

from addon import log, CACHE_PATH

MAX_AGE_ALBUMS = 3600
MAX_AGE_PHOTOS = 0
CACHE_VERSION = 1


class ScraperPlugin(object):

    def __init__(self, id):
        self.__scaper_id = id
        self.albums = []
        self.photos = []

    def _get_albums(self):
        # Needs to be overloaded by scraper
        pass

    def _get_photos(self, album_url):
        # Needs to be overloaded by scraper
        pass

    def _get_tree(self, url):
        log('scraper._get_tree started with url=%s' % url)
        req = urllib2.Request(url)
        try:
            html = urllib2.urlopen(req).read()
            log('scraper._get_tree got web response')
        except urllib2.HTTPError, error:
            log('HTTPError: %s' % error)
        tree = BeautifulSoup(html, convertEntities='html')
        log('scraper._get_tree got tree')
        return tree

    def _collapse(self, iterable):
        return ''.join([e.string for e in iterable if e.string]).strip()

    @property
    def title(self):
        return self._title

    @property
    def id(self):
        return self.__scaper_id


class ScraperManager(object):

    def __init__(self, scrapers_path):
        log('manager.__init__')
        self.__scrapers = self.__get_scrapers(scrapers_path)
        self.__cur_scaper_id = 0
        self.__read_cache()
        self._num_scrapers = len(self.__scrapers)

    def switch_to_next(self):
        id = self.__cur_scaper_id + 1
        if id in range(0, self._num_scrapers):
            self.__cur_scaper_id = id
        else:
            self.__cur_scaper_id = 0
        log('manager.switch_to_next id=%d' % self.__cur_scaper_id)

    def switch_to_previous(self):
        id = self.__cur_scaper_id - 1
        if id in range(0, self._num_scrapers):
            self.__cur_scaper_id = id
        else:
            self.__cur_scaper_id = self._num_scrapers - 1
        log('manager.switch_to_previous id=%d' % self.__cur_scaper_id)

    def switch_to_given_id(self, id):
        if id in range(0, self._num_scrapers):
            self.__cur_scaper_id = id
        log('manager.switch_to_given_id id=%d' % self.__cur_scaper_id)

    def get_scrapers(self):
        scrapers = []
        for scraper in self.__scrapers:
            scrapers.append({'id': scraper.id,
                             'title': scraper.title})
        return scrapers

    def get_albums(self):
        element_id = 'albums_%d' % self.__cur_scaper_id
        albums = self.__get_cache(element_id, MAX_AGE_ALBUMS)
        if not albums:
            albums = self.__current_scraper()._get_albums()
            self.__set_cache(element_id, albums)
        log('manager.get_albums got %d items' % len(albums))
        return albums

    def get_photos(self, album_url):
        element_id = 'photos_%d_%s' % (self.__cur_scaper_id, album_url)
        photos = self.__get_cache(element_id, MAX_AGE_PHOTOS)
        if not photos:
            photos = self.__current_scraper()._get_photos(album_url)
            self.__set_cache(element_id, photos)
        log('manager.get_photos got %d items' % len(photos))
        return photos

    @property
    def scraper_id(self):
        return self.__current_scraper().id

    @property
    def scraper_title(self):
        return self.__current_scraper().title

    def __get_scrapers(self, scrapers_path):
        sys.path.insert(0, scrapers_path)
        scraper_modules = []
        for f in os.listdir(scrapers_path):
            if f.endswith('.py') and f[0].isdigit():
                scraper_modules.append(f[:-3])
        modules = [__import__(scraper) for scraper in scraper_modules]
        return [m.register(id) for id, m in enumerate(modules)]

    def __current_scraper(self):
        return self.__scrapers[self.__cur_scaper_id]

    def __read_cache(self):
        log('manager.__read_cache started')
        cache_file = os.path.join(CACHE_PATH, 'cache.json')
        if os.path.isfile(cache_file):
            try:
                c = json.load(open(cache_file, 'r'))
                if 'version' in c and c['version'] == CACHE_VERSION:
                    self.__cache = c
                else:
                    log('manager.__read_cache cache version to old')
                    self.__recreate_cache()
            except ValueError:
                log('manager.__read_cache could not read: "%s"' % cache_file)
                self.__recreate_cache()
        else:
            log('manager.__read_cache file does not exist: "%s"' % cache_file)
            self.__recreate_cache()
        log('manager.__read_cache finished')

    def __recreate_cache(self):
        log('manager.__recreate_cache version: %d' % CACHE_VERSION)
        self.__cache = {'version': CACHE_VERSION,
                        'content': {}}

    def __write_cache(self):
        log('manager.__write_cache started')
        if not os.path.isdir(CACHE_PATH):
            os.makedirs(CACHE_PATH)
        cache_file = os.path.join(CACHE_PATH, 'cache.json')
        json.dump(self.__cache, open(cache_file, 'w'), indent=1)
        log('manager.__write_cache finished')

    def __get_cache(self, element_id, max_age):
        log('manager.__get_cache started with element_id:%s' % element_id)
        if element_id in self.__cache['content']:
            log('manager.__get_cache found element')
            element = self.__cache['content'][element_id]
            if max_age and time.time() - element['timestamp'] > max_age:
                log('manager.__get_cache element too old')
            else:
                return element['data']

    def __set_cache(self, element_id, element_data):
        log('manager.__set_cache started with element_id:%s' % element_id)
        self.__cache['content'][element_id] = {'timestamp': time.time(),
                                               'data': element_data}
        self.__write_cache()
