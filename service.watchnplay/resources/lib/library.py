# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
"""Kodi-Bibliothek per JSON-RPC lesen und Gesehen-Status setzen.

Keine Abgleich-Logik hier: das Add-on schickt nur, was Kodi weiss; der Server entscheidet.
"""

import json
import time

import xbmc

PAGE = 1000
CHUNK = 500

MOVIE_PROPS = ['title', 'year', 'uniqueid', 'imdbnumber', 'playcount', 'lastplayed']
SHOW_PROPS = ['title', 'year', 'uniqueid', 'imdbnumber']
EPISODE_PROPS = ['tvshowid', 'title', 'season', 'episode', 'playcount', 'lastplayed', 'uniqueid']


# JSON-RPC "Invalid params": so meldet Kodi eine Film-/Folgen-Id, die es nicht (mehr) gibt
RPC_INVALID_PARAMS = -32602
# Seriendaten beim Nachlesen einzelner Folgen kurz merken (ganze Staffel markiert)
SHOW_CACHE_TTL = 60


class RpcError(Exception):
    def __init__(self, message, code=None):
        Exception.__init__(self, message)
        self.code = code


def rpc(method, params=None):
    payload = {'jsonrpc': '2.0', 'id': 1, 'method': method}
    if params is not None:
        payload['params'] = params
    raw = xbmc.executeJSONRPC(json.dumps(payload))
    data = json.loads(raw or '{}')
    if 'error' in data:
        err = data['error']
        code = err.get('code') if isinstance(err, dict) else None
        raise RpcError('%s: %s' % (method, err), code)
    return data.get('result') or {}


# --- reine Umwandlungen (getestet) ---

def lastplayed_to_ms(value):
    """Kodi speichert lastplayed in LOKALER Zeit 'YYYY-MM-DD HH:MM:SS'."""
    if not value:
        return None
    try:
        return int(time.mktime(time.strptime(value.strip(), '%Y-%m-%d %H:%M:%S')) * 1000)
    except (ValueError, OverflowError):
        return None


def now_local_string():
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())


def _to_int(value):
    try:
        n = int(str(value).strip())
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _imdb(value):
    value = (value or '').strip() if isinstance(value, str) else ''
    return value if value.startswith('tt') and len(value) > 2 else None


def parse_ids(uniqueid, imdbnumber=None):
    """ids aus uniqueid; imdbnumber nur, wenn es wirklich eine IMDb-Nummer ist."""
    uniqueid = uniqueid if isinstance(uniqueid, dict) else {}
    ids = {}
    tmdb = _to_int(uniqueid.get('tmdb'))
    if tmdb:
        ids['tmdb'] = tmdb
    tvdb = _to_int(uniqueid.get('tvdb'))
    if tvdb:
        ids['tvdb'] = tvdb
    imdb = _imdb(uniqueid.get('imdb')) or _imdb(imdbnumber)
    if imdb:
        ids['imdb'] = imdb
    return ids


def _year(value):
    y = _to_int(value)
    return y if y and 1870 < y < 2200 else None


def build_movie_item(m):
    item = {
        'kid': 'movie:%d' % m['movieid'],
        'type': 'movie',
        'title': m.get('title') or m.get('label') or '',
        'ids': parse_ids(m.get('uniqueid'), m.get('imdbnumber')),
        'watched': (m.get('playcount') or 0) > 0,
    }
    year = _year(m.get('year'))
    if year:
        item['year'] = year
    lp = lastplayed_to_ms(m.get('lastplayed'))
    if lp:
        item['lastPlayed'] = lp
    return item


def build_show(s):
    show = {'title': s.get('title') or s.get('label') or '', 'ids': parse_ids(s.get('uniqueid'), s.get('imdbnumber'))}
    year = _year(s.get('year'))
    if year:
        show['year'] = year
    return show


def build_episode_item(e, shows):
    """shows: {tvshowid: build_show(...)}"""
    item = {
        'kid': 'episode:%d' % e['episodeid'],
        'type': 'episode',
        'title': e.get('title') or e.get('label') or '',
        'ids': parse_ids(e.get('uniqueid')),
        'watched': (e.get('playcount') or 0) > 0,
    }
    show = shows.get(e.get('tvshowid'))
    if show:
        item['show'] = show
    if isinstance(e.get('season'), int) and e['season'] >= 0:
        item['season'] = e['season']
    if isinstance(e.get('episode'), int) and e['episode'] >= 0:
        item['episode'] = e['episode']
    lp = lastplayed_to_ms(e.get('lastplayed'))
    if lp:
        item['lastPlayed'] = lp
    return item


def chunks(items, size=CHUNK):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def build_index(items):
    """Id-Index der Kodi-Bibliothek: Filme nach tmdb/imdb, Folgen nach Serien-Id + Staffel + Folge.

    Damit faellt eine Streaming-Wiedergabe weg, die Kodi ueber den playcount ohnehin meldet.
    """
    index = set()
    for item in items or []:
        if item.get('type') == 'movie':
            for key in ('tmdb', 'imdb'):
                value = (item.get('ids') or {}).get(key)
                if value:
                    index.add(('movie', key, value))
        elif item.get('type') == 'episode':
            season, episode = item.get('season'), item.get('episode')
            if not isinstance(season, int) or not isinstance(episode, int):
                continue
            for key, value in ((item.get('show') or {}).get('ids') or {}).items():
                if key in ('tmdb', 'imdb', 'tvdb') and value:
                    index.add(('episode', key, value, season, episode))
    return index


