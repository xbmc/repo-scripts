#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""One-way import of the Simkl history into the Kodi library (playcount, last played, cleared resume point) and,
when switched on, the resume positions of what was paused on Simkl."""

import calendar
import os
import threading
import time
import traceback
import urllib.parse

import xbmc
import xbmcgui

from resources.lib import settings, store, utils
from resources.lib.api import ApiError, QUOTA_WAIT, RATE_RETRY, TIMEOUT, TIMEOUT_LONG
from resources.lib.auth import InvalidToken
from resources.lib.history import same_item
from resources.lib.marks import IMPORT_GUARD_SECONDS

TYPES = ('shows', 'anime', 'movies')
BUCKETS = {'shows': 'tv_shows', 'anime': 'anime', 'movies': 'movies'}
# plantowatch too: a title moved there (off completed) must reach the kept copy of the history, or a library growth
# would mark it from the stale row
WATCH_KEYS = ('watching', 'hold', 'completed', 'dropped', 'notinteresting', 'plantowatch')
# /sync/ratings lists unrated titles too unless a rating filter is given, and its 20k cap counts them: this filter is every rating
RATINGS = ','.join(str(rating) for rating in range(1, 11))
SLACK = 60
# the playback look of a box whose Simkl account never reported a pause: older than any activity stamp to come
EPOCH = '1970-01-01T00:00:00Z'
COOLDOWN = 120
# the playback-only run a switched-on Continue watching asks for waits this long: a Sync or Reset pressed on the same
# settings page arrives right after the save and fetches the pauses itself
PLAYBACK_DELAY = 5
# a scheduled run that got no answer (the network was not up) is tried again after this, not at the next interval, a
# few times: a box with no network for days does not keep knocking
AUTO_RETRY = 900
AUTO_RETRIES = 3
CHUNK = 50
RESUME_TOLERANCE = 5
PAGE = 2000
MISS_LINES = 25
MOVIE_PROPERTIES = ['uniqueid', 'playcount', 'lastplayed', 'dateadded', 'runtime', 'resume', 'userrating']
SHOW_PROPERTIES = ['uniqueid', 'userrating']
EPISODE_PROPERTIES = ['tvshowid', 'season', 'episode', 'uniqueid', 'playcount', 'lastplayed', 'dateadded', 'runtime', 'resume', 'firstaired']
SERIES_KEYS = ('tvdb', 'imdb', 'tmdb', 'anidb', 'mal', 'anilist')
MOVIE_KEYS = ('imdb', 'tmdb', 'anidb', 'mal', 'anilist')
ABSOLUTE = ('anidb', 'mal', 'anilist')
# per kind: the details method, its result key, the details setter, the id parameter
RPC = {
    'movie': ('VideoLibrary.GetMovieDetails', 'moviedetails', 'VideoLibrary.SetMovieDetails', 'movieid'),
    'episode': ('VideoLibrary.GetEpisodeDetails', 'episodedetails', 'VideoLibrary.SetEpisodeDetails', 'episodeid'),
    'tvshow': ('VideoLibrary.GetTVShowDetails', 'tvshowdetails', 'VideoLibrary.SetTVShowDetails', 'tvshowid'),
}


class RunError(Exception):
    pass


def _keys(uniqueid, names):
    for name in names:
        value = str((uniqueid or {}).get(name) or '').strip()
        if value and value != '0':
            yield '%s:%s' % (name, value)


def _lookup(index, ids, names):
    """Every hit the ids reach over all the id names, each once (a library may hold a title twice), with the name it
    was first matched by: [(hit, name)]."""
    hits = []
    seen = set()
    for name in names:
        value = str((ids or {}).get(name) or '').strip()
        if not value or value == '0':
            continue
        for hit in index.get('%s:%s' % (name, value), []):
            marker = id(hit) if isinstance(hit, dict) else hit
            if marker in seen:
                continue
            seen.add(marker)
            hits.append((hit, name))
    return hits


def _row(details, kind, dbid):
    return {
        'kind': kind,
        'dbid': dbid,
        'key': '%s:%d' % (kind, dbid),
        'playcount': int(details.get('playcount') or 0),
        'lastplayed': details.get('lastplayed') or '',
        'dateadded': details.get('dateadded') or '',
        'runtime': int(details.get('runtime') or 0),
        'resume': int((details.get('resume') or {}).get('position') or 0),
        'resume_total': int((details.get('resume') or {}).get('total') or 0),
        'userrating': int(details.get('userrating') or 0),
    }


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _max_items(exc):
    return exc.status == 400 and exc.error.lower() == 'max_items'


def _aired_after(firstaired, watched):
    """Whether an episode's air date (Kodi's YYYY-MM-DD, taken as midnight UTC) lies more than a day after a watch;
    False without either. Sliced, not parsed: one per episode row of every completed show."""
    if not firstaired or not watched:
        return False
    text = str(firstaired)
    try:
        aired = calendar.timegm((int(text[0:4]), int(text[5:7]), int(text[8:10]), 0, 0, 0, 0, 0, 0))
    except ValueError:
        return False
    return aired > watched + 86400


def _auto_interval():
    """Seconds between scheduled runs, a little under the setting so a run lands at the same time each day."""
    return max(1, settings.get_int(settings.AUTO_IMPORT_HOURS, 24)) * 3600 - 300


def _simkl_id(entry):
    return str(((entry.get('movie') or entry.get('show') or {}).get('ids') or {}).get('simkl') or '')


def _slim(entry):
    """An all-items row reduced to what the apply steps read, for the cached history: the id block, the status, the
    dates, the rating, the episode rows."""
    block = 'movie' if isinstance(entry.get('movie'), dict) else 'show'
    source = entry.get(block) or {}
    slim = {block: {'ids': source.get('ids') or {}, 'title': source.get('title')}}
    for key in ('status', 'last_watched_at', 'user_rating', 'anime_type', 'mapped_tvdb_seasons'):
        if entry.get(key) is not None:
            slim[key] = entry[key]
    seasons = [{'number': season.get('number'),
                'episodes': [{key: episode[key] for key in ('number', 'watched_at', 'tvdb', 'ids') if episode.get(key) is not None}
                             for episode in season.get('episodes') or [] if isinstance(episode, dict)]}
               for season in entry.get('seasons') or [] if isinstance(season, dict)]
    if seasons:
        slim['seasons'] = seasons
    return slim


def _query(kind=None, episodes=True, tvdb_ids=True):
    """The all-items parameters of one call. Shows need no anime mapping (extended=full) and get only the episodes really
    recorded ('original'): the virtual rows the server would add for every episode of a completed show are the bulk of a
    big history, and completion is applied here from Kodi's own episode list. Anime keeps them (their TVDB mapping is the
    server's to build), and so does the delta of an incremental run, one call for every type. episodes=False: titles only.
    tvdb_ids=False: without the TVDB episode ids, a third of the server's budget per episode (the rows then match by numbering)."""
    extended = 'full' if kind == 'shows' else 'full_anime_seasons'
    flag = ('original' if kind == 'shows' else 'yes') if episodes else ''
    return 'extended=%s&episode_watched_at=yes%s%s' % (extended, '&episode_tvdb_id=yes' if tvdb_ids else '', '&include_all_episodes=' + flag if flag else '')


