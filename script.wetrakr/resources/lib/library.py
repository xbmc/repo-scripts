"""
library.py — read and write the Kodi video library through JSON-RPC for the
library sync (resources/lib/sync_engine.py).

Reads are paginated (VideoLibrary.GetEpisodes WITHOUT tvshowid, so a 50k
episode library is ~100 calls of 500 instead of one call per show, which is
what freezes Kodi in other scrobblers). Writes go in JSON-RPC batches of
WRITE_BATCH calls.

Kodi stores `lastplayed` in LOCAL time ("YYYY-MM-DD HH:MM:SS"); everything
that leaves the device is UTC ISO 8601.
"""

import calendar
import json
import time

import xbmc

from resources.lib import utils

PAGE_SIZE = 500
WRITE_BATCH = 50
KODI_DATE_FMT = "%Y-%m-%d %H:%M:%S"

MOVIE_PROPS = [
    "title", "year", "playcount", "lastplayed", "resume", "uniqueid",
    "imdbnumber", "userrating", "file", "runtime", "tag", "originaltitle",
    "premiered"
]
SHOW_PROPS = ["title", "year", "uniqueid", "imdbnumber", "tag"]
EPISODE_PROPS = [
    "title", "showtitle", "season", "episode", "playcount", "lastplayed",
    "resume", "uniqueid", "tvshowid", "userrating", "file", "runtime",
    "firstaired"
]


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log("[WeTrakr] Library: {}".format(msg), level)


# ─── Dates ────────────────────────────────────────────────────────

def kodi_date_to_iso(value):
    """Kodi local 'YYYY-MM-DD HH:MM:SS' -> UTC ISO 'YYYY-MM-DDTHH:MM:SSZ' (or None)."""
    value = str(value or "").strip()
    if not value:
        return None
    try:
        local = time.strptime(value[:19], KODI_DATE_FMT)
        ts = time.mktime(local)
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))
    except (ValueError, OverflowError):
        return None


def iso_to_kodi_date(value):
    """UTC ISO -> Kodi local 'YYYY-MM-DD HH:MM:SS' (or None)."""
    ts = iso_to_ts(value)
    if ts is None:
        return None
    return time.strftime(KODI_DATE_FMT, time.localtime(ts))


def iso_to_ts(value):
    """UTC ISO ('...Z' or with milliseconds) -> unix seconds (or None)."""
    value = str(value or "").strip()
    if not value:
        return None
    try:
        return calendar.timegm(time.strptime(value[:19], "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, OverflowError):
        return None


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def local_filter_date(ts):
    """unix seconds -> Kodi local date string for a `lastplayed after` filter."""
    return time.strftime(KODI_DATE_FMT, time.localtime(ts))


# ─── JSON-RPC ─────────────────────────────────────────────────────

def rpc(method, params):
    """One JSON-RPC call. Returns the `result` (or {}); logs errors."""
    request = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1})
    response = json.loads(xbmc.executeJSONRPC(request))
    if "error" in response:
        _log("{} failed: {}".format(method, response["error"]), xbmc.LOGWARNING)
        return {}
    return response.get("result", {})


def rpc_batch(calls):
    """Several JSON-RPC calls in one request. Returns the list of responses."""
    if not calls:
        return []
    request = json.dumps([
        {"jsonrpc": "2.0", "method": m, "params": p, "id": i + 1}
        for i, (m, p) in enumerate(calls)
    ])
    response = json.loads(xbmc.executeJSONRPC(request))
    if isinstance(response, dict):
        response = [response]
    errors = [r for r in response if isinstance(r, dict) and "error" in r]
    if errors:
        _log("batch: {} of {} calls failed, first: {}".format(len(errors), len(calls), errors[0]["error"]), xbmc.LOGWARNING)
    return response


def _paged(method, params, key, should_stop=None):
    """Iterate a paginated VideoLibrary.Get* call, PAGE_SIZE items at a time."""
    start = 0
    while True:
        if should_stop and should_stop():
            return
        p = dict(params)
        p["limits"] = {"start": start, "end": start + PAGE_SIZE}
        result = rpc(method, p)
        items = result.get(key) or []
        for item in items:
            yield item
        total = (result.get("limits") or {}).get("total", 0)
        start += PAGE_SIZE
        if not items or start >= total:
            return


