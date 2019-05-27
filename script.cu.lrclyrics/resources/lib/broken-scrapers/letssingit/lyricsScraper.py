#-*- coding: UTF-8 -*-
import re
import urllib
import requests
import socket
import difflib
from utilities import *

__title__ = 'letssingit'
__priority__ = '230'
__lrc__ = False


socket.setdefaulttimeout(10)

class LyricsFetcher:
    def __init__(self):
        self.url = 'https://search.letssingit.com/?s=%s&a=search&l=archive'
        self.rqs = requests.Session()

    def get_lyrics(self, song):
        log('%s: searching lyrics for %s - %s' % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__
        query = '%s+%s' % (urllib.quote_plus(song.artist), urllib.quote_plus(song.title))
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:59.0) Gecko/20100101 Firefox/59.0'}
            request = self.rqs.get(self.url % query, headers=headers, cookies={'cookieconsent':'1'})
            response = request.text
        except:
            return
        matchcode = re.search('</td><td><a href="(.*?)"', response)
        if matchcode:
            lyricscode = (matchcode.group(1))
            clean = lyricscode.lstrip('http://www.letssingit.com/').rsplit('-',1)[0]
            result = clean.replace('-lyrics-', ' ')
            if (difflib.SequenceMatcher(None, query.lower().replace('+', ''), result.lower().replace('-', '')).ratio() > 0.8):
                try:
                    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:59.0) Gecko/20100101 Firefox/59.0'}
                    request = self.rqs.get(lyricscode, headers=headers, cookies={'cookieconsent':'1'})
                    resp = request.text
                except:
                    return
                match = re.search('id=lyrics>(.*?)<div i', resp, flags=re.DOTALL)
                if match:
                    lyrics.lyrics = match.group(1).replace('<br>', '')
                    return lyrics
