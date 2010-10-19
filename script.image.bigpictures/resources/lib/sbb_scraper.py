import urllib2
import re
import sys
from BeautifulSoup import BeautifulSoup

scriptName = sys.modules['__main__'].__scriptname__


class SBB:

    def getHTML(self, url, headers = [('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.14) Gecko/20080404 Firefox/2.0.0.14')]):
        """Returns HTML from a given URL"""
        opener = urllib2.build_opener()
        opener.addheaders = headers
        try:
            print '[SCRIPT][%s] %s attempting to open %s' % (scriptName, __name__, url)
            usock = opener.open(url)
            response = usock.read()
            usock.close()
            return response
        except urllib2.HTTPError, error:
            print '[SCRIPT][%s] %s error opening %s' % (scriptName, __name__, url)
            print error.msg, error.code, error.geturl()
            try:
                import xbmcgui
                xbmcgui.Dialog().ok(error.msg, '%s\n%s' % (error.code, error.geturl()))
            except:
                pass

    def cleanHTML(self, s):
        """The 2nd half of this removes HTML tags.
        The 1st half deals with the fact that beautifulsoup sometimes spits
        out a list of NavigableString objects instead of a regular string.
        This only happens when there are HTML elements, so it made sense to
        fix both problems in the same function."""
        tmp = list()
        for ns in s:
            tmp.append(str(ns))
        s = ''.join(tmp)
        s = re.sub('\s+', ' ', s) #remove extra spaces
        s = re.sub('<.+?>|Image:.+?\r|\r', '', s) #remove htmltags, image captions, & newlines
        s = s.replace('&#39;', '\'') #replace html-encoded double-quotes
        s = s.strip()
        return s

    def getAlbums(self, url):
        """creates an ordered list albums = [{title, pic, description, link}, ...]"""
        tree = BeautifulSoup(self.getHTML(url))
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
        tree = BeautifulSoup(self.getHTML(url))
        title = tree.find('div', 'asset-name entry-title title').a.string
        self.photos = list()
        subtree_img = tree.findAll('div', attrs={'style': 'background: rgb(224, 224, 224); width: 982px; padding: 4px;'})
        subtree_txt = tree.findAll('div', attrs={'style': 'background: rgb(224, 224, 224); width: 970px; padding: 10px;'})
        # this is very dirty because this website is very dirty :(
        for i, node_img in enumerate(subtree_img):
            print i
            pic = node_img.find('img')['src']
            try:
                description = self.cleanHTML(subtree_txt[i])
            except:
                description = ''
            self.photos.append({'title': title, 'pic': pic, 'description': description})
