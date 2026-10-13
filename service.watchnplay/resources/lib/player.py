# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
"""Wiedergaben ausserhalb der Bibliothek (Streaming-Add-ons) erfassen.

Bibliothekseintraege laufen ueber Kodis eigenen playcount (VideoLibrary.OnUpdate),
hier zaehlen nur Eintraege ohne Bibliotheks-ID, und auch die nur, wenn sie eindeutig
ein Film oder eine Folge aus einem Video-Add-on sind (should_report). Lokale Dateien
aus dem Dateimanager, Trailer und Videoplattformen werden nicht gemeldet.
"""

import re
import threading

import xbmc

from . import library, util

ITEM_PROPS = ['title', 'year', 'uniqueid', 'showtitle', 'season', 'episode', 'file', 'imdbnumber']

# Mindestlaenge, damit Trailer und Clips nicht als Sichtung zaehlen
MIN_MOVIE_SECONDS = 20 * 60
MIN_EPISODE_SECONDS = 5 * 60

# Videoplattformen: liefern keine Filme/Folgen im Sinne von WatchNPlay
DENIED_PLUGINS = frozenset((
    'plugin.video.youtube',
    'plugin.video.vimeo',
    'plugin.video.dailymotion_com',
    'plugin.video.twitch',
    'plugin.video.invidious',
    'plugin.video.tubed',
))


def plugin_id(path):
    m = re.match(r'^plugin://([^/?#]+)', path or '')
    return m.group(1) if m else None


def is_library_item(item):
    return (item.get('id') or 0) > 0 and item.get('type') in ('movie', 'episode')


def is_plugin_path(path):
    return isinstance(path, str) and path.startswith('plugin://')


def explicit_type(info):
    """'movie'/'episode' nur, wenn Kodi oder das Add-on es ausdruecklich sagt, sonst None."""
    mediatype = (info or {}).get('type')
    return mediatype if mediatype in ('movie', 'episode') else None


def source_ok(info):
    """Quelle und Typ: Video-Add-on (plugin://, keine Videoplattform), ausdruecklich Film oder Folge."""
    if not info:
        return False, 'no item'
    path = info.get('file')
    if not is_plugin_path(path):
        return False, 'not an add-on playback'
    pid = plugin_id(path)
    if pid in DENIED_PLUGINS:
        return False, 'video platform %s' % pid
    if explicit_type(info) is None:
        return False, 'media type not movie/episode'
    return True, None


def should_report(info, total):
    """Gilt nur fuer Eintraege ohne Bibliotheks-ID. Alle Bedingungen muessen erfuellt sein."""
    ok, why = source_ok(info)
    if not ok:
        return ok, why
    minimum = MIN_MOVIE_SECONDS if explicit_type(info) == 'movie' else MIN_EPISODE_SECONDS
    if not total or total < minimum:
        return False, 'too short (%ds)' % int(total or 0)
    return True, None


def percent(position, total):
    if not total or total <= 0:
        return 0.0
    return max(0.0, min(100.0, position * 100.0 / total))


def reached(pct, threshold):
    return pct >= threshold


def _split_ids(uniqueid):
    """'tvshow.tmdb' o. ae. gehoert zur Serie, der Rest zum Eintrag selbst."""
    own, show = {}, {}
    for key, value in (uniqueid or {}).items():
        k = str(key).lower()
        if k.startswith('tvshow.'):
            show[k[len('tvshow.'):]] = value
        else:
            own[k] = value
    return own, show


def build_play(info, watched_at_ms, pct, path=None):
    """info: zusammengefuehrte Angaben aus Player.GetItem und InfoTag.

    None ohne Titel oder ohne ausdruecklichen Typ (kein Raten von 'movie').
    """
    title = (info.get('title') or '').strip()
    showtitle = (info.get('showtitle') or '').strip()
    season = info.get('season')
    episode = info.get('episode')
    mediatype = explicit_type(info)
    if mediatype is None:
        return None
    own, show_ids = _split_ids(info.get('uniqueid'))
    if not title and not showtitle:
        return None
    play = {
        'type': mediatype,
        'title': title or showtitle,
        'ids': library.parse_ids(own, info.get('imdbnumber')),
        'watchedAt': int(watched_at_ms),
        'percent': round(pct, 1),
    }
    year = info.get('year')
    if isinstance(year, int) and 1870 < year < 2200:
        play['year'] = year
    if mediatype == 'episode':
        play['show'] = {'title': showtitle or title, 'ids': library.parse_ids(show_ids)}
        if isinstance(season, int) and season >= 0:
            play['season'] = season
        if isinstance(episode, int) and episode >= 0:
            play['episode'] = episode
    pid = plugin_id(path or info.get('file'))
    if pid:
        play['plugin'] = pid
    return play


