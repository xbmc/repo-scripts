#-*- coding: UTF-8 -*-
"""
Scraper for https://xiami.com

Taxigps
"""

import urllib
import urllib2
import socket
import re
import difflib
import chardet
from utilities import *

__title__ = "Xiami"
__priority__ = '110'
__lrc__ = True

UserAgent = 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:51.0) Gecko/20100101 Firefox/51.0'

socket.setdefaulttimeout(10)

class LyricsFetcher:
    def __init__( self ):
        self.LIST_URL = 'https://www.xiami.com/search?key=%s'
        self.SONG_URL = 'https://www.xiami.com/song/playlist/id/%s/object_name/default/object_id/0'

    def get_lyrics(self, song):
        log( "%s: searching lyrics for %s - %s" % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__
        keyword = "%s %s" % (song.title, song.artist)
        url = self.LIST_URL % (urllib.quote(keyword))
        try:
            request = urllib2.Request(url)
            request.add_header('User-Agent', UserAgent)
            request.add_header('Referer', 'https://www.xiami.com/play')
            response = urllib2.urlopen(request)
            result = response.read()
        except:
            log( "%s: %s::%s (%d) [%s]" % (
                   __title__, self.__class__.__name__,
                   sys.exc_info()[ 2 ].tb_frame.f_code.co_name,
                   sys.exc_info()[ 2 ].tb_lineno,
                   sys.exc_info()[ 1 ]
                   ))
            return None
        match = re.compile('<td class="chkbox">.+?value="(.+?)".+?href="//www.xiami.com/song/[^"]+" title="([^"]+)".*?href="//www.xiami.com/artist/[^"]+" title="([^"]+)"', re.DOTALL).findall(result)
        links = []
        for x in match:
            title = x[1]
            artist = x[2]
            if (difflib.SequenceMatcher(None, song.artist.lower(), artist.lower()).ratio() > 0.8) and (difflib.SequenceMatcher(None, song.title.lower(), title.lower()).ratio() > 0.8):
                links.append( ( artist + ' - ' + title, x[0], artist, title ) )
        if len(links) == 0:
            return None
        elif len(links) > 1:
            lyrics.list = links
        lyr = self.get_lyrics_from_list(links[0])
        if not lyr:
            return None
        lyrics.lyrics = lyr
        return lyrics

    def get_lyrics_from_list(self, link):
        title,id,artist,song = link
        try:
            request = urllib2.Request(self.SONG_URL % (id))
            request.add_header('User-Agent', UserAgent)
            request.add_header('Referer', 'https://www.xiami.com/play')
            response = urllib2.urlopen(request)
            data = response.read()
            url = re.compile('<lyric>(.+?)</lyric>').search(data).group(1)
            request = urllib2.Request('https:%s' % url)
            request.add_header('User-Agent', UserAgent)
            request.add_header('Referer', 'https://www.xiami.com/play')
            response = urllib2.urlopen(request)
            lyrics = response.read()
        except:
            log( "%s: %s::%s (%d) [%s]" % (
                   __title__, self.__class__.__name__,
                   sys.exc_info()[ 2 ].tb_frame.f_code.co_name,
                   sys.exc_info()[ 2 ].tb_lineno,
                   sys.exc_info()[ 1 ]
                   ))
            return
        enc = chardet.detect(lyrics)
        lyrics = lyrics.decode(enc['encoding'], 'ignore')
        return lyrics
