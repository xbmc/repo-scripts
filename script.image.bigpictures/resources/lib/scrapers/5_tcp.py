import re
from scraper import ScraperPlugin


class Scraper(ScraperPlugin):

    _title = 'TotallyCoolPix.com'

    def _get_albums(self):
        self.albums = []
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
            self.albums.append({'title': title,
                                'album_id': id,
                                'pic': pic,
                                'description': description,
                                'album_url': album_url})
        return self.albums

    def _get_photos(self, album_url):
        self.photos = []
        tree = self._get_tree(album_url)
        album_title = tree.find('h1').a.string
        photos = tree.findAll('div', {'class': re.compile('^wp-caption')})
        for id, photo in enumerate(photos):
            pic = photo.img['src']
            description = self._collapse(photo.p.contents)
            self.photos.append({'title': '%d - %s' % (id + 1, album_title),
                                'album_title': album_title,
                                'photo_id': id,
                                'pic': pic,
                                'description': description,
                                'album_url': album_url})
        return self.photos


def register(id):
    return Scraper(id)
