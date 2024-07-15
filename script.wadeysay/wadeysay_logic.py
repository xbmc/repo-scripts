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

""" core logic that returns result """

import re
import json
from dataclasses import dataclass
from wadeysay_conf import CONF
from wadeysay_conf import SUBTITLE_DISABLED
from wadeysay_conf import SUBTITLE_FORCED

@dataclass
class SUBTITLE_STATE:
   """ subtitle state represented as a data class """
   index: int = -1
   enabled: bool = False

@dataclass
class RESULT:
   """ result represented as a data class """
   initial: SUBTITLE_STATE = None
   action: SUBTITLE_STATE = None

def is_forced(subtitle):
   """ returns bool of whether subtitle is forced or not """
   return ((subtitle.get("isforced") == True)
      or (re.search('forced', subtitle.get("name"), re.IGNORECASE) != None))

def is_sdh(subtitle):
   """ returns bool of whether subtitle is SDH or not """
   return ((subtitle.get("isimpaired") == True)
      or (re.search('SDH', subtitle.get("name"), re.IGNORECASE) != None))

def wadeysay_logic(media_properties: json, conf: CONF) -> RESULT:
   """ parses json and populates initial and action states """

   # inital state is what needs to be restored
   # action state is what needs to be done

   result = RESULT()

   _json_properties = json.loads(media_properties)

   _current_audio_language = _json_properties.get("result", {}).get("currentaudiostream", {}).get("language")
   _current_subtitle_state = _json_properties.get("result", {}).get("subtitleenabled")
   _subtitles = _json_properties.get("result", {}).get("subtitles")


   _current_subtitle = _json_properties.get("result", {}).get("currentsubtitle")
   _current_subtitle_index = None
   _current_subtitle_isforced = None
   _current_subtitle_language = None
   _current_subtitle_isimpaired = None
   _current_subtitle_isdefault = None
   if ((_current_subtitle != None) and (len(_current_subtitle)>0)):
      _current_subtitle_index = _current_subtitle.get("index")
      _current_subtitle_isforced = is_forced(_current_subtitle)
      _current_subtitle_language = _current_subtitle.get("language")
      _current_subtitle_isimpaired = is_sdh(_current_subtitle)
      _current_subtitle_isdefault = _current_subtitle.get("isdefault")

      initial = SUBTITLE_STATE(_current_subtitle_index, _current_subtitle_state)
      result.initial = initial

   if ((_current_subtitle_state == True and (_current_subtitle_isforced == True))
      or (_current_subtitle_state == False)):
      # subtitle enabled and is forced or subtitle is disabled so determine subtitle

      _prefer_language = _current_audio_language

      if (((_current_subtitle_state == False) and (_current_subtitle_isforced == False))
         and ((conf.p_subtitle_disabled == SUBTITLE_DISABLED.SELECTED_SUBTITLE)
         or ((conf.p_subtitle_disabled == SUBTITLE_DISABLED.AUDIO_LANGUAGE)
         and (_current_subtitle_language == _current_audio_language)
         and (_current_subtitle_isimpaired == conf.p_sdh)))):
         # subtitle disabled and current is not forced
         # preference is enable selected or audio language and current subtitle is a match including sdh preference

         # index of -1 implies don't touch subtitle but just enable
         action = SUBTITLE_STATE(-1, True)
         result.action = action

      else:
         # figure out preferred language for subtitle
         if ((_current_subtitle_state == False)
            and (conf.p_subtitle_disabled == SUBTITLE_DISABLED.AUDIO_LANGUAGE)):
            _prefer_language = _current_audio_language
         elif (_current_subtitle_isforced == True):
            if (conf.p_subtitle_forced == SUBTITLE_FORCED.FORCED_LANGUAGE):
               _prefer_language = _current_subtitle_language
            elif (conf.p_subtitle_forced == SUBTITLE_FORCED.AUDIO_LANGUAGE):
               _prefer_language = _current_audio_language

         # determine subtitle based on preferred language and preferences
         _preferred_subtitle_index = -1
         _subtitle_other = []
         for _subtitle in _subtitles:
            if (_prefer_language == _subtitle['language'] and is_forced(_subtitle) == False):
               if (is_sdh(_subtitle) == conf.p_sdh):
                  _preferred_subtitle_index = _subtitle['index']
                  break
               _subtitle_other.append(_subtitle['index'])

         if ((_preferred_subtitle_index == -1) and (len(_subtitle_other) > 0)):
            # fallback - could not find exact match per preferences
            _preferred_subtitle_index = _subtitle_other[0]

         if (_preferred_subtitle_index != -1):
            # set determined subtitle and enable
            if (_preferred_subtitle_index == _current_subtitle_index):
               # determinded subtitle is the same as current so just enable
               # probably sdh mismatch only
               _preferred_subtitle_index = -1
            action = SUBTITLE_STATE(_preferred_subtitle_index, True)
            result.action = action

   return result
