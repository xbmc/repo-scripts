#-*- coding: UTF-8 -*-
import os
import sys
import xbmc
import unicodedata

__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__profile__    = sys.modules[ "__main__" ].__profile__
__cwd__        = sys.modules[ "__main__" ].__cwd__

LYRIC_SCRAPER_DIR = os.path.join(__cwd__, "resources", "lib", "scrapers")
CANCEL_DIALOG     = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )

def log(msg):
    xbmc.log("### [%s] - %s" % (__scriptname__,msg,),level=xbmc.LOGDEBUG )

def deAccent(str):
    return unicodedata.normalize('NFKD', unicode(unicode(str, 'utf-8'))).encode('ascii','ignore')

def replace(string):
    replace_char = [" ",",","'","&","and"]
    for char in replace_char:
        string.replace(char,"-")
    return string

class Lyrics:
    def __init__( self ):
        self.song = Song()
        self.lyrics = ""
        self.source = ""

class Song:
    def __init__( self ):
        self.artist = ""
        self.title = ""

    def __str__(self):
        return "Artist: %s, Title: %s" % ( self.artist, self.title)

    def __cmp__(self, song):
        if (self.artist != song.artist):
            return cmp(self.artist, song.artist)
        else:
            return cmp(self.title, song.title)

    def sanitize(self, str):
        return str.replace( "\\", "_" ).replace( "/", "_" ).replace(":","_").replace("?","_").replace("!","_")

    def path(self):
        return unicode( os.path.join( __profile__, "lyrics", self.sanitize(self.artist), self.sanitize(self.title) + ".txt" ), "utf-8" )

    @staticmethod
    def current():
        song = Song.by_offset(0)

        if not song.artist and not xbmc.getInfoLabel( "MusicPlayer.TimeRemaining"):
            # no artist and infinite playing time ? We probably listen to a radio
            # which usually set the song title as "Artist - Title" (via ICY StreamTitle)
            sep = song.title.find("-")
            if sep > 1:
                song.artist = song.title[:sep - 1].strip()
                song.title = song.title[sep + 1:].strip()
                # The title in the radio often contains some additional
                # bracketed information at the end:
                #  Radio version, short version, year of the song...
                # It often disturbs the lyrics search so we remove it
                song.title = re.sub(r'\([^\)]*\)$', '', song.title)

        log( "Current Song: %s:%s" % (song.artist, song.title))
        return song

    @staticmethod
    def next():
        song = Song.by_offset(1)
        log( "Next Song: %s:%s" % (song.artist, song.title))
        if song.artist != '' and song.title != '':
            return song
        else:
            return None

    @staticmethod
    def by_offset(offset = 0):
        song = Song()
    	if offset > 0:
            offset_str = ".offset(%i)" % offset
        else:
            offset_str = ""	
        song.title = xbmc.getInfoLabel( "MusicPlayer%s.Title" % offset_str)
        song.title = deAccent(song.title)
        song.artist = xbmc.getInfoLabel( "MusicPlayer%s.Artist" % offset_str)
        song.artist = deAccent(song.artist)

        return song    
