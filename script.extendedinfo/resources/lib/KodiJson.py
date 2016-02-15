# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from Utils import *


def play_media(media_type, dbid, resume=True):
    if media_type in ['movie', 'episode']:
        get_kodi_json(method="Player.Open",
                      params='{"item": {"%sid": %s},"options":{"resume": %s}}' % (media_type, dbid, resume))
    elif media_type in ['musicvideo', 'album', 'song']:
        get_kodi_json(method="Player.Open",
                      params='{"item": {"%sid": %s}}' % (media_type, dbid))


def send_text(text, close_keyboard=True):
    get_kodi_json(method="Input.SendText",
                  params='{"text":"%s", "done":%s}' % (text, "true" if close_keyboard else "false"))


def get_artists(properties=[]):
    data = get_kodi_json(method="AudioLibrary.GetArtists",
                         params='{"properties": ["%s"]}' % '","'.join(properties))
    return data["result"]["artists"]
