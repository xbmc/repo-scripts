# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import json
import xbmc


def play_media(media_type, dbid, resume=True):
    '''
    Start playback of media item
    *media_type: movie, episode, musicvideo, album, song
    *dbid: DBID of media to play
    *resume: Resume from last position (only movie/episode)
    '''
    if media_type in ['movie', 'episode']:
        return get_json(method="Player.Open",
                        params={"item": {"%sid" % media_type: int(dbid)}, "options": {"resume": resume}})
    elif media_type in ['musicvideo', 'album', 'song']:
        return get_json(method="Player.Open",
                        params={"item": {"%sid" % media_type: int(dbid)}})


def get_directory(path, media_type="files"):
    """
    get list with items from directory *path.
    """
    return get_json(method="Files.GetDirectory",
                    params={"directory": path, "media": media_type})


def send_text(text, close_keyboard=True):
    """
    SendText JSON message
    """
    return get_json(method="Input.SendText",
                    params={"text": text, "done": "true" if close_keyboard else "false"})


def get_artists(properties=None):
    """
    return list of artists from database
    """
    properties = properties if properties else []
    data = get_json(method="AudioLibrary.GetArtists",
                    params={"properties": properties})
    if "result" in data and "artists" in data["result"]:
        return data["result"]["artists"]
    return []


def get_addons(properties=None, installed=True, enabled="all"):
    '''
    Get a list of addons
    *properties: list of properties
    *installed: True, False or "all"
    *enabled: True, False or "all"
    '''
    params = {"properties": properties if properties else [],
              "installed": installed,
              "enabled": enabled}
    data = get_json(method="Addons.GetAddons",
                    params=params)
    if "result" in data and "addons" in data["result"]:
        return data["result"]["addons"]
    return []


def get_movies(properties=None):
    '''
    Get a list of movies
    *properties: list of properties
    '''
    properties = properties if properties else []
    data = get_json(method="VideoLibrary.GetMovies",
                    params={"properties": properties})
    if "result" in data and "movies" in data["result"]:
        return data["result"]["movies"]
    return []


def get_tvshows(properties=None):
    '''
    Get a list of TvShows
    *properties: list of properties
    '''
    properties = properties if properties else []
    data = get_json(method="VideoLibrary.GetTVShows",
                    params={"properties": properties})
    if "result" in data and "tvshows" in data["result"]:
        return data["result"]["tvshows"]
    return []


def set_userrating(media_type, dbid, rating):
    '''
    Set the userrating for media items
    *media_type: movie, tv or episode
    *dbid: DBID of media to get rated
    *rating: Actual rating value: 1-10
    '''
    if media_type == "movie":
        return get_json(method="VideoLibrary.SetMovieDetails",
                        params={"movieid": dbid, "userrating": rating})
    elif media_type == "tv":
        return get_json(method="VideoLibrary.SetTVShowDetails",
                        params={"tvshowid": dbid, "userrating": rating})
    elif media_type == "episode":
        return get_json(method="VideoLibrary.SetEpisodeDetails",
                        params={"episodeid": dbid, "userrating": rating})


def get_favourites():
    """
    get list with favourites
    """
    return get_json(method="Favourites.GetFavourites",
                    params={"type": None, "properties": ["path", "thumbnail", "window", "windowparameter"]})


def set_art(media_type, art, dbid):
    """
    set artwork via json
    """
    return get_json(method="VideoLibrary.Set%sDetails" % media_type,
                    params={"art": art,
                            "%sid" % media_type.lower(): int(dbid)})


def get_json(method, params):
    """
    communicate with kodi JSON-RPC
    """
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "%s", "params": %s, "id": 1}' % (method, json.dumps(params)))
    return json.loads(json_query)
