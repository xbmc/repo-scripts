#-*- coding: UTF-8 -*-
'''
Scraper for https://syair.info/
'''

import os
import socket
import requests
import re
import difflib
from bs4 import BeautifulSoup
from utilities import *

__title__ = "Syair"
__priority__ = '140'
__lrc__ = True

UserAgent = 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:51.0) Gecko/20100101 Firefox/51.0'

socket.setdefaulttimeout(10)

class LyricsFetcher:
    def __init__(self):
        self.SEARCH_URL = 'https://syair.info/search?q=%s'
        self.LYRIC_URL = 'https://syair.info%s'

    def get_lyrics(self, song):
        log("%s: searching lyrics for %s - %s" % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__
        search_artist = song.artist.replace(' ', '-')
        search_title = song.title.replace(' ', '-')
        search = '%s-%s' % (search_artist, search_title)
        try:
            url = self.SEARCH_URL % search
            req = requests.get(url, headers={"User-Agent": UserAgent})
            Page = req.text
        except:
            return None
        links = []
        soup = BeautifulSoup(Page, 'html.parser')
        for link in soup.find_all('a'):
            if link.get('href').startswith('/lyrics/'):
                try:
                    artist, title = link.string.rstrip('.lrc').split(' - ', 1)
                except:
                    continue
                if (difflib.SequenceMatcher(None, song.artist.lower(), artist.lower()).ratio() > 0.8) and (difflib.SequenceMatcher(None, song.title.lower(), title.lower()).ratio() > 0.8):
                    links.append((link.string, self.LYRIC_URL % link.get('href'), artist, title))
        if len(links) == 0:
            return None
        lyrics.list = links
        lyr = self.get_lyrics_from_list(links[0])
        if lyr:
            lyrics.lyrics = lyr
            return lyrics
        return None

    def get_lyrics_from_list(self, link):
        title,url,artist,song = link
        try:
            log('%s: search url: %s' % (__title__, url))
            req = requests.get(url, headers={"User-Agent": UserAgent})
            Page = req.text
        except:
            return None
        lyricdata = re.search('</a></p>(.*?)<div', Page, re.DOTALL)
        if not lyricdata:
            return
        lyrics = lyricdata.group(1).replace('<br>', '')
        return lyrics
