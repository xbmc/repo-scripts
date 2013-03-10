'''
    XBMC LCDproc addon
    Copyright (C) 2012 Team XBMC
    
    Support for extra symbols on SoundGraph iMON LCD displays
    Copyright (C) 2012 Daniel 'herrnst' Scheller
    Original C implementation (C) 2010 Christian Leuschen
    
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

import xbmc
import sys
import time

__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__settings__ = sys.modules[ "__main__" ].__settings__
__cwd__ = sys.modules[ "__main__" ].__cwd__
__icon__ = sys.modules[ "__main__" ].__icon__

from lcdproc import *
from lcdbase import LCD_EXTRAICONS
from extraicons import *
from lcdproc_extra_base import *

IMON_OUTPUT_INTERVAL = 0.2 # seconds

def log(loglevel, msg):
  xbmc.log("### [%s] - %s" % (__scriptname__,msg,), level=loglevel) 
  
# extra icon bitmasks
class IMON_ICONS:
  ICON_SPINDISC        = 0x01 << 0
  ICON_TOP_MUSIC       = 0x01 << 1
  ICON_TOP_MOVIE       = 0x01 << 2
  ICON_TOP_PHOTO       = (0x01 << 1) | (0x01 << 2)
  ICON_TOP_CDDVD       = 0x01 << 3
  ICON_TOP_TV          = (0x01 << 1) | (0x01 << 3)
  ICON_TOP_WEBCASTING  = (0x01 << 2) | (0x01 << 3)
  ICON_TOP_NEWSWEATHER = (0x01 << 1) | (0x01 << 2) | (0x01 << 3)
  ICON_CH_2_0          = 0x01 << 4
  ICON_CH_5_1          = 0x01 << 5
  ICON_CH_7_1          = (0x01 << 4) | (0x01 << 5)
  ICON_SPDIF           = 0x01 << 6
  ICON_OUT_SRC         = 0x01 << 7
  ICON_OUT_FIT         = 0x01 << 8
  ICON_OUT_SD          = 0x01 << 9
  ICON_OUT_HDTV        = 0x01 << 10
  ICON_SCR1            = 0x01 << 11
  ICON_SCR2            = 0x01 << 12
  ICON_ACODEC_MP3      = 0x01 << 13
  ICON_ACODEC_OGG      = 0x01 << 14
  ICON_ACODEC_AWMA     = (0x01 << 13) | (0x01 << 14)
  ICON_ACODEC_WAV      = 0x01 << 15
  ICON_ACODEC_MPEG     = 0x01 << 16
  ICON_ACODEC_AC3      = 0x01 << 17
  ICON_ACODEC_DTS      = (0x01 << 16) | (0x01 << 17)
  ICON_ACODEC_VWMA     = 0x01 << 18
  ICON_VCODEC_MPEG     = 0x01 << 19
  ICON_VCODEC_DIVX     = 0x01 << 20
  ICON_VCODEC_XVID     = (0x01 << 19) | (0x01 << 20)
  ICON_VCODEC_WMV      = 0x01 << 21
  ICON_VOLUME          = 0x01 << 22
  ICON_TIME            = 0x01 << 23
  ICON_ALARM           = 0x01 << 24
  ICON_REC             = 0x01 << 25
  ICON_REPEAT          = 0x01 << 26
  ICON_SHUFFLE         = 0x01 << 27
  BARS                 = 0x01 << 28 # additionally needs bar values in other bits
  ICON_DISC_IN         = 0x01 << 29
  ICON_DUMMY           = 0x01 << 30 # Dummy icon so bars won't reset

  # clear masks
  ICON_CLEAR_TOPROW    = 0xffffffff &~ ((0x01 << 1) | (0x01 << 2) | (0x01 << 3))
  ICON_CLEAR_OUTSCALE  = 0xffffffff &~ ((0x01 << 7) | (0x01 << 8) | (0x01 << 9) | (0x01 << 10))
  ICON_CLEAR_CHANNELS  = 0xffffffff &~ ((0x01 << 4) | (0x01 << 5))
  ICON_CLEAR_BR        = 0xffffffff &~ ((0x01 << 13) | (0x01 << 14) | (0x01 << 15))
  ICON_CLEAR_BM        = 0xffffffff &~ ((0x01 << 16) | (0x01 << 17) | (0x01 << 18))
  ICON_CLEAR_BL        = 0xffffffff &~ ((0x01 << 19) | (0x01 << 20) | (0x01 << 21))

class LCDproc_extra_imon(LCDproc_extra_base):
  def __init__(self):
    self.m_iOutputValueOldIcons = 1
    self.m_iOutputValueOldBars = 1
    self.m_iOutputValueIcons = 0
    self.m_iOutputValueBars = 0
    self.m_iOutputTimer = time.time()

    LCDproc_extra_base.__init__(self)

  # private
  def _DoOutputCommand(self):
    ret = False

    if (self.m_iOutputTimer + IMON_OUTPUT_INTERVAL) < time.time():
      ret = True
      self.m_iOutputTimer = time.time()

    return ret

  # private
  def _SetBarDo(self, barnum, percent):
    if barnum == 1:
      bitmask = 0x00000FC0
      bitshift = 6
    elif barnum == 2:
      bitmask = 0x00FC0000
      bitshift = 18
    elif barnum == 3:
      bitmask = 0x0000003F
      bitshift = 0
    elif barnum == 4:
      bitmask = 0x0003F000
      bitshift = 12
    else:
      return

    if percent < 0:
      rpercent = 0
    elif percent > 100:
      rpercent = 100
    else:
      rpercent = percent

    self.m_iOutputValueBars = (self.m_iOutputValueBars &~ bitmask)
    self.m_iOutputValueBars |= (int(32 * (rpercent / 100)) << bitshift) & bitmask
    self.m_iOutputValueBars |= IMON_ICONS.BARS

  # private
  def _SetIconStateDo(self, bitmask, state):
    if state:
      self.m_iOutputValueIcons |= bitmask
    else:
      self.m_iOutputValueIcons &= ~bitmask

  def Initialize(self):
    for i in range(1, 5):
      self.SetBar(i, float(0))

  def SetOutputIcons(self):
    ret = ""

    # Make sure we don't send "0" to LCDproc, this would reset bars
    self.m_iOutputValueIcons |= IMON_ICONS.ICON_DUMMY

    if self.m_iOutputValueIcons != self.m_iOutputValueOldIcons:
      self.m_iOutputValueOldIcons = self.m_iOutputValueIcons
      ret += "output %d\n" % (self.m_iOutputValueIcons)

    return ret

  def SetOutputBars(self):
    ret = ""

    if self.m_iOutputValueBars != self.m_iOutputValueOldBars:
      self.m_iOutputValueOldBars = self.m_iOutputValueBars
      ret += "output %d\n" % (self.m_iOutputValueBars)

    return ret

  def GetOutputCommands(self):
    ret = ""
    
    if self._DoOutputCommand():
      ret += self.SetOutputIcons()

      if ret == "":
        ret += self.SetOutputBars()

    return ret

  def SetBar(self, barnum, percent):
    self._SetBarDo(barnum, percent)

  def SetIconState(self, icon, state):
    if icon == LCD_EXTRAICONS.LCD_EXTRAICON_PLAYING:
      self._SetIconStateDo(IMON_ICONS.ICON_SPINDISC, state)

    # Icons used for "Modes" category
    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_MOVIE:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_TOPROW
      self._SetIconStateDo(IMON_ICONS.ICON_TOP_MOVIE, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_MUSIC:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_TOPROW
      self._SetIconStateDo(IMON_ICONS.ICON_TOP_MUSIC, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_WEATHER:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_TOPROW
      self._SetIconStateDo(IMON_ICONS.ICON_TOP_NEWSWEATHER, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_TV:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_TOPROW
      self._SetIconStateDo(IMON_ICONS.ICON_TOP_TV, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_PHOTO:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_TOPROW
      self._SetIconStateDo(IMON_ICONS.ICON_TOP_PHOTO, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_RESOLUTION_SD:
      self._SetIconStateDo(IMON_ICONS.ICON_OUT_SD, state)
      self._SetIconStateDo(IMON_ICONS.ICON_OUT_HDTV, False)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_RESOLUTION_HD:
      self._SetIconStateDo(IMON_ICONS.ICON_OUT_SD, False)
      self._SetIconStateDo(IMON_ICONS.ICON_OUT_HDTV, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_OUTSOURCE:
      self._SetIconStateDo(IMON_ICONS.ICON_OUT_SRC, state)
      self._SetIconStateDo(IMON_ICONS.ICON_OUT_FIT, False)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_OUTFIT:
      self._SetIconStateDo(IMON_ICONS.ICON_OUT_SRC, False)
      self._SetIconStateDo(IMON_ICONS.ICON_OUT_FIT, state)

    # Codec/Channel information
    # Video Codecs
    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_VCODEC_MPEG:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BL
      self._SetIconStateDo(IMON_ICONS.ICON_VCODEC_MPEG, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_VCODEC_DIVX:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BL
      self._SetIconStateDo(IMON_ICONS.ICON_VCODEC_DIVX, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_VCODEC_XVID:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BL
      self._SetIconStateDo(IMON_ICONS.ICON_VCODEC_XVID, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_VCODEC_WMV:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BL
      self._SetIconStateDo(IMON_ICONS.ICON_VCODEC_WMV, state)

    # Audio Codecs
    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_ACODEC_MPEG:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BM
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BR
      self._SetIconStateDo(IMON_ICONS.ICON_ACODEC_MPEG, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_ACODEC_AC3:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BM
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BR
      self._SetIconStateDo(IMON_ICONS.ICON_ACODEC_AC3, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_ACODEC_DTS:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BM
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BR
      self._SetIconStateDo(IMON_ICONS.ICON_ACODEC_DTS, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_ACODEC_MP3:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BM
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BR
      self._SetIconStateDo(IMON_ICONS.ICON_ACODEC_MP3, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_ACODEC_VWMA:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BM
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BR
      self._SetIconStateDo(IMON_ICONS.ICON_ACODEC_VWMA, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_ACODEC_AWMA:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BM
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BR
      self._SetIconStateDo(IMON_ICONS.ICON_ACODEC_AWMA, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_ACODEC_OGG:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BM
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BR
      self._SetIconStateDo(IMON_ICONS.ICON_ACODEC_OGG, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_ACODEC_WAV:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BM
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BR
      self._SetIconStateDo(IMON_ICONS.ICON_ACODEC_WAV, state)

    # Output channels
    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_OUT_2_0:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_CHANNELS
      self._SetIconStateDo(IMON_ICONS.ICON_CH_2_0, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_OUT_5_1:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_CHANNELS
      self._SetIconStateDo(IMON_ICONS.ICON_CH_5_1, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_OUT_7_1:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_CHANNELS
      self._SetIconStateDo(IMON_ICONS.ICON_CH_7_1, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_SPDIF:
      self._SetIconStateDo(IMON_ICONS.ICON_SPDIF, state)

    # Generic application state icons
    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_RECORD:
      self._SetIconStateDo(IMON_ICONS.ICON_REC, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_SHUFFLE:
      self._SetIconStateDo(IMON_ICONS.ICON_SHUFFLE, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_REPEAT:
      self._SetIconStateDo(IMON_ICONS.ICON_REPEAT, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_DISC_IN:
      self._SetIconStateDo(IMON_ICONS.ICON_DISC_IN, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_TIME:
      self._SetIconStateDo(IMON_ICONS.ICON_TIME, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_VOLUME:
      self._SetIconStateDo(IMON_ICONS.ICON_VOLUME, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_ALARM:
      self._SetIconStateDo(IMON_ICONS.ICON_ALARM, state)

  def ClearIconStates(self, category):
    if category == LCD_EXTRAICONCATEGORIES.LCD_ICONCAT_MODES:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_TOPROW

    elif category == LCD_EXTRAICONCATEGORIES.LCD_ICONCAT_OUTSCALE:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_OUTSCALE

    elif category == LCD_EXTRAICONCATEGORIES.LCD_ICONCAT_CODECS:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_CHANNELS
      self.m_iOutputValueIcons &= ~IMON_ICONS.ICON_SPDIF
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BL
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BM
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BR

    elif category == LCD_EXTRAICONCATEGORIES.LCD_ICONCAT_VIDEOCODECS:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BL

    elif category == LCD_EXTRAICONCATEGORIES.LCD_ICONCAT_AUDIOCODECS:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BM
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_BR

    elif category == LCD_EXTRAICONCATEGORIES.LCD_ICONCAT_AUDIOCHANNELS:
      self.m_iOutputValueIcons &= IMON_ICONS.ICON_CLEAR_CHANNELS

  def GetClearAllCmd(self):
    self.m_iOutputValueOldIcons = 0
    self.m_iOutputValueOldBars = 0
    self.m_iOutputValueIcons = 0
    self.m_iOutputValueBars = 0

    return "output 0\n"
