#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""The Kodi player callbacks (events only), the item dicts every module works with, identification of what is
playing, exclusions."""

import base64
import json
import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ElementTree

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib import settings, store, utils
from resources.lib.api import ApiError

# mediapath is the plugin:// URL of an add-on item; file and getPlayingFile() carry the resolved stream on a first play
ITEM_PROPERTIES = ['title', 'showtitle', 'season', 'episode', 'year', 'file', 'mediapath', 'tvshowid', 'uniqueid', 'runtime', 'customproperties']
MOVIE_PROPERTIES = ['title', 'year', 'uniqueid', 'trailer', 'file', 'runtime', 'lastplayed', 'playcount', 'userrating']
EPISODE_PROPERTIES = ['showtitle', 'title', 'season', 'episode', 'uniqueid', 'tvshowid', 'file', 'runtime', 'lastplayed', 'playcount']
SHOW_PROPERTIES = ['title', 'year', 'uniqueid']
# the conventions other add-ons speak, Trakt's and ours: ids of what plays (a home-window property, or the same name as a
# property of the playing ListItem, which survives a playlist), "I scrobble this playback to Simkl myself", and a ListItem
# property that keeps one item (a trailer, a preview) out of any scrobbler; flat per-id properties as some add-ons set
# them (tmdb_id, imdb_id, and tvshow.tmdb_id for the show of an episode) are read when nothing else names the item
IDS_PROPERTIES = ('script.simkl.ids', 'script.trakt.ids')
PAUSED_PROPERTY = 'script.simkl.paused'
EXCLUDE_PROPERTIES = ('script.simkl.exclude', 'script.trakt.exclude')
SHOW_PREFIX = 'tvshow.'
# what this add-on tells the others: the item it tracks (window property) and the watches it recorded (NotifyAll)
PLAYING_PROPERTY = 'script.simkl.playing'
# a show's ids do not change between the hundred OnUpdate events of a season mark
SHOW_CACHE_SECONDS = 60
_shows = {}
# the file search's answers by the name asked, kept across restarts: Simkl's answer for 7 days, "no such file" for 3
SEARCH_HIT_SECONDS = 7 * 86400
SEARCH_MISS_SECONDS = 3 * 86400
SEARCH_MAX = 1000
_searches = None
# Kodi VFS schemes that still name a file (the file search can work with them); everything else with :// is a stream
FILE_SCHEMES = ('smb', 'nfs', 'ftp', 'ftps', 'sftp', 'dav', 'davs', 'special', 'stack', 'zip', 'rar', 'iso9660', 'udf', 'file')
TRAILER_STRING = 20410
# a file Kodi reads as several episodes, the shapes its scanner finds (VideoInfoScanner.cpp): after the first episode
# number another one right after it (S01E01E02, S01E01-02, 1x01x02, E1071E1072), or the same pattern again later in the
# name (S01E01.S01E02, 1x01 - 1x02); only such a name is worth asking about its other episodes
MULTI_EPISODE = re.compile(r'(?i)(?:s\d+[ ._x-]*e\d+(?:[-_ex]+\d+|.*?s\d+[ ._x-]*e\d+)'
                           r'|\d+x\d+(?:[-_ex]+\d+|.*?[\\/._ \[(-]\d+x\d+)'
                           r'|\be(?:p[ ._-]?)?\d+(?:[-_ex]+\d+|.*?[._ -]e(?:p[ ._-]?)?\d+))')


class Player(xbmc.Player):
    """Every callback only hands an event to the service; nothing runs on Kodi's callback thread."""

    def __init__(self, emit):
        super().__init__()
        self.emit = emit
        self.playback_id = 0

    def onAVStarted(self):
        self.playback_id += 1
        self.emit(('av_started', self.playback_id))

    def onPlayBackPaused(self):
        self.emit(('paused', self.playback_id))

    def onPlayBackResumed(self):
        self.emit(('resumed', self.playback_id))

    def onPlayBackSeek(self, seek_time, seek_offset):
        # the offset is in milliseconds; a chapter jump has none and counts as far
        self.emit(('seek', self.playback_id, seek_offset))

    def onPlayBackSeekChapter(self, chapter):
        self.emit(('seek', self.playback_id, None))

    def onPlayBackSpeedChanged(self, speed):
        # Kodi reports the speed as an integer, so a tempo under 1.0x arrives as 0 (a pause never calls this)
        self.emit(('speed', self.playback_id, speed or 1))

    def onPlayBackStopped(self):
        self.emit(('stopped', self.playback_id))

    def onPlayBackEnded(self):
        self.emit(('ended', self.playback_id))

    def onPlayBackError(self):
        self.emit(('error', self.playback_id))

    def sample(self):
        """(position, total) in seconds while a video plays, else None; getTime raises once playback is over."""
        try:
            if self.isPlayingVideo():
                return self.getTime(), self.getTotalTime()
        except RuntimeError:
            pass
        return None

    def playing_file(self):
        try:
            return self.getPlayingFile()
        except RuntimeError:
            return ''


