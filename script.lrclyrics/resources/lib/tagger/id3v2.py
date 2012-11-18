""" ID3v2 Tag Representation """

__author__ = "Alastair Tse <alastair@tse.id.au>"
__license__ = "BSD"
__copyright__ = "Copyright (c) 2004, Alastair Tse" 

__revision__ = "$Id: id3v2.py,v 1.4 2004/12/21 12:02:06 acnt2 Exp $"

from tagger.exceptions import *
from tagger.constants import *
from tagger.id3v2frame import *
from tagger.utility import *
from tagger.debug import *

import os, struct, sys, types, tempfile, math

class ID3v2:
    """
    ID3v2 Tag Parser/Writer for MP3 files

    @cvar supported: list of version that this parser supports
    @ivar tag: dictionary of parameters that the tag has
    @type tag: dictionary

    @note: tag has the following options

    size = size of the whole header, excluding header and footer
    ext = has extension header (2.3, 2.4 only)
    exp = is experimental (2.4, 2.3 only)
    footer = has footer (2.3, 2.4 only)
    compression = has compression enabled (2.2 only)
    unsync = uses unsynchronise method of encoding data

    @ivar frames: list of frames that is in the tag
    @type frames: dictionary of ID3v2*Frame(s)

    @ivar version: version this tag supports
    @type version: float (2.2, 2.3, 2.4)

    @todo: parse/write footers
    @todo: parse/write appended tags
    @todo: parse/write ext header

    """
    f = None
    supported = [2.2, 2.3, 2.4]
    
    # ---------------------------------------------------------
    def __init__(self, filename, version=ID3V2_DEFAULT_VERSION):
        """
        @param filename: the file to open or write to.
        @type filename: string

        @param version: if header doesn't exists, we need this to tell us what version \
                        header to use
        @type version: float

        @raise ID3Exception: if file does not have an ID3v2 but is specified
        to be in read or modify mode.
        """

        if version not in self.supported:
            raise ID3ParameterException("version %s not valid" % str(version))

        if not os.path.exists(filename):
            raise ID3ParameterException("filename %s not valid" % filename)
        
        try:
          self.f = open(filename, 'rb+')
          self.read_only = False
        except IOError, (errno, strerror):
            if errno == 13: # permission denied
                self.f = open(filename, 'rb')
                self.read_only = True

        self.filename = filename

        if self.tag_exists():
            self.parse_header()
            self.parse_frames()
        else:
            self.new_header(version)
            
    def __del__(self):
        if self.f:
            self.f.close()

    # ---------------------------------------------------------
    # query functions
    # ---------------------------------------------------------
    
    def mp3_data_offset(self):
        """ How many bytes into the file does MP3 data start? """
        if not self.tag_exists():
            return 0
        else:
            if self.version > 2.2:
                if self.tag["footer"]:
                    return ID3V2_FILE_HEADER_LENGTH + \
                           ID3V2_FILE_FOOTER_LENGTH + \
                           self.tag["size"]
            return ID3V2_FILE_HEADER_LENGTH + self.tag["size"]
    
    # ---------------------------------------------------------
    def tag_exists(self):
        self.f.seek(0)
        if self.f.read(3) == 'ID3':
            return True
        return False

    # ---------------------------------------------------------
    def dump_header(self):
        """
        Debugging purposes, dump the whole header of the file.

        @todo: dump footer and extension header as well
        """
        old_pos = self.f.tell()
        output = ''
        if self.tag["size"]:
            self.f.seek(0)
            output = self.f.read(ID3V2_FILE_HEADER_LENGTH + self.tag["size"])
            self.f.seek(old_pos)
            
        return output


    # ---------------------------------------------------------
    def new_frame(self, fid=None, frame=None):
        """
        Return a new frame of the correct type for this tag

        @param fid: frame id
        @param frame: bytes in the frame
        """
        if self.version == 2.2:
            return ID3v2_2_Frame(frame=frame, fid=fid)
        elif self.version == 2.3:
            return ID3v2_3_Frame(frame=frame, fid=fid)
        elif self.version == 2.4:
            return ID3v2_4_Frame(frame=frame, fid=fid)
        else:
            raise ID3NotImplemented("version %f not supported." % self.version)

    # ---------------------------------------------------------
    def set_version(self, version):
        self.version = version

    # ---------------------------------------------------------
    def _read_null_bytes(self):
        """
        Count the number of null bytes at the specified file pointer
        """
        nullbuffer = 0
        while 1:
            if self.f.read(1) == '\x00':
                nullbuffer += 1
            else:
                break
        return nullbuffer


    # ---------------------------------------------------------
    def new_header(self, version=ID3V2_DEFAULT_VERSION):
        """
        Create a new default ID3v2 tag data structure

        @param version: version of the tag to use. default is 2.4.
        @type version: float
        """

        if version not in self.supported:
            raise ID3ParameterException("version %s not supported" % str(version))
        
        self.tag = {}
        if version in self.supported:
            self.version = version
        else:
            raise ID3NotImplementedException("Version %s not supported", \
                                             str(version))

        if version in [2.4, 2.3]:
            self.tag["ext"] = 0
            self.tag["exp"] = 0
            self.tag["footer"] = 0
        elif version == 2.2:
            self.tag["compression"] = 0
            
        self.tag["unsync"] = 0
        self.tag["size"] = 0
        self.frames = []
        
    # ---------------------------------------------------------
    def parse_header(self):
        """
        Parse Header of the file

        """
        self.f.seek(0)
        data = self.f.read(ID3V2_FILE_HEADER_LENGTH)
        if len(data) != ID3V2_FILE_HEADER_LENGTH:
            raise ID3HeaderInvalidException("ID3 tag header is incomplete")
        
        self.tag = {}
        self.frames = []
        id3, ver, flags, rawsize = struct.unpack("!3sHB4s", data)
        
        if id3 != "ID3":
            raise ID3HeaderInvalidException("ID3v2 header not found")

        self.tag["size"] = unsyncsafe(rawsize)
        # NOTE: size  = excluding header + footer
        version = 2 + (ver / 0x100) * 0.1
        if version not in self.supported:
            raise ID3NotImplementedException("version %s not supported" % \
                                             str(version))
        else:
            self.version = version
            
        if self.version in [2.4, 2.3]:
            for flagname, bit in ID3V2_3_TAG_HEADER_FLAGS:
                self.tag[flagname] = (flags >> bit) & 0x01
        elif self.version in [2.2]:
            for flagname, bit in ID3V2_2_TAG_HEADER_FLAGS:
                self.tag[flagname] = (flags >> bit) & 0x01

        if self.tag.has_key("ext") and self.tag["ext"]:
            self.parse_ext_header()
    
        debug(self.tag)
        
    # ---------------------------------------------------------    
    def parse_ext_header(self):
        """ Parse Extension Header """

        # seek to the extension header position
        self.f.seek(ID3V2_FILE_HEADER_LENGTH)
        data = self.f.read(ID3V2_FILE_EXTHEADER_LENGTH)
        extsize, flagbytes = struct.unpack("!4sB", data)
        extsize = unsyncsafe(extsize)
        readdata = 0
        if flagbytes == 1:
            flags = struct.unpack("!B",self.f.read(flagbytes))[0]
            self.tag["update"] = ( flags & 0x40 ) >> 6
            if ((flags & 0x20) >> 5):
                self.tag["crc"] = unsyncsafe(self.f.read(5))
                readdata += 5
            if ((flags & 0x10) >> 4):
                self.tag["restrictions"] = struct.unpack("!B", self.f.read(1))[0]
                # FIXME: store these restrictions properly
                readdata += 1
                
            # work around dodgy ext headers created by libid3tag
            if readdata < extsize - ID3V2_FILE_EXTHEADER_LENGTH - flagbytes:
                self.f.read(extsize - ID3V2_FILE_EXTHEADER_LENGTH - flagbytes - readdata)
        else:
            # ignoring unrecognised extension header
            self.f.read(extsize - ID3V2_FILE_EXTHEADER_LENGTH)
        return 1
    
    # ---------------------------------------------------------
    def parse_footer(self):
        """Parse Footer

        @todo: implement me
        """
        return 0 # FIXME

    # ---------------------------------------------------------    
    def parse_frames(self):
        """ Recursively Parse Frames """
        read = 0
        readframes = 0
        
        while read < self.tag["size"]:
            framedata = self.get_next_frame(self.tag["size"] - read)
            if framedata:
                try:
                    read += len(framedata)
                    if self.version == 2.2:
                        frame = ID3v2_2_Frame(frame=framedata)
                    elif self.version == 2.3:
                        frame = ID3v2_3_Frame(frame=framedata)
                    elif self.version == 2.4:
                        frame = ID3v2_4_Frame(frame=framedata)
                    readframes += 1
                    self.frames.append(frame)
                except ID3Exception:
                    pass # ignore unrecognised frames
            else:
                self.tag["padding"] = self._read_null_bytes()
                debug("NULL Padding: %d" % self.tag["padding"])
                break

        # do a sanity check on the size/padding
        if not self.tag.has_key("padding"):
            self.tag["padding"] = 0
            
        if self.tag["size"] != read + self.tag["padding"]:
            self.tag["size"] = read + self.tag["padding"]
            
        return len(self.frames)

    # ---------------------------------------------------------
    def get_next_frame(self, search_length):

        # skip null frames
        c = self.f.read(1)
        self.f.seek(-1, 1)
        if c == '\x00':
            return '' # check for NULL frames
        
        hdr = self.f.read(id3v2_header_len[self.version])
        size = id3v2_data_len[self.version](hdr)
        data = self.f.read(size)
        return hdr + data

    # ---------------------------------------------------------     
    def construct_header(self, size):
        """
        Construct Header Bytestring to for tag

        @param size: size to encode into the bytestring. Note the size is the whole \
                      size of the tag minus the header and footer
        @type size: int
        """
        if self.version in [2.3, 2.4]:
            flags = ID3V2_3_TAG_HEADER_FLAGS
        elif self.version in [2.2]:
            flags = ID3V2_2_TAG_HEADER_FLAGS

        bytestring = 'ID3'
        flagbyte = 0
        for flagname, bit in flags:
            flagbyte = flagbyte | ((self.tag[flagname] & 0x01) << bit)
            
        bytestring += struct.pack('<H', int((self.version * 10) % 10))
        bytestring += struct.pack('!B', flagbyte)
        bytestring += syncsafe(size, 4)
        return bytestring

    # ---------------------------------------------------------
    def construct_ext_header(self):
        """
        Construct an Extension Header (FIXME)
        """
        self.tag['ext'] = 0
        return '' # FIXME!
        
    # ---------------------------------------------------------
    def construct_footer(self):
        """
        Construct a Footer (FIXME)
        """
        return '' # FIXME!
        
    # ---------------------------------------------------------     
    def commit_to_file(self, filename):
        newf = open(filename, 'wb+')
        framesstring = ''.join(map(lambda x: x.output(), self.frames))
        footerstring = ''
        extstring = ''
        
        # backup existing mp3 data 
        self.f.seek(self.mp3_data_offset())
        t = tempfile.TemporaryFile()
        buf = self.f.read(1024)
        while buf:
            t.write(buf)
            buf = self.f.read(1024)

        tag_content_size = len(extstring) + len(framesstring)
        headerstring = self.construct_header(tag_content_size + \
                                              ID3V2_FILE_DEFAULT_PADDING)
        
        newf.write(headerstring)
        newf.write(extstring)
        newf.write(framesstring)
        newf.write('\x00' * ID3V2_FILE_DEFAULT_PADDING)
        newf.write(footerstring)
        t.seek(0)
        buf = t.read(1024)
        while buf:
            newf.write(buf)
            buf = t.read(1024)
        t.close()
        newf.close()

    # ---------------------------------------------------------
    def commit(self, pretend=False):
        """ Commit Changes to MP3. This means writing to file.
        Will fail if file is not writable
        
        @param pretend: boolean
        @type pretend: Do not actually write to file, but pretend to.
        """
        
        if self.read_only:
            return False # give up if it's readonly - don't bother!
            
        # construct frames, footers and extensions
        framesstring = ''.join(map(lambda x: x.output(), self.frames))
        footerstring = ''
        extstring = ''
        
        if self.tag.has_key("ext") and self.tag["ext"]:
            extstring = self.construct_ext_header()
        if self.tag.has_key("footer") and self.tag["footer"]:
            footerstring = self.construct_footer()

        

        # make sure there is enough space from start of file to
        # end of tag, otherwise realign tag
        tag_content_size = len(extstring) + len(framesstring)
                
        if self.tag["size"] < tag_content_size:
            headerstring = self.construct_header(tag_content_size + \
                                                  ID3V2_FILE_DEFAULT_PADDING)
            
            # backup existing mp3 data 
            self.f.seek(self.mp3_data_offset())
            t = tempfile.TemporaryFile()
            buf = self.f.read(1024)
            while buf:
                t.write(buf)
                buf = self.f.read(1024)
                
            # write to a new file
            if not pretend:
                self.f.close()
                self.f = open(self.filename, 'wb+')
                self.f.write(headerstring)
                self.f.write(extstring)
                self.f.write(framesstring)
                self.f.write('\x00' * ID3V2_FILE_DEFAULT_PADDING)
                self.f.write(footerstring)
                
                # write mp3 data to new file
                t.seek(0)
                buf = t.read(1024)
                while buf:
                    self.f.write(buf)
                    buf = t.read(1024)
                t.close()
                self.f.close()
                
                self.f = open(self.filename, 'rb+')
                self.tag["size"] = len(headerstring) + len(extstring) + \
                                   ID3V2_FILE_DEFAULT_PADDING
            
        else:
            headerstring = self.construct_header(self.tag["size"])
            if not pretend:
                self.f.seek(0)
                self.f.write(headerstring)
                self.f.write(extstring)
                self.f.write(framesstring)
                written = len(extstring) + len(framesstring)
                warn("Written Bytes: %d" % written)
                # add padding
                self.f.write('\x00' * (self.tag["size"] - written))
                # add footerstring
                self.f.write(footerstring)
                self.f.flush()

    
