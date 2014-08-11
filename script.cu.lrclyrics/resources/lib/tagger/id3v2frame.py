""" ID3v2 Frames """

__author__ = "Alastair Tse <alastair@tse.id.au>"
__license__ = "BSD"
__copyright__ = "Copyright (c) 2004, Alastair Tse" 

__revision__ = "$Id: id3v2frame.py,v 1.4 2004/12/21 12:02:06 acnt2 Exp $"

from tagger.constants import *
from tagger.exceptions import *
from tagger.utility import *
from tagger.debug import *
from tagger.encoding import *

from encodings import normalize_encoding

import struct, types, tempfile

class ID3v2BaseFrame:
    """ Base ID3v2 Frame for 2.2, 2.3 and 2.4

    Abstract class that defines basic functions that are common for
    2.2, 2.3 and 2.4.

    o_* functions means output_*, they output a bytestring encoding
    the given data

    x_* functions means extract_*, they extract data into accessible
    structures when given a suitable length bytestream

    @cvar header_length: header portion length
    @cvar supported: supported frame ids
    @cvar status_flags: status flags required
    @cvar format_flags: format flags required
    
    @ivar fid: frame id code
    @ivar rawdata: rawdata of the rest of the frame minus the header
    @ivar length: length of the frame in bytes
    @ivar flags: dictionary of flags for this frame

    @ivar encoding: optional - for text fields we have the encoding name
    @ivar strings: a list of strings for text fields
    
    @ivar shortcomment: set if this frame is a comment
    @ivar longcomment: set if this frame is a comment (optional)
    @ivar language: set if this frame is a comment (2 character code)
    
    
    @ivar mimetype: mimetype for GEOB, APIC
    @ivar filename: filename for GEOB
    @ivar obj: data for GEOB
    @ivar desc: for geob and URL
    @ivar url: for URL
    
    @ivar counter: for playcount (PCNT)
    """
    supported = {}
    header_length = 0
    status_flags = {}
    format_flags = {}
    
    fid = None
    rawdata = None
    length = 0
    flags = 0
    encoding = ''
    strings = []
    shortcomment = ''
    longcomment = ''
    language = ''
    mimetype = ''
    filename = ''
    obj = None
    desc = ''
    url = ''

    def __init__(self, frame=None, fid=None):
        """
        creates an ID3v2BaseFrame structure. If you specify frame,
        then it will go into parse mode. If you specify the fid,
        then it will create a new frame.

        @param frame: frame bytestring
        @param fid: frame id for creating a new frame
        """

        if fid and not frame and fid not in self.supported.keys():
            raise ID3ParameterException("Unsupported ID3v2 Field: %s" % fid)
        elif fid and not frame:
            self.fid = fid
            self.new_frame_header()
        elif frame:
            self.parse_frame_header(frame)
            self.parse_field()

    def parse_frame_header(self, frame):

        """
        Parse the frame header from a bytestring

        @param frame: bytestring of the frame
        @type frame: string

        @todo: apple's id3 tags doesn't seem to follow the unsync safe format
        """
        self.rawdata = ''
        self.length = 0     
        raise ID3NotImplementedException("parse_frame_header")

    def new_frame_header(self):
        """
        creates a new frame header
        """
        self.flags = {}
        for flagname, bit in self.status_flags + self.format_flags:
            self.flags[flagname] = 0
    
    def output(self):
        """
        Create a bytestring representing the frame contents
        and the field

        @todo: no syncsafing
        @todo: no status format flags used
        """
        raise ID3NotImplementedException("output")

    def parse_field(self):
        if self.fid not in self.supported.keys():
            raise ID3FrameException("Unsupported ID3v2 Field: %s" % self.fid)
        parser = self.supported[self.fid][0]
        eval('self.x_' + parser + '()')

    def output_field(self):
        if self.fid not in self.supported.keys():
            raise ID3FrameException("Unsupported ID3v2 Field: %s" % self.fid)
        parser = self.supported[self.fid][0]
        return eval('self.o_' + parser + '()')

    def o_string(self, s, toenc, fromenc='latin_1'):
        """
        Converts a String or Unicode String to a byte string of specified encoding.

        @param toenc: Encoding which we wish to convert to. This can be either ID3V2_FIELD_ENC_* or the actual python encoding type
        @param fromenc: converting from encoding specified
        """

        # sanitise input - convert to string repr
        try:
            if type(encodings[toenc]) == types.StringType:
                toenc = encodings[toenc]
        except KeyError:
            toenc = 'latin_1'

        outstring = ''

        # make sure string is of a type we understand
        if type(s) not in [types.StringType, types.UnicodeType]:
            s = unicode(s)

        if type(s) == types.StringType:
            if  toenc == fromenc:
                # don't need any conversion here
                outstring = s
            else:
                try:
                    outstring = s.decode(fromenc).encode(toenc)
                except (UnicodeEncodeError, UnicodeDecodeError):
                    warn("o_string: frame conversion failed. leaving as is.")
                    outstring = s
        
        elif type(s) == types.UnicodeType:
            try:
                outstring = s.encode(toenc)
            except UnicodeEncodeError, err:
                warn("o_string: frame conversion failed - leaving empty. %s" %\
                     err)
                outstring = ''
                
        return outstring
        

    def o_text(self):
        """
        Output text bytestring
        """
        newstrings = []
        for s in self.strings:
            newstrings.append(self.o_string(s, self.encoding))
            
        output = chr(encodings[self.encoding])
        for s in newstrings:
            output += null_terminate(self.encoding, s)

        """
        # strip the last null terminator
        if is_double_byte(self.encoding) and len(output) > 1:
            output = output[:-2]
        elif not is_double_byte(self.encoding) and len(output) > 0:
            output = output[:-1]
        """
        
        return output

    def x_text(self):
        """
        Extract Text Fields

        @todo: handle multiple strings seperated by \x00

        sets: encoding, strings
        """
        data = self.rawdata
        self.encoding = encodings[ord(data[0])]
        rawtext = data[1:]
        
        if normalize_encoding(self.encoding) == 'latin_1':
            text = rawtext
            self.strings = text.split('\x00')
        else:
            text = rawtext.decode(self.encoding)
            if is_double_byte(self.encoding):
                self.strings = text.split('\x00\x00')               
            else:
                self.strings = text.split('\x00')
                
        try:
            dummy = text.encode('utf_8')
            debug('Read Field: %s Len: %d Enc: %s Text: %s' %
                   (self.fid, self.length, self.encoding, str([text])))
        except UnicodeDecodeError:
            debug('Read Field: %s Len: %d Enc: %s Text: %s (Err)' %
                   (self.fid, self.length, self.encoding, str([text])))

    def set_text(self, s, encoding = 'utf_16'):
        self.strings = [s]
        self.encoding = encoding

    def o_comm(self):
        if is_double_byte(self.encoding):
            sep = '\x00\x00'
        else:
            sep = '\x00'
            
        return chr(encodings[self.encoding]) + self.language + \
               self.o_string(self.shortcomment, self.encoding) + sep + \
               self.o_string(self.longcomment, self.encoding) + sep

    def x_comm(self):
        """
        extract comment field

        sets: encoding, lang, shortcomment, longcomment
        """
        data = self.rawdata
        self.encoding = encodings[ord(data[0])]
        self.language = data[1:4]
        self.shortcomment = ''
        self.longcomment = ''

        if is_double_byte(self.encoding):
            for i in range(4,len(data)-1):
                if data[i:i+2] == '\x00\x00':
                    self.shortcomment = data[4:i].strip('\x00')
                    self.longcomment = data[i+2:].strip('\x00')
                    break
        else:
            for i in range(4,len(data)):
                if data[i] == '\x00':
                    self.shortcomment = data[4:i].strip('\x00')
                    self.longcomment = data[i+1:].strip('\x00')
                    break
                
        debug('Read Field: %s Len: %d Enc: %s Lang: %s Comm: %s' %
              (self.fid, self.length, self.encoding, self.language,
               str([self.shortcomment, self.longcomment])))
        

    def o_pcnt(self):
        counter = ''
        if self.length == 4:
            counter = struct.pack('!I', self.counter)
        else:
            for i in range(0, self.length):
                x = (self.counter >> (i*8) ) & 0xff
                counter = counter + struct.pack('!B',x)
        return counter
     
    def x_pcnt(self):
        """
        Extract Play Count

        sets: counter
        """
        data = self.rawdata
        bytes = self.length
        counter = 0
        if bytes == 4:
            counter = struct.unpack('!I',data)[0]
        else:
            for i in range(0,bytes):
                counter += struct.unpack('B',data[i]) * pow(256,i)
                
        debug('Read Field: %s Len: %d Count: %d' % (self.fid, bytes, counter))
        self.counter = counter

    def o_bin(self):
        return self.rawdata

    def x_bin(self):
        pass

    def o_wxxx(self):
        if is_double_byte(self.encoding):
            return chr(encodings[self.encoding]) + \
                   self.o_string(self.desc, self.encoding) + '\x00\x00' + \
                   self.o_string(self.url, self.encoding) + '\x00\x00'
        else:
            return chr(encodings[self.encoding]) + \
                   self.o_string(self.desc, self.encoding) + '\x00' + \
                   self.o_string(self.url, self.encoding) + '\x00'

    def x_wxxx(self):
        """
        Extract URL
        
        set: encoding, desc, url
        """
        data = self.rawdata
        self.encoding = encodings[ord(data[0])]
        if is_double_byte(self.encoding):
            for i in range(1,len(data)-1):
                if data[i:i+2] == '\x00\x00':
                    self.desc = data[1:i]
                    self.url = data[i+2:]
                    break
        else:
            for i in range(1,len(data)):
                if data[i] == '\x00':
                    self.desc = data[1:i]
                    self.url = data[i+1:]
                    break

        debug("Read field: %s Len: %s Enc: %s Desc: %s URL: %s" %
               (self.fid, self.length, self.encoding,
                self.desc, str([self.url])))
        
    def o_apic(self):
        enc = encodings[self.encoding]
        sep = '\x00'
        if is_double_byte(self.encoding):
            sep = '\x00\x00'
        return '%c%s\x00%c%s%s%s' % (enc, self.mimetype, self.picttype, 
                                     self.o_string(self.desc, self.encoding),
                                     sep, self.pict)

    def x_apic(self):
        """
        Extract APIC

        set: encoding, mimetype, desc, pict, picttype
        """
        data = self.rawdata
        self.encoding = encodings[ord(data[0])]
        self.mimetype = ''
        self.desc = ''
        self.pict = ''
        self.picttype = 0

        # get mime type (must be latin-1)
        for i in range(1,len(data)):
            if data[i] == '\x00':
                self.mimetype = data[1:i]
                break

        if not self.mimetype:
            raise ID3FrameException("APIC extraction failed. Missing mimetype")

        picttype = ord(data[len(self.mimetype) + 2])

        # get picture description
        for i in range(len(self.mimetype) + 2, len(data)-1):
            if data[i] == '\x00':
                self.desc = data[len(self.mimetype)+2:i]
                if data[i+1] == '\x00':
                    self.pict = data[i+2:]
                else:
                    self.pict = data[i+1:]
                break

        debug('Read Field: %s Len: %d PicType: %d Mime: %s Desc: %s PicLen: %d' % 
               (self.fid, self.length, self.picttype, self.mimetype,
                self.desc, len(self.pict)))
        
        # open("test.png","w").write(pictdata)

    def o_url(self):
        return self.rawdata

    def x_url(self):
        debug("Read Field: %s Len: %d Data: %s" %
               (self.fid, self.length, [self.rawdata]))
        return

    def o_geob(self):
        if is_double_byte(self.encoding):
            return chr(encodings[self.encoding]) + self.mimetype + '\x00' + \
                   self.filename + '\x00\x00' + self.desc + \
                   '\x00\x00' + self.obj
        else:
            return chr(encodings[self.encoding]) + self.mimetype + '\x00' + \
                   self.filename + '\x00' + self.desc + \
                   '\x00' + self.obj

    def x_geob(self):
        """
        Extract GEOB

        set: encoding, mimetype, filename, desc, obj
        """
        data = self.rawdata
        self.encoding = encodings[ord(data[0])]
        self.mimetype = ''
        self.filename = ''
        self.desc = ''
        self.obj = ''
        
        for i in range(1,len(data)):
            if data[i] == '\x00':
                self.mimetype = data[1:i]
                break

        if not self.mimetype:
            raise ID3FrameException("Unable to extract GEOB. Missing mimetype")

        # FIXME: because filename and desc are optional, we should be
        #        smarter about splitting
        if is_double_byte(self.encoding):
            for i in range(len(self.mimetype)+2,len(data)-1):
                if data[i:i+2] == '\x00\x00':
                    self.filename = data[len(self.mimetype)+2:i]
                    ptr = len(self.mimetype) + len(self.filename) + 4
                    break
        else:
            for i in range(len(self.mimetype)+2,len(data)-1):
                if data[i] == '\x00':
                    self.filename = data[len(self.mimetype)+2:i]
                    ptr = len(self.mimetype) + len(self.filename) + 3
                    break

        if is_double_byte(self.encoding):
            for i in range(ptr,len(data)-1):
                if data[i:i+2] == '\x00\x00':
                    self.desc = data[ptr:i]
                    self.obj = data[i+2:]
                    break
        else:
            for i in range(ptr,len(data)-1):
                if data[i] == '\x00':
                    self.desc = data[ptr:i]
                    self.obj = data[i+1:]
                    break

        debug("Read Field: %s Len: %d Enc: %s Mime: %s Filename: %s Desc: %s ObjLen: %d" %
               (self.fid, self.length, self.encoding, self.mimetype,
                self.filename, self.desc, len(self.obj)))


