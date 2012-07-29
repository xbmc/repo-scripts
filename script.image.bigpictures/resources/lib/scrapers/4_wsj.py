from scraper import ScraperPlugin


class Scraper(ScraperPlugin):

    _title = 'Wallstreetjournal: The Photo Journal'

    def _get_albums(self):
        self.albums = []
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
            self.albums.append({'title': title,
                                'album_id': id,
                                'pic': pic,
                                'description': description,
                                'album_url': album_url})
        return self.albums

    def _get_photos(self, album_url):
        self.photos = []
        while album_url:
            photos, album_url = self.__get_photo_page(album_url)
            self.photos.extend(photos)
        return self.photos

    def __get_photo_page(self, album_url):
        page_photos = []
        next_page_url = None
        tree = self._get_tree(album_url)
        c = 'articleHeadlineBox headlineType-newswire'
        album_title = tree.find('div', c).h1.string
        section = tree.find('div', {'class': 'articlePage'})
        photos = section.findAll('p')
        for id, photo in enumerate(photos):
            pic = photo.img['src'].strip()
            description = self._collapse(photo.contents)
            page_photos.append({'title': '%d - %s' % (id + 1, album_title),
                                'album_title': album_title,
                                'photo_id': id,
                                'pic': pic,
                                'description': description,
                                'album_url': album_url})
        if tree.find('a', 'nav_next'):
            next_page_url = tree.find('a', 'nav_next')['href']
        return page_photos, next_page_url


def register(id):
    return Scraper(id)
