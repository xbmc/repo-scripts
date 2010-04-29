import os
import utilities
import xbmc

class Song:
    def __init__( self ):
        self.artist = ""
        self.title = ""
        self.settings = utilities.Settings().get_settings()
    
    def __str__(self):
        return "Artist: %s, Title: %s" % ( self.artist, self.title)
    
    def __cmp__(self, song):
        if (self.artist != song.artist):
            return cmp(self.artist, song.artist)
        else:
            return cmp(self.title, song.title)
    
    def sanitize(self, str):
        return str.replace( "\\", "_" ).replace( "/", "_" )
    
    def path(self):
        extension = ( "", ".txt", )[ self.settings[ "use_extension" ] ]
        path = unicode( os.path.join( self.settings[ "lyrics_path" ], self.sanitize(self.artist), self.sanitize(self.title) + extension ), "utf-8" )
        return utilities.make_legal_filepath( path, self.settings[ "compatible" ], self.settings[ "use_extension" ] )
    
    @staticmethod
    def current():
        song = Song()
        song.title = xbmc.getInfoLabel( "MusicPlayer.Title" )
        song.title = utilities.deAccent(song.title)
        song.artist = xbmc.getInfoLabel( "MusicPlayer.Artist")
        song.artist = utilities.deAccent(song.artist)
        
        print "Current Song: %s:%s" % (song.artist, song.title)
        
        return song

    @staticmethod
    def next():
        song = Song()
        song.title = xbmc.getInfoLabel( "MusicPlayer.offset(1).Title" )
        song.title = utilities.deAccent(song.title)
        song.artist = xbmc.getInfoLabel( "MusicPlayer.offset(1).Artist")
        song.artist = utilities.deAccent(song.artist)
        
        print "Next Song: %s:%s" % (song.artist, song.title)
        
        return song
