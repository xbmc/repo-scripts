# SPDX-License-Identifier: GPL-2.0-or-later
#
# XBMC LCDproc addon
# Copyright (C) 2012-2024 Team Kodi
# Copyright (C) 2012-2024 Daniel 'herrnst' Scheller
#
# Stub class for extra symbol support e.g. on SoundGraph iMON or mdm166a LCDs/VFDs
#

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