def is_paused():
    return xbmc.getCondVisibility('Player.Paused')


def is_local(path):
    """A file the file search can name: a local path or a file on a share, not a stream."""
    if not path:
        return False
    if '://' not in path:
        return True
    return path.split('://', 1)[0].lower() in FILE_SCHEMES


def inner_paths(path):
    """The file paths behind Kodi's wrapper schemes: the parts of a stack://, the archive behind a zip:// or rar:// (its
    URL sits percent-encoded in the host); any other path is its own."""
    lower = path.lower()
    if lower.startswith('stack://'):
        return [part.strip() for part in path[len('stack://'):].split(' , ')]
    if lower.startswith(('zip://', 'rar://')):
        return [urllib.parse.unquote(path.split('://', 1)[1].partition('/')[0])]
    return [path]


def sanitized(path):
    """The path without the credentials a Kodi source may carry (smb://user:pass@host/...), inside a stack:// or an
    archive path as well."""
    if '://' not in path:
        return path
    scheme, rest = path.split('://', 1)
    if scheme.lower() == 'stack':
        return 'stack://' + ' , '.join(sanitized(part) for part in inner_paths(path))
    host, slash, tail = rest.partition('/')
    if scheme.lower() in ('zip', 'rar'):
        host = urllib.parse.quote(sanitized(urllib.parse.unquote(host)), safe='')
    elif '@' in host:
        host = host.rsplit('@', 1)[1]
    return '%s://%s%s%s' % (scheme, host, slash, tail)


def excluded(path):
    """The exclusion that applies to a playing or library path, or '' when none does."""
    if not path:
        return ''
    lower = path.lower()
    if lower.startswith('pvr://') and settings.get_bool(settings.EXCLUDE_LIVETV, True):
        return 'live tv'
    if lower.startswith(('http://', 'https://')) and settings.get_bool(settings.EXCLUDE_HTTP):
        return 'http'
    if lower.startswith('plugin://') and settings.get_bool(settings.EXCLUDE_PLUGIN):
        return 'plugin'
    folders = [folder.lower() for folder in settings.excluded_paths()]
    # a stacked or archived item carries its folder inside the wrapper path
    if any(inner.lower().startswith(folder) for inner in inner_paths(path) for folder in folders):
        return 'excluded folder'
    return ''


# ---------- item dicts ----------

def _movie_label(title, year):
    return '%s (%s)' % (title, year) if year else title


def _episode_label(showtitle, season, number):
    return '%s S%02dE%02d' % (showtitle, season, number)


def movie_item(details):
    title = details.get('title') or details.get('label') or ''
    year = details.get('year') or None
    return {
        'kind': 'movie',
        'key': 'movie:%d' % details['movieid'],
        'dbid': details['movieid'],
        'title': title,
        'year': year,
        'ids': utils.ids_from(details.get('uniqueid')),
        'file': details.get('file') or '',
        'trailer': details.get('trailer') or '',
        'runtime': int(details.get('runtime') or 0),
        'lastplayed': details.get('lastplayed') or '',
        'playcount': int(details.get('playcount') or 0),
        'userrating': int(details.get('userrating') or 0),
        'label': _movie_label(title, year),
    }


