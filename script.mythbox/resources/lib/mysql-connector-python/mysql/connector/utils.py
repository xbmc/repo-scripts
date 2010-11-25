# MySQL Connector/Python - MySQL driver written in Python.
# Copyright (c) 2009,2010, Oracle and/or its affiliates. All rights reserved.
# Use is subject to license terms. (See COPYING)

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation.
# 
# There are special exceptions to the terms and conditions of the GNU
# General Public License as it is applied to this software. View the
# full text of the exception in file EXCEPTIONS-CLIENT in the directory
# of this software distribution or see the FOSS License Exception at
# www.mysql.com.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

"""Utilities
"""

__MYSQL_DEBUG__ = False

import struct

def intread(b):
    """Unpacks the given buffer to an integer"""
    try:
        if isinstance(b,int):
            return b
        l = len(b)
        if l == 1:
            return int(ord(b))
        if l <= 4:
            tmp = b + '\x00'*(4-l)
            return struct.unpack('<I', tmp)[0]
        else:
            tmp = b + '\x00'*(8-l)
            return struct.unpack('<Q', tmp)[0]
    except:
        raise

def int1store(i):
    """
    Takes an unsigned byte (1 byte) and packs it as string.
    
    Returns string.
    """
    if i < 0 or i > 255:
        raise ValueError('int1store requires 0 <= i <= 255')
    else:
        return struct.pack('<B',i)

def int2store(i):
    """
    Takes an unsigned short (2 bytes) and packs it as string.
    
    Returns string.
    """
    if i < 0 or i > 65535:
        raise ValueError('int2store requires 0 <= i <= 65535')
    else:
        return struct.pack('<H',i)

def int3store(i):
    """
    Takes an unsigned integer (3 bytes) and packs it as string.
    
    Returns string.
    """
    if i < 0 or i > 16777215:
        raise ValueError('int3store requires 0 <= i <= 16777215')
    else:
        return struct.pack('<I',i)[0:3]

def int4store(i):
    """
    Takes an unsigned integer (4 bytes) and packs it as string.
    
    Returns string.
    """
    if i < 0 or i > 4294967295L:
        raise ValueError('int4store requires 0 <= i <= 4294967295')
    else:
        return struct.pack('<I',i)

def intstore(i):
    """
    Takes an unsigned integers and packs it as a string.
    
    This function uses int1store, int2store, int3store and
    int4store depending on the integer value.
    
    returns string.
    """
    if i < 0 or i > 4294967295L:
        raise ValueError('intstore requires 0 <= i <= 4294967295')
        
    if i <= 255:
        fs = int1store
    elif i <= 65535:
        fs = int2store
    elif i <= 16777215:
        fs = int3store
    else:
        fs = int4store
        
    return fs(i)

def read_bytes(buf, size):
    """
    Reads bytes from a buffer.
    
    Returns a tuple with buffer less the read bytes, and the bytes.
    """
    s = buf[0:size]
    return (buf[size:], s)

def read_lc_string(buf):
    """
    Takes a buffer and reads a length coded string from the start.
    
    This is how Length coded strings work
    
    If the string is 250 bytes long or smaller, then it looks like this:

      <-- 1b  -->
      +----------+-------------------------
      |  length  | a string goes here
      +----------+-------------------------
  
    If the string is bigger than 250, then it looks like this:
    
      <- 1b -><- 2/3/4 ->
      +------+-----------+-------------------------
      | type |  length   | a string goes here
      +------+-----------+-------------------------
      
      if type == \xfc:
          length is code in next 2 bytes
      elif type == \xfd:
          length is code in next 3 bytes
      elif type == \xfe:
          length is code in next 4 bytes
     
    NULL has a special value. If the buffer starts with \xfb then
    it's a NULL and we return None as value.
    
    Returns a tuple (trucated buffer, string).
    """
    if buf[0] == '\xfb':
        # NULL value
        return (buf[1:], None)
        
    l = lsize = 0
    fst = ord(buf[0])
    
    if fst <= 250:
        l = fst
        return (buf[1+l:], buf[1:l+1])

    lsize = fst - 250
    l = intread(buf[1:lsize+1])
    return (buf[lsize+l+1:], buf[lsize+1:l+lsize+1])
    
def read_lc_string_list(buf):
    """Reads all length encoded strings from the given buffer
    
    Returns a list of strings
    """
    strlst = []
    
    while buf:
        (buf, b) = read_lc_string(buf)
        strlst.append(b)

    return strlst

def read_string(buf, end=None, size=None):
    """
    Reads a string up until a character or for a given size.
    
    Returns a tuple (trucated buffer, string).
    """
    if end is None and size is None:
        raise ValueError('read_string() needs either end or size')
    
    if end is not None:
        try:
            idx = buf.index(end)
        except (ValueError), e:
            raise ValueError("end byte not precent in buffer")
        return (buf[idx+1:], buf[0:idx])
    elif size is not None:
        return read_bytes(buf,size)
    
    raise ValueError('read_string() needs either end or size (weird)')
    
def read_int(buf, size):
    """Read an integer from buffer
    
    Returns a tuple (truncated buffer, int)
    """
    
    try:
        res = intread(buf[0:size])
    except:
        raise
    
    return (buf[size:], res)

def read_lc_int(buf):
    """
    Takes a buffer and reads an length code string from the start.
    
    Returns a tuple with buffer less the integer and the integer read.
    """
    if len(buf) == 0:
        raise ValueError("Empty buffer.")
    
    (buf,s) = read_int(buf,1)    
    if s == 251:
        l = 0
        return (buf,None)
    elif s == 252:
        (buf,i) = read_int(buf,2)
    elif s == 253:
        (buf,i) = read_int(buf,3)
    elif s == 254:
        (buf,i) = read_int(buf,8)
    else:
        i = s
    
    return (buf, int(i))

#
# For debugging
#
def _dump_buffer(buf, label=None):
    import __main__
    if not __main__.__dict__.has_key('__MYSQL_DEBUG__'):
        return
    else:
        debug = __main__.__dict__['__MYSQL_DEBUG__']
        
    try:
        if debug:
            if len(buf) == 0:
                print "%s : EMPTY BUFFER" % label
            import string
            if debug == 1:
                print "%s: %s" % (label,string.join( [ "%02x" % ord(c) for c in buf ], ' '))
            elif debug == 2:
                print "%s: %s" % (label,string.join( [ "\\x%02x" % ord(c) for c in buf ], ''))
            elif debug > 2:
                print "%s: " % label,
                for c in buf:
                    o = ord(c)
                    if o >= 33 and o < 127:
                        print "%s" % c,
                    else:
                        print "%02x" % o,
                print
    except:
        raise
