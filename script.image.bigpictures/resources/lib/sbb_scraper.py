from scraper import Scraper
from BeautifulSoup import BeautifulSoup


class SBB(Scraper):

    def getAlbums(self, url):
        """creates an ordered list albums = [{title, pic, description, link}, ...]"""
        tree = BeautifulSoup(self.getCachedURL(url))
        self.albums = list()
        storyNodes = tree.findAll('div', 'entry-asset asset hentry story')
        for node in storyNodes:
            title = node.find('a').string
            link = node.find('a')['href']
            description = self.cleanHTML(node.find('div', attrs={'style': 'width: 980px; padding: 5px; text-align: left;'}).contents)
            pic = node.find('img')['src']
            self.albums.append({'title': title, 'pic': pic, 'description': description, 'link': link})

    def getPhotos(self, url):
        """creates an ordered list photos = [{title, pic, description}, ...] """
        tree = BeautifulSoup(self.getCachedUrl(url))
        title = tree.find('div', 'asset-name entry-title title').a.string
        self.photos = list()
        subtree_img = tree.findAll('div', attrs={'style': 'background: rgb(224, 224, 224); width: 982px; padding: 4px;'})
        subtree_txt = tree.findAll('div', attrs={'style': 'background: rgb(224, 224, 224); width: 970px; padding: 10px;'})
        # this is very dirty because this website is very dirty :(
        for i, node_img in enumerate(subtree_img):
            pic = node_img.find('img')['src']
            try:
                description = self.cleanHTML(subtree_txt[i])
            except:
                description = ''
            self.photos.append({'title': title, 'pic': pic, 'description': description})
