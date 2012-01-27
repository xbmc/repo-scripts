from scraper import ScraperPlugin
import re

class Scraper(ScraperPlugin):

    NAME = 'Time.com: LightBox - Closeup'


    def getAlbums(self):
        url = 'http://lightbox.time.com/category/closeup/feed/'
        
        self.albums = list()
        tree = self.getCachedTree(url)
        title = tree.find('title')
        photoNodes = tree.findAll('item')
        for node in photoNodes:
            item_title = self.cleanHTML(node.find('title'))
            title = item_title
            pic = node.find('large_image').string
            link = node.find('guid').string
            ugly_desc = node.find(re.compile('description')).string
            description = self.cleanHTML(ugly_desc.encode('utf-8'))
            self.albums.append({'title': title,
                                'pic': pic,
                                'description': description,
                                'link': link})
        return self.albums

    def getPhotos(self, url):
        self.photos = list()
        tree = self.getCachedTree(url)
        js_code = tree.find('text/javascript', text=re.compile('var images'))
        js_var = re.search('var images = \[(.*)\]', js_code).group(1)
        nodes = re.findall('{([^}]*?)}', js_var)
        pic_regex = re.compile('"fullscreen":"(.*?)"')
        desc_regex = re.compile('"post_content":"(.*?)"')
        title_regex = re.compile('"post_title":"(.*?)"')
        for node in nodes:
            try:
                pic = re.search(pic_regex, node).group(1).replace('\/', '/')
                ugly_title = re.search(title_regex, node).group(1)
                if ugly_title.endswith('\\'):  # fix python bug
                    ugly_title = ugly_title[:-1]
                title = ugly_title.decode('unicode-escape')
                ugly_desc = re.search(desc_regex, node).group(1)
                if ugly_desc.endswith('\\'):  # fix python bug
                    ugly_desc = ugly_desc[:-1]
                description = ugly_desc.decode('unicode-escape')
                self.photos.append({'title': title,
                                    'pic': pic,
                                    'description': description})
            except:
                pass
        return self.photos


def register():
    return Scraper()