def episode_item(details, show):
    """show: the tvshowdetails of the episode's show (ids live there)."""
    season = int(details.get('season') or 0)
    number = int(details.get('episode') or 0)
    showtitle = show.get('title') or details.get('showtitle') or ''
    return {
        'kind': 'episode',
        'key': 'episode:%d' % details['episodeid'],
        'dbid': details['episodeid'],
        'tvshowid': details.get('tvshowid'),
        'showtitle': showtitle,
        'title': details.get('title') or '',
        'year': show.get('year') or None,
        'season': season,
        'number': number,
        'ids': utils.ids_from(show.get('uniqueid')),
        'episode_ids': episode_ids_from(details.get('uniqueid')),
        'file': details.get('file') or '',
        'runtime': int(details.get('runtime') or 0),
        'lastplayed': details.get('lastplayed') or '',
        'playcount': int(details.get('playcount') or 0),
        'label': _episode_label(showtitle, season, number),
    }


def episode_ids_from(uniqueid):
    """An episode's own ids: only the TVDB episode id is one Simkl resolves."""
    tvdb = str((uniqueid or {}).get('tvdb') or '').strip()
    return {'tvdb': tvdb} if tvdb and tvdb != '0' else {}


def remote_movie(ids, title, year, path='', runtime=0):
    return {
        'kind': 'movie', 'key': 'm:%s' % json.dumps(ids, sort_keys=True), 'dbid': None, 'title': title or '', 'year': year, 'ids': ids,
        'file': path, 'runtime': int(runtime or 0), 'label': _movie_label(title or '', year),
    }


def remote_episode(ids, showtitle, title, year, season, number, path='', runtime=0, episode_ids=None):
    """ids are the SHOW's ids; an unknown season (Kodi reports -1) is Simkl's default, season 1, never the specials."""
    try:
        season = int(season)
    except (TypeError, ValueError):
        season = -1
    if season < 0:
        season = 1
    number = int(number or 0)
    return {
        'kind': 'episode', 'key': 'e:%s:%d:%d' % (json.dumps(ids, sort_keys=True), season, number), 'dbid': None,
        'showtitle': showtitle or title or '', 'title': title or '', 'year': year, 'season': season, 'number': number, 'ids': ids,
        'episode_ids': episode_ids or {}, 'file': path, 'runtime': int(runtime or 0), 'label': _episode_label(showtitle or title or '', season, number),
    }


def library_item(kind, dbid):
    """A movie or episode of the library; None when Kodi has no such row."""
    if kind == 'movie':
        details = utils.jsonrpc('VideoLibrary.GetMovieDetails', {'movieid': dbid, 'properties': MOVIE_PROPERTIES})
        details = (details or {}).get('moviedetails')
        return movie_item(details) if details else None
    details = utils.jsonrpc('VideoLibrary.GetEpisodeDetails', {'episodeid': dbid, 'properties': EPISODE_PROPERTIES})
    details = (details or {}).get('episodedetails')
    if not details:
        return None
    return episode_item(details, show_details(details.get('tvshowid')))


def show_details(tvshowid):
    now = time.time()
    cached = _shows.get(tvshowid)
    if cached and cached[0] > now:
        return cached[1]
    result = utils.jsonrpc('VideoLibrary.GetTVShowDetails', {'tvshowid': tvshowid, 'properties': SHOW_PROPERTIES})
    details = (result or {}).get('tvshowdetails') or {}
    _shows[tvshowid] = (now + SHOW_CACHE_SECONDS, details)
    return details


def season_details(seasonid):
    """{'tvshowid', 'season'} of a library season, {} when Kodi has no such row."""
    result = utils.jsonrpc('VideoLibrary.GetSeasonDetails', {'seasonid': seasonid, 'properties': ['tvshowid', 'season']})
    return (result or {}).get('seasondetails') or {}


def show_episodes(tvshowid, season=None, filter=None):
    """Every episode Kodi has for a show, or for one of its seasons, as items (two JSON-RPC calls, not two per episode);
    filter: a List.Filter of Kodi's for a narrower answer."""
    show = show_details(tvshowid)
    params = {'tvshowid': tvshowid, 'properties': EPISODE_PROPERTIES}
    if season is not None:
        params['season'] = season
    if filter:
        params['filter'] = filter
    result = utils.jsonrpc('VideoLibrary.GetEpisodes', params) or {}
    return [episode_item(details, show) for details in result.get('episodes') or []]


