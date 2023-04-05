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

""" this module contains all xbmc/kodi specific code """

import sys
import json
import xbmc
import xbmcaddon
from wadeysay_conf import CONF, SUBTITLE_FORCED, SUBTITLE_DISABLED

# this is a pointer to the module object instance itself
this = sys.modules[__name__]
this._player_id = None

def get_conf() -> CONF:
   """ instantiation of immutatable configuration object using addon settings """
   _addon = xbmcaddon.Addon()

   _rewind_time = _addon.getSettingInt('rewind')
   _longer_time = _addon.getSettingInt('longer')
   _p_sdh = _addon.getSettingBool('p_sdh')
   _p_subtitle_forced = SUBTITLE_FORCED(_addon.getSettingInt('p_subtitle_forced'))
   _p_subtitle_disabled = SUBTITLE_DISABLED(_addon.getSettingInt('p_subtitle_disabled'))

   return CONF(_rewind_time,_longer_time,_p_sdh,_p_subtitle_forced,_p_subtitle_disabled)

def is_playing_video() -> bool:
   """ return true if video is playing """
   return xbmc.Player().isPlayingVideo()

def rewind_wait(rewind_time: int, longer_time: int):
   """ rewind video for rewind_time and wait for rewind_time + longer_time """

   xbmc.executebuiltin('Seek(-%d)' %(rewind_time))
   xbmc.Monitor().waitForAbort(rewind_time + longer_time)

def media_has_streams() -> bool:
   """ check current media for at least one subtitle and one audio stream """
   # at least one subtitle and one audio available
   return ((len(xbmc.Player().getAvailableSubtitleStreams()) > 0)
      and (len(xbmc.Player().getAvailableAudioStreams()) > 0))

def _get_active_player_id() -> int:
   """ determine and return active player id """
   if (this._player_id == None):
      _json_query = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.GetActivePlayers","id":1}')
      _json_properties = json.loads(_json_query)
      _players = _json_properties["result"]
      for _player in _players:
         if (_player["type"] == "video"):
            this._player_id = _player["playerid"]
            break
   return this._player_id

def get_player_properties() -> json:
   """ get playing media properties as json """
   _player_id = _get_active_player_id()
   return xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.GetProperties","params":{"playerid":%d,"properties":["subtitles","subtitleenabled","currentsubtitle","audiostreams","currentaudiostream"]},"id":1}' %(_player_id))

def enable_subtitle():
   """ just enable subtitle that is currently selected """
   xbmc.Player().showSubtitles(True)

def disable_subtitle():
   """ just disable subtitle that is currently selected """
   xbmc.Player().showSubtitles(False)

def enable_subtitle_index(index):
   """ enable subtitle by index """
   set_subtitle(index, True)

def set_subtitle(index: int, subtitle_state: bool):
   """ set subtitle by index and set subtitle state """
   _player_id = _get_active_player_id()
   xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.SetSubtitle","params":{"playerid":%d,"subtitle":%d,"enable":%s},"id":1}' %(_player_id, index, ("%r" %(subtitle_state)).lower()))
   # TODO: workaround since enable:false params does not disable subtitles
   xbmc.Player().showSubtitles(subtitle_state)
