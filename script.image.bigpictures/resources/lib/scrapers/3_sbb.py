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
            s = 'width: 980px; padding: 5px; text-align: left;'
            d = album.find('div', {'style': s}).contents
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
        s = 'background: rgb(224, 224, 224); width: 982px; padding: 4px;'
        images = tree.findAll('div', {'style': s})
        s = 'background: rgb(224, 224, 224); width: 970px; padding: 10px;'
        descriptions = tree.findAll('div', {'style': s})
        for id, photo in enumerate(images):
            pic = photo.find('img')['src']
            description = self._collapse(descriptions[id]).replace('  ', ' ')
            self.photos.append({'title': '%d - %s' % (id + 1, album_title),
                                'album_title': album_title,
                                'photo_id': id,
                                'pic': pic,
                                'description': description,
                                'album_url': album_url})
        return self.photos


def register(id):
    return Scraper(id)