def file_siblings(item):
    """The other episodes of a library episode's file (S01E01E02): Kodi keeps one play state per file, so they are
    watched and unwatched together, and Simkl must hear of each. A name without a second episode number is no such
    file and costs no request; for one that has it, Kodi is asked for that file name alone."""
    name = os.path.basename(item.get('file') or '')
    if item.get('kind') != 'episode' or not item.get('dbid') or not item.get('tvshowid') or not MULTI_EPISODE.search(name):
        return []
    by_name = {'field': 'filename', 'operator': 'is', 'value': name}
    # a stacked file (on Kodi 19 one inside an archive too) is stored under its whole path as the file name
    whole = item['file'].lower().startswith(('stack://', 'rar://', 'zip://'))
    rows = show_episodes(item['tvshowid'], item.get('season'), {'or': [by_name, dict(by_name, value=item['file'])]} if whole else by_name)
    return [e for e in rows if e['file'] == item['file'] and e['dbid'] != item['dbid']]


# Kodi counts a playback as watched from this share of the file on, unless advancedsettings.xml says otherwise (0 or
# over 100: never). Kodi reads that file once at start: the system one, then the user's, which is the profile's when
# the profile has one, else the master profile's (one or the other, never both)
WATCHED_PERCENT = 90.0
SYSTEM_ADVANCED_SETTINGS = 'special://xbmc/system/advancedsettings.xml'
USER_ADVANCED_SETTINGS = ('special://profile/advancedsettings.xml', 'special://masterprofile/advancedsettings.xml')


def kodi_watched_percent():
    """From what share of a file on Kodi counts a playback as watched (playcountminimumpercent), as Kodi reads it."""
    percent = WATCHED_PERCENT
    paths = [xbmcvfs.translatePath(name) for name in USER_ADVANCED_SETTINGS]
    for path in [xbmcvfs.translatePath(SYSTEM_ADVANCED_SETTINGS), next((p for p in paths if os.path.exists(p)), paths[-1])]:
        try:
            node = ElementTree.parse(path).find('./video/playcountminimumpercent')
            percent = min(101.0, max(0.0, float(node.text.strip())))
        except (OSError, ElementTree.ParseError, AttributeError, ValueError):
            continue
    return percent


SET_DETAILS = {'movie': ('VideoLibrary.SetMovieDetails', 'movieid'), 'episode': ('VideoLibrary.SetEpisodeDetails', 'episodeid')}


def _play_state(watched):
    """The fields of a play-state write, as Kodi's own Mark as watched / unwatched sets them: the resume point is cleared
    both ways (a position of 0 clears the bookmark), and an unmark clears the last played date too (an empty date is
    an invalid one to Kodi's handler, which then writes NULL for both, as its own unmark does)."""
    return {'playcount': 1 if watched else 0, 'lastplayed': utils.ts_to_kodi_date(time.time()) if watched else '', 'resume': {'position': 0, 'total': 0}}


def set_watched(items, watched):
    """Kodi's own play state of library items, as its Mark as watched / unwatched sets it. Items already in that state
    are left alone. Returns how many writes Kodi refused."""
    calls = []
    for item in items:
        if ((item.get('playcount') or 0) > 0) == watched:
            continue
        method, param = SET_DETAILS[item['kind']]
        calls.append((method, dict(_play_state(watched), **{param: item['dbid']})))
    answers = utils.jsonrpc_batch(calls)
    return len(calls) if answers is None else sum(1 for answer in answers if 'error' in answer)


def set_file_watched(path, watched):
    """The checkmark of a video outside the library (a Kodi that lacks the method answers an error, which is only logged)."""
    utils.jsonrpc('Files.SetFileDetails', dict(_play_state(watched), file=path, media='video'))


# ---------- what is playing ----------

def window_ids():
    """The home-window values an add-on may have set for its playback (the ids and the "scrobbles itself" flag), as they are."""
    window = xbmcgui.Window(10000)
    return {name: window.getProperty(name) for name in IDS_PROPERTIES + (PAUSED_PROPERTY,)}


