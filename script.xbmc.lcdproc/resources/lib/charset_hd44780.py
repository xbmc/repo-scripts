# SPDX-License-Identifier: GPL-2.0-or-later
#
# XBMC LCDproc addon
# Copyright (C) 2012-2024 Team Kodi
# Copyright (C) 2012-2024 Daniel 'herrnst' Scheller
#
# HD44780 charset codec
#

import codecs
from .charset_map_hd44780_a00 import *
from .charset_map_hd44780_a02 import *

class HD44780_Codec(codecs.Codec):

  def encode_a00(self,input,errors='strict'):
    return codecs.charmap_encode(input,errors,encmap_hd44780_a00)

  def encode_a02(self,input,errors='strict'):
    return codecs.charmap_encode(input,errors,encmap_hd44780_a02)

  def decode(self,input,errors='strict'):
    pass

class HD44780_IncrementalEncoder_a00(codecs.IncrementalEncoder):
  def encode(self, input, final=False):
    return codecs.charmap_encode(input,self.errors,encmap_hd44780_a00)[0]

class HD44780_IncrementalEncoder_a02(codecs.IncrementalEncoder):
  def encode(self, input, final=False):
    return codecs.charmap_encode(input,self.errors,encmap_hd44780_a02)[0]

class HD44780_IncrementalDecoder(codecs.IncrementalDecoder):
  pass

class HD44780_StreamWriter(HD44780_Codec,codecs.StreamWriter):
  pass

class HD44780_StreamReader(HD44780_Codec,codecs.StreamReader):
  pass

def charset_hd44780(mapname):
  if mapname == "hd44780_a00":
    return codecs.CodecInfo(
      name               = mapname,
      encode             = HD44780_Codec().encode_a00,
      decode             = HD44780_Codec().decode,
      incrementalencoder = HD44780_IncrementalEncoder_a00,
      incrementaldecoder = HD44780_IncrementalDecoder,
      streamreader       = HD44780_StreamReader,
      streamwriter       = HD44780_StreamWriter,
    )
  elif mapname == "hd44780_a02":
    return codecs.CodecInfo(
      name               = mapname,
      encode             = HD44780_Codec().encode_a02,
      decode             = HD44780_Codec().decode,
      incrementalencoder = HD44780_IncrementalEncoder_a02,
      incrementaldecoder = HD44780_IncrementalDecoder,
      streamreader       = HD44780_StreamReader,
      streamwriter       = HD44780_StreamWriter,
    )
  else:
    return None