def _normalize(status):
    return 'dropped' if status == 'notinteresting' else (status or '')


def _latest(buckets, keys):
    latest = ''
    for bucket in buckets:
        for key in keys:
            value = (bucket or {}).get(key)
            if value and value > latest:
                latest = value
    return latest


class LibraryIndex:
    """Provider-id and season/episode lookups over the Kodi library, read once per run and only the parts a run needs.
    A title the library holds twice (1080p and 4K, two sources) is every one of its rows: each lookup answers a list."""

    def __init__(self):
        self.movies = {}
        self.series = {}
        self.shows = {}
        self.by_coord = {}
        self.by_tvdb = {}
        # the regular episodes (no specials) of each Kodi show: what a completed show marks as a whole
        self.episodes_of = {}
        # every movie and episode row by the queue's key (kind:dbid), for the unmark ledger
        self.by_key = {}
        self.movies_read = False
        self.shows_read = False
        self.counts = {'movies': 0, 'shows': 0, 'episodes': 0}

    def prepare(self, types):
        if 'movies' in types or 'anime' in types:
            self.read_movies()
        if 'shows' in types or 'anime' in types:
            self.read_shows()

    @staticmethod
    def _query(method, params):
        result = utils.jsonrpc(method, params)
        if result is None:
            raise RunError(utils.get_str(32269))
        return result

    def read_movies(self):
        if self.movies_read:
            return
        self.movies_read = True
        result = self._query('VideoLibrary.GetMovies', {'properties': MOVIE_PROPERTIES})
        for details in result.get('movies') or []:
            self.counts['movies'] += 1
            row = _row(details, 'movie', details['movieid'])
            self.by_key[row['key']] = row
            for key in _keys(details.get('uniqueid'), MOVIE_KEYS):
                self.movies.setdefault(key, []).append(row)

    def read_shows(self):
        if self.shows_read:
            return
        self.shows_read = True
        result = self._query('VideoLibrary.GetTVShows', {'properties': SHOW_PROPERTIES})
        for details in result.get('tvshows') or []:
            self.counts['shows'] += 1
            self.shows[details['tvshowid']] = {'kind': 'tvshow', 'dbid': details['tvshowid'], 'userrating': int(details.get('userrating') or 0)}
            for key in _keys(details.get('uniqueid'), SERIES_KEYS):
                self.series.setdefault(key, []).append(details['tvshowid'])
        # every episode of the library, in pages so a big library does not come back as one answer
        start = 0
        while True:
            result = self._query('VideoLibrary.GetEpisodes', {'properties': EPISODE_PROPERTIES, 'sort': {'method': 'none'},
                                                              'limits': {'start': start, 'end': start + PAGE}})
            episodes = result.get('episodes') or []
            for details in episodes:
                self.counts['episodes'] += 1
                row = _row(details, 'episode', details['episodeid'])
                self.by_key[row['key']] = row
                tvdb = str((details.get('uniqueid') or {}).get('tvdb') or '').strip()
                # the row's own TVDB episode id ('' without one): a twin copy without ids is still this episode
                row['tvdb'] = tvdb if tvdb != '0' else ''
                row['firstaired'] = details.get('firstaired') or ''
                if row['tvdb']:
                    self.by_tvdb.setdefault(tvdb, []).append(row)
                self.by_coord.setdefault('%s:%s:%s' % (details.get('tvshowid'), details.get('season'), details.get('episode')), []).append(row)
                if int(details.get('season') or 0) > 0:
                    self.episodes_of.setdefault(details.get('tvshowid'), []).append(row)
            start += PAGE
            if len(episodes) < PAGE or start >= int((result.get('limits') or {}).get('total') or 0):
                break

    def describe(self):
        return 'indexed %s, %s' % ('%d movies' % self.counts['movies'] if self.movies_read else 'no movies (not needed)',
                                   '%d shows, %d episodes' % (self.counts['shows'], self.counts['episodes']) if self.shows_read else 'no shows (not needed)')

    def find_movie(self, ids):
        """The movie rows these ids reach."""
        self.read_movies()
        return [row for row, _ in _lookup(self.movies, ids, MOVIE_KEYS)]

    def find_series(self, ids):
        """[(tvshowid, matched_by)]: tvdb/imdb/tmdb libraries number episodes by TVDB seasons, anidb/mal/anilist ones absolutely."""
        self.read_shows()
        return _lookup(self.series, ids, SERIES_KEYS)

    def find_episode(self, tvshowid, season, number):
        return self.by_coord.get('%s:%s:%s' % (tvshowid, season, number), [])

    def find_episode_by_tvdb(self, tvdb_id):
        return self.by_tvdb.get(str(tvdb_id), [])


class Job:
    def __init__(self, reset):
        self.reset = reset
        self.seen = set()
        self.writes = []
        self.movies_marked = 0
        self.episodes_marked = 0
        self.already = 0
        self.refreshed = 0
        self.movies_missing = 0
        self.shows_missing = 0
        self.episodes_missing = 0
        self.resume_updated = 0
        self.changed = 0
        self.write_failures = 0
        self.miss_lines = 0
        self.rated = set()
        self.rating_writes = []
        # per rated Kodi row, the Simkl ids of its title: the write re-checks the queue for them
        self.rating_ids = {}
        self.ratings_updated = 0
        self.partial = set()
        self.unrated = set()
        # key -> time of the library items the user unmarked in Kodi; the ones Simkl saw watched after that, marked now;
        # read_at: when the library index was read (an unmark after it cannot be settled by that index); removed: the
        # keys whose unmark Simkl applied (any later watched row is the user's new word, a show's date included)
        self.unmarked = {}
        self.kept = 0
        self.rewatched = []
        self.read_at = None
        self.removed = set()
        # the ids of the titles whose Kodi rating is still on its way to Simkl: left alone this run
        self.pending_ratings = []
        # a scheduled run holds its library writes while a video plays
        self.scheduled = False

    def missed(self, what):
        """A debug line per item Simkl has and Kodi lacks, capped: a big history would write thousands (the counts are in the summary)."""
        if self.miss_lines < MISS_LINES:
            utils.log('not in the library: %s' % what)
        elif self.miss_lines == MISS_LINES:
            utils.log('further items not in the library are not listed, see the counts of the summary')
        self.miss_lines += 1