def clear_ids(snapshot=None):
    """What an add-on set for the playback that just ended must not apply to the next one (Trakt's add-on does the same);
    script.trakt.paused is Trakt's to clear. snapshot: the values as they were when that playback began; a property
    holding another value now belongs to the next item (an add-on sets it for the next item before Kodi announces the
    end of the previous one) and stays. Two items carrying the same value cannot be told apart: the value goes and the
    second item, if it set nothing of its own, goes untracked, a missed scrobble over a wrong mark. Without a snapshot
    everything goes. The item this add-on announced as playing goes always."""
    window = xbmcgui.Window(10000)
    for name in IDS_PROPERTIES + (PAUSED_PROPERTY,):
        if snapshot is None or window.getProperty(name) == snapshot.get(name, ''):
            window.clearProperty(name)
    window.clearProperty(PLAYING_PROPERTY)


def set_playing(item):
    """Tells skins and add-ons what is being tracked (the home-window property script.simkl.playing, JSON)."""
    xbmcgui.Window(10000).setProperty(PLAYING_PROPERTY, json.dumps(public_item(item)))


def announce(message, item):
    """NotifyAll(script.simkl, <message>, {"data": base64 JSON}) for the other add-ons; base64 keeps Kodi's builtin
    parser from splitting the JSON at its commas (Up Next uses the same trick)."""
    data = base64.b64encode(json.dumps(public_item(item)).encode('utf-8')).decode('ascii')
    xbmc.executebuiltin('NotifyAll(%s, %s, {"data": "%s"})' % (utils.ADDON_ID, message, data))


def public_item(item):
    public = {'kind': item.get('kind'), 'label': item.get('label'), 'ids': item.get('ids') or {}, 'dbid': item.get('dbid')}
    if item.get('kind') == 'episode':
        public.update({'showtitle': item.get('showtitle'), 'season': item.get('season'), 'number': item.get('number')})
    else:
        public.update({'title': item.get('title'), 'year': item.get('year')})
    return public


def _json_ids(raw):
    if not raw:
        return {}
    try:
        return utils.ids_from(json.loads(raw))
    except ValueError:
        return {}


def _flat_ids(custom, prefix):
    """tmdb_id-style properties of the ListItem: with the tvshow. prefix the show's, without it the item's own."""
    return utils.ids_from({name[len(prefix):]: value for name, value in custom.items()
                           if name.lower().startswith(prefix) and '.' not in name[len(prefix):]})


def _property_ids(custom, show, window=True):
    """The ids an add-on provided for what plays, in order of precision: the JSON property on the ListItem, its flat
    per-id properties, then the JSON home-window properties. show: the show's ids of an episode rather than the item's
    own. window: whether the home-window properties count; they do not for a local file, which an add-on never plays,
    since Kodi announces no end for a playback it replaces in place and the add-on's ids would name the file."""
    for name in IDS_PROPERTIES:
        ids = _json_ids(custom.get(name))
        if ids:
            return ids
    ids = _flat_ids(custom, SHOW_PREFIX if show else '')
    if ids or not window:
        return ids
    home = xbmcgui.Window(10000)
    for name in IDS_PROPERTIES:
        ids = _json_ids(home.getProperty(name))
        if ids:
            return ids
    return {}


def _player_ids():
    """The playing tag's ids by info label: once Kodi has a files row for a plugin URL (after a stop with a position),
    Player.GetItem answers from that row, without the ids the add-on listed; the tag itself keeps them."""
    return utils.ids_from({name: xbmc.getInfoLabel('VideoPlayer.UniqueID(%s)' % name) for name in utils.ID_KEYS})


def _infolabel_int(label):
    try:
        return int(xbmc.getInfoLabel(label) or -1)
    except ValueError:
        return -1


def _playing_item():
    """Player.GetItem of the video player, {} when none plays."""
    players = utils.jsonrpc('Player.GetActivePlayers') or []
    player_id = next((p['playerid'] for p in players if p.get('type') == 'video'), None)
    if player_id is None:
        return {}
    return (utils.jsonrpc('Player.GetItem', {'playerid': player_id, 'properties': ITEM_PROPERTIES}) or {}).get('item') or {}


def library_identity():
    """(kind, dbid) of the playing library item, (None, 0) for anything else: a playback left alone still needs them,
    so that Kodi's own play-count bump at its end is not taken for a mark of the user's."""
    data = _playing_item()
    return (data['type'], int(data['id'])) if data.get('type') in ('movie', 'episode') and data.get('id') else (None, 0)


