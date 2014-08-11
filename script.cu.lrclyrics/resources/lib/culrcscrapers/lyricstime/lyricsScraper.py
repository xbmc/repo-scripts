#-*- coding: UTF-8 -*-
import sys
import urllib
import re
from utilities import *

__title__ = 'lyricstime'
__priority__ = '220'
__lrc__ = False

def replace_char(string):
    invalid_char = [" ",",","'",]
    for char in invalid_char:
        string = string.replace(char,"-")
    return string

class LyricsFetcher:
    def __init__( self ):
        self.clean_lyrics_regex = re.compile( "<.+?>" )
        self.normalize_lyrics_regex = re.compile( "&#[x]*(?P<name>[0-9]+);*" )
        self.clean_br_regex = re.compile( "<br[ /]*>[\s]*", re.IGNORECASE )
        self.clean_info_regex = re.compile( "\[[a-z]+?:.*\]\s" )

    def get_lyrics(self, song):
        log( "%s: searching lyrics for %s - %s" % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__

        try: # ***** parser - changing this changes search string
            url = "http://www.lyricstime.com/%s-%s-lyrics.html" % (replace_char(song.artist.lower()).replace("&","and").replace("---","-").replace("--","-"),replace_char(song.title.lower()).replace("&","and").replace("---","-").replace("--","-"))
            song_search = urllib.urlopen(url).read()
            log( "%s: search url: %s" % (__title__, url))
            lyr = song_search.split('<div id="songlyrics" style="padding-right:20px;">')[1].split('</div>')[0]
            lyr = self.clean_br_regex.sub( "\n", lyr ).strip()
            lyr = self.clean_lyrics_regex.sub( "", lyr ).strip()
            lyr = self.normalize_lyrics_regex.sub(
                      lambda m: unichr( int( m.group( 1 ) ) ), lyr.decode("ISO-8859-1") )
            lyr = u"\n".join( [ lyric.strip() for lyric in lyr.splitlines() ] )
            lyr = self.clean_info_regex.sub( "", lyr )
            lyrics.lyrics = lyr
            return lyrics
        except:
            log( "%s: %s::%s (%d) [%s]" % ( __title__, self.__class__.__name__, sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ] ))
            return None
