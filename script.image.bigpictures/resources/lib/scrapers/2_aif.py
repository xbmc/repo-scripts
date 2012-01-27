from scraper import ScraperPlugin
import re


class Scraper(ScraperPlugin):

    NAME = 'The Atlantic: In Focus'

    def getAlbums(self):
        url = 'http://www.theatlantic.com/infocus/'
        tree = self.getCachedTree(url)
        self.albums = list()
        section = tree.find('div', attrs={'class': 'middle'})
        
        headlines = section.findAll('h1', attrs={'class': 'headline'})
        descriptions = section.findAll('div', attrs={'class': 'dek'})
        images = section.findAll('span', 'if1280')
        for i, node in enumerate(headlines):
            title = self.cleanHTML(node.a.string)
            link = headlines[i].a['href']
            desc_raw = descriptions[i].p.contents
            description = self.cleanHTML(desc_raw)
            pic = images[i].find('img')['src']
            self.albums.append({'title': title,
                                'pic': pic,
                                'description': description,
                                'link': link})
        return self.albums

    def getPhotos(self, url):
        tree = self.getCachedTree(url)
        title = self.cleanHTML(tree.find('h1', 'headline').string)
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

    