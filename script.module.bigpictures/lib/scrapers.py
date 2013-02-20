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

import re
import json
import urllib2
from BeautifulSoup import BeautifulSoup

import xbmc


class BasePlugin(object):

    _title = ''
    _id = 0

    def __init__(self, _id):
        self._albums = []
        self._photos = {}
        self._id = _id

    def get_albums(self):
        return self._albums or self._get_albums()

    def get_photos(self, album_url):
        return self._photos.get(album_url) or self._get_photos(album_url)

    def _get_albums(self):
        raise NotImplementedError

    def _get_photos(self, album_url):
        raise NotImplementedError

    def _get_tree(self, url, language='html'):
        self.log('get_tree opening url "%s"' % url)
        req = urllib2.Request(url)
        try:
            html = urllib2.urlopen(req).read()
            self.log('get_tree received %d bytes' % len(html))
        except urllib2.HTTPError, error:
            self.log('HTTPError: %s' % error)
        tree = BeautifulSoup(html, convertEntities=language)
        return tree

    def _collapse(self, iterable):
        return u''.join([e.string.strip() for e in iterable if e.string])

    @property
    def title(self):
        return self._title

    def log(self, msg):
        xbmc.log('TheBigPictures ScraperPlugin[%s]: %s' % (
            self.__class__.__name__, msg
        ))


class TheBigPictures(BasePlugin):

    _title = 'Boston.com: The Big Picture'

    def _get_albums(self):
        self._albums = []
        url = 'http://www.boston.com/bigpicture/'
        tree = self._get_tree(url)
        albums = tree.findAll('div', 'headDiv2')
        for id, album in enumerate(albums):
            title = album.find('a').string
            album_url = album.find('a')['href']
            d = album.find('div', {'class': 'bpBody'})
            if not d:
                continue
            description = self._collapse(d.contents)
            pic = album.find('img')['src']
            self._albums.append({
                'title': title,
                'album_id': id,
                'pic': pic,
                'description': description,
                'album_url': album_url}
            )
        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        tree = self._get_tree(album_url)
        album_title = tree.find('h2').a.string
        images = tree.findAll('div', {'class':
                                      re.compile('bpImageTop|bpBoth')})
        for id, photo in enumerate(images):
            pic = photo.img['src']
            d = photo.find('div', {'class': 'bpCaption'}).contents
            description = self._collapse(d).rstrip('#')
            self._photos[album_url].append({
                'title': '%d - %s' % (id + 1, album_title),
                'album_title': album_title,
                'photo_id': id,
                'pic': pic,
                'description': description,
                'album_url': album_url
            })
        return self._photos[album_url]


class AtlanticInFocus(BasePlugin):

    _title = 'The Atlantic: In Focus'

    def _get_albums(self):
        self._albums = []
        url = 'http://www.theatlantic.com/infocus/'
        tree = self._get_tree(url)
        section = tree.find('div', {'class': 'middle'})
        headlines = section.findAll('h1', {'class': 'headline'})
        descriptions = section.findAll('div', {'class': 'dek'})
        images = section.findAll('span', 'if1280')
        for id, node in enumerate(headlines):
            title = node.a.string
            album_url = headlines[id].a['href']
            d = descriptions[id].p.contents
            description = self._collapse(d).replace('\n', '')
            pic = images[id].find('img')['src']
            self._albums.append({
                'title': title,
                'album_id': id,
                'pic': pic,
                'description': description,
                'album_url': album_url}
            )
        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        tree = self._get_tree(album_url)
        album_title = tree.find('h1', 'headline').string
        images = tree.findAll('span', {'class': 'if1024'})
        for id, photo in enumerate(images):
            pic = photo.find('img')['src']
            d = photo.find('div', 'imgCap').contents
            description = self._collapse(d)
            self._photos[album_url].append({
                'title': '%d - %s' % (id + 1, album_title),
                'album_title': album_title,
                'photo_id': id,
                'pic': pic,
                'description': description,
                'album_url': album_url
            })
        return self._photos[album_url]


