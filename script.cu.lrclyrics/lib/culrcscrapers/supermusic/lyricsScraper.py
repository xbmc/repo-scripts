#-*- coding: UTF-8 -*-
import sys
import re
import requests
import difflib
import html
import time
import xbmc
import xbmcaddon
from bs4 import BeautifulSoup
from lib.utils import *

__title__ = 'supermusic'
__priority__ = '250'
__lrc__ = False

headers = {}
headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:51.0) Gecko/20100101 Firefox/51.0'

def fnv(s: str) -> int:
    # 32-bit FNV-1a offset basis
    h = 0x811c9dc5    
    for char in s:
        h ^= ord(char)
        # Replicating JavaScript's 32-bit integer addition overflow
        h = (h + (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24)) & 0xFFFFFFFF
    return h


class LyricsFetcher:
    def __init__(self, *args, **kwargs):
        self.DEBUG = kwargs['debug']
        self.settings = kwargs['settings']
        self.SEARCH_URL = 'https://www.supermusic.cz/najdi.php?hladane=%s+%s'
        self.LYRIC_URL = 'https://www.supermusic.cz/'

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
                lyricstype = item.find('span', {'class': 'result-song-type'}).get_text() 
                if lyricstype != 'text':
                    continue
                artistdata = item.find('span', {'class': 'result-artist'})
                songdata = item.find('h3', {'class': 'result-title'})
                artistname = artistdata.find('a').get_text()
                songtitle = songdata.find('a').get_text()
                url = songdata.find('a').get('href').replace('?id=', '?idpiesne=')
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
        #get token
        try:
            response = requests.get(url, headers=headers, timeout=10)
            result = response.text
        except:
            return None
        match = re.search(r'data-n="(.*?)"', result, re.IGNORECASE)
        if match:
            nonce = match.group(1)
        else:
            return None
        match = re.search(r'data-l="(.*?)"', result, re.IGNORECASE)
        if match:
            limit = int(match.group(1), 10)
        else:
            return None
        match = re.search(r'data-t="(.*?)"', result, re.IGNORECASE)
        if match:
            token = match.group(1)
        else:
            return None
        if limit < 1:
            return None
        i = 0
        starttime = time.time()
        while i < 100000000:
            if fnv(f"{nonce}:{i}") < limit:
                break
            i += 1
            endtime = time.time()
            if endtime - starttime > 10: # this will never happen, but guard us just in case
                return None
        #get lyrics
        try:
            response = requests.get(url + '&_smc=%s' % token + '.' + str(i), headers=headers, timeout=10)
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
