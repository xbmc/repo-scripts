#-*- coding: UTF-8 -*-
import sys
import urllib
import re
from utilities import *

__language__ = sys.modules[ "__main__" ].__language__
__title__ = __language__(30007)
__service__ = 'lyricstime'

class LyricsFetcher:
    def __init__( self ):
        self.clean_lyrics_regex = re.compile( "<.+?>" )
        self.normalize_lyrics_regex = re.compile( "&#[x]*(?P<name>[0-9]+);*" )
        self.clean_br_regex = re.compile( "<br[ /]*>[\s]*", re.IGNORECASE )
        self.clean_info_regex = re.compile( "\[[a-z]+?:.*\]\s" )

    def get_lyrics_thread(self, song):
        log( "%s: searching lyrics for %s" % (__service__, song))
        l = Lyrics()
        l.song = song
        try: # ***** parser - changing this changes search string
            url = "http://www.lyricstime.com/%s-%s-lyrics.html" % (
                     replace(song.artist.lower().replace(" ","-").replace("---","-").replace("--","-")),
                     replace(song.title.lower().replace(" ","-").replace("---","-").replace("--","-"))
                     )
            song_search = urllib.urlopen(url).read()
            log( "%s: search url: %s" % (__service__, url))
            lyr = song_search.split('<div id="songlyrics" >')[1].split('</div>')[0]
            lyr = self.clean_br_regex.sub( "\n", lyr ).strip()
            lyr = self.clean_lyrics_regex.sub( "", lyr ).strip()
            lyr = self.normalize_lyrics_regex.sub(
                      lambda m: unichr( int( m.group( 1 ) ) ), lyr.decode("ISO-8859-1") )
            lyr = u"\n".join( [ lyric.strip() for lyric in lyr.splitlines() ] )
            lyr = self.clean_info_regex.sub( "", lyr )
            l.lyrics = lyr
            l.source = __title__
            return l, None, __service__
        except:
            log( "%s: %s::%s (%d) [%s]" % ( __service__, self.__class__.__name__,
                                        sys.exc_info()[ 2 ].tb_frame.f_code.co_name,
                                        sys.exc_info()[ 2 ].tb_lineno,
                                        sys.exc_info()[ 1 ]
                                        ))
            return None, __language__(30004) % (__title__), __service__