def in_index(index, play):
    """True, wenn die Wiedergabe (build_play) zu einem Eintrag der Kodi-Bibliothek gehoert."""
    if not index or not play:
        return False
    if play.get('type') == 'movie':
        ids = play.get('ids') or {}
        return any(('movie', key, ids.get(key)) in index for key in ('tmdb', 'imdb') if ids.get(key))
    if play.get('type') == 'episode':
        season, episode = play.get('season'), play.get('episode')
        if not isinstance(season, int) or not isinstance(episode, int):
            return False
        ids = (play.get('show') or {}).get('ids') or {}
        return any(('episode', key, ids.get(key), season, episode) in index
                   for key in ('tmdb', 'imdb', 'tvdb') if ids.get(key))
    return False


def parse_kid(kid):
    try:
        kind, raw = kid.split(':', 1)
        dbid = int(raw)
    except (AttributeError, ValueError):
        return None, None
    if kind not in ('movie', 'episode') or dbid <= 0:
        return None, None
    return kind, dbid


# --- JSON-RPC ---

def _paged(method, key, props, extra=None):
    out = []
    start = 0
    while True:
        params = {'properties': props, 'limits': {'start': start, 'end': start + PAGE}}
        if extra:
            params.update(extra)
        result = rpc(method, params)
        batch = result.get(key) or []
        out.extend(batch)
        total = (result.get('limits') or {}).get('total', 0)
        start += PAGE
        if not batch or start >= total:
            return out


def collect_all():
    """Alle Filme und Folgen als LibItems."""
    items = [build_movie_item(m) for m in _paged('VideoLibrary.GetMovies', 'movies', MOVIE_PROPS)]
    shows = dict((s['tvshowid'], build_show(s))
                 for s in _paged('VideoLibrary.GetTVShows', 'tvshows', SHOW_PROPS))
    items.extend(build_episode_item(e, shows)
                 for e in _paged('VideoLibrary.GetEpisodes', 'episodes', EPISODE_PROPS))
    return items


_show_cache = {}


def _show(tvshowid):
    now = time.time()
    hit = _show_cache.get(tvshowid)
    if hit and hit[0] > now:
        return hit[1]
    s = rpc('VideoLibrary.GetTVShowDetails',
            {'tvshowid': tvshowid, 'properties': SHOW_PROPS}).get('tvshowdetails')
    show = build_show(s) if s else None
    if len(_show_cache) > 200:
        _show_cache.clear()
    _show_cache[tvshowid] = (now + SHOW_CACHE_TTL, show)
    return show


def get_item(kid):
    """Aktueller Stand eines einzelnen Eintrags, None wenn nicht (mehr) vorhanden.

    Ein anderer Lesefehler (Datenbank waehrend eines Scans beschaeftigt, MySQL weg) geht als
    RpcError weiter: die Aenderung soll spaeter erneut versucht werden, nicht verloren gehen."""
    kind, dbid = parse_kid(kid)
    try:
        if kind == 'movie':
            m = rpc('VideoLibrary.GetMovieDetails', {'movieid': dbid, 'properties': MOVIE_PROPS}).get('moviedetails')
            return build_movie_item(m) if m else None
        if kind == 'episode':
            e = rpc('VideoLibrary.GetEpisodeDetails', {'episodeid': dbid, 'properties': EPISODE_PROPS}).get('episodedetails')
            if not e:
                return None
            shows = {}
            if e.get('tvshowid'):
                show = _show(e['tvshowid'])
                if show:
                    shows[e['tvshowid']] = show
            return build_episode_item(e, shows)
    except RpcError as exc:
        if exc.code == RPC_INVALID_PARAMS:
            return None
        raise
    return None


def set_watched(kid, watched, has_lastplayed=True):
    """mark -> playcount 1 (lastplayed setzen, falls leer), unmark -> playcount 0."""
    kind, dbid = parse_kid(kid)
    if not kind:
        return False
    params = {'playcount': 1 if watched else 0}
    if watched:
        # wie Kodis eigenes "Als gesehen markieren": Fortsetzen-Punkt weg
        params['resume'] = {'position': 0, 'total': 0}
        if not has_lastplayed:
            params['lastplayed'] = now_local_string()
    if kind == 'movie':
        params['movieid'] = dbid
        method = 'VideoLibrary.SetMovieDetails'
    else:
        params['episodeid'] = dbid
        method = 'VideoLibrary.SetEpisodeDetails'
    try:
        rpc(method, params)
        return True
    except RpcError as exc:
        xbmc.log('[service.watchnplay] %s failed: %s' % (method, exc), xbmc.LOGWARNING)
        return False