def identify(player):
    """What is playing, as ('ok', item), ('file', candidate) for a file that only the file search can name, or
    ('skip', reason). A non-library episode's own uniqueid is the episode's ids (Kodi's convention); its show's ids
    must come from the script.simkl.ids / script.trakt.ids window property."""
    data = _playing_item()
    if not data:
        return 'skip', 'no video player'
    path = player.playing_file() or data.get('file') or ''
    reason = excluded(path) or excluded(data.get('file') or '') or excluded(data.get('mediapath') or '')
    if reason:
        return 'skip', reason
    custom = data.get('customproperties') or {}
    stream = not is_local(path)
    if any(name in custom for name in EXCLUDE_PROPERTIES):
        return 'skip', 'excluded by the add-on playing it'
    if str(custom.get(PAUSED_PROPERTY, '')).lower() == 'true' or xbmcgui.Window(10000).getProperty(PAUSED_PROPERTY).lower() == 'true':
        return 'skip', 'the add-on playing it scrobbles to Simkl itself (%s)' % PAUSED_PROPERTY

    kind = data.get('type')
    dbid = data.get('id')
    if kind == 'movie' and dbid:
        item = library_item('movie', dbid)
        if item is None:
            return 'skip', 'movie %s is not in the library any more' % dbid
        if item['trailer'] and item['trailer'] in (path, data.get('file')):
            return 'skip', 'trailer'
        item['file'] = path or item['file']
        item['ids'] = item['ids'] or _property_ids(custom, False, stream)
        if item['ids']:
            return 'ok', item
        return ('file', item) if is_local(item['file']) else ('skip', 'movie without ids')
    if kind == 'episode' and dbid:
        item = library_item('episode', dbid)
        if item is None:
            return 'skip', 'episode %s is not in the library any more' % dbid
        item['file'] = path or item['file']
        item['ids'] = item['ids'] or _property_ids(custom, True, stream)
        if item['ids'] or item['episode_ids']:
            return 'ok', item
        return ('file', item) if is_local(item['file']) else ('skip', 'episode without ids')

    season = data.get('season') if isinstance(data.get('season'), int) else -1
    number = data.get('episode') if isinstance(data.get('episode'), int) else -1
    if season < 0:
        season = _infolabel_int('VideoPlayer.Season')
    if number < 0:
        number = _infolabel_int('VideoPlayer.Episode')
    showtitle = data.get('showtitle') or xbmc.getInfoLabel('VideoPlayer.TVShowTitle') or ''
    title = data.get('title') or xbmc.getInfoLabel('VideoPlayer.Title') or data.get('label') or ''
    year = data.get('year') or _infolabel_int('VideoPlayer.Year')
    year = int(year) if year and int(year) > 0 else None
    runtime = data.get('runtime') or 0
    if title.endswith('(%s)' % xbmc.getLocalizedString(TRAILER_STRING)):
        # Kodi's "Play trailer" plays the trailer under a copy of the movie's own tag
        return 'skip', 'trailer'
    episodic = kind == 'episode' or (season >= 0 and number > 0)
    if episodic:
        if number <= 0:
            return 'skip', 'episode without a number'
        show_ids = _property_ids(custom, True, stream)
        if show_ids:
            episode_ids = episode_ids_from(data.get('uniqueid')) or episode_ids_from(_player_ids()) or episode_ids_from(_flat_ids(custom, ''))
            return 'ok', remote_episode(show_ids, showtitle, title, year, season, number, path, runtime, episode_ids)
    else:
        ids = utils.ids_from(data.get('uniqueid')) or _player_ids() or _property_ids(custom, False, stream)
        if ids:
            return 'ok', remote_movie(ids, title, year, path, runtime)
    if is_local(path):
        return 'file', {'kind': None, 'key': 'file:%s' % sanitized(path), 'dbid': None, 'title': title, 'year': year, 'ids': {}, 'file': path,
                        'runtime': int(runtime), 'label': os.path.basename(path)}
    if episodic:
        return 'skip', 'episode without show ids (the add-on playing it should set script.simkl.ids)'
    return 'skip', 'no ids (type %s)' % (kind or 'unknown')


