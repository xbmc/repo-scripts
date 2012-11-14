import re
from scraper import ScraperPlugin


class Scraper(ScraperPlugin):

    _title = 'The Atlantic: In Focus'

    def _get_albums(self):
        self.albums = []
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
            self.albums.append({'title': title,
                                'album_id': id,
                                'pic': pic,
                                'description': description,
                                'album_url': album_url})
        return self.albums

    def _get_photos(self, album_url):
        self.photos = []
        tree = self._get_tree(album_url)
        album_title = tree.find('h1', 'headline').string
        photos = tree.findAll('span', {'class': 'if1024'})
        for id, photo in enumerate(photos):
            pic = photo.find('img')['src']
            d = photo.find('div', 'imgCap').contents
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
