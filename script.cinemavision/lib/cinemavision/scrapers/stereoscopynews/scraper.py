import urllib2
import re

url = 'http://www.stereoscopynews.com/references-links-books/3d-videos/1633-3d-movies-trailers.html'
regex_pageLink = '"(/references-links-books/3d-videos/\d+-[^"]+)"'
regex_youtubeID_title = '(?s)<a href="https://www.youtube.com/embed/([^?]+)\?[^>]*?title="([^"]+?) \d\d:\d\d[^>]*?>'


def getTrailers():
    first = urllib2.urlopen(url).read()

    ret = []
    for link in set(re.findall(regex_pageLink, first)):
        html = urllib2.urlopen('http://www.stereoscopynews.com{0}'.format(link)).read()
        for ID, title in re.findall(regex_youtubeID_title, html):
            ret.append({'ID': ID, 'title': title})

    return ret
