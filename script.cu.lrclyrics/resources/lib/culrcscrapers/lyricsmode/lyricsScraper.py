#-*- coding: UTF-8 -*-
import sys
import urllib
import re
from utilities import *

__title__ = 'lyricsmode'
__priority__ = '220'
__lrc__ = False

class LyricsFetcher:

    def get_lyrics(self, song):
        log('%s: searching lyrics for %s - %s' % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        artist = deAccent(song.artist)
        title = deAccent(song.title)
        url = 'http://www.lyricsmode.com/lyrics/%s/%s/%s.html' % (artist.lower()[:1], artist.lower().replace('&','and').replace(' ','_'), title.lower().replace('&','and').replace(' ','_'))
        result = self.direct_url(url)
        if not result:
            result = self.search_url(artist, title)
        if result:
            lyr = result.split('style="position: relative;">')[1].split('<div')[0]
            lyrics.lyrics = lyr.replace('<br />', '')
            return lyrics

    def direct_url(self, url):
        try:
            log('%s: search url: %s' % (__title__, url))
            song_search = urllib.urlopen(url).read()
            if song_search.find('lyrics_text') >= 0:
                return song_search
        except:
            log('error in direct url')

    def search_url(self, artist, title):
        try:
            url = 'http://www.lyricsmode.com/search.php?search=' + urllib.quote_plus(artist.lower() + ' ' + title.lower())
            song_search = urllib.urlopen(url).read()
            matchcode = re.search('lm-list__cell-title">.*?<a href="(.*?)" class="lm-link lm-link--primary', song_search, flags=re.DOTALL)
            try:
                url = 'http://www.lyricsmode.com' + (matchcode.group(1))
                result = self.direct_url(url)
                if result:
                    return result
            except:
                return
        except:
            log('error in search url')
