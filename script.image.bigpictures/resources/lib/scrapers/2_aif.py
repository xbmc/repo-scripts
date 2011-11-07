from scraper import ScraperPlugin
import re


class Scraper(ScraperPlugin):

    NAME = 'The Atlantic: In Focus'

    def getAlbums(self):
        url = 'http://www.theatlantic.com/infocus/'
        tree = self.getCachedTree(url)
        self.albums = list()
        storyNodes = tree.findAll('div', 'articleContent')
        imgNodes = tree.findAll('span', 'if1280')
        for i, node in enumerate(storyNodes):
            title = node.find('a').string
            link = node.find('a')['href']
            desc_raw = node.find('div',
                                 attrs={'class': 'entry_body'}).p.contents
            description = self.cleanHTML(desc_raw)
            try:
                pic = imgNodes[i].find('img')['src']
            except:
                pic = ''
            self.albums.append({'title': title,
                                'pic': pic,
                                'description': description,
                                'link': link})
        return self.albums

    def getPhotos(self, url):
        tree = self.getCachedTree(url)
        title = tree.find('h1', 'headline').string
        self.photos = list()
        photoNodes = tree.findAll('span', {'class': 'if1024'})
        for node in photoNodes:
            pic = node.find('img')['src']
            description = self.cleanHTML(node.find('div',
                                                   'imgCap').contents)
            self.photos.append({'title': title,
                                'pic': pic,
                                'description': description})
        return self.photos


def register():
    return Scraper()