# ---------- the file search ----------

def _search_cache():
    """name -> [stamp, answer] ({} = Simkl knows no such file), read once; a file that cannot be read is only a cache."""
    global _searches
    if _searches is None:
        try:
            data = store.read(store.SEARCH, {})
        except Exception:
            data = {}
        _searches = data if isinstance(data, dict) else {}
    return _searches


def _fresh_search(entry, now):
    return (isinstance(entry, list) and len(entry) == 2 and isinstance(entry[0], (int, float)) and isinstance(entry[1], dict)
            and now - entry[0] <= (SEARCH_HIT_SECONDS if entry[1] else SEARCH_MISS_SECONDS))


def _keep_search(name, answer):
    """Stores an answer; the expired entries go, then the oldest over the cap; a write that fails costs only the next search."""
    cache = _search_cache()
    now = time.time()
    cache[name] = [now, answer]
    for key in [key for key, entry in cache.items() if not _fresh_search(entry, now)]:
        del cache[key]
    for key in sorted(cache, key=lambda k: cache[k][0])[:max(0, len(cache) - SEARCH_MAX)]:
        del cache[key]
    try:
        store.write(store.SEARCH, cache)
    except OSError as exc:
        utils.warn('cannot write the file-search cache: %s' % exc)


def search_file(api, auth, account, item):
    """The item Simkl's file search names for item['file'] (the sanitized path, which carries the folders the search
    reads a title from; the bare name alone is answered with whatever its leftover words match; of a stacked or
    archived item the first part or the archive), None when it knows none; an answer of another kind than the item's
    is not it. Simkl's answer per path is kept, so a replayed file costs no request and is named even offline; a
    failure is not kept. Raises like any request."""
    name = sanitized(inner_paths(item.get('file') or '')[0])
    cached = _search_cache().get(name)
    if _fresh_search(cached, time.time()):
        answer = cached[1]
    else:
        try:
            answer = auth.authorized(lambda token: api.call('POST', '/search/file', {'file': name}, token=token), account)
        except ApiError as exc:
            if exc.status != 404:
                raise
            answer = {}
        if not isinstance(answer, dict) or not answer.get('type'):
            answer = {}
        _keep_search(name, answer)
    if not answer:
        return None
    resolved = _resolved_from(answer, item)
    if resolved is None or (item.get('kind') and item['kind'] != resolved['kind']):
        return None
    if answer['type'] == 'show' and not isinstance(answer.get('episode'), dict) and not _anime_movie(api, resolved['ids']['simkl']):
        utils.log('the file search places %s in a series but at no episode, not reported' % os.path.basename(name))
        return None
    return resolved


def _anime_movie(api, simkl_id):
    """A 'show' answered without an episode is an anime movie or a series whose episode the search could not place;
    only the title's own record tells them apart (a series taken for a movie would be marked or removed as a whole).
    A public record, asked without the token so that the edge cache answers it."""
    try:
        answer = api.call('GET', '/anime/%s' % simkl_id)
    except ApiError as exc:
        if exc.status == 404:
            return False
        raise
    return isinstance(answer, dict) and answer.get('anime_type') == 'movie'


def _resolved_from(answer, item):
    """The /search/file answer as an item keyed by its Simkl id; the library dbid of the file, if any, stays with it."""
    kind = answer.get('type')
    episode = answer.get('episode') if isinstance(answer.get('episode'), dict) else None
    block = answer.get('movie') if kind == 'movie' else answer.get('show')
    if not isinstance(block, dict) or kind not in ('movie', 'episode', 'show') or (kind == 'episode' and episode is None):
        return None
    ids = {'simkl': str((block.get('ids') or {}).get('simkl') or '')}
    if not ids['simkl']:
        return None
    if kind == 'episode':
        resolved = remote_episode(ids, block.get('title') or item.get('showtitle'), episode.get('title'), block.get('year'),
                                  episode.get('season'), episode.get('episode'), item.get('file'))
    else:
        resolved = remote_movie(ids, block.get('title') or item.get('title'), block.get('year'), item.get('file'))
    resolved['dbid'] = item.get('dbid')
    return resolved
