from scraper import Scraper
from BeautifulSoup import BeautifulSoup


class WSJ(Scraper):

    def getAlbums(self, url):
        """creates an ordered list albums = [{title, pic, description, link}, ...]"""
        tree = BeautifulSoup(self.getCachedURL(url))
        self.albums = list()
        storyNodes = tree.findAll('li', 'postitem imageFormat-P')
        for node in storyNodes:
            title = self.cleanHTML(node.find('h2').a.string)
            link = node.find('h2').a['href']
            description = self.cleanHTML(node.findAll('div', attrs={'class': 'postContent'})[1].p)
            pic = node.find('img')['src'].strip()
            self.albums.append({'title': title, 'pic': pic, 'description': description, 'link': link})

    def getPhotos(self, url, append=False):
        """creates an ordered list photos = [{title, pic, description}, ...] """
        tree = BeautifulSoup(self.getCachedUrl(url))
        title = tree.find('div', 'articleHeadlineBox headlineType-newswire').h1.string
        if not append:
            self.photos = list()
        subtree = tree.find('div', {'class': 'articlePage'})
        subtree.extract()
        photoNodes = subtree.findAll('p')
        for node in photoNodes:
            pic = node.img['src'].strip()
            description = self.cleanHTML(node.contents)
            self.photos.append({'title': title, 'pic': pic, 'description': description})
        if tree.find('a', 'nav_next'):
            self.getPhotos(tree.find('a', 'nav_next')['href'], append=True)
