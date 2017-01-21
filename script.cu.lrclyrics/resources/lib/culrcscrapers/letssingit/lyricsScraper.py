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
        self.url = 'http://search.letssingit.com/?a=search&s=%s'

    def get_lyrics(self, song):
        log('%s: searching lyrics for %s - %s' % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__
        query = '%s+lyrics+%s' % (urllib.quote_plus(song.artist), urllib.quote_plus(song.title))
        try:
            request = urllib2.urlopen(self.url % query)
            response = request.read()
        except:
            return
        request.close()
        matchcode = re.search('</TD><TD><A href="(.*?)"', response)
        if matchcode:
            lyricscode = (matchcode.group(1))
            result = lyricscode.lstrip('http://www.letssingit.com/').rsplit('-',1)[0]
            if (difflib.SequenceMatcher(None, query.lower().replace('+', ''), result.lower().replace('-', '')).ratio() > 0.8):
                try:
                    req = urllib2.urlopen(lyricscode)
                    resp = req.read()
                except:
                    return
                match = re.search('id=lyrics>(.*?)<DIV', resp, flags=re.DOTALL)
                if match:
                    lyrics.lyrics = match.group(1).replace('<BR>', '')
                    return lyrics
