"""ID3v1 Class """

__author__ = "Alastair Tse <alastair@tse.id.au>"
__license__ = "BSD"
__copyright__ = "Copyright (c) 2004, Alastair Tse" 

__revision__ = "$Id: $"

from tagger.exceptions import *
from tagger.constants import *

import struct, os

class ID3v1(object):
    """
    ID3v1 Class
    
    This class parses and writes ID3v1 tags using a very simplified
    interface.
    
    You can access the ID3v1 tag variables by directly accessing the
    object attributes. For example:
    
    id3v1 = ID3v1('some.mp3')
    id3v1.track = 1
    print id3v1.songname
    del id3v1
    
    @ivar songname: the songname in iso8859-1
    @type songname: string
    @ivar artist: the artist name in iso8859-1
    @type artist: string
    @ivar album: the album name in iso8859-1
    @type album: string
    @ivar year: the year of the track
    @type year: string
    @ivar comment: comment string. limited to 28 characters
    @type comment: string
    @ivar genre: genre number
    @type genre: int
    @ivar track: track number
    @type track: int


    @ivar read_only: file is read only
    """

    __f = None
    __tag = None
    __filename = None

    def __init__(self, filename):
        """
        constructor

        tries to load the id3v1 data from the filename given. if it succeeds it
        will set the tag_exists parameter.

        @param filename: filename
        @type filename: string
        @param mode: ID3_FILE_{NEW,READ,MODIFY}
        @type mode: constant
        """

        if not os.path.exists(filename):
            raise ID3ParameterException("File not found: %s" % filename)

        try:
            self.__f = open(filename, 'rb+')
            self.read_only = False
        except IOError, (errno, strerr):
            if errno == 13: # permission denied
                self.__f = open(filename, 'rb')
                self.read_only = True
            else:
                raise
        
        self.__filename = filename
        self.__tag = self.default_tags()
        
        if self.tag_exists():
            self.parse()
                    
    def default_tags(self):
        return { 'songname':'', 'artist':'', 'album':'', 
                 'year':'', 'comment':'', 'genre':0, 'track':0}
    
    def tag_exists(self):
        self.__f.seek(-128, 2)
        if self.__f.read(3) == 'TAG':
            return True
        return False
        
    def remove_and_commit(self):
        """ Remove ID3v1 Tag """
        if self.tag_exists() and not self.read_only:
            self.__f.seek(-128, 2)
            self.__f.truncate()
            self.__f.flush()
            self.__tag = self.default_tags()
            return True
        else:
            return False

    def commit(self):
        id3v1 = struct.pack("!3s30s30s30s4s30sb",
            'TAG',
            self.songname,
            self.artist,
            self.album,
            self.year,
            self.comment,
            self.genre)
    
        if self.tag_exists():
            self.__f.seek(-128, 2)
            self.__f.truncate()
        else:
            self.__f.seek(0, 2)
        
        self.__f.write(id3v1)
        self.__f.flush()

    def commit_to_file(self, filename):
        id3v1 = struct.pack("!3s30s30s30s4s30sb",
            'TAG',
            self.songname,
            self.artist,
            self.album,
            self.year,
            self.comment,
            self.genre)
    
        f = open(filename, 'wb+')
        self.__f.seek(0)
        buf = self.__f.read(4096)
        while buf:
            f.write(buf)
            buf = self.__f.read(4096)
            
        if self.tag_exists():
            f.seek(-128, 0)
            f.truncate()
        
        f.write(id3v1)
        f.close()
        

    def __getattr__(self, name):
        if self.__tag and self.__tag.has_key(name):
            return self.__tag[name]
        else:
            raise AttributeError, "%s not found" % name

    def __setattr__(self, name, value):
        if self.__tag and self.__tag.has_key(name):
            if name == 'genre' and type(value) != types.IntValue:
                raise TypeError, "genre should be an integer"
            if name == 'track' and type(value) != types.IntValue:
                raise TypeError, "track should be an integer"
            if name == 'year':
                self.__tag[name] = str(value)[:4]
            self.__tag[name] = value
        else:
            object.__setattr__(self, name, value)

    def __del__(self):
        if self.__f:
            self.__f.close()

    def parse(self):
        try:
            self.__f.seek(-128, 2)
        except IOError:
            raise ID3HeaderInvalidException("not enough bytes")
            
        id3v1 = self.__f.read(128)
        
        tag, songname, artist, album, year, comment, genre = \
             struct.unpack("!3s30s30s30s4s30sb", id3v1)
        
        if tag != "TAG":
            raise ID3HeaderInvalidException("ID3v1 TAG not found")
        else:
            if comment[28] == '\x00':
                track = ord(comment[29])
                comment = comment[0:27]
            else:
                track = 0

                
            self.__tag["songname"] = self.unpad(songname).strip()
            self.__tag["artist"] = self.unpad(artist).strip()
            self.__tag["album"] = self.unpad(album).strip()
            self.__tag["year"] = self.unpad(year).strip()
            self.__tag["comment"] = self.unpad(comment).strip()
            self.__tag["genre"] = genre
            self.__tag["track"] = track
    
    def unpad(self, field):
        length = 0
        for x in field:
            if x == '\x00':
                break
            else:
                length += 1
        return field[:length]
