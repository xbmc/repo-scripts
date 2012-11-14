import re
from scraper import ScraperPlugin


class Scraper(ScraperPlugin):

    _title = 'Boston.com: The Big Picture'

    def _get_albums(self):
        self.albums = []
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
            self.albums.append({'title': title,
                                'album_id': id,
                                'pic': pic,
                                'description': description,
                                'album_url': album_url})
        return self.albums

    def _get_photos(self, album_url):
        self.photos = []
        tree = self._get_tree(album_url)
        album_title = tree.find('h2').a.string
        photos = tree.findAll('div', {'class':
                                      re.compile('bpImageTop|bpBoth')})
        for id, photo in enumerate(photos):
            pic = photo.img['src']
            d = photo.find('div', {'class': 'bpCaption'}).contents
            description = self._collapse(d).rstrip('#')
            self.photos.append({'title': '%d - %s' % (id + 1, album_title),
                                'album_title': album_title,
                                'photo_id': id,
                                'pic': pic,
                                'description': description,
                                'album_url': album_url})
        return self.photos


def register(id):
    return Scraper(id)
