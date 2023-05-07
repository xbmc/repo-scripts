# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2023 iCR8IONS LLC www.icr8ions.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# part of an addon called script.wadeysay for Kodi - https://kodi.tv

# pylint: disable=C0103

""" provides configuration class definition """ 

from enum import Enum
from dataclasses import dataclass

class SUBTITLE_FORCED(Enum):
   """ enum for subtitle forced options """
   FORCED_LANGUAGE=0
   AUDIO_LANGUAGE=1

class SUBTITLE_DISABLED(Enum):
   """ enum for subtitle selected options """
   SELECTED_SUBTITLE=0
   AUDIO_LANGUAGE=1

@dataclass(frozen=True)
class CONF:
   """ immutable class for configuration """ 
   rewind_time: int
   longer_time: int
   p_sdh: bool
   p_subtitle_forced: SUBTITLE_FORCED
   p_subtitle_disabled: SUBTITLE_DISABLED

   def __init__(self, rewind_time, longer_time, p_sdh, p_subtitle_forced, p_subtitle_disabled):
      object.__setattr__(self, "rewind_time", rewind_time)
      object.__setattr__(self, "longer_time", longer_time)
      object.__setattr__(self, "p_sdh", p_sdh)
      object.__setattr__(self, "p_subtitle_forced", p_subtitle_forced)
      object.__setattr__(self, "p_subtitle_disabled", p_subtitle_disabled)
