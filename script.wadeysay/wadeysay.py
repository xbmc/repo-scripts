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

# part of an addon called script.wadyasay for Kodi - https://kodi.tv

# pylint: disable=C0103

""" entry point invoked by Kodi """

from wadeysay_xbmc import get_conf
from wadeysay_xbmc import is_playing_video
from wadeysay_xbmc import media_has_streams
from wadeysay_xbmc import get_player_properties
from wadeysay_xbmc import enable_subtitle
from wadeysay_xbmc import enable_subtitle_index
from wadeysay_xbmc import set_subtitle
from wadeysay_xbmc import rewind_wait
from wadeysay_logic import wadeysay_logic

#import web_pdb

#web_pdb.set_trace()

def wadeysay():
   if (is_playing_video()):
      # video is playing
      _conf = get_conf()
      _dirty = False
      if (media_has_streams()):
         # at least one subtitle and one audio available
         # obtain current media properties
         _media_properties = get_player_properties()
         result = wadeysay_logic(_media_properties, _conf)
         if (result.action != None):
            if ((result.action.index == -1) and (result.action.enabled == True)):
               enable_subtitle()
            elif ((result.action.index != -1) and (result.action.enabled == True)):
               enable_subtitle_index(result.action.index)
            _dirty = True
         # skip now
         # non forced subtitle was enabled or subtitle set and enabled as preferred
         rewind_wait(_conf.rewind_time, _conf.longer_time)
         if ((_dirty == True) and (result.initial != None)):
            # there was a change to subtitle so restore along with enabled state
            set_subtitle(result.initial.index, result.initial.enabled)