class ID3v2_2_Frame(ID3v2BaseFrame):
    supported = ID3V2_2_FRAME_SUPPORTED_IDS
    header_length = ID3V2_2_FRAME_HEADER_LENGTH
    version = 2.2
    status_flags = []
    format_flags = []

    def parse_frame_header(self, frame):
        header = frame[:self.header_length]

        self.fid = header[0:3]
        self.rawdata = frame[self.header_length:]
        self.length = struct.unpack('!I', '\x00' + header[3:6])[0]

    def output(self):
        fieldstr = self.output_field()
        # FIXME: no syncsafe
        # NOTE: ID3v2 uses only 3 bytes for size, so we strip of MSB
        header = self.fid + struct.pack('!I', len(fieldstr))[1:]
        return header + fieldstr
    
    def o_text(self):
        """
        Output Text Field

        ID3v2.2 text fields do not support multiple fields
        """
        newstring = self.o_string(self.strings[0], self.encoding)
        enc = encodings[self.encoding]
        return chr(enc) + null_terminate(self.encoding, newstring)

    def o_apic(self):
        enc = encodings[self.encoding]
        if is_double_byte(self.encoding):
            sep = '\x00\x00'
        else:
            sep = '\x00'
        
        imgtype = self.mimetype
        if len(imgtype) != 3:
            #attempt conversion
            if imgtype in ID3V2_2_FRAME_MIME_TYPE_TO_IMAGE_FORMAT.keys():
                imgtype = ID3V2_2_FRAME_MIME_TYPE_TO_IMAGE_FORMAT[imgtype]
            else:
                raise ID3FrameException("ID3v2.2 picture format must be three characters")
        
        return '%c%s%c%s%s%s' % (enc, imgtype, self.picttype,
                                 self.o_string(self.desc, self.encoding),
                                 sep, self.pict)

    def x_apic(self):
        """
        Extract APIC

        set: encoding, mimetype, desc, pict, picttype
        """
        data = self.rawdata
        self.encoding = encodings[ord(data[0])]
        self.mimetype = ''
        self.desc = ''
        self.pict = ''
        self.picttype = 0

        # get mime type (must be latin-1)
        imgtype = data[1:4]
        if not imgtype:
            raise ID3FrameException("APIC extraction failed. Missing mimetype")

        if imgtype not in ID3V2_2_FRAME_IMAGE_FORMAT_TO_MIME_TYPE.keys():
            raise ID3FrameException("Unrecognised mime-type")            
        else:
            self.mimetype = ID3V2_2_FRAME_IMAGE_FORMAT_TO_MIME_TYPE[imgtype]

        picttype = ord(data[len(imgtype) + 1])

        # get picture description
        for i in range(len(imgtype) + 2, len(data) - 1):
            print [data[i:i+3]]
            if data[i] == '\x00':
                self.desc = data[len(imgtype)+2:i]
                if data[i+1] == '\x00':
                    self.pict = data[i+2:]
                else:
                    self.pict = data[i+1:]
                break
                    
        debug('Read Field: %s Len: %d PicType: %d Mime: %s Desc: %s PicLen: %d' % 
               (self.fid, self.length, self.picttype, self.mimetype,
                self.desc, len(self.pict)))
        
        # open("test.png","w").write(pictdata)