class Tracker(xbmc.Player):
    """Merkt sich laufende Nicht-Bibliotheks-Wiedergabe; on_play(play) bei Erreichen der Schwelle."""

    def __init__(self, on_play):
        xbmc.Player.__init__(self)
        self.on_play = on_play
        self.current = None
        self.playing_file = None
        self.position = 0.0
        self.total = 0.0
        # update() laeuft im Mess-Thread des Dienstes, die Player-Callbacks im Dienst-Thread
        self.lock = threading.RLock()

    def onAVStarted(self):
        # Wiedergabeliste: der Wechsel zum naechsten Eintrag meldet kein Ende fuer den vorigen
        if self.current is not None:
            self._finish()
        with self.lock:
            self.current = None
            self.playing_file = None
            self.position = 0.0
            self.total = 0.0
        try:
            if not self.isPlayingVideo():
                return
            info = self._read_item()
        except Exception as exc:
            util.warn('player item not readable: %s' % exc)
            return
        if info is None or is_library_item(info):
            return
        # Laenge steht erst beim Ende sicher fest (should_report), Quelle und Typ schon jetzt
        ok, why = source_ok(info)
        if not ok:
            util.debug('playback not tracked: %s' % why)
            return
        with self.lock:
            self.current = info
            self.playing_file = self._playing_file()
        self.update()

    def _read_item(self):
        players = library.rpc('Player.GetActivePlayers') or []
        pid = None
        for p in players if isinstance(players, list) else []:
            if p.get('type') == 'video':
                pid = p.get('playerid')
        if pid is None:
            return None
        item = library.rpc('Player.GetItem', {'playerid': pid, 'properties': ITEM_PROPS}).get('item') or {}
        info = dict(item)
        info['title'] = item.get('title') or item.get('label') or ''
        uid = dict(item.get('uniqueid') or {})
        try:
            tag = self.getVideoInfoTag()
        except Exception:
            tag = None
        if tag is not None:
            def read(getter, *args):
                # einzeln: fehlt eine Methode (aeltere Kodi-Version), zaehlen die uebrigen weiter
                try:
                    return getattr(tag, getter)(*args)
                except Exception:
                    return None
            for key in ('tmdb', 'imdb', 'tvdb', 'tvshow.tmdb', 'tvshow.imdb', 'tvshow.tvdb'):
                value = read('getUniqueID', key)
                if value and not uid.get(key):
                    uid[key] = value
            if not info.get('imdbnumber'):
                info['imdbnumber'] = read('getIMDBNumber')
            if not info['title']:
                info['title'] = read('getTitle') or ''
            if not info.get('showtitle'):
                info['showtitle'] = read('getTVShowTitle')
            if not info.get('year'):
                info['year'] = read('getYear')
            if info.get('season') in (None, -1):
                info['season'] = read('getSeason')
            if info.get('episode') in (None, -1):
                info['episode'] = read('getEpisode')
            mt = read('getMediaType')
            if mt in ('movie', 'episode') and info.get('type') not in ('movie', 'episode'):
                info['type'] = mt
        info['uniqueid'] = uid
        # Pfad des Eintrags (plugin://...) hat Vorrang vor der aufgeloesten Stream-Adresse
        if not is_plugin_path(info.get('file')):
            for candidate in (xbmc.getInfoLabel('Player.Filenameandpath'), self._playing_file()):
                if is_plugin_path(candidate):
                    info['file'] = candidate
                    break
            else:
                if not info.get('file'):
                    info['file'] = self._playing_file()
        return info

    def _playing_file(self):
        try:
            return self.getPlayingFile()
        except Exception:
            return ''

    def update(self):
        """Position regelmaessig mitschreiben (nach dem Stopp ist sie nicht mehr lesbar).

        Zaehlt wie Kodi die letzte Position, nicht die weiteste: wer ans Ende springt und
        zurueckspult, hat den Titel nicht gesehen."""
        with self.lock:
            if self.current is None:
                return
            try:
                if self.isPlayingVideo():
                    # Wiedergabeliste: zwischen Ende und naechstem onAVStarted laeuft schon der Folgetitel
                    if self.playing_file and self._playing_file() != self.playing_file:
                        return
                    pos = self.getTime()
                    tot = self.getTotalTime()
                    if tot > 0:
                        self.total = tot
                        self.position = max(0.0, pos)
            except Exception:
                pass

    def _finish(self):
        """Prozent immer aus der zuletzt mitgeschriebenen Position, nie pauschal 100 %:
        HTTP-/inputstream-Quellen melden 'ended' bei jedem vorzeitigen Dateiende."""
        with self.lock:
            info, self.current = self.current, None
            position, total = self.position, self.total
        if info is None:
            return
        ok, why = should_report(info, total)
        if not ok:
            util.debug('streaming playback not reported: %s' % why)
            return
        pct = percent(position, total)
        threshold = util.watched_threshold()
        if not reached(pct, threshold):
            util.debug('streaming playback stopped at %.0f%% (< %.0f%%), not reported' % (pct, threshold))
            return
        play = build_play(info, util.now_ms(), pct)
        if play:
            util.log('streaming playback reached %.0f%%, queued (%s)' % (pct, play.get('plugin') or '?'))
            self.on_play(play)

    def onPlayBackStopped(self):
        self._finish()

    def onPlayBackEnded(self):
        self._finish()

    def onPlayBackError(self):
        self._finish()
