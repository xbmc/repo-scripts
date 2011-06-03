from parent import ScraperParent
from BeautifulSoup import BeautifulSoup


class Scraper(ScraperParent):

    NAME = 'Sacramento Bee: The Frame'

    def getAlbums(self):
        url = 'http://blogs.sacbee.com/photos/'
        tree = BeautifulSoup(self.getCachedURL(url))
        self.albums = list()
        storyNodes = tree.findAll('div', 'entry-asset asset hentry story')
        for node in storyNodes:
            title = node.find('a').string
            link = node.find('a')['href']
            style = 'width: 980px; padding: 5px; text-align: left;'
            desc = self.cleanHTML(node.find('div',
                                            attrs={'style': style}).contents)
            pic = node.find('img')['src']
            self.albums.append({'title': title,
                                'pic': pic,
                                'description': desc,
                                'link': link})
        return self.albums

    def getPhotos(self, url):
        tree = BeautifulSoup(self.getCachedURL(url))
        title = tree.find('div', 'asset-name entry-title title').a.string
        self.photos = list()
        style = 'background: rgb(224, 224, 224); width: 982px; padding: 4px;'
        subtree_img = tree.findAll('div',
                                   attrs={'style': style})
        style = 'background: rgb(224, 224, 224); width: 970px; padding: 10px;'
        subtree_txt = tree.findAll('div',
                                   attrs={'style': style})
        # this is very dirty because this website is very dirty :(
        for i, node_img in enumerate(subtree_img):
            pic = node_img.find('img')['src']
            try:
                description = self.cleanHTML(subtree_txt[i])
            except:
                description = ''
            self.photos.append({'title': title,
                                'pic': pic,
                                'description': description})
        return self.photos
