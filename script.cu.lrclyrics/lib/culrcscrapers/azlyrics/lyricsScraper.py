#-*- coding: UTF-8 -*-
import sys
import re
import requests
import html
import difflib
from bs4 import BeautifulSoup
import xbmc
import xbmcaddon
from lib.utils import *

__title__ = 'azlyrics'
__priority__ = '230'
__lrc__ = False


class LyricsFetcher:
    def __init__(self, *args, **kwargs):
        self.DEBUG = kwargs['debug']
        self.settings = kwargs['settings']
        self.jsurl = 'https://www.azlyrics.com/geo.js'
        self.url = 'https://www.azlyrics.com/search/?q=%s+-+%s&x=%s'

    def get_lyrics(self, song):
        log('%s: searching lyrics for %s - %s' % (__title__, song.artist, song.title), debug=self.DEBUG)
        lyrics = Lyrics(settings=self.settings)
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__
        artist = re.sub("[^a-zA-Z0-9]+", "+", song.artist).lower().lstrip('the ')
        title = re.sub("[^a-zA-Z0-9]+", "+", song.title).lower()
        #get hidden value 
        try:
            headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0'}
            req = requests.get(self.jsurl, headers=headers, timeout=10)
            response = req.text
        except:
            return None
        match = re.search(r'"value", "(.*?)"', response, re.IGNORECASE)
        if match:
            tag = match.group(1)
        else:
            return None
        #get result list
        try:
            headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0'}
            req = requests.get(self.url % (artist, title, tag), headers=headers, timeout=10)
            response = req.text
        except:
            return None
        #get lyrics
        soup = BeautifulSoup(response, 'html.parser')
        lyriclist = soup.find_all('a')
        url = ''
        for item in lyriclist:
            if item.get('href', '').startswith("https://www.azlyrics.com/lyrics/"):
                songdata = item.find_all('b')
                artistname = songdata[1].get_text()
                songtitle = songdata[0].get_text()[1:-1]
                if (difflib.SequenceMatcher(None, song.artist.lower(), artistname.lower()).ratio() > 0.8) and (difflib.SequenceMatcher(None, song.title.lower(), songtitle.lower()).ratio() > 0.8):
                    url = item.get('href')
                    break #only use first result, do not create a list
        if url == '':
            return None
        try:
            headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0'}
            req = requests.get(url, headers=headers, timeout=10)
            response = req.text
        except:
            return None
        try:
            lyricscode = response.split('t. -->')[1].split('</div')[0]
            lyricstext = html.unescape(lyricscode).replace('<br />', '\n')
            lyr = re.sub('<[^<]+?>', '', lyricstext)
            lyrics.lyrics = lyr
            return lyrics
        except:
            return None
