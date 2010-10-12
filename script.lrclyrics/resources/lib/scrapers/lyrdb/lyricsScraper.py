# -*- Mode: python; coding: utf-8; tab-width: 8; indent-tabs-mode: t; -*-
"""
Scraper for http://www.lyrdb.com/

taxigps
"""

import os
import urllib
import re
import random
import codecs

__title__ = "lyrdb.com"
__allow_exceptions__ = False

class LyricsFetcher:
    def __init__( self ):
        self.base_url = "http://www.lyrdb.com/karaoke/"

    def get_lyrics(self, artist, song):
        url = 'http://www.lyrdb.com/karaoke/?q=%s+%s&action=search' %(artist.replace(' ','+').lower(), song.replace(' ','+').lower())
        f = urllib.urlopen(url)
        Page = f.read()

        links_query = re.compile('<tr><td class="tresults"><a href="/karaoke/([0-9]+).htm">(.*?)</td><td class="tresults">(.*?)</td>')
        urls = re.findall(links_query, Page)
        links = []
        for x in urls:
            links.append( ( x[2] + ' - ' + x[1], x[0], x[2], x[1] ) )
        if len(links) == 0:
            lyrics = ""
            return lyrics
        elif len(links) == 1:
            lyrics = self.get_lyrics_from_list(links[0])
            return lyrics
        else:
            return links

    def get_lyrics_from_list(self, link):
        title,Id,artist,song = link
        print Id, artist, song
        url = 'http://www.lyrdb.com/karaoke/downloadlrc.php?q=%s' %(Id)
        f = urllib.urlopen(url)
        Page = f.read()
        return Page

if ( __name__ == '__main__' ):
    # used to test get_lyrics() 
    artist = "Groove Coverage"
    song = "God Is A Girl"

    lyrics = LyricsFetcher().get_lyrics( artist, song )
    if ( isinstance( lyrics, list ) ):
        for song in lyrics:
            print song
    else:
        print lyrics

    LyricsFetcher().get_lyrics_from_list(lyrics[0])