def _played_or_touched_filter(since_local=None):
    """Smart-playlist filter: played, in progress or rated; or, with
    `since_local`, played after that local date or in progress."""
    if since_local:
        return {"or": [
            {"field": "lastplayed", "operator": "after", "value": since_local},
            {"field": "inprogress", "operator": "true", "value": ""},
        ]}
    return {"or": [
        {"field": "playcount", "operator": "greaterthan", "value": "0"},
        {"field": "inprogress", "operator": "true", "value": ""},
        {"field": "userrating", "operator": "greaterthan", "value": "0"},
    ]}


# ─── Reads ────────────────────────────────────────────────────────

def iter_movies(touched_only=False, since_local=None, should_stop=None):
    params = {"properties": MOVIE_PROPS}
    if touched_only:
        params["filter"] = _played_or_touched_filter(since_local)
    return _paged("VideoLibrary.GetMovies", params, "movies", should_stop)


def iter_episodes(touched_only=False, since_local=None, should_stop=None):
    params = {"properties": EPISODE_PROPS}
    if touched_only:
        params["filter"] = _played_or_touched_filter(since_local)
    return _paged("VideoLibrary.GetEpisodes", params, "episodes", should_stop)


def get_shows():
    """{tvshowid: show dict} for the whole library (one paginated read)."""
    shows = {}
    for show in _paged("VideoLibrary.GetTVShows", {"properties": SHOW_PROPS}, "tvshows"):
        shows[show.get("tvshowid")] = show
    return shows


def get_movie(movieid):
    item = rpc("VideoLibrary.GetMovieDetails", {"movieid": movieid, "properties": MOVIE_PROPS}).get("moviedetails")
    if item:
        item["type"] = "movie"
    return item


def get_episode(episodeid):
    item = rpc("VideoLibrary.GetEpisodeDetails", {"episodeid": episodeid, "properties": EPISODE_PROPS}).get("episodedetails")
    if item:
        item["type"] = "episode"
    return item


def get_show(tvshowid):
    if not tvshowid or tvshowid < 0:
        return {}
    return rpc("VideoLibrary.GetTVShowDetails", {"tvshowid": tvshowid, "properties": SHOW_PROPS}).get("tvshowdetails") or {}


def is_excluded(item, exclude_plugin_paths):
    """Items the sync leaves alone: PVR, and (optionally) add-on sources such
    as Jellyfin for Kodi or Plex Kodi Connect, which already sync with WeTrakr
    through their own server."""
    f = str(item.get("file") or "")
    if f.startswith("pvr://"):
        return True
    if exclude_plugin_paths and f.startswith("plugin://"):
        return True
    return False


def series_ids(show):
    """External ids of a show dict (same rules as the scrobble payload)."""
    return utils.extract_ids(show) if show else {"tmdb": None, "imdb": None, "tvdb": None}


# ─── Writes ───────────────────────────────────────────────────────

class Writer(object):
    """Collects VideoLibrary.Set*Details calls and flushes them in batches.

    `expect(kind, dbid, playcount, userrating)` is called before each write so
    the monitor can tell our own VideoLibrary.OnUpdate echo from a change the
    user made (see sync_monitor.py).
    """

    def __init__(self, expect=None):
        self._calls = []
        self._expect = expect
        self.written = 0

    def set_movie(self, movieid, fields):
        self._add("VideoLibrary.SetMovieDetails", "movie", movieid, dict(fields, movieid=movieid))

    def set_episode(self, episodeid, fields):
        self._add("VideoLibrary.SetEpisodeDetails", "episode", episodeid, dict(fields, episodeid=episodeid))

    def set_show(self, tvshowid, fields):
        self._add("VideoLibrary.SetTVShowDetails", "tvshow", tvshowid, dict(fields, tvshowid=tvshowid))

    def _add(self, method, kind, dbid, params):
        if self._expect:
            self._expect(kind, dbid, params.get("playcount"), params.get("userrating"))
        self._calls.append((method, params))
        if len(self._calls) >= WRITE_BATCH:
            self.flush()

    def flush(self):
        if not self._calls:
            return
        calls, self._calls = self._calls, []
        responses = rpc_batch(calls)
        ok = sum(1 for r in responses if isinstance(r, dict) and "error" not in r)
        self.written += ok
