import re
import socket
from urllib2 import urlopen, URLError
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup

socket.setdefaulttimeout(15)

class Search:
    def __init__(self):
        return NotImplemented
    def search(terms):
        return NotImplemented

class Mininova(Search):
    def __init__(self):
        self.search_uri = 'http://www.mininova.org/rss/%s'
    def search(self, terms):
        torrents = []
        url = self.search_uri % '+'.join(terms.split(' '))
        f = urlopen(url)
        soup = BeautifulStoneSoup(f.read())
        for item in soup.findAll('item'):
            (seeds, leechers) = re.findall('Ratio: (\d+) seeds, (\d+) leechers', item.description.text)[0]
            torrents.append({
                'url': item.enclosure['url'],
                'name': item.title.text,
                'seeds': int(seeds),
                'leechers': int(leechers),
            })
        return torrents
class TPB(Search):
    def __init__(self):
        self.search_uris = ['http://thepiratebay.se/search/%s/',
                            'http://pirateproxy.net/search/%s/']
    def search(self, terms):
        torrents = []
        f = None
        for url in [u % '+'.join(terms.split(' ')) for u in self.search_uris]:
            try:
                f = urlopen(url)
                break
            except URLError:
                continue
        if not f:
            raise Exception('Out of pirate bay proxies')
        soup = BeautifulSoup(f.read())
        for details in soup.findAll('a', {'class': 'detLink'}):
            name = details.text
            url = details.findNext('a', {'href': re.compile('^magnet:')})['href']
            td = details.findNext('td')
            seeds = int(td.text)
            td = td.findNext('td')
            leechers = int(td.text)
            torrents.append({
                'url': url,
                'name': name,
                'seeds': seeds,
                'leechers': leechers,
            })
        return torrents
class Kickass(Search):
    def __init__(self):
        self.search_uri = 'http://kickass.to/usearch/%s/?field=seeders&sorder=desc&rss=1'
    def search(self, terms):
        torrents = []
        url = self.search_uri % '+'.join(terms.split(' '))
        f = urlopen(url)
        soup = BeautifulStoneSoup(f.read())
        for item in soup.findAll('item'):
            torrents.append({
                'url': item.enclosure['url'],
                'name': item.title.text,
                'seeds': int(item.find('torrent:seeds').text),
                'leechers': int(item.find('torrent:peers').text),
            })
        return torrents

if __name__ == '__main__':
    s = TPB()
    results = s.search('zettai')
