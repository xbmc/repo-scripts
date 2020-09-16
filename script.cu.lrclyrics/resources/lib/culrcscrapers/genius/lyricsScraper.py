#-*- coding: UTF-8 -*-
import sys
import re
import urllib2
import socket
import HTMLParser
import xbmc
import xbmcaddon
import json
import difflib
from utilities import *

__title__ = 'genius'
__priority__ = '210'
__lrc__ = False

socket.setdefaulttimeout(10)

class LyricsFetcher:
    def __init__(self):
        self.url = 'http://api.genius.com/search?q=%s%s%s&access_token=Rq_cyNZ6fUOQr4vhyES6vu1iw3e94RX85ju7S8-0jhM-gftzEvQPG7LJrrnTji11'

    def get_lyrics(self, song):
        log('%s: searching lyrics for %s - %s' % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__
        try:
            request = urllib2.Request(self.url % (urllib2.quote(song.artist), '%20', urllib2.quote(song.title)))
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; rv:77.0) Gecko/20100101 Firefox/77.0')
            req = urllib2.urlopen(request)
            response = req.read()
        except:
            return None
        req.close()
        data = json.loads(response)
        try:
            name = data['response']['hits'][0]['result']['primary_artist']['name']
            track = data['response']['hits'][0]['result']['title']
            if (difflib.SequenceMatcher(None, song.artist.lower(), name.lower()).ratio() > 0.8) and (difflib.SequenceMatcher(None, song.title.lower(), track.lower()).ratio() > 0.8):
                self.page = data['response']['hits'][0]['result']['url']
            else:
                return None
        except:
            return None
        log('%s: search url: %s' % (__title__, self.page))
        try:
            request = urllib2.Request(self.page)
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; rv:77.0) Gecko/20100101 Firefox/77.0')
            req = urllib2.urlopen(request)
            response = req.read()
        except:
            return None
        req.close()
        htmlparser = HTMLParser.HTMLParser()
        response = htmlparser.unescape(response.decode('utf-8'))
        matchcode = re.search('<div class="[lL]yrics.*?">(.*?)</div>', response, flags=re.DOTALL)
        try:
            lyricscode = (matchcode.group(1))
            lyr = re.sub('<[^<]+?>', '', lyricscode)
            lyrics.lyrics = lyr.replace('\\n','\n').strip()
            return lyrics
        except:
            return None
