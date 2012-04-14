import os
import utilities
import xbmc
import sys
import re

__cwd__     = sys.modules[ "__main__" ].__cwd__
__profile__ = sys.modules[ "__main__" ].__profile__

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

        print "Current Song: %s:%s" % (song.artist, song.title)
        return song

    @staticmethod
    def next():
        song = Song.by_offset(1)
        print "Next Song: %s:%s" % (song.artist, song.title)
        
        return song

    @staticmethod
    def by_offset(offset = 0):
        song = Song()
    	if offset > 0:
            offset_str = ".offset(%i)" % offset
        else:
            offset_str = ""	
        song.title = xbmc.getInfoLabel( "MusicPlayer%s.Title" % offset_str)
        song.title = utilities.deAccent(song.title)
        song.artist = xbmc.getInfoLabel( "MusicPlayer%s.Artist" % offset_str)
        song.artist = utilities.deAccent(song.artist)
        
        return song
