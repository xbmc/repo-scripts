from scraper import ScraperPlugin


class Scraper(ScraperPlugin):

    NAME = 'Wallstreetjournal: The Photo Journal'

    def getAlbums(self):
        url = 'http://blogs.wsj.com/photojournal/'
        tree = self.getCachedTree(url)
        self.albums = list()
        storyNodes = tree.findAll('li',
                                  'postitem imageFormat-P')
        for node in storyNodes:
            try:
                title = self.cleanHTML(node.find('h2').a.string)
                link = node.find('h2').a['href']
                content_raw = node.findAll('div', attrs={'class':
                                                         'postContent'})
                description = self.cleanHTML(content_raw[1].p)
                pic = node.find('img')['src'].strip()
                self.albums.append({'title': title,
                                    'pic': pic,
                                    'description': description,
                                    'link': link})
            except:
                pass
        return self.albums

    def getPhotos(self, url, append=False):
        tree = self.getCachedTree(url)
        title = tree.find('div',
                          'articleHeadlineBox headlineType-newswire').h1.string
        if not append:
            self.photos = list()
        subtree = tree.find('div', {'class': 'articlePage'})
        subtree.extract()
        photoNodes = subtree.findAll('p')
        for node in photoNodes:
            try:
                pic = node.img['src'].strip()
                description = self.cleanHTML(node.contents)
                self.photos.append({'title': self.cleanHTML(title),
                                    'pic': pic,
                                    'description': description})
            except:
                pass
        if tree.find('a', 'nav_next'):
            self.getPhotos(tree.find('a', 'nav_next')['href'], append=True)
        return self.photos


def register():
    return Scraper()