class Importer:
    def __init__(self, api, auth, marks, history):
        self.api = api
        self.auth = auth
        self.marks = marks
        self.history = history
        self.monitor = xbmc.Monitor()
        self.thread = None
        self.last_finish = 0.0
        self.playback_full = False
        self.playback_due = 0.0
        self.run_account = ''
        self.last_auto = None
        self.retries = 0
        # a daily quota holds the scheduled check until the reset Simkl named
        self.retry_at = 0.0
        # the gate of the scheduled check: the last playback, the service start, the last look at the library. Kodi's
        # idle counter runs from its first read: read here, so an input before the first evaluation already counts
        self.used_at = 0.0
        self.idle_from = time.time()
        xbmc.getGlobalIdleTime()
        self.looked_at = 0.0

    def running(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self, mode='check', manual=True, scheduled=False, force=False):
        """mode: check (what changed since the last run, or the first full import), reset (full + refresh dates),
        playback (only the continue-watching step)."""
        if not self.auth.logged_in():
            if manual:
                utils.notify(utils.get_str(32224))
            return False
        if not settings.account_id():
            if manual:
                utils.notify(utils.get_str(32210))
            return False
        if self.running():
            if manual:
                utils.notify(utils.get_str(32225))
            return False
        if not force and time.time() - self.last_finish < COOLDOWN:
            if manual:
                utils.notify(utils.get_str(32228))
            return False
        self.thread = threading.Thread(target=self._run, args=(mode, manual, scheduled), name='simkl-import')
        self.thread.daemon = True
        self.thread.start()
        return True

    def auto_check(self):
        """Once the interval has passed, and only for a box in use since the last check: an input (Kodi's start alone
        is none), a playback, or a change of the library (another box's on a shared one, looked at once per interval).
        A box nobody uses asks Simkl nothing, however long it stays on; the first key press after weeks away runs the
        check within the minute."""
        if not settings.get_bool(settings.AUTO_IMPORT) or not self.auth.logged_in() or self.running():
            return
        now = time.time()
        if self.last_auto is None:
            # a stamp from a clock that ran ahead would hold the sync until the real time caught up
            self.last_auto = min(utils.parse_stamp(self._load().get('last_auto_run_at')) or 0, now)
        if now - self.last_auto < _auto_interval() or now < self.retry_at:
            return
        if self._used_since(self.last_auto, now) or self._library_changed(now):
            self.start('check', manual=False, scheduled=True)

    def note_use(self):
        self.used_at = time.time()

    def _used_since(self, since, now):
        """An input or a playback after `since`. Kodi's idle time counts from its last input, else from the service
        start, so a box that only booted is not in use until someone presses a key."""
        idle = xbmc.getGlobalIdleTime()
        return self.used_at > since or idle + 1 < min(now - since, now - self.idle_from)

    def _library_changed(self, now):
        """The totals against the last run's, once per interval (four local counts): a shared library changes under a
        box nobody touches. Without a baseline (no run succeeded yet) nothing is "changed": a first import that keeps
        failing must not run again and again on a box nobody uses."""
        if now - self.looked_at < _auto_interval():
            return False
        self.looked_at = now
        stored = self._load().get('library_totals')
        return bool(stored) and self._library_totals() != stored

    def request_playback_full(self):
        """Continue watching was switched on: fetch the pauses, whatever the last look says, and only that (a box that
        never imported its watched history must not start a full import because of this switch). Not at once: a Sync
        or Reset pressed on the same settings page arrives right after the save, and a run already going would refuse
        it; given PLAYBACK_DELAY it runs first and fetches the pauses itself (playback_full)."""
        self.playback_full = True
        self.playback_due = time.time() + PLAYBACK_DELAY

    def start_due(self):
        """Every turn of the service loop: the playback-only run once its moment has passed, unless a run fetched the
        pauses meanwhile."""
        if not self.playback_due or time.time() < self.playback_due or self.running():
            return
        self.playback_due = 0.0
        if self.playback_full:
            self.start('playback', manual=False, force=True)

    # ---------- state ----------

    def _load(self):
        try:
            data = store.read(store.IMPORT_STATE, {})
        except Exception:
            data = {}
        return data if isinstance(data, dict) else {}

    def _save(self, state):
        try:
            store.write(store.IMPORT_STATE, state)
        except OSError as exc:
            utils.error('cannot write the import state: %s' % exc)

    @staticmethod
    def _load_cache(account):
        """The history as Simkl last answered it, per type by Simkl id; None when there is none for this account (the
        first run, a reset, an unreadable file), which makes the run fetch it whole."""
        try:
            data = store.read(store.HISTORY, None)
        except Exception:
            data = None
        if not isinstance(data, dict) or data.get('account') != account or not all(isinstance(data.get(kind), dict) for kind in TYPES):
            return None
        return data

    @staticmethod
    def _save_cache(cache):
        """A copy that could not be written fails the run: its cursors stay, and the next run fetches the same changes
        again against the copy still on disk (store.write leaves the old file in place)."""
        try:
            store.write(store.HISTORY, cache)
        except OSError as exc:
            utils.error('cannot write the history cache: %s' % exc)
            raise RunError(utils.get_str(32313))

    # ---------- the run (its own thread) ----------

    def _run(self, mode, manual, scheduled):
        started = time.time()
        state = self._load()
        state.setdefault('cursors', {})
        job = Job(mode == 'reset')
        job.scheduled = scheduled
        progress = None
        status = missing = message = ''
        failed = False
        try:
            if manual:
                progress = xbmcgui.DialogProgressBG()
                progress.create('Simkl', utils.get_str(32232))
            account = settings.account_id()
            self.run_account = account
            if job.reset or state.get('account') != account:
                state['cursors'] = {}
                state['full_import_at'] = ''
                state['synced_at'] = ''
                state['playback_cursor'] = ''
                state.pop('rated', None)
                state.pop('removed', None)
            if job.reset:
                # a reset takes Simkl's state again, the items unmarked in Kodi included
                self.history.forget_unmarks(self.history.library_unmarks())
            if scheduled:
                # written before the work: a run that takes Kodi down with it must not start again at the next tick
                state['last_auto_run_at'] = utils.utc_stamp(started)
                self.last_auto = started
                self._save(state)
            activities = self._get('/sync/activities')
            activities = activities if isinstance(activities, dict) else {}
            job.pending_ratings = self.history.pending_ratings()
            cursors = {kind: _latest([activities.get(BUCKETS[kind])], WATCH_KEYS) for kind in TYPES}
            rated = {kind: _latest([activities.get(BUCKETS[kind])], ('rated_at',)) for kind in TYPES}
            removed = {kind: _latest([activities.get(BUCKETS[kind])], ('removed_from_list',)) for kind in TYPES}
            watched = mode != 'playback'
            totals = self._library_totals() if watched else {}
            grown = any(totals[key] > int((state.get('library_totals') or {}).get(key) or 0) for key in totals)
            full = watched and (mode == 'reset' or not state.get('full_import_at') or not os.path.exists(store.path(store.HISTORY)))
            changed = [kind for kind in TYPES if cursors[kind] and cursors[kind] > (state['cursors'].get(kind) or '')] if watched and not full else []
            gone = [kind for kind in TYPES if removed[kind] and removed[kind] > ((state.get('removed') or {}).get(kind) or '')] if watched and not full else []
            cache = None
            if watched and not full and (changed or grown or gone or self._rated_moved(state, rated)):
                # the kept copy is parsed only when something is to be applied to it (megabytes on a big account); one
                # that cannot be read, or another account's, is fetched whole again
                cache = self._load_cache(account)
                if cache is None:
                    full, changed, gone = True, [], []
            parts = (['full'] if full else []) + (['changes in ' + ', '.join(changed)] if changed else []) + (['the library grew'] if grown and not full else [])
            utils.log('import started: %s, %s' % (mode, ', '.join(parts) or 'nothing changed'))
            unreconciled = set()
            index = LibraryIndex()
            if full or changed or grown:
                self._progress(progress, 10, 32233)
                job.read_at = time.time()
                index.prepare(TYPES if full or grown else changed)
                utils.log('import: %s' % index.describe())
                # read after the library: an unmark made meanwhile is still queued and counts
                job.unmarked = self.history.library_unmarks()
                job.removed = self.history.removed_on_simkl(job.unmarked)
            if full:
                # the whole history, per type: into the cache and the library
                cache = {'account': account}
                for position, kind in enumerate(TYPES):
                    self._progress(progress, 20 + position * 25, 32234)
                    entries = [entry for entry in self._fetch_type(job, kind, None) if isinstance(entry, dict)]
                    cache[kind] = {_simkl_id(entry): _slim(entry) for entry in entries if _simkl_id(entry)}
                    self._apply(job, index, kind, entries)
                    self._write(job, job.writes)
                    job.writes = []
                self._save_cache(cache)
            else:
                response = {}
                if changed:
                    self._progress(progress, 20, 32234)
                    # no watermark yet (Simkl had no activity at the last run): everything, never the box's own clock
                    since = utils.parse_stamp(state.get('synced_at'))
                    response = self._fetch_all(job, utils.utc_stamp(since - SLACK) if since else None)
                    for kind in TYPES:
                        cache[kind].update((_simkl_id(entry), _slim(entry)) for entry in response.get(kind) or [] if isinstance(entry, dict) and _simkl_id(entry))
                    self._save_cache(cache)
                if gone:
                    unreconciled = self._prune_removed(cache, gone)
                if cache is not None:
                    # Simkl's newer ratings before the kept copy: a cached rating applied first would keep them out (job.rated)
                    self._changed_ratings(job, index, state, rated, cache)
                # what Kodi got since the last run takes its marks from the cached history, no request for it; the
                # delta alone is applied otherwise
                for kind in TYPES:
                    self._apply(job, index, kind, list(cache[kind].values()) if grown else response.get(kind) or [])
                self._write(job, job.writes)
                job.writes = []
            if full and job.partial and settings.get_bool(settings.IMPORT_RATINGS, True):
                # a type fetched per status came without its plan-to-watch rows (and dropped movies): their ratings, one call per type
                for kind in sorted(job.partial):
                    rows = self._all_ratings(kind)
                    if rows is None:
                        job.unrated.add(kind)
                        continue
                    for entry in rows:
                        self._check_abort()
                        self._rate_entry(job, index, entry, kind == 'movies' or entry.get('anime_type') == 'movie')
            self._write_ratings(job)
            self._progress(progress, 90, 32235)
            self._continue_watching(job, index, state, activities, grown)
            if job.write_failures:
                raise RunError(utils.get_str(32267).format(job.write_failures))
            if watched:
                self.history.forget_unmarks(self._settled_unmarks(job, index))
                for kind in TYPES:
                    if cursors[kind]:
                        state['cursors'][kind] = cursors[kind]
                if full:
                    state['full_import_at'] = utils.utc_stamp()
                # a type whose removals could not be reconciled keeps its old stamp: the next run sees them moved again
                kept = state.get('removed') or {}
                state['removed'] = {kind: stamp for kind, stamp in ((kind, kept.get(kind, '') if kind in unreconciled else stamp) for kind, stamp in removed.items()) if stamp}
                # counted again after the writes: the marks this run made are not growth. A title that arrived during the
                # run is not in the index, which was read before the fetch: the baseline then stays at the start's count,
                # so the next run sees the growth and takes it from the kept copy
                after = self._library_totals()
                state['library_totals'] = totals if any(after[key] > totals[key] for key in ('movies', 'episodes')) else after
                state['synced_at'] = activities.get('all') or ''
                # the rated stamps move only while ratings are imported, so switching the import on later still fetches
                # everything; a type whose ratings were skipped (too many for one call) keeps its old stamp and is asked again
                if settings.get_bool(settings.IMPORT_RATINGS, True):
                    stored = state.get('rated') or {}
                    for kind in job.unrated:
                        rated[kind] = stored.get(kind, '')
                    state['rated'] = {kind: stamp for kind, stamp in rated.items() if stamp}
            state['account'] = account
            status, message, missing = self._summary(job, not (full or changed or grown))
            # the toast stops before the not-in-the-library counts: on screen they are noise, in the log and the
            # settings they are the answer to "why was X not marked"
            toast = message
            if missing:
                message += ' %s: %s' % (utils.get_str(32279), missing)
        except Exception as exc:
            failed = True
            status = message = toast = utils.get_str(32231).format(self._reason(exc))
            missing = ''
            if scheduled and isinstance(exc, ApiError) and exc.transport and self.retries < AUTO_RETRIES:
                # no answer at all: the box may have started or woken without its network, so this is tried again soon;
                # any other failure (a refusal, a token, the cap) waits for the next interval
                self.retries += 1
                self.last_auto = started - _auto_interval() + AUTO_RETRY
                state['last_auto_run_at'] = utils.utc_stamp(self.last_auto)
        finally:
            if scheduled and not failed:
                self.retries = 0
            if progress is not None:
                progress.close()
            state['last_import_at'] = utils.utc_stamp()
            state['last_summary'] = message
            self._save(state)
            # two settings lines: the result, and what Simkl has that Kodi lacks (one line would not fit the page)
            settings.put(settings.IMPORT_STATUS, status)
            settings.put(settings.IMPORT_MISSING, missing)
            if mode != 'playback':
                # a playback-only run (one light call) arms no cooldown: the Sync pressed after the switch must run
                self.last_finish = time.time()
            utils.log('import: %s' % message)
            if manual or (not failed and (job.movies_marked or job.episodes_marked or job.resume_updated)):
                utils.notify(toast, time_ms=8000)

    @staticmethod
    def _library_totals():
        """How many movies and episodes Kodi has, and how many of them are unwatched, from the limits of one-item answers.
        A library that grew since the last run, or got unwatched rows for old items (a file replaced, a source moved),
        gets the whole history again, so what Kodi added since then gets its marks without a reset."""
        totals = {}
        for key, method in (('movies', 'VideoLibrary.GetMovies'), ('episodes', 'VideoLibrary.GetEpisodes')):
            for suffix, params in (('', {}), ('_unwatched', {'filter': {'field': 'playcount', 'operator': 'is', 'value': '0'}})):
                result = utils.jsonrpc(method, dict(params, limits={'start': 0, 'end': 1})) or {}
                totals[key + suffix] = int((result.get('limits') or {}).get('total') or 0)
        return totals

    def _breathe(self, scheduled=False):
        """One call that waits for Kodi's GUI turn: the writes of a big run would otherwise queue up faster than the
        active window redraws for them, freezing the GUI and holding back the echoes the marks guard is set for. A
        scheduled run (started idle) also holds its writes while a video plays unpaused; a manual one was asked for."""
        while scheduled and xbmc.getCondVisibility('Player.HasVideo + !Player.Paused'):
            if self.monitor.waitForAbort(5):
                raise RunError(utils.get_str(32266))
        xbmc.getCondVisibility('Player.HasMedia')

    @staticmethod
    def _reason(exc):
        if isinstance(exc, InvalidToken):
            return utils.get_str(32265)
        if isinstance(exc, RunError):
            return str(exc)
        if isinstance(exc, ApiError):
            return utils.get_str(32246) if exc.transport else utils.get_str(32247).format(exc.status)
        utils.error('import failed: %s' % traceback.format_exc())
        return repr(exc)

    @staticmethod
    def _progress(progress, percent, string_id, *args):
        if progress is not None:
            progress.update(percent, 'Simkl', utils.get_str(string_id).format(*args))

    def _check_abort(self):
        if self.monitor.abortRequested():
            raise RunError(utils.get_str(32266))

    # ---------- Simkl ----------

    def _get(self, path, timeout=TIMEOUT):
        """A GET with Simkl's limits honoured: a short limit is tried again after RATE_RETRY, a few times; the daily
        quota ends the run at once and holds the next scheduled one until the reset Simkl named."""
        for attempt in range(5):
            self._check_abort()
            try:
                return self.auth.authorized(lambda token: self.api.call('GET', path, token=token, timeout=timeout), self.run_account)
            except ApiError as exc:
                if exc.quota:
                    self.retry_at = time.time() + (exc.retry_after or QUOTA_WAIT)
                    raise RunError(utils.get_str(32245))
                if not exc.rate_limited:
                    raise
                if attempt == 4:
                    raise RunError(utils.get_str(32245))
                utils.log('import: rate limited, retrying in %d s' % RATE_RETRY)
                if self.monitor.waitForAbort(RATE_RETRY):
                    raise RunError(utils.get_str(32266))

    def _dropped(self):
        return 'dropped' if self.auth.is_v2() else 'notinteresting'

    def _all_items(self, suffix, date_from, query=None):
        path = '/sync/all-items%s?%s' % (suffix, query or _query())
        if date_from:
            path += '&date_from=' + urllib.parse.quote(date_from)
        answer = self._get(path, timeout=TIMEOUT_LONG)
        return answer if isinstance(answer, dict) else {}

    def _prune_removed(self, cache, kinds):
        """A title removed from the Simkl list never comes back through a delta: the kept copy of each type with a
        removal is cut down to the ids Simkl still lists. Returns the types that could not be listed (their copy stays
        as it is and their removal stamp is not advanced, so the next run asks again)."""
        unreconciled = set()
        for kind in kinds:
            listed = self._listed_ids(kind)
            if listed is None:
                unreconciled.add(kind)
                continue
            before = len(cache[kind])
            cache[kind] = {sid: row for sid, row in cache[kind].items() if sid in listed}
            utils.log('import: %d %s removed on Simkl dropped from the kept copy' % (before - len(cache[kind]), kind))
        self._save_cache(cache)
        return unreconciled

    def _listed_ids(self, kind):
        """The Simkl ids of every title of a type: one ids-only call, or one per status when the type is over the cap;
        None when a status is over it too."""
        try:
            return self._ids_only('/' + kind, kind)
        except ApiError as exc:
            if not _max_items(exc):
                raise
        statuses = ('completed', 'plantowatch', self._dropped()) if kind == 'movies' else ('completed', 'watching', 'hold', self._dropped(), 'plantowatch')
        listed = set()
        for status in statuses:
            try:
                listed |= self._ids_only('/%s/%s' % (kind, status), kind)
            except ApiError as exc:
                if not _max_items(exc):
                    raise
                utils.warn('import: too many %s/%s to list their ids in one call, the titles removed on Simkl stay in the kept copy' % (kind, status))
                return None
        return listed

    def _ids_only(self, suffix, kind):
        return {_simkl_id(entry) for entry in self._all_items(suffix, None, 'extended=simkl_ids_only').get(kind) or [] if isinstance(entry, dict)}

    def _fetch_all(self, job, date_from):
        """Everything changed since date_from in one call; when Simkl refuses the size, per type, then per status."""
        try:
            return self._all_items('', date_from)
        except ApiError as exc:
            if not _max_items(exc):
                raise
        utils.log('import: too many changed items for one call, fetching per type')
        return {kind: self._fetch_type(job, kind, date_from) for kind in TYPES}

    def _fetch_type(self, job, kind, date_from):
        query = _query(kind)
        try:
            return self._all_items('/' + kind, date_from, query).get(kind) or []
        except ApiError as exc:
            if not _max_items(exc):
                raise
        utils.log('import: too many %s for one call, fetching per status' % kind)
        # the statuses left out carry no watches, but they can be rated: a full run fetches this type's ratings apart
        job.partial.add(kind)
        statuses = ('completed',) if kind == 'movies' else ('completed', 'watching', 'hold', self._dropped())
        if date_from:
            # a delta must bring back what moved off these statuses as well, or the kept copy keeps a stale completed row
            statuses += ('plantowatch',) + ((self._dropped(),) if kind == 'movies' else ())
        return [entry for status in statuses for entry in self._fetch_status(kind, status, date_from, query)]

    def _fetch_status(self, kind, status, date_from, query):
        """The rows of one status. When Simkl refuses the size, once more without the TVDB episode ids (a third of the
        server's budget per episode), and for the completed TV shows alone once more as titles (every regular episode
        Kodi has of such a show is marked at the show's date); movies have no episode rows to shed, their cap is the
        item count. Refused at the end: the run fails, it never loops."""
        variants = [query]
        if kind != 'movies':
            variants.append(_query(kind, True, False))
            if kind == 'shows' and status == 'completed':
                variants.append(_query(kind, False))
        for variant in variants:
            try:
                return self._all_items('/%s/%s' % (kind, status), date_from, variant).get(kind) or []
            except ApiError as exc:
                if not _max_items(exc):
                    raise
                utils.log('import: too many %s/%s for one call, asking for less' % (kind, status))
        raise RunError(utils.get_str(32244))

    # ---------- watched ----------

    def _apply(self, job, index, kind, entries):
        for entry in entries:
            self._check_abort()
            if not isinstance(entry, dict):
                continue
            status = _normalize(entry.get('status'))
            movie = kind == 'movies' or entry.get('anime_type') == 'movie'
            # a plan-to-watch or dropped title has nothing to mark, but its rating counts: the rated stamps advance for it too
            if status == 'plantowatch' or (movie and status != 'completed'):
                self._rate_entry(job, index, entry, movie)
            elif movie:
                self._apply_movie(job, index, entry)
            else:
                self._apply_show(job, index, entry, kind == 'anime', status)

    def _apply_movie(self, job, index, entry):
        block = entry.get('movie') or entry.get('show') or {}
        rows = index.find_movie(block.get('ids') or {})
        if not rows:
            job.movies_missing += 1
            job.missed('movie %s' % block.get('title'))
            return
        for row in rows:
            self._rate(job, row, entry)
            if self._mark(job, row, utils.parse_stamp(entry.get('last_watched_at')), None):
                job.movies_marked += 1

    def _apply_show(self, job, index, entry, anime, status):
        block = entry.get('show') or {}
        shows = index.find_series(block.get('ids') or {})
        for tvshowid, _ in shows:
            self._rate(job, index.shows.get(tvshowid), entry)
        fallback = utils.parse_stamp(entry.get('last_watched_at'))
        seasons = [s for s in entry.get('seasons') or [] if isinstance(s, dict)]
        # a completed show carries synthesized episode rows that all share the show's date; the episode really watched
        # last shares it too, so a date several episodes share counts as synthesized and may not replace a Kodi date
        shared = sum(1 for s in seasons for e in s.get('episodes') or [] if utils.parse_stamp(e.get('watched_at')) == fallback)
        synthesized = status == 'completed' and shared > 1
        hits = 0
        for season in seasons:
            for episode in season.get('episodes') or []:
                if not isinstance(episode, dict):
                    continue
                rows = self._find_episode(index, shows, anime, entry, season, episode)
                if not rows:
                    if shows:
                        job.episodes_missing += 1
                    continue
                hits += 1
                own = utils.parse_stamp(episode.get('watched_at'))
                if synthesized and own == fallback:
                    own = None
                for row in rows:
                    if self._mark(job, row, own, fallback):
                        job.episodes_marked += 1
        if status == 'completed' and not anime:
            # a completed TV show: every regular episode Kodi has is watched, the ones without a row at the show's date,
            # except one that aired after that date: a new season of a show Simkl set back to watching without a word
            # (no activity moves for it), which the kept copy still holds as completed. A row Kodi has as watched is
            # counted as before, whatever its date
            for tvshowid, _ in shows:
                for row in index.episodes_of.get(tvshowid, []):
                    if (row['playcount'] > 0 or not _aired_after(row.get('firstaired'), fallback)) and self._mark(job, row, None, fallback):
                        job.episodes_marked += 1
        if not shows and hits == 0:
            job.shows_missing += 1
            job.missed('show %s' % block.get('title'))

    # ---------- ratings ----------

    @staticmethod
    def _rate(job, row, entry):
        """Simkl's rating of a matched movie or show becomes Kodi's user rating when it differs; a rating Simkl does not
        have is left alone in Kodi (never removed)."""
        rating = _int(entry.get('user_rating'))
        if row is None or not rating or not 1 <= rating <= 10 or not settings.get_bool(settings.IMPORT_RATINGS, True):
            return
        key = (row['kind'], row['dbid'])
        if key in job.rated or row['userrating'] == rating:
            return
        ids = (entry.get('movie') or entry.get('show') or {}).get('ids') or {}
        if any(same_item(ids, pending) for pending in job.pending_ratings):
            # Kodi's own rating of it is still on its way to Simkl: the newer one
            return
        job.rated.add(key)
        job.rating_ids[key] = ids
        job.rating_writes.append((row, {'userrating': rating}))

    def _rate_entry(self, job, index, entry, movie):
        if movie:
            block = entry.get('movie') or entry.get('show') or {}
            for row in index.find_movie(block.get('ids') or {}):
                self._rate(job, row, entry)
        else:
            for tvshowid, _ in index.find_series((entry.get('show') or {}).get('ids') or {}):
                self._rate(job, index.shows.get(tvshowid), entry)

    def _all_ratings(self, kind):
        """Every rating of one type, one call: for a full run whose rows of that type came per status, and for an incremental
        run with no stamp to ask from. Only rated rows count against the cap; over it (20k ratings of one type) None: skipped
        this run, and the caller leaves the type's stamp where it was."""
        try:
            answer = self._get('/sync/ratings/%s/%s' % (kind, RATINGS), timeout=TIMEOUT_LONG)
        except ApiError as exc:
            if not _max_items(exc):
                raise
            utils.warn('import: too many %s ratings for one call, not imported this run' % kind)
            return None
        return [entry for entry in ((answer if isinstance(answer, dict) else {}).get(kind) or []) if isinstance(entry, dict)]

    @staticmethod
    def _rated_moved(state, rated):
        """The types whose ratings moved on Simkl since the stored stamp, while ratings are imported at all."""
        if not settings.get_bool(settings.IMPORT_RATINGS, True):
            return []
        stored = state.get('rated') or {}
        return [kind for kind in TYPES if rated[kind] and rated[kind] > (stored.get(kind) or '')]

    def _changed_ratings(self, job, index, state, rated, cache):
        """An incremental run: a rating changed on its own does not come back through all-items, but the activities
        feed says when ratings moved and /sync/ratings lists them by that time; with no stamp to ask from, every rating."""
        stored = state.get('rated') or {}
        moved = self._rated_moved(state, rated)
        if not moved:
            return
        since = min(utils.parse_stamp(stored[kind]) or 0 for kind in moved if stored.get(kind)) if all(stored.get(kind) for kind in moved) else None
        touched = False
        if since:
            # no rating filter on the delta: it is small (rateTimeChanged since the stamp), and a removal moves that
            # stamp too and comes back as user_rating null, which the kept copy must learn
            answer = self._get('/sync/ratings?date_from=%s' % urllib.parse.quote(utils.utc_stamp(since - SLACK)), timeout=TIMEOUT_LONG)
            rows = {kind: (answer if isinstance(answer, dict) else {}).get(kind) or [] for kind in moved}
        else:
            rows = {kind: self._all_ratings(kind) for kind in moved}
            job.unrated.update(kind for kind, got in rows.items() if got is None)
            for kind, got in rows.items():
                if got is None:
                    continue
                # the whole list names every rated title of the type: a cached rating of any other title (kept while
                # the import was off) was removed on Simkl since, and a run applying the copy later must not write it
                still_rated = {_simkl_id(entry) for entry in got if isinstance(entry, dict)}
                for sid, cached in cache[kind].items():
                    if 'user_rating' in cached and sid not in still_rated:
                        cached.pop('user_rating')
                        touched = True
            rows = {kind: got or [] for kind, got in rows.items()}
        for kind in moved:
            for entry in rows[kind]:
                if not isinstance(entry, dict):
                    continue
                self._check_abort()
                self._rate_entry(job, index, entry, kind == 'movies' or entry.get('anime_type') == 'movie')
                cached = cache[kind].get(_simkl_id(entry))
                if cached is not None and cached.get('user_rating') != entry.get('user_rating'):
                    # the kept copy follows, a removal included: a run applying it later must not write the old rating back
                    if entry.get('user_rating') is None:
                        cached.pop('user_rating', None)
                    else:
                        cached['user_rating'] = entry['user_rating']
                    touched = True
        if touched:
            self._save_cache(cache)

    def _write_ratings(self, job):
        """VideoLibrary.Set*Details with the user rating, in batches. Each batch is re-read first: a rating changed in
        Kodi since the index was read, or one queued for Simkl meanwhile, is the newer word and is left alone."""
        for start in range(0, len(job.rating_writes), CHUNK):
            self._check_abort()
            self._breathe(job.scheduled)
            chunk = job.rating_writes[start:start + CHUNK]
            # the queue as of this chunk: a rating queued while the previous one was written counts too
            pending = self.history.pending_ratings()
            current = utils.jsonrpc_batch([(RPC[row['kind']][0], {RPC[row['kind']][3]: row['dbid'], 'properties': ['userrating']}) for row, _ in chunk])
            if current is None:
                job.write_failures += len(chunk)
                continue
            calls = []
            kept = []
            for (row, fields), answer in zip(chunk, current):
                details = (answer.get('result') or {}).get(RPC[row['kind']][1]) or {}
                if not details:
                    job.write_failures += 1
                    continue
                ids = job.rating_ids.get((row['kind'], row['dbid']), {})
                if int(details.get('userrating') or 0) != row['userrating'] or any(same_item(ids, queued) for queued in pending):
                    job.changed += 1
                    continue
                calls.append((RPC[row['kind']][2], dict(fields, **{RPC[row['kind']][3]: row['dbid']})))
                kept.append((row, fields))
            if not calls:
                continue
            answers = utils.jsonrpc_batch(calls)
            failed = len(calls) if answers is None else sum(1 for answer in answers if 'error' in answer)
            job.write_failures += failed
            job.ratings_updated += len(calls) - failed
            for (row, fields), answer in zip(kept, answers or []):
                if 'error' not in answer:
                    row['userrating'] = fields['userrating']
        job.rating_writes = []

    @staticmethod
    def _find_episode(index, shows, anime, entry, season, episode):
        """The Kodi rows of one Simkl episode, every copy: the rows carrying its TVDB episode id (a hit even when the
        series itself did not match), plus the rows at its coordinates in every matched show (TVDB ones for anime matched
        through tvdb/imdb/tmdb). When Simkl names the id, a coordinate row carrying another one is another episode
        (Kodi's TMDB scraper numbers some shows otherwise and stores TVDB's episode id on each row) and stays out, hit
        or not; one without ids (a copy scraped without them) is this one."""
        tvdb_id = str((episode.get('ids') or {}).get('tvdb_id') or '')
        rows = list(index.find_episode_by_tvdb(tvdb_id)) if tvdb_id else []
        for tvshowid, matched_by in shows:
            if anime and matched_by not in ABSOLUTE:
                number, number_in = Importer._tvdb_coordinates(entry, season, episode)
            else:
                number, number_in = _int(season.get('number')), _int(episode.get('number'))
            rows += [row for row in index.find_episode(tvshowid, number, number_in)
                     if not (tvdb_id and row.get('tvdb') and row['tvdb'] != tvdb_id) and not any(row is known for known in rows)]
        return rows

    @staticmethod
    def _tvdb_coordinates(entry, season, episode):
        """Anime matched through tvdb/imdb/tmdb is stored with TVDB seasons in Kodi. The per-episode block is what this
        trusts: without a mapping the server fills it with Simkl's own numbers. A tvdb season of 0 is deliberate (specials)
        and never falls through to mapped_tvdb_seasons, which cannot express season 0."""
        tvdb = episode.get('tvdb') or {}
        s = _int(tvdb.get('season'))
        e = _int(tvdb.get('episode'))
        if s is not None and e is not None and s > 0 and e > 0:
            return s, e
        if s == 0 and e is not None and e > 0:
            return 0, e
        number = _int(episode.get('number'))
        if _int(season.get('number')) == 0:
            return 0, number
        mapped = entry.get('mapped_tvdb_seasons')
        if isinstance(mapped, list) and len(mapped) == 1 and _int(mapped[0]) and _int(mapped[0]) > 0:
            return _int(mapped[0]), number
        return 1, number

    @staticmethod
    def _mark(job, row, own, fallback):
        """True when the item gets its first watched mark. Items Kodi already has as watched are left alone, unless a
        reset asks for Simkl's own date of that very item. An item the user unmarked in Kodi after Simkl's watch of it
        stays unwatched; a newer Simkl watch marks it and closes the unmark. A resume point Kodi set after the Simkl
        watch is a re-viewing in progress and stays, with its date; an item Simkl has no date for gets its Kodi added
        date, not 'now'."""
        key = (row['kind'], row['dbid'])
        if key in job.seen:
            return False
        job.seen.add(key)
        if row['playcount'] > 0:
            job.already += 1
            if not job.reset or own is None:
                return False
            job.refreshed += 1
            job.writes.append((row, {'lastplayed': utils.ts_to_kodi_date(own)}))
            return False
        unmarked = job.unmarked.get(row['key'])
        # for an unmark Simkl never got only the item's own date counts (a show's last watch says nothing about this
        # episode); for one Simkl applied, any later watched row is the user's new word
        simkl = own or (fallback if row['key'] in job.removed else None)
        if unmarked and not (simkl and simkl > unmarked):
            job.kept += 1
            return False
        if unmarked:
            job.rewatched.append(row['key'])
        fields = {'playcount': max(1, row['playcount'])}
        watched = own or fallback
        local_newer = row['resume'] > 0 and watched and (utils.kodi_date_to_ts(row['lastplayed']) or 0) > watched
        if not local_newer:
            fields['resume'] = {'position': 0, 'total': 0}
            if watched:
                fields['lastplayed'] = utils.ts_to_kodi_date(watched)
            elif row['dateadded']:
                fields['lastplayed'] = row['dateadded']
        job.writes.append((row, fields))
        return True

    @staticmethod
    def _settled_unmarks(job, index):
        """The ledger entries this run closes, with the unmark time it saw: the items Simkl saw watched after the unmark
        (marked now) and, in the library parts read, the items watched again in Kodi or gone from it. An unmark made
        after the index was read is not judged by that index."""
        settled = {key: job.unmarked[key] for key in job.rewatched if key in job.unmarked}
        for key, when in job.unmarked.items():
            if key in settled or job.read_at is None or when >= job.read_at or not (index.movies_read if key.startswith('movie:') else index.shows_read):
                continue
            row = index.by_key.get(key)
            if row is None or row['playcount'] > 0:
                settled[key] = when
        return settled

    def _write(self, job, writes):
        """VideoLibrary.Set*Details in chunks of 50. Each chunk is re-read first: an item whose play state changed in Kodi
        since the index was read is left alone. Every written item is guarded so its OnUpdate is not taken for a manual
        mark. Failed writes are counted on the job and fail the run, so the cursors do not move past them."""
        written = 0
        for start in range(0, len(writes), CHUNK):
            self._check_abort()
            # before the chunk, the first one included: a scheduled run holds its writes while a video plays unpaused
            self._breathe(job.scheduled)
            chunk = writes[start:start + CHUNK]
            current = utils.jsonrpc_batch([(RPC[row['kind']][0], {RPC[row['kind']][3]: row['dbid'], 'properties': ['playcount', 'lastplayed']}) for row, _ in chunk])
            if current is None:
                job.write_failures += len(chunk)
                continue
            calls = []
            pending = []
            for (row, fields), answer in zip(chunk, current):
                details = (answer.get('result') or {}).get(RPC[row['kind']][1]) or {}
                if not details:
                    job.write_failures += 1
                    continue
                if int(details.get('playcount') or 0) != row['playcount'] or (details.get('lastplayed') or '') != row['lastplayed']:
                    job.changed += 1
                    continue
                if 'playcount' in fields:
                    # only a changed play count comes back as an OnUpdate the marks could take for the user's; a date-only
                    # write is announced without a play count, which the marks drop (marks.py), and would leave the guard hanging
                    self.marks.guard(row['kind'], row['dbid'], IMPORT_GUARD_SECONDS)
                calls.append((RPC[row['kind']][2], dict(fields, **{RPC[row['kind']][3]: row['dbid']})))
                pending.append((row, fields))
            if not calls:
                continue
            answers = utils.jsonrpc_batch(calls)
            failed = len(calls) if answers is None else sum(1 for answer in answers if 'error' in answer)
            if failed:
                job.write_failures += failed
                utils.warn('%d of %d library writes failed%s' % (failed, len(calls), '' if answers is None else ': %s' % next(a['error'] for a in answers if 'error' in a)))
            written += len(calls) - failed
            # the index row follows a successful write, so a later step of the same run (the resume positions) sees the
            # item as Kodi now has it instead of taking its own write for a change made in Kodi meanwhile
            for (row, fields), answer in zip(pending, answers or []):
                if 'error' in answer:
                    continue
                row['playcount'] = fields.get('playcount', row['playcount'])
                row['lastplayed'] = fields.get('lastplayed', row['lastplayed'])
                if 'resume' in fields:
                    row['resume'] = fields['resume']['position']
        return written

    # ---------- continue watching ----------

    def _continue_watching(self, job, index, state, activities, grown=False):
        """Simkl's pauses as Kodi resume points. The whole list each time (one row per paused title, the watched ones
        left out by Simkl: a short answer, and no cursor to miss a pause by), asked for on a full run, when Simkl's
        playback activity moved since the last look, when the switch was just turned on, or when the library grew (a
        pause fetched for a title Kodi did not have yet reaches it now). The look is stamped with Simkl's own activity
        time, never this box's clock."""
        if not settings.get_bool(settings.CONTINUE_WATCHING):
            return
        latest = _latest([activities.get(BUCKETS[kind]) for kind in TYPES], ('playback',))
        stored = state.get('playback_cursor') or ''
        if stored and not self.playback_full and not grown and (not latest or latest <= stored):
            return
        index.prepare(('movies', 'shows'))
        rows = self._get('/sync/playback', timeout=TIMEOUT_LONG)
        writes = []
        for row in rows if isinstance(rows, list) else []:
            writes.extend(self._resume_write(index, row))
        failures = job.write_failures
        job.resume_updated = self._write(job, writes)
        utils.log('import: %d resume positions updated from %d Simkl pauses' % (job.resume_updated, len(rows) if isinstance(rows, list) else 0))
        if job.write_failures != failures:
            return
        state['playback_cursor'] = latest or EPOCH
        self.playback_full = False

    @staticmethod
    def _resume_write(index, row):
        """The writes of a Simkl pause, one per copy of the item Kodi has unwatched (none for most rows)."""
        if not isinstance(row, dict):
            return []
        try:
            progress = float(row.get('progress') or 0)
        except (TypeError, ValueError):
            return []
        paused = utils.parse_stamp(row.get('paused_at'))
        if not paused or progress <= 0:
            return []
        if row.get('type') == 'movie':
            items = index.find_movie((row.get('movie') or {}).get('ids') or {})
        else:
            block = row.get('show') or row.get('anime') or {}
            episode = row.get('episode') or {}
            items = []
            for tvshowid, matched_by in index.find_series(block.get('ids') or {}):
                if 'anime' in row and matched_by not in ABSOLUTE and _int(episode.get('tvdb_number')):
                    season, number = _int(episode.get('tvdb_season')), _int(episode.get('tvdb_number'))
                else:
                    season, number = _int(episode.get('season')), _int(episode.get('number'))
                items += [item for item in index.find_episode(tvshowid, season, number) if not any(item is known for known in items)]
        writes = [Importer._resume_for(item, paused, progress) for item in items]
        return [write for write in writes if write is not None]

    @staticmethod
    def _resume_for(item, paused, progress):
        """A Simkl pause lands in Kodi only when the item is unwatched there, the pause is newer than Kodi's own last
        play, the length is known and the position really differs; a pause at Kodi's own bookmark is this box's early
        stop coming back from Simkl, stamped a second later by the server, and is left alone."""
        if item['playcount'] > 0:
            return None
        # Kodi's bookmark knows the file's real length; the scraper's runtime stands in when there is no bookmark
        total = item.get('resume_total') or item['runtime']
        if total <= 0:
            return None
        last = utils.kodi_date_to_ts(item['lastplayed'])
        if last and paused <= last:
            return None
        if item['resume'] and abs(100.0 * item['resume'] / total - progress) <= 1.0:
            return None
        position = int(round(total * progress / 100.0))
        if position < 1 or abs(position - item['resume']) <= RESUME_TOLERANCE:
            return None
        return item, {'resume': {'position': position, 'total': total}, 'lastplayed': utils.ts_to_kodi_date(paused)}

    # ---------- result ----------

    @staticmethod
    def _summary(job, nothing):
        """(the settings line, the full text for the toast and the log, the not-in-the-library counts or '' when nothing
        was fetched; the log gets them appended, the toast does not). The settings line is built for the width of the
        settings page, about sixty characters: the marks, and one more figure, the refreshed dates of a reset or the
        resume points."""
        parts = []
        if nothing:
            parts.append(utils.get_str(32229))
            short = utils.get_str(32229)
        else:
            if job.reset:
                parts.append(utils.get_str(32248))
            parts.append(utils.get_str(32230).format(job.movies_marked, job.episodes_marked, job.already))
            if job.refreshed:
                parts.append(utils.get_str(32259).format(job.refreshed))
            short = utils.get_str(32283).format(job.episodes_marked, job.movies_marked)
            if job.refreshed:
                short += '; ' + utils.get_str(32284).format(job.refreshed)
            elif job.resume_updated:
                short += '; ' + utils.get_str(32285).format(job.resume_updated)
        if job.resume_updated:
            parts.append(utils.get_str(32243).format(job.resume_updated))
        if job.ratings_updated:
            parts.append(utils.get_str(32298).format(job.ratings_updated))
        if job.kept:
            parts.append(utils.get_str(32302).format(job.kept))
        if job.changed:
            parts.append(utils.get_str(32268).format(job.changed))
        missing = '' if nothing else utils.get_str(32280).format(job.movies_missing, job.shows_missing, job.episodes_missing)
        return short, ' '.join(parts), missing
