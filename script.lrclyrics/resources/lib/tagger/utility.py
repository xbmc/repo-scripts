""" Data Utility Functions  """

import struct
from encodings import normalize_encoding
from tagger.constants import *
from tagger.encoding import *

id3v2_header_len = {2.2: ID3V2_2_FRAME_HEADER_LENGTH,
					2.3: ID3V2_3_FRAME_HEADER_LENGTH,
					2.4: ID3V2_3_FRAME_HEADER_LENGTH}

def id3v2_2_get_size(header):
	return struct.unpack('!I', '\x00' + header[3:6])[0]
def id3v2_3_get_size(header): 
	return struct.unpack('!4sIBB', header)[1]

id3v2_data_len = {2.2: id3v2_2_get_size,
				  2.3: id3v2_3_get_size,
				  2.4: id3v2_3_get_size}
	
def syncsafe(num, size):
	"""	Given a number, sync safe it """
	result = ''
	for i in range(0,size):
		x = (num >> (i*7)) & 0x7f
		result = chr(x) + result
	return result

def nosyncsafe(data):
	return struct.unpack('!I', data)[0]

def unsyncsafe(data):
	"""
	Given a byte string, it will assume it is big-endian and un-SyncSafe
	a number
	"""
	bytes = len(data)
	bs = struct.unpack("!%dB" % bytes, data)
	total = 0
	for i in range(0,bytes-1):
		total += bs[bytes-1-i] * pow(128,i)
	return total

def null_terminate(enc, s):
	"""
	checks if a string is null terminated already, if it is, then ignore
	it, otherwise, terminate it properly.

	@param enc: encoding (idv2 valid ones: iso8859-1, utf-8, utf-16, utf-16be)
	@type enc: string

	@param s: string to properly null-terminate
	@type s: string
	"""
	if is_double_byte(enc):
		if len(s) > 1 and s[-2:] == '\x00\x00':
			return s
		else:
			return s + '\x00\x00'
	elif is_valid_encoding(enc):
		if len(s) > 0 and s[-1] == '\x00':
			return s
		else:
			return s + '\x00'
	else:
		return s

def is_double_byte(enc):
	if normalize_encoding(enc) in ID3V2_DOUBLE_BYTE_ENCODINGS:
		return 1
	else:
		return 0
		
def is_valid_encoding(encoding):
	if normalize_encoding(encoding) in ID3V2_VALID_ENCODINGS:
		return 1
	else:
		return 0
    
def seek_to_sync(self, fd):
    """
    Reads the file object until it reaches a sync frame of an MP3 file
    (FIXME - inefficient, and possibly useless)
    """
    buf = ''
    hit = -1
    read = 0
    
    while hit == -1:
        # keep on reading until we have 3 chars in the buffer
        while len(buf) < 3:
            buf += fd.read(1)
            read += 1
        # do pattern matching for a 11 bit on pattern in the first 2 bytes
        # (note: that it may extend to the third byte)
        b0,b1,b2 = struct.unpack('!3B',buf)
        if (b0 & 0xff) and (b1 & 0xe0):
            hit = 0
        elif (b0 & 0x7f) and (b1 & 0xf0):
            hit = 1
        elif (b0 & 0x3f) and (b1 & 0xf8):
            hit = 2
        elif (b0 & 0x1f) and (b1 & 0xfc):
            hit = 3
        elif (b0 & 0x0f) and (b1 & 0xfe):
            hit = 4
        elif (b0 & 0x07) and (b1 & 0xff):
            hit = 5
        elif (b0 & 0x03) and (b1 & 0xff) and (b2 & 0x80):
            hit = 6
        elif (b0 & 0x01) and (b1 & 0xff) and (b2 & 0xc0):
            hit = 7
        else:
            buf = buf[1:]
            
    return read + 0.1 * hit - 3
