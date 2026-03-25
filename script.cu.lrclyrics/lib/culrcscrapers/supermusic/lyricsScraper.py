#-*- coding: UTF-8 -*-
import sys
import re
import requests
import difflib
import html
import xbmc
import xbmcaddon
from bs4 import BeautifulSoup
from lib.utils import *

__title__ = 'supermusic'
__priority__ = '250'
__lrc__ = False

headers = {}
headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:51.0) Gecko/20100101 Firefox/51.0'


class LyricsFetcher:
    def __init__(self, *args, **kwargs):
        self.DEBUG = kwargs['debug']
        self.settings = kwargs['settings']
        self.SEARCH_URL = 'https://www.supermusic.cz/najdi.php?hladane=%s+%s&typhladania=skupina'
        self.LYRIC_URL = 'https://supermusic.cz/'

    def get_lyrics(self, song):
        log('%s: searching lyrics for %s - %s' % (__title__, song.artist, song.title), debug=self.DEBUG)
        lyrics = Lyrics(settings=self.settings)
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__
        artist = song.artist.lower().replace(' ', '+')
        title = song.title.lower().replace(' ', '+')
        try:
            req = requests.get(self.SEARCH_URL % (artist, title), headers=headers, timeout=10)
            response = req.text
        except:
            return None
        req.close()
        links = []
        soup = BeautifulSoup(response, 'html.parser')
        for item in soup.find_all('div', {'class': 'result-item'}):
            try:
                artistdata = item.find('span', {'class': 'result-artist'})
                songdata = item.find('h3', {'class': 'result-title'})
                artistname = artistdata.find('a').get_text()
                songtitle = songdata.find('a').get_text()
                url = songdata.find('a').get('href')
                if (difflib.SequenceMatcher(None, song.artist.lower(), artistname.lower()).ratio() > 0.8) and (difflib.SequenceMatcher(None, song.title.lower(), songtitle.lower()).ratio() > 0.8):
                    links.append((artistname + ' - ' + songtitle, self.LYRIC_URL + url, artistname, songtitle))
            except:
                continue
        if len(links) == 0:
            return None
        elif len(links) > 1:
            lyrics.list = links
        for link in links:
            lyr = self.get_lyrics_from_list(link)
            if lyr:
                lyrics.lyrics = lyr
                return lyrics
        return None

    def get_lyrics_from_list(self, link):
        title,url,artist,song = link
        log('%s: search url: %s' % (__title__, url), debug=self.DEBUG)
        try:
            response = requests.get(url, headers=headers, timeout=10)
            result = response.text
        except:
            return None
        soup = BeautifulSoup(result, 'html.parser')
        for item in soup.find_all('a', {'class': 'version-tab'}):
            if item.get_text() == 'text':
                newurl = self.LYRIC_URL + item.get('href')
                if newurl != url:
                    try:
                        log('%s: search url: %s' % (__title__, newurl), debug=self.DEBUG)
                        response = requests.get(newurl, headers=headers, timeout=10)
                        result = response.text
                    except:
                        return None
                    soup = BeautifulSoup(result, 'html.parser')
                try:
                    lyr = soup.find('div', {'class': 'chord-text'}).get_text()
                except:
                    return None
                lyrics = lyr
                return lyrics
