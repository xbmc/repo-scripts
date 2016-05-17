# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import json
import xbmc


def play_media(media_type, dbid, resume=True):
    if media_type in ['movie', 'episode']:
        get_json(method="Player.Open",
                 params={"item": {"%sid" % media_type: int(dbid)}, "options": {"resume": resume}})
    elif media_type in ['musicvideo', 'album', 'song']:
        get_json(method="Player.Open",
                 params={"item": {"%sid" % media_type: int(dbid)}})


def send_text(text, close_keyboard=True):
    get_json(method="Input.SendText",
             params={"text": text, "done": "true" if close_keyboard else "false"})


def get_artists(properties=None):
    properties = [] if not properties else properties
    data = get_json(method="AudioLibrary.GetArtists",
                    params={"properties": properties})
    if "result" in data and "artists" in data["result"]:
        return data["result"]["artists"]
    return []


def get_movies(properties=None):
    properties = [] if not properties else properties
    data = get_json(method="VideoLibrary.GetMovies",
                    params={"properties": properties})
    if "result" in data and "movies" in data["result"]:
        return data["result"]["movies"]
    return []


def get_tvshows(properties=None):
    properties = [] if not properties else properties
    data = get_json(method="VideoLibrary.GetTVShows",
                    params={"properties": properties})
    if "result" in data and "tvshows" in data["result"]:
        return data["result"]["tvshows"]
    return []


def set_userrating(media_type, dbid, rating):
    if media_type == "movie":
        get_json(method="VideoLibrary.SetMovieDetails",
                 params={"movieid": dbid, "userrating": rating})
    elif media_type == "tv":
        get_json(method="VideoLibrary.SetTVShowDetails",
                 params={"tvshowid": dbid, "userrating": rating})
    elif media_type == "episode":
        get_json(method="VideoLibrary.SetEpisodeDetails",
                 params={"episodeid": dbid, "userrating": rating})


def get_favourites():
    return get_json(method="Favourites.GetFavourites",
                    params={"type": None, "properties": ["path", "thumbnail", "window", "windowparameter"]})


def set_art(media_type, art, dbid):
    get_json(method="VideoLibrary.Set%sDetails" % media_type,
             params={"art": art,
                     "%sid" % media_type.lower(): int(dbid)})


def get_json(method, params):
    """
    communicate with kodi JSON-RPC
    """
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "%s", "params": %s, "id": 1}' % (method, json.dumps(params)))
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    return json.loads(json_query)