class SacBeeFrame(BasePlugin):

    _title = 'Sacramento Bee: The Frame'

    def _get_albums(self):
        self._albums = []
        url = 'http://blogs.sacbee.com/photos/'
        tree = self._get_tree(url)
        albums = tree.findAll('div', 'entry-asset asset hnews hentry story')
        for id, album in enumerate(albums):
            title = album.find('a').string
            album_url = album.find('a')['href']
            d = album.find('div', {'class': 'caption'}).contents
            description = self._collapse(d)
            pic = album.find('img')['src']
            self._albums.append({
                'title': title,
                'album_id': id,
                'pic': pic,
                'description': description,
                'album_url': album_url}
            )
        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        tree = self._get_tree(album_url)
        album_title = tree.find('div', 'asset-name entry-title title').a.string
        images = tree.findAll('div', {'class': 'frame-image'})
        for id, photo in enumerate(images):
            pic = photo.find('img')['src']
            d = photo.find('div', {'class': 'caption'})
            description = self._collapse(d)
            self._photos[album_url].append({
                'title': '%d - %s' % (id + 1, album_title),
                'album_title': album_title,
                'photo_id': id,
                'pic': pic,
                'description': description,
                'album_url': album_url
            })
        return self._photos[album_url]


class WallStreetJournal(BasePlugin):

    _title = 'Wallstreetjournal: The Photo Journal'

    def _get_albums(self):
        self._albums = []
        url = 'http://blogs.wsj.com/photojournal/'
        tree = self._get_tree(url)
        albums = tree.findAll('li', 'postitem imageFormat-P')
        for id, album in enumerate(albums):
            author = album.find('cite').string
            if not author == u'By WSJ Staff':
                continue
            if not album.find('img'):
                continue
            title = album.find('h2').a.string
            album_url = album.find('h2').a['href']
            d = album.findAll('div', {'class': 'postContent'})[1].p
            description = self._collapse(d)
            pic = album.find('img')['src'].strip()
            self._albums.append({
                'title': title,
                'album_id': id,
                'pic': pic,
                'description': description,
                'album_url': album_url}
            )
        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        photos, next_page_url = self.__get_page(album_url)
        self._photos[album_url].extend(photos)
        while next_page_url:
            photos, next_page_url = self.__get_page(next_page_url or album_url)
            self._photos[album_url].extend(photos)
        return self._photos[album_url]

    def __get_page(self, album_url):
        page_photos = []
        next_page_url = None
        tree = self._get_tree(album_url)
        c = 'articleHeadlineBox headlineType-newswire'
        album_title = tree.find('div', c).h1.string
        section = tree.find('div', {'class': 'articlePage'})
        images = section.findAll('p')
        for id, photo in enumerate(images):
            if not photo.find('img'):
                continue
            pic = photo.img['src'].strip()
            description = self._collapse(photo.contents)
            page_photos.append({
                'title': '%d - %s' % (id + 1, album_title),
                'album_title': album_title,
                'photo_id': id,
                'pic': pic,
                'description': description,
                'album_url': album_url
            })
        if tree.find('a', 'nav_next'):
            next_page_url = tree.find('a', 'nav_next')['href']
        return page_photos, next_page_url


class TotallyCoolPix(BasePlugin):

    _title = 'TotallyCoolPix.com'

    def _get_albums(self):
        self._albums = []
        url = 'http://totallycoolpix.com/'
        tree = self._get_tree(url)
        section = tree.find('div', {'class': 'pri'})
        albums = section.findAll('div', {'class': 'block'})
        for id, album in enumerate(albums):
            title = album.find('h1').a.string
            album_url = album.find('h1').a['href']
            d = album.find('div', {'class': 'post-intro'}).p.contents
            description = self._collapse(d)
            pic = album.find('img')['src']
            self._albums.append({
                'title': title,
                'album_id': id,
                'pic': pic,
                'description': description,
                'album_url': album_url}
            )
        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        tree = self._get_tree(album_url)
        album_title = tree.find('h1').a.string
        photos = tree.findAll('div', {
            'class': re.compile('^wp-caption')
        })
        for id, photo in enumerate(photos):
            pic = photo.img['src']
            description = self._collapse(photo.p.contents)
            self._photos[album_url].append({
                'title': '%d - %s' % (id + 1, album_title),
                'album_title': album_title,
                'photo_id': id,
                'pic': pic,
                'description': description,
                'album_url': album_url
            })
        return self._photos[album_url]


