#-*- coding: UTF-8 -*-
import sys
import re
import requests
import socket
from html.parser import HTMLParser
import xbmc
import xbmcaddon
from lib.utils import *

__title__ = 'azlyrics'
__priority__ = '240'
__lrc__ = False


socket.setdefaulttimeout(10)

class LyricsFetcher:
    def __init__(self):
        self.url = 'https://www.azlyrics.com/lyrics/%s/%s.html'

    def get_lyrics(self, song):
        log('%s: searching lyrics for %s - %s' % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__
        artist = re.sub("[^a-zA-Z0-9]+", "", song.artist).lower().lstrip('the ')
        title = re.sub("[^a-zA-Z0-9]+", "", song.title).lower()
        try:
            req = requests.get(self.url % (artist, title))
            response = req.text
        except:
            return None
        req.close()
        try:
            lyricscode = response.split('. -->')[1].split('</div')[0]
            htmlparser = HTMLParser()
            lyricstext = htmlparser.unescape(lyricscode).replace('<br />', '\n')
            lyr = re.sub('<[^<]+?>', '', lyricstext)
            lyrics.lyrics = lyr
            return lyrics
        except:
            return None
