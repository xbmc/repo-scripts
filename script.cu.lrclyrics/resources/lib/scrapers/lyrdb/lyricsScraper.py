# -*- Mode: python; coding: utf-8; tab-width: 8; indent-tabs-mode: t; -*-
"""
Scraper for http://www.lyrdb.com/

taxigps
"""

import os
import urllib
import socket
import re
import difflib
from utilities import *

__title__ = "Lyrdb"
__priority__ = '150'
__lrc__ = True

socket.setdefaulttimeout(30)

class LyricsFetcher:
    def __init__( self ):
        self.base_url = "http://www.lyrdb.com/karaoke/"

    def get_lyrics(self, song):
        log( "%s: searching lyrics for %s - %s" % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__

        try:
            url = 'http://www.lyrdb.com/karaoke/?q=%s+%s&action=search' %(song.artist.replace(' ','+').lower(), song.title.replace(' ','+').lower())
            f = urllib.urlopen(url)
            Page = f.read()
        except:
            log( "%s: %s::%s (%d) [%s]" % (
                   __title__, self.__class__.__name__,
                   sys.exc_info()[ 2 ].tb_frame.f_code.co_name,
                   sys.exc_info()[ 2 ].tb_lineno,
                   sys.exc_info()[ 1 ]
                   ))
            return None

        links_query = re.compile('<tr><td class="tresults"><a href="/karaoke/([0-9]+).htm">(.*?)</td><td class="tresults">(.*?)</td>')
        urls = re.findall(links_query, Page)
        links = []
        for x in urls:
            if (difflib.SequenceMatcher(None, song.artist.lower(), x[2].lower()).ratio() > 0.8) and (difflib.SequenceMatcher(None, song.title.lower(), x[1].lower()).ratio() > 0.8):
                links.append( ( x[2] + ' - ' + x[1], x[0], x[2], x[1] ) )
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
        title,Id,artist,song = link
        log('%s %s %s' %(Id, artist, song))
        try:
            url = 'http://www.lyrdb.com/karaoke/downloadlrc.php?q=%s' %(Id)
            f = urllib.urlopen(url)
            Page = f.read()
        except:
            log( "%s: %s::%s (%d) [%s]" % (
                   __title__, self.__class__.__name__,
                   sys.exc_info()[ 2 ].tb_frame.f_code.co_name,
                   sys.exc_info()[ 2 ].tb_lineno,
                   sys.exc_info()[ 1 ]
                   ))
            return None
        return Page
