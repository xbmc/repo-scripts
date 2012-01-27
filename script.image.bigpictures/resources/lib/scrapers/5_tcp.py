from scraper import ScraperPlugin
import re


class Scraper(ScraperPlugin):

    NAME = 'TotallyCoolPix.com'

    def getAlbums(self):
        url = 'http://totallycoolpix.com/'
        tree = self.getCachedTree(url)
        self.albums = list()
        storyNodes = tree.find('div', {'class': 'pri'}).findAll('div', {'class': 'block'})
        for node in storyNodes:
            try:
                title = self.cleanHTML(node.find('h1').a.string)
                link = node.find('h1').a['href']
                desc_raw = node.find('div',
                                     attrs={'class': 'post-intro'}).p.contents
                description = self.cleanHTML(desc_raw)
                pic = node.find('img')['src']
                self.albums.append({'title': title,
                                    'pic': pic,
                                    'description': description,
                                    'link': link})
            except:
                pass
        return self.albums

    def getPhotos(self, url):
        tree = self.getCachedTree(url)
        title = self.cleanHTML(tree.find('h1').a.string)
        self.photos = list()
        photoNodes = tree.findAll('div', {'class':
                                          re.compile('^wp-caption')})
        for node in photoNodes:
            pic = node.img['src']
            description = self.cleanHTML(node.p.contents)
            self.photos.append({'title': title,
                                'pic': pic,
                                'description': description})
        return self.photos


def register():
    return Scraper()
