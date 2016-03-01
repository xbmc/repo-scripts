#-*- coding: UTF-8 -*-
import sys
import urllib
import re
from utilities import *

__title__ = 'lyricsmode'
__priority__ = '220'
__lrc__ = False

class LyricsFetcher:
    def __init__( self ):
        self.clean_lyrics_regex = re.compile( "<.+?>" )
        self.normalize_lyrics_regex = re.compile( "&#[x]*(?P<name>[0-9]+);*" )
        self.clean_br_regex = re.compile( "<br[ /]*>[\s]*", re.IGNORECASE )
        self.search_results_regex = re.compile("<a href=\"[^\"]+\">([^<]+)</a></td>[^<]+<td><a href=\"([^\"]+)\" class=\"b\">[^<]+</a></td>", re.IGNORECASE)
        self.next_results_regex = re.compile("<A href=\"([^\"]+)\" class=\"pages\">next .</A>", re.IGNORECASE)

    def get_lyrics(self, song):
        log( "%s: searching lyrics for %s - %s" % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__

        artist = deAccent(song.artist)
        title = deAccent(song.title)
        try: # below is borowed from XBMC Lyrics
            url = "http://www.lyricsmode.com/lyrics/%s/%s/%s.html" % (artist.lower()[:1], artist.lower().replace("&","and").replace(" ","_"), title.lower().replace("&","and").replace(" ","_"))
            lyrics_found = False
            while True:
                log( "%s: search url: %s" % (__title__, url))
                song_search = urllib.urlopen(url).read()
                if song_search.find("<div id='songlyrics_h' class='dn'>") >= 0:
                    break

                if lyrics_found:
                    # if we're here, we found the lyrics page but it didn't
                    # contains the lyrics part (licensing issue or some bug)
                    return None

                # Let's try to use the research box if we didn't yet
                if not 'search' in url:
                    url = "http://www.lyricsmode.com/search.php?what=songs&s=" + urllib.quote_plus(title.lower())
                else:
                    # the search gave more than on result, let's try to find our song
                    url = ""
                    start = song_search.find('<!--output-->')
                    end = song_search.find('<!--/output-->', start)
                    results = self.search_results_regex.findall(song_search, start, end)

                    for result in results:
                        if result[0].lower() in artist.lower():
                            url = "http://www.lyricsmode.com" + result[1]
                            lyrics_found = True
                            break

                    if not url:
                        # Is there a next page of results ?
                        match = self.next_results_regex.search(song_search[end:])
                        if match:
                            url = "http://www.lyricsmode.com/search.php" + match.group(1)
                        else:
                            return None

            lyr = song_search.split("<div id='songlyrics_h' class='dn'>")[1].split('<!-- /SONG LYRICS -->')[0]
            lyr = self.clean_br_regex.sub( "\n", lyr ).strip()
            lyr = self.clean_lyrics_regex.sub( "", lyr ).strip()
            lyr = self.normalize_lyrics_regex.sub( lambda m: unichr( int( m.group( 1 ) ) ), lyr.decode("ISO-8859-1") )
            lir = []
            for line in lyr.splitlines():
                line.strip()
                if line.find("Lyrics from:") < 0:
                    lir.append(line)
            lyr = u"\n".join( lir )
            if lyr.startswith('These lyrics are missing'):
                return None
            lyrics.lyrics = lyr
            return lyrics
        except:
            log( "%s: %s::%s (%d) [%s]" % (
                   __title__, self.__class__.__name__,
                   sys.exc_info()[ 2 ].tb_frame.f_code.co_name,
                   sys.exc_info()[ 2 ].tb_lineno,
                   sys.exc_info()[ 1 ]
                   ))
            return None
