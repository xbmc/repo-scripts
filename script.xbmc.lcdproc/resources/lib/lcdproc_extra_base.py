'''
    XBMC LCDproc addon
    Copyright (C) 2012-2018 Team Kodi

    Stub class for extra symbol support e.g. on SoundGraph iMON or mdm166a LCDs/VFDs
    Copyright (C) 2012-2018 Daniel 'herrnst' Scheller

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

class LCDproc_extra_base():
  def __init__(self):
    pass

# @abstractmethod
  def Initialize(self):
    pass

# @abstractmethod
  def SetOutputIcons(self):
    pass

# @abstractmethod
  def SetOutputBars(self):
    pass

# @abstractmethod
  def GetOutputCommands(self):
    pass

# @abstractmethod
  def SetBar(self, barnum, percent):
    pass

# @abstractmethod
  def SetIconState(self, icon, state):
    pass

# @abstractmethod
  def ClearIconStates(self, category):
    pass

# @abstractmethod
  def GetClearAllCmd(self):
    pass
