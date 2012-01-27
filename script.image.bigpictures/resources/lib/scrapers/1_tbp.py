from scraper import ScraperPlugin
import re


class Scraper(ScraperPlugin):

    NAME = 'Boston.com: The Big Picture'

    def getFilters(self, url):
        tree = self.getCachedTree(url)
        self.months = list()
        self.categories = list()
        optionNodes = tree.findAll('option', value=re.compile('.+?'))
        for node in optionNodes:
            if node.parent.option.contents[0] == 'Select a month':
                self.months.append([node.string, node['value']])
            elif node.parent.option.contents[0] == 'Select a category':
                self.categories.append([node.string, node['value']])

    def getAlbums(self):
        url = 'http://www.boston.com/bigpicture/'
        tree = self.getCachedTree(url)
        self.albums = list()
        storyNodes = tree.findAll('div', 'headDiv2')
        for node in storyNodes:
            try:
                title = node.find('a').string
                link = node.find('a')['href']
                desc_raw = node.find('div',
                                     attrs={'class': 'bpBody'}).contents
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
        referer = 'http://www.boston.com/bigpicture/'
        tree = self.getCachedTree(url, referer)
        title = tree.find('h2').a.string
        self.photos = list()
        photoNodes = tree.findAll('div', {'class':
                                          re.compile('bpImageTop|bpBoth')})
        for node in photoNodes:
            pic = node.img['src']
            if node.find('div', 'photoNum'):
                node.find('div', 'photoNum').replaceWith('')
            description = self.cleanHTML(node.find('div',
                                                   'bpCaption').contents)
            self.photos.append({'title': title,
                                'pic': pic,
                                'description': description})
        return self.photos


def register():
    return Scraper()
