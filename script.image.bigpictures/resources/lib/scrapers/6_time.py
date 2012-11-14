import re
import simplejson as json
from scraper import ScraperPlugin


class Scraper(ScraperPlugin):

    _title = 'Time.com: LightBox - Closeup'

    def _get_albums(self):
        self.albums = []
        url = 'http://lightbox.time.com/category/closeup/'
        tree = self._get_tree(url)
        albums = tree.findAll('div', {'id': re.compile('^post')})
        for id, album in enumerate(albums):
            title = album.find('h2').a.string
            p = album.find('img')['src']
            pic = self.__buildImg(p)
            album_url = album.find('h2').a['href']
            description = album.find('p').string
            self.albums.append({'title': title,
                                'album_id': id,
                                'pic': pic,
                                'description': description,
                                'album_url': album_url})
        return self.albums

    def _get_photos(self, album_url):
        self.photos = []
        tree = self._get_tree(album_url)
        album_title = tree.find('h1').string
        js_code = tree.find('text/javascript', text=re.compile('var images'))
        json_photos = re.search('var images = (\[.*?"ID":0.*?\])', js_code).group(1)
        photos = json.loads(json_photos)
        for id, photo in enumerate(photos):
            if u'post_mime_type' in photo:
                photo_title = photo['post_title'].strip()
                t = album_title.replace('Pictures of the Week, ', '')
                title = ' - '.join([t, photo_title])
                pic = photo['fullscreen']
                description = photo['post_content']
                self.photos.append({'title': title,
                                    'album_title': album_title,
                                    'photo_id': id,
                                    'pic': pic,
                                    'description': description,
                                    'album_url': album_url})
        return self.photos

    def __buildImg(self, url):
        path, params = url.split('?')
        return '%s?w=1178' % path


def register(id):
    return Scraper(id)