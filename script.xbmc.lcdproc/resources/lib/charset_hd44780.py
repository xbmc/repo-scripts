'''
    XBMC LCDproc addon
    Copyright (C) 2012-2018 Team Kodi

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

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

def charset_hd44780(name):
  if name == "hd44780-a00":
    return codecs.CodecInfo(
      name               = "hd44780-a00",
      encode             = HD44780_Codec().encode_a00,
      decode             = HD44780_Codec().decode,
      incrementalencoder = HD44780_IncrementalEncoder_a00,
      incrementaldecoder = HD44780_IncrementalDecoder,
      streamreader       = HD44780_StreamReader,
      streamwriter       = HD44780_StreamWriter,
    )
  elif name == "hd44780-a02":
    return codecs.CodecInfo(
      name               = "hd44780-a02",
      encode             = HD44780_Codec().encode_a02,
      decode             = HD44780_Codec().decode,
      incrementalencoder = HD44780_IncrementalEncoder_a02,
      incrementaldecoder = HD44780_IncrementalDecoder,
      streamreader       = HD44780_StreamReader,
      streamwriter       = HD44780_StreamWriter,
    )
  else:
    return None
