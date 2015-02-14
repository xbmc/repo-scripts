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
from CommonFunctions import parseDOM, stripTags
import HTMLParser

try:
    import xbmc
    XBMC_MODE = True
except ImportError:
    XBMC_MODE = False


ALL_SCRAPERS = (
    'TheBigPictures',
    'AtlanticInFocus',
    'SacBeeFrame',
    'WallStreetJournal',
    'TotallyCoolPix',
    # 'TimeLightbox',
    # 'NewYorkTimesLens',
)


class BasePlugin(object):

    _title = ''
    _id = 0

    def __init__(self, _id):
        self._albums = []
        self._photos = {}
        self._id = _id
        self._parser = HTMLParser.HTMLParser()

    def get_albums(self):
        return self._albums or self._get_albums()

    def get_photos(self, album_url):
        return self._photos.get(album_url) or self._get_photos(album_url)

    def _get_albums(self):
        raise NotImplementedError

    def _get_photos(self, album_url):
        raise NotImplementedError

    def _get_tree(self, url, language='html'):
        html = self._get_html(url)
        try:
            tree = BeautifulSoup(html, convertEntities=language)
        except TypeError:
            # Temporary fix for wrong encoded utf-8 chars in NewYork
            # Times Lens Blog. Shame on you.
            html = html.decode('utf-8', 'ignore')
            tree = BeautifulSoup(html, convertEntities=language)
        return tree

    def _get_html(self, url):
        self.log('_get_html opening url "%s"' % url)
        req = urllib2.Request(url)
        html = urllib2.urlopen(req).read()
        self.log('get_tree received %d bytes' % len(html))
        return html

    def _collapse(self, iterable):
        return u''.join([e.string.strip() for e in iterable if e.string])

    @property
    def title(self):
        return self._title

    def log(self, msg):
        if XBMC_MODE:
            xbmc.log('TheBigPictures ScraperPlugin[%s]: %s' % (
                self.__class__.__name__, msg
            ))
        else:
            print('TheBigPictures ScraperPlugin[%s]: %s' % (
                self.__class__.__name__, msg
            ))

    @classmethod
    def get_scrapers(cls, name_list):
        enabled_scrapers = []
        for sub_class in cls.__subclasses__():
            if sub_class.__name__ in name_list:
                enabled_scrapers.append(sub_class)
        return enabled_scrapers


class TheBigPictures(BasePlugin):

    _title = 'The Boston Globe: The Big Picture'

    def _get_albums(self):
        self._albums = []
        url = 'http://www.bostonglobe.com/news/bigpicture'

        html = self._get_html(url)

        for _id, album in enumerate(parseDOM(html, 'section')):
            title = parseDOM(album, 'a')[0]
            album_url = 'http://www.bostonglobe.com' + parseDOM(album, 'a', ret='href')[0]
            d = parseDOM(album, 'div', attrs={'class': 'subhead geor'})[0]
            if not d:
                continue
            description = stripTags(self._parser.unescape(d))
            pic = urllib2.quote(parseDOM(album, 'img', ret='src')[0])
            if not pic:
                continue
            self._albums.append({
                'title': title,
                'album_id': _id,
                'pic': 'http:' + pic,
                'description': description,
                'album_url': album_url})

        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        html = self._get_html(album_url)
        album_title = parseDOM(html, 'title')[0]
        images = parseDOM(html, 'div', attrs={'class': 'photo'})
        descs = parseDOM(html, 'article', attrs={'class': 'pcaption'})

        for _id, photo in enumerate(images):
            pic = urllib2.quote(parseDOM(photo, 'img', ret='src')[0])
            description = stripTags(parseDOM(descs[_id], 'div', attrs={'class': 'gcaption geor'})[0])
            self._photos[album_url].append({
                'title': '%d - %s' % (_id + 1, album_title),
                'album_title': album_title,
                'photo_id': _id,
                'pic': 'http:' + pic,
                'description': description,
                'album_url': album_url
            })
        return self._photos[album_url]


class AtlanticInFocus(BasePlugin):

    _title = 'The Atlantic: In Focus'

    def _get_albums(self):
        self._albums = []
        url = 'http://www.theatlantic.com/infocus/'
        html = self._get_html(url)
        pattern = r'@media\(min-width:1632px\){#river1 \.lead-image{background-image:url\((.+?)\)'
        for _id, li in enumerate(parseDOM(html, 'li', attrs={'class': 'article'})):
            headline = parseDOM(li, 'h1')[0]
            match = re.search(pattern.replace('river1', 'river%d' % (_id + 1)), html)
            if match:
                self._albums.append({
                    'title': parseDOM(headline, 'a')[0],
                    'album_id': _id,
                    'pic': match.group(1),
                    'description': stripTags(self._parser.unescape(parseDOM(li, 'p', attrs={'class': 'dek'})[0])),
                    'album_url': 'http://www.theatlantic.com' + parseDOM(headline, 'a', ret='href')[0],
                })
        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        html = self._get_html(album_url)
        pattern = r'@media\(min-width:1592px\){#img01 \.img{background-image:url\((.+?)\)'
        id_pattern = re.compile(r'#img(\d\d)')
        album_title = parseDOM(html, 'title')[0]
        for _id, p in enumerate(parseDOM(html, 'p', attrs={'class': 'caption'})):
            match = re.search(id_pattern, p)
            if match:
                img_id = match.group(1)
                match = re.search(pattern.replace('img01', 'img%s' % img_id), html)
                if match:
                    self._photos[album_url].append({
                        'title': '%d - %s' % (_id + 1, album_title),
                        'album_title': album_title,
                        'photo_id': _id,
                        'pic': match.group(1),
                        'description': stripTags(self._parser.unescape(p)).replace('\n                #', ''),
                        'album_url': album_url,
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
        albums = tree.findAll('article', {'class': re.compile('post-snippet')})
        for id, album in enumerate(albums):
            title = album.find('h2').a.string
            album_url = album.find('h2').a['href']
            d = album.findAll('div', {'class': 'post-content'})[0].p
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
        album_title = self._collapse(tree.find('h1', {'class': 'post-title h-main'}).contents)
        images = tree.findAll('dl')
        for id, photo in enumerate(images):
            if not photo.find('img'):
                continue
            pic = photo.find('img')['src'].strip()
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
        albums = tree.findAll('div', {'class': 'item'})
        for id, album in enumerate(albums):
            if not album.find('a', {'class': 'open'}):
                continue
            title = album.find('h2').string
            album_url = album.find('a')['href']
            p = album.find('p')
            description = self._collapse(p.contents) if p else ''
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
        album_title = tree.find('h2').string
        for id, photo in enumerate(tree.findAll('div', {'class': 'image'})):
            print photo
            img = photo.find('img')
            if not img:
                continue
            description = self._collapse(photo.find('p', {'class': 'info-txt'}).contents)
            self._photos[album_url].append({
                'title': '%d - %s' % (id + 1, album_title),
                'album_title': album_title,
                'photo_id': id,
                'pic': img['src'],
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
            if not album.photo.url.string:
                continue
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


def get_scrapers(enabled_scrapers=None):
    if enabled_scrapers is None:
        enabled_scrapers = ALL_SCRAPERS
    scrapers = [
        scraper(i) for i, scraper
        in enumerate(BasePlugin.get_scrapers(enabled_scrapers))
    ]
    return scrapers
