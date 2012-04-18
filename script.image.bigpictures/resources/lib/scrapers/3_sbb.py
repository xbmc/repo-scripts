from scraper import ScraperPlugin


class Scraper(ScraperPlugin):

    _title = 'Sacramento Bee: The Frame'

    def _get_albums(self):
        self.albums = []
        url = 'http://blogs.sacbee.com/photos/'
        tree = self._get_tree(url)
        albums = tree.findAll('div', 'entry-asset asset hnews hentry story')
        for id, album in enumerate(albums):
            title = album.find('a').string
            album_url = album.find('a')['href']
            d = album.find('div', {'class': 'caption'}).contents
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
        album_title = tree.find('div', 'asset-name entry-title title').a.string
        images = tree.findAll('div', {'class': 'frame-image'})
        for id, photo in enumerate(images):
            pic = photo.find('img')['src']
            d = photo.find('div', {'class': 'caption'})
            description = self._collapse(d)
            self.photos.append({'title': '%d - %s' % (id + 1, album_title),
                                'album_title': album_title,
                                'photo_id': id,
                                'pic': pic,
                                'description': description,
                                'album_url': album_url})
        return self.photos


def register(id):
    return Scraper(id)
