#-*- coding: UTF-8 -*-
'''
Scraper for http://www.darklyrics.com/ - the largest metal lyrics archive on the Web.

smory
'''

import hashlib
import math
import urllib2
import re
import requests
import time
from utilities import *

__title__ = 'darklyrics'
__priority__ = '250';
__lrc__ = False;

class LyricsFetcher:
    
    def __init__(self):
        self.base_url = 'http://www.darklyrics.com/'
        self.searchUrl = 'http://www.darklyrics.com/search?q=%s'
        self.cookie = self.getCookie()

    def getCookie(self):
         # http://www.darklyrics.com/tban.js
         lastvisitts = str(int(math.ceil(time.time() * 1000 / (60 * 60 * 6 * 1000))))
         lastvisittscookie = 0
         for i in range(len(lastvisitts)):
             lastvisittscookie = ((lastvisittscookie << 5) - lastvisittscookie) + ord(lastvisitts[i])
             lastvisittscookie = lastvisittscookie & lastvisittscookie
         return str(lastvisittscookie)
        
    def search(self, artist, title):
        term = urllib2.quote((artist if artist else '') + '+' + (title if title else ''));
        
        try:
            headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0'}
            req = requests.get(self.searchUrl % term, headers=headers, cookies={'lastvisitts': self.cookie}, timeout=10)
            searchResponse = req.text
        except:
            return None

        searchResult = re.findall('<h2><a\shref="(.*?#([0-9]+))".*?>(.*?)</a></h2>', searchResponse);
        
        if len(searchResult) == 0:
            return None;
        
        links = [];
        
        i = 0;
        for result in searchResult:
            a = [];
            a.append(result[2] + (' ' + self.getAlbumName(self.base_url + result[0]) if i < 6 else '')); # title from server + album nane
            a.append(self.base_url + result[0]);  # url with lyrics
            a.append(artist);
            a.append(title);
            a.append(result[1]); # id of the side part containing this song lyrics
            links.append(a);
            i += 1;
            
        return links;
    
    def findLyrics(self, url, index):
        try:
            headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0'}
            req = requests.get(url, headers=headers, cookies={'lastvisitts': self.cookie}, timeout=10)
            res = req.text
        except:
            return None
        
        pattern = '<a\sname="%index%">(.*?)(?:<h3>|<div)';  # require multi line and dot all mode
        pattern = pattern.replace('%index%', index);
        
        match = re.search(pattern, res, re.MULTILINE | re.DOTALL);
        if match:  
            s = match.group(1);
            s = s.replace('<br />', '');
            s = s.replace('<i>', '');
            s = s.replace('</i>', '');
            s = s.replace('</a>', '');
            s = s.replace('</h3>', '');
            return s;
        else:
            return None;
        
    def getAlbumName(self, url):
        try:
            headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0'}
            req = requests.get(url, headers=headers, cookies={'lastvisitts': self.cookie}, timeout=10)
            res = req.text
        except:
            return ''
             
        match = re.search('<h2>(?:album|single|ep|live):?\s?(.*?)</h2>', res, re.IGNORECASE);
        
        if match:
            return ('(' + match.group(1) + ')').replace('\'', '');
        else:
            return '';        

    def get_lyrics(self, song):
        log('%s: searching lyrics for %s - %s' % (__title__, song.artist, song.title))
        lyrics = Lyrics();
        lyrics.song = song;
        lyrics.source = __title__;
        lyrics.lrc = __lrc__;
        
        links = self.search(song.artist , song.title);
        
        if(links == None or len(links) == 0):
            return None;
        elif len(links) > 1:
            lyrics.list = links
        
        lyr = self.get_lyrics_from_list(links[0])
        if not lyr:
            return None
        lyrics.lyrics = lyr
        return lyrics;

    def get_lyrics_from_list(self, link):
        title, url, artist, song, index = link;
        return self.findLyrics(url, index);