class TimeLightbox(BasePlugin):

    _title = 'Time.com: LightBox - Closeup'

    def _get_albums(self):
        self._albums = []
        url = 'http://lightbox.time.com/category/closeup/'
        tree = self._get_tree(url)
        albums = tree.findAll('div', {'id': re.compile('^post')})
        for id, album in enumerate(albums):
            title = album.find('h2').a.string
            p = album.find('img')['src']
            pic = self.__buildImg(p)
            album_url = album.find('h2').a['href']
            description = album.find('p').string
            self._albums.append({
                'title': title,
                'album_id': id,
                'pic': pic,
                'description': description,
                'album_url': album_url}
            )
        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        tree = self._get_tree(album_url)
        entry_top = tree.find('div', {'class': 'entry-top'})
        album_title = entry_top.find('h1').string or ''
        js_code = tree.find('text/javascript', text=re.compile('var images'))
        json_photos = re.search(
            'var images = (\[.*?"ID":0.*?\])',
            js_code
        ).group(1)
        photos = json.loads(json_photos)
        for id, photo in enumerate(photos):
            if u'post_mime_type' in photo:
                photo_title = photo['post_title'].strip()
                t = album_title.replace('Pictures of the Week, ', '')
                title = ' - '.join([t, photo_title])
                pic = photo['fullscreen']
                description = photo['post_content']
                self._photos[album_url].append({
                    'title': title,
                    'album_title': album_title,
                    'photo_id': id,
                    'pic': pic,
                    'description': description,
                    'album_url': album_url
                })
        return self._photos[album_url]

    def __buildImg(self, url):
        path, params = url.split('?')
        return '%s?w=1178' % path


class NewYorkTimesLens(BasePlugin):

    _title = "NewYorkTimes.com: Lens Blog"

    def _get_albums(self):
        self._albums = []
        url = 'http://lens.blogs.nytimes.com/asset-data/'
        tree = self._get_tree(url, language='xml')
        for id, album in enumerate(tree.findAll('post')):
            self._albums.append({
                'title': album.title.string,
                'album_id': id,
                'pic': self.__build_img(album.photo.url.string),
                'description': self.__text(album.excerpt.string),
                'album_url': album.asset.string}
            )
        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        tree = self._get_tree(album_url, language='xml')
        for id, slide in enumerate(tree.findAll('slide')):
            photo = slide.photo
            self._photos[album_url].append({
                'title': 'by %s' % photo.credit.string,
                'album_title': album_url.split('/')[-1].split('.')[0],
                'photo_id': id,
                'pic': photo.url.string,
                'description': self.__text(photo.caption.string),
                'album_url': album_url
            })
        return self._photos[album_url]

    @staticmethod
    def __build_img(url):
        url = url.replace('-custom2', '-jumbo').replace('-custom3', '-jumbo')
        return url.replace('-custom1', '-jumbo')

    @staticmethod
    def __text(txt):
        return txt.replace('&#x2019;s', "'")


def get_scrapers():
    ENABLED_SCRAPERS = (
        TheBigPictures,
        AtlanticInFocus,
        SacBeeFrame,
        WallStreetJournal,
        TotallyCoolPix,
        TimeLightbox,
        NewYorkTimesLens,
    )
    scrapers = [scraper(i) for i, scraper in enumerate(ENABLED_SCRAPERS)]
    return scrapers