class ID3v2_3_Frame(ID3v2BaseFrame):
    supported = ID3V2_3_ABOVE_SUPPORTED_IDS
    header_length = ID3V2_3_FRAME_HEADER_LENGTH
    status_flags = ID3V2_3_FRAME_STATUS_FLAGS
    format_flags = ID3V2_3_FRAME_FORMAT_FLAGS
    version = 2.3

    def parse_frame_header(self, frame):

        frame_header = frame[:self.header_length]
        
        (fid, rawsize, status, format) = struct.unpack("!4sIBB", frame_header)

        self.fid = fid
        self.rawdata = frame[self.header_length:]
        self.length = rawsize
        self.flags = {}
        
        for flagname, bit in self.status_flags:
            self.flags[flagname] = (status >> bit) & 0x01

        for flagname, bit in self.format_flags:
            self.flags[flagname] = (format >> bit) & 0x01
        
    def output(self):
        fieldstr = self.output_field()
        header = self.fid + struct.pack('!IBB', len(fieldstr), \
                                        self.getstatus(), \
                                        self.getformat())
        return header + fieldstr        
        
    def getstatus(self):
        status_word = 0
        if self.flags and self.status_flags:
            for flag, bit in self.status_flags:
                if self.flags.has_key(flag):
                    status_word = status_word & (0x01 << bit)
        return status_word

        
    def getformat(self):
        format_word = 0
        if self.flags and self.format_flags:
            for flag, bit in self.format_flags:
                if self.flags.has_key(flag):
                    format_word = format_word & (0x01 << bit)
        return format_word      
            

class ID3v2_4_Frame(ID3v2_3_Frame):
    supported = ID3V2_3_ABOVE_SUPPORTED_IDS
    header_length = ID3V2_3_FRAME_HEADER_LENGTH
    flags = ID3V2_3_FRAME_FLAGS 
    version = 2.4


ID3v2Frame = ID3v2_4_Frame
