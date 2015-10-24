#-*- coding: UTF-8 -*-
import sys, re, urllib2, socket, HTMLParser
import xbmc, xbmcaddon
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson
from utilities import *

__title__ = 'genius'
__priority__ = '210'
__lrc__ = False

socket.setdefaulttimeout(10)

class LyricsFetcher:
    def __init__( self ):
        self.url = 'http://api.genius.com/search?q=%s%s%s&access_token=Rq_cyNZ6fUOQr4vhyES6vu1iw3e94RX85ju7S8-0jhM-gftzEvQPG7LJrrnTji11'

    def get_lyrics(self, song):
        log( "%s: searching lyrics for %s - %s" % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__
        try:
            request = urllib2.Request(self.url % (urllib2.quote(song.artist), '%20', urllib2.quote(song.title)))
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:25.0) Gecko/20100101 Firefox/25.0')
            req = urllib2.urlopen(request)
            response = req.read()
        except:
            return None
        req.close()
        data = simplejson.loads(response)
        try:
            self.page = data['response']['hits'][0]['result']['url']
        except:
            return None
        log( "%s: search url: %s" % (__title__, self.page))
        try:
            request = urllib2.Request(self.page)
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:25.0) Gecko/20100101 Firefox/25.0')
            req = urllib2.urlopen(request)
            response = req.read()
        except:
            return None
        req.close()
        matchcode = re.search('div class="lyrics".*?">(.*?)</div', response, flags=re.DOTALL)
        try:
            lyricscode = (matchcode.group(1))
            htmlparser = HTMLParser.HTMLParser()
            lyricstext = htmlparser.unescape(lyricscode).replace('<br />', '\n')
            templyr = re.sub('<[^<]+?>', '', lyricstext)
            lyr = re.sub('\[(.*?)\]', '', templyr)
            lyrics.lyrics = lyr.strip().replace('\n\n\n', '\n\n')
            return lyrics
        except:
            return None
