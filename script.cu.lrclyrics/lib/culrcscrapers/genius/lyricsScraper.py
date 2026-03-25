#-*- coding: UTF-8 -*-
import sys
import re
import urllib.parse
import requests
import html
import xbmc
import xbmcaddon
import json
import difflib
from bs4 import BeautifulSoup
from lib.utils import *

__title__ = 'genius'
__priority__ = '200'
__lrc__ = False


class LyricsFetcher:
    def __init__(self, *args, **kwargs):
        self.DEBUG = kwargs['debug']
        self.settings = kwargs['settings']
        self.url = 'https://genius.com/api/search/multi?per_page=5&q=%s %s'

    def get_lyrics(self, song):
        log('%s: searching lyrics for %s - %s' % (__title__, song.artist, song.title), debug=self.DEBUG)
        lyrics = Lyrics(settings=self.settings)
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__
        try:
            headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; rv:77.0) Gecko/20100101 Firefox/77.0'}
            url = self.url % (song.artist, song.title)
            req = requests.get(url, headers=headers, timeout=10)
            response = req.text
        except:
            return None
        data = json.loads(response)
        links = []
        if (len(data['response']['sections']) < 2):
            return None
        for item in data['response']['sections'][1]['hits']:
            try:
                artistname = item['result']['artist_names']
                songtitle = item['result']['title']
                url = item['result']['url']
                if (difflib.SequenceMatcher(None, song.artist.lower(), artistname.lower()).ratio() > 0.8) and (difflib.SequenceMatcher(None, song.title.lower(), songtitle.lower()).ratio() > 0.8):
                    links.append((artistname + ' - ' + songtitle, url, artistname, songtitle))
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
            headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; rv:77.0) Gecko/20100101 Firefox/77.0'}
            req = requests.get(url, headers=headers, timeout=10)
            response = req.text
        except:
            return None
        try:
            matchcode = re.search(r'\\"html\\":\\"(.*?)\\",\\"', response, flags=re.DOTALL)
            if matchcode:
                lyr1 = matchcode.group(1).replace('\\\\\\', '')
                lyr2 = re.sub('<[^<]+?>', '', lyr1)
                lyr3 = lyr2.replace('\\\\n','\n').replace("\\'", "'").strip()
                lyrics = lyr3
                return lyrics
        except:
            return None
