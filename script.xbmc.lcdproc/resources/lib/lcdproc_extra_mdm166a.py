'''
    XBMC LCDproc addon
    Copyright (C) 2012 Team XBMC
    
    Support for extra symbols on Futaba/Targa USB mdm166a VFD displays
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

__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__settings__ = sys.modules[ "__main__" ].__settings__
__cwd__ = sys.modules[ "__main__" ].__cwd__
__icon__ = sys.modules[ "__main__" ].__icon__

from lcdproc import *
from lcdbase import LCD_EXTRAICONS
from extraicons import *
from lcdproc_extra_base import *

def log(loglevel, msg):
  xbmc.log("### [%s] - %s" % (__scriptname__,msg,), level=loglevel) 
  
# extra icon bitmasks
class MDM166A_ICONS:
  ICON_PLAY             = 0x01 << 0
  ICON_PAUSE            = 0x01 << 1
  ICON_RECORD           = 0x01 << 2
  ICON_MESSAGE          = 0x01 << 3
  ICON_AT               = 0x01 << 4
  ICON_MUTE             = 0x01 << 5
  ICON_ANTENNA          = 0x01 << 6
  ICON_VOLUME           = 0x01 << 7
  ICON_ANTLOW           = 0x01 << 13
  ICON_ANTMED           = 0x01 << 14
  ICON_ANTHIGH          = (0x01 << 13) | (0x01 << 14)

  # clear masks
  ICON_CLEAR_ANTENNABAR = 0xffffffff &~ ((0x01 << 13) | (0x01 << 14))

class LCDproc_extra_mdm166a(LCDproc_extra_base):
  def __init__(self):
    self.m_iOutputValueOldIcons = 1
    self.m_iOutputValueIcons = 0

    LCDproc_extra_base.__init__(self)

  # private
  def _SetBarDo(self, barnum, percent):
    # progress bar
    if barnum == 1:
      bitmask = 0x003F8000
      bitshift = 15
      scale = 96
    # volume indicator
    elif barnum == 2:
      bitmask = 0x00001F00
      bitshift = 8
      scale = 28
    else:
      return

    if percent < 0:
      rpercent = 0
    elif percent > 100:
      rpercent = 100
    else:
      rpercent = percent

    self.m_iOutputValueIcons = (self.m_iOutputValueIcons &~ bitmask)
    self.m_iOutputValueIcons |= (int(scale * (rpercent / 100)) << bitshift) & bitmask

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

    if self.m_iOutputValueIcons != self.m_iOutputValueOldIcons:
      self.m_iOutputValueOldIcons = self.m_iOutputValueIcons
      ret += "output %d\n" % (self.m_iOutputValueIcons)

    return ret

  def GetOutputCommands(self):
    return self.SetOutputIcons()

  def SetBar(self, barnum, percent):
    self._SetBarDo(barnum, percent)

  def SetIconState(self, icon, state):
    # General states
    if icon == LCD_EXTRAICONS.LCD_EXTRAICON_MUTE:
      self._SetIconStateDo(MDM166A_ICONS.ICON_MUTE, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_PLAYING:
      self._SetIconStateDo(MDM166A_ICONS.ICON_PLAY, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_PAUSE:
      self._SetIconStateDo(MDM166A_ICONS.ICON_PAUSE, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_ALARM:
      self._SetIconStateDo(MDM166A_ICONS.ICON_MESSAGE, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_RECORD:
      self._SetIconStateDo(MDM166A_ICONS.ICON_RECORD, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_VOLUME:
      self._SetIconStateDo(MDM166A_ICONS.ICON_VOLUME, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_SPDIF:
      self._SetIconStateDo(MDM166A_ICONS.ICON_ANTENNA, state)

    # Output channels
    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_OUT_2_0:
      self.m_iOutputValueIcons &= MDM166A_ICONS.ICON_CLEAR_ANTENNABAR
      self._SetIconStateDo(MDM166A_ICONS.ICON_ANTLOW, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_OUT_5_1:
      self.m_iOutputValueIcons &= MDM166A_ICONS.ICON_CLEAR_ANTENNABAR
      self._SetIconStateDo(MDM166A_ICONS.ICON_ANTMED, state)

    elif icon == LCD_EXTRAICONS.LCD_EXTRAICON_OUT_7_1:
      self.m_iOutputValueIcons &= MDM166A_ICONS.ICON_CLEAR_ANTENNABAR
      self._SetIconStateDo(MDM166A_ICONS.ICON_ANTHIGH, state)

  def ClearIconStates(self, category):
    if category == LCD_EXTRAICONCATEGORIES.LCD_ICONCAT_CODECS:
      self.m_iOutputValueIcons &= MDM166A_ICONS.ICON_CLEAR_ANTENNABAR

    elif category == LCD_EXTRAICONCATEGORIES.LCD_ICONCAT_AUDIOCHANNELS:
      self.m_iOutputValueIcons &= MDM166A_ICONS.ICON_CLEAR_ANTENNABAR

  def GetClearAllCmd(self):
    self.m_iOutputValueOldIcons = 0
    self.m_iOutputValueIcons = 0

    return "output 0\n"
