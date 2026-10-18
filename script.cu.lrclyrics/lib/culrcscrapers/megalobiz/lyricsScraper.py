#-*- coding: UTF-8 -*-
'''
Scraper for https://www.megalobiz.com/

megalobiz

https://github.com/rtcq/syncedlyrics
'''

import json
import requests
import difflib
from bs4 import BeautifulSoup
from lib.utils import *

__title__ = "Megalobiz"
__priority__ = '140'
__lrc__ = True

def convert_ms(ms):
    minutes = (ms // 1000) // 60
    seconds = (ms // 1000) % 60
    milliseconds = ms % 1000 // 10
    return f"[{minutes:02d}:{seconds:02d}:{milliseconds:02d}]"

class LyricsFetcher:
    def __init__(self, *args, **kwargs):
        self.DEBUG = kwargs['debug']
        self.settings = kwargs['settings']
        self.SEARCH_URL = 'https://api.megalobiz.com/api/v1/lrcs?page=1&pageSize=20&search=%s %s'
        self.MAIN_URL = 'https://megalobiz.com/'
        self.LYRIC_URL = 'https://www.megalobiz.com/%s'
        self.TOKEN_URL = 'https://megalobiz.com%s'

    def get_lyrics(self, song):
        log("%s: searching lyrics for %s - %s" % (__title__, song.artist, song.title), debug=self.DEBUG)
        lyrics = Lyrics(settings=self.settings)
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__
        # find the token file in the header. not sure if the order of the .js files changes over time...
        try:
            response = requests.get(self.MAIN_URL, timeout=10)
            result = response.text
        except:
            return None
        soup = BeautifulSoup(result, 'html.parser')
        js_urls = [script['src'] for script in soup.find_all('script') if script.has_attr('src')]
        #currently the fifth link in the header is the one we need
        try:
            response = requests.get(self.TOKEN_URL % js_urls[4], timeout=10)
            result = response.text
        except:
            return None
        tokencode = re.search('api/v1",[a-z]="(.*?)",', result, flags=re.DOTALL)
        if tokencode:
            token = 'Bearer %s' % tokencode.group(1)
        else:
            return None
        headers = {"Authorization": token}
        # get the lyrics list
        try:
            url = self.SEARCH_URL % (song.artist, song.title)
            response = requests.get(url, headers=headers, timeout=10)
            result = response.json()
        except:
            return None
        links = []
        if not 'models' in result:
            return None
        for item in result["models"]:
            try:
                artistname = item['title'].split(' - ')[0].strip()
                songtitle = item['title'].split(' - ')[1].strip()
            except:
                try:
                    artistname = item['title'].split('-')[0].strip()
                    songtitle = item['title'].split('-')[1].strip()
                except:
                    continue
            #quick check if the lyrics are valid
            validlines = False
            for line in item['content']['lines']:
                if 'time' not in line: # skip partially synchronized lyrics
                    validlines = False
                    break
                elif line['time'] == 0:  # either the song has no timestamps, or has only 1 line of text starting at 0 (false possitive, too bad)
                    continue
                elif line['time'] == 0 and line['text'].startswith('('): # skip lines like (verse) or (chorus) which have no timestamp attached to them
                    continue
                validlines = True
            if validlines:
                if (difflib.SequenceMatcher(None, song.artist.lower(), artistname.lower()).ratio() > 0.8) and (difflib.SequenceMatcher(None, song.title.lower(), songtitle.lower()).ratio() > 0.8):
                    lyr = ''
                    for line in item['content']['lines']:
                        if line['time'] == 0 and line['text'].startswith('('):
                            continue
                        else:
                            linetime =  line['time']
                            linetext = line['text']
                            timestamp = convert_ms(linetime)
                            lyr = lyr + timestamp + ' ' + linetext + '\n'
                    links.append((artistname + ' - ' + songtitle, lyr, artistname, songtitle))
        if len(links) == 0:
            return None
        elif len(links) > 1:
            lyrics.list = links
        # get the lyrics
        for link in links:
            lyr = self.get_lyrics_from_list(link)
            if lyr:
                lyrics.lyrics = lyr
                return lyrics
        return None

    def get_lyrics_from_list(self, link):
        title,lyr,artist,song = link
        return lyr
