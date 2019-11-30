#-*- coding: UTF-8 -*-
import re
import urllib
import urllib2
import socket
import difflib
from bs4 import BeautifulSoup
from utilities import *

__title__ = 'lyricscom'
__priority__ = '240'
__lrc__ = False


socket.setdefaulttimeout(10)

class LyricsFetcher:
    def __init__(self):
        self.url = 'http://www.lyrics.com/serp.php?st=%s&qtype=2'

    def get_lyrics(self, song):
        log('%s: searching lyrics for %s - %s' % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__
        try:
            request = urllib2.urlopen(self.url % urllib.quote_plus(song.artist))
            response = request.read()
        except:
            return
        request.close()
        soup = BeautifulSoup(response, 'html.parser')
        url = ''
        for link in soup.find_all('a'):
            if link.string and link.get('href').startswith('artist/'):
                url = 'http://www.lyrics.com/' + link.get('href')
                break
        if url:
            try:
                req = urllib2.urlopen(url)
                resp = req.read()
            except:
                return
            req.close()
            soup = BeautifulSoup(resp, 'html.parser')
            url = ''
            for link in soup.find_all('a'):
                if link.string and (difflib.SequenceMatcher(None, link.string.lower(), song.title.lower()).ratio() > 0.8):
                    url = 'http://www.lyrics.com' + link.get('href')
                    break
            if url:
                try:
                    req2 = urllib2.urlopen(url)
                    resp2 = req2.read()
                except:
                    return
                req2.close()
                matchcode = re.search('<pre.*?>(.*?)</pre>', resp2, flags=re.DOTALL)
                if matchcode:
                    lyricscode = (matchcode.group(1))
                    lyr = re.sub('<[^<]+?>', '', lyricscode)
                    lyrics.lyrics = lyr.replace('\\n','\n')
                    return lyrics
