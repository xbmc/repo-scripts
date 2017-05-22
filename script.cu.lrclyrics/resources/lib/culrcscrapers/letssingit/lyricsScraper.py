#-*- coding: UTF-8 -*-
import re
import urllib
import urllib2
import socket
import difflib
from utilities import *

__title__ = 'letssingit'
__priority__ = '230'
__lrc__ = False


socket.setdefaulttimeout(10)

class LyricsFetcher:
    def __init__(self):
        self.url = 'https://search.letssingit.com/?a=search&s=%s'

    def get_lyrics(self, song):
        log('%s: searching lyrics for %s - %s' % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__
        query = '%s+lyrics+%s' % (urllib.quote_plus(song.artist), urllib.quote_plus(song.title))
        try:
            request = urllib2.Request(self.url % query)
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:25.0) Gecko/20100101 Firefox/25.0')
            req = urllib2.urlopen(request)
            response = req.read()
        except:
            return
        req.close()
        matchcode = re.search('</TD><TD><A href="(.*?)"', response)
        if matchcode:
            lyricscode = (matchcode.group(1))
            result = lyricscode.lstrip('http://www.letssingit.com/').rsplit('-',1)[0]
            if (difflib.SequenceMatcher(None, query.lower().replace('+', ''), result.lower().replace('-', '')).ratio() > 0.8):
                try:
                    request = urllib2.Request(lyricscode)
                    request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:25.0) Gecko/20100101 Firefox/25.0')
                    req = urllib2.urlopen(request)
                    resp = req.read()
                except:
                    return
                req.close()
                match = re.search('id=lyrics style="display:table-cell;vertical-align:top;">(.*?)<DIV', resp, flags=re.DOTALL)
                if match:
                    lyrics.lyrics = match.group(1).replace('<BR>', '')
                    return lyrics
