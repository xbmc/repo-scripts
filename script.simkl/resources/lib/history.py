#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""The write-ahead history queue: every watch of a finished playback and every manual mark goes through here and
is sent to /sync/history (or /sync/history/remove) in as few requests as the server rules allow."""

import json
import threading
import time
import traceback
import uuid

import xbmc

from resources.lib import player as playerlib
from resources.lib import settings, store, utils
from resources.lib.api import ApiError, QUOTA_WAIT, RATE_RETRY
from resources.lib.auth import InvalidToken

WATCH = 'watch'
MARK = 'mark'
UNMARK = 'unmark'
RATE = 'rate'

# a show marked at once can be a thousand episodes and more (One Piece): the cap bounds queue.json, never one action
MAX_ENTRIES = 10000
# entries per /sync/history request
BATCH = 1000
MAX_AGE = 30 * 86400
HOLD = 2.0
# Kodi's unmark of a season or a show announces every episode within milliseconds; a person needs a second per item
BURST = 1.0
START_DELAY = 10
BACKOFF_MIN = 30
BACKOFF_MAX = 3600


def show_key(item):
    return json.dumps(item.get('ids') or {}, sort_keys=True)


def scrobble_payload(item, progress):
    """The body of a /scrobble call for a movie or an episode."""
    payload = {'progress': round(float(progress), 2)}
    if item['kind'] == 'movie':
        payload['movie'] = _title_block(item.get('title'), item.get('year'), item.get('ids'))
    else:
        payload['show'] = _title_block(item.get('showtitle'), item.get('year'), item.get('ids'))
        episode = {'season': int(item.get('season') or 0), 'number': int(item.get('number') or 0)}
        if item.get('episode_ids'):
            episode['ids'] = item['episode_ids']
        payload['episode'] = episode
    return payload


def _title_block(title, year, ids):
    block = {'ids': ids or {}}
    if title:
        block['title'] = title
    if year:
        block['year'] = int(year)
    return block


def same_item(ids, other):
    """Two id sets name the same title when any id they both carry agrees (Kodi's are strings, Simkl's may be numbers)."""
    return any(str(ids[key]) == str(other[key]) for key in ids if ids.get(key) and other.get(key))


def _owned(entry, account):
    """The flush sends an entry recorded before the account id was known under the current account, so it counts as this
    account's here too; another account's entries are not this one's to cancel (a file action that finished after a re-login)."""
    return not entry.get('account') or entry['account'] == account


def _library_key(key):
    """A Kodi library item's key (kind:dbid). The other keys name files or ids and are forgotten with age; these only
    once the sync finds the item watched again or gone."""
    return key.startswith(('movie:', 'episode:'))


def _unfound(item, not_found):
    """Whether Simkl's not_found names this item: a movie by its ids, an episode by its show's ids (the whole show
    unknown) or by its show's ids with its season and number."""
    ids = item.get('ids') or {}
    movie = item.get('kind') == 'movie'
    rows = [row for row in not_found.get('movies' if movie else 'shows') or [] if isinstance(row, dict)]
    if any(same_item(ids, row.get('ids') or {}) for row in rows):
        return True
    if movie:
        return False
    season, number = int(item.get('season') or 0), int(item.get('number') or 0)
    for row in not_found.get('episodes') or []:
        if not isinstance(row, dict) or not same_item(ids, row.get('ids') or {}):
            continue
        seasons = [s for s in row.get('seasons') or [] if isinstance(s, dict)]
        if not seasons or any(int(s.get('number') or 0) == season and any(int(e.get('number') or 0) == number for e in s.get('episodes') or [] if isinstance(e, dict)) for s in seasons):
            return True
    return False


def _held_back(entry):
    """A wait of the entry's own after a request of its own failed (a file search, the list check before a movie
    unmark): 30 s, doubling up to an hour, while the rest of the flush goes on."""
    entry['retry_wait'] = min(BACKOFF_MAX, 2 * entry.get('retry_wait', 0)) or BACKOFF_MIN
    entry['retry_at'] = time.time() + entry['retry_wait']
    return entry['retry_wait']


def _parts(entries):
    return [entries[start:start + BATCH] for start in range(0, len(entries), BATCH)]


def list_request(entries):
    """movies[] for /sync/add-to-list: an unmarked movie goes to Plan to watch."""
    return {'movies': [dict(_title_block(e['item'].get('title'), e['item'].get('year'), e['item'].get('ids')), to='plantowatch') for e in entries]}


def ratings_request(entries):
    """movies[] and shows[] for /sync/ratings (ids and rating) or /sync/ratings/remove (ids alone)."""
    request = {}
    for entry in entries:
        block = {'ids': entry['item']['ids']}
        if entry['rating']:
            block['rating'] = entry['rating']
        request.setdefault(entry['item']['bucket'], []).append(block)
    return request


def _request_for(path, batch, merge):
    if '/add-to-list' in path:
        return list_request(batch)
    if '/sync/ratings' in path:
        return ratings_request(batch)
    return history_request(batch, merge, '/history/remove' in path)


def _bulk(entries):
    """The library unmarks that arrived in a burst, consecutive announcements less than BURST apart (Kodi's unmark of a
    season, a show or a set); a person needs longer between two items."""
    ordered = sorted(entries, key=lambda e: float(e.get('window') or 0))
    bulk = set()
    group = ordered[:1]
    for before, entry in zip(ordered, ordered[1:]):
        if float(entry.get('window') or 0) - float(before.get('window') or 0) < BURST:
            group.append(entry)
            continue
        if len(group) > 1:
            bulk.update(e['id'] for e in group)
        group = [entry]
    if len(group) > 1:
        bulk.update(e['id'] for e in group)
    return bulk


def history_request(entries, merge, remove=False):
    """movies[] and shows[] for /sync/history: episodes nested under their show; with merge the episodes of one
    show share one entry, without it every entry is its own show entry (rewatch detection is per show entry)."""
    movies = []
    shows = []
    index = {}
    for entry in entries:
        item = entry['item']
        date = None if remove else (entry.get('watched_at') or utils.utc_stamp(entry['time']))
        if item['kind'] == 'movie':
            movie = _title_block(item.get('title'), item.get('year'), item.get('ids'))
            if date:
                movie['watched_at'] = date
                if entry.get('rewatch'):
                    movie['rewatch_status'] = 'completed'
            movies.append(movie)
            continue
        # a show without ids is never merged: its key would pool every id-less show under the first one's title
        merged = merge and bool(item.get('ids'))
        key = show_key(item)
        show = index.get(key) if merged else None
        if show is None:
            show = _title_block(item.get('showtitle'), item.get('year'), item.get('ids'))
            show['seasons'] = []
            shows.append(show)
            if merged:
                index[key] = show
        number = int(item.get('season') or 0)
        season = next((s for s in show['seasons'] if s['number'] == number), None)
        if season is None:
            season = {'number': number, 'episodes': []}
            show['seasons'].append(season)
        episode = {'number': int(item.get('number') or 0)}
        if date:
            episode['watched_at'] = date
        if item.get('episode_ids'):
            episode['ids'] = item['episode_ids']
        season['episodes'].append(episode)
    return {'movies': movies, 'shows': shows}


class History:
    def __init__(self, api, auth, ask=None):
        """ask(entry_id): hands an unmarked movie to the service for its question (remove, Plan to watch or keep); the
        answer comes back through answer_unmark. Without it such an unmark is kept on Simkl."""
        self.api = api
        self.auth = auth
        self.ask = ask
        self.lock = threading.Lock()
        self.entries = []
        # key -> time of the user's last unmark (delivered, dropped or bulk): a watch older than it is a leftover, not the
        # user's last word, and the sync leaves a library item unwatched after it (library_unmarks). The ledger belongs
        # to an account and survives a sign-out and a reconnect to it; the unmarks Simkl applied are noted apart
        self.unmarked = {}
        self.unmarked_account = ''
        self.sent_unmarks = {}
        try:
            data = store.read(store.QUEUE, {})
        except Exception:
            # unreadable: moved aside, the queue starts fresh and stays on disk
            store.quarantine(store.QUEUE)
            data = {}
        if isinstance(data, dict):
            self.entries = list(data.get('entries') or [])
            self.unmarked = dict(data.get('unmarked') or {})
            self.unmarked_account = str(data.get('unmarked_account') or '')
            self.sent_unmarks = dict(data.get('sent_unmarks') or {})
        # an entry still in flight when Kodi closed never got its stop acknowledged: flushed like a failed one; a movie
        # unmark whose question got no answer is asked again at the first tick
        self.reask = []
        for entry in self.entries:
            entry['inflight'] = False
            if entry['kind'] == UNMARK and entry['item'].get('kind') == 'movie' and not entry.get('action') and not entry.get('window'):
                entry['asking'] = True
                self.reask.append(entry['id'])
        # library unmarks still inside their window when Kodi closed are settled at the first tick
        self.window_unmarks = [e['id'] for e in self.entries if e.get('window')]
        self.window_last = 0.0
        self.window_folder = False
        self.due = time.time() + START_DELAY if self.entries else None
        self.backoff = BACKOFF_MIN
        self.flushing = False
        self.waiting_toast = False
        self.quota_toast = False
        self.dirty = False
        # the watches Simkl recorded during the current flush: one toast for them all at its end
        self.reported = []

    # ---------- storage ----------

    def _save(self):
        """Written at once: a watch event before its stop goes out, and every change made from the sender."""
        self.dirty = False
        self.unmarked_account = self.unmarked_account or settings.account_id()
        try:
            store.write(store.QUEUE, {'entries': self.entries, 'unmarked': self.unmarked, 'unmarked_account': self.unmarked_account, 'sent_unmarks': self.sent_unmarks})
        except OSError as exc:
            utils.error('cannot write the queue: %s' % exc)

    def _save_later(self):
        """Manual marks arrive by the hundred when a show is marked: the worker writes them once per loop turn."""
        self.dirty = True

    def save_if_dirty(self):
        if not self.dirty:
            return
        with self.lock:
            if self.dirty:
                self._save()

    def _new(self, kind, item, account=None):
        return {
            'id': uuid.uuid4().hex,
            'kind': kind,
            'key': item['key'],
            'item': item,
            'time': time.time(),
            'account': settings.account_id() if account is None else account,
            'inflight': False,
            'attempts': 0,
            'rewatch': False,
            'watched_at': None,
        }

    def _supersede(self, key, account, kinds, before=None):
        """Drops this account's queued actions of these kinds for the item, all of them or only those up to a point in time."""
        count = len(self.entries)
        self.entries = [e for e in self.entries if not (e['key'] == key and _owned(e, account) and e['kind'] in kinds and (before is None or e['time'] <= before))]
        return count - len(self.entries)

    def _append(self, entry):
        """Over the cap the oldest manual marks go first; a watch event is evicted only when nothing else is left."""
        self.entries.append(entry)
        over = len(self.entries) - MAX_ENTRIES
        if over <= 0:
            return
        for kinds in ((MARK, UNMARK), (WATCH,)):
            kept = []
            for e in self.entries:
                if over > 0 and e['kind'] in kinds and e is not entry:
                    over -= 1
                    continue
                kept.append(e)
            self.entries = kept
        utils.warn('history queue over %d entries, the oldest were dropped' % MAX_ENTRIES)

    def _remember(self, entries):
        for entry in entries:
            self.unmarked[entry['key']] = max(self.unmarked.get(entry['key'], 0), entry['time'])

    def _forget(self, key):
        """The user's later word is "watched": the unmark is no more, applied or not."""
        self.sent_unmarks.pop(key, None)
        return self.unmarked.pop(key, None) is not None

    def _ask(self, entry_ids):
        """The questions for unmarked movies, after the lock is released; without a service to ask, they are kept."""
        for entry_id in entry_ids:
            if self.ask is None:
                self.answer_unmark(entry_id, 'keep')
            else:
                self.ask(entry_id)

    # ---------- recording ----------

    def watch_event(self, item, watched_ts, rewatch, account=None, inflight=True):
        """Persisted before the /scrobble/stop goes out, in flight until the stop is acknowledged or released. A watch
        supersedes only the unmarks queued before it; one queued or delivered after it is the user's later word, and
        then nothing is recorded (None). account: the one the playback belongs to, by default the connected one.
        inflight=False: delivered by the queue alone (an episode sharing the played file), held like a mark."""
        with self.lock:
            entry = self._new(WATCH, item, account)
            if self.unmarked.get(item['key'], 0) > watched_ts or any(e['key'] == item['key'] and _owned(e, entry['account']) and e['kind'] == UNMARK and e['time'] > watched_ts for e in self.entries):
                return None
            self._supersede(item['key'], entry['account'], (UNMARK,), watched_ts)
            entry['time'] = watched_ts
            entry['inflight'] = inflight
            entry['watched_at'] = utils.utc_stamp(watched_ts)
            entry['rewatch'] = bool(rewatch)
            self._append(entry)
            self._save()
        if not inflight:
            self._hold()
        return entry['id']

    def add_mark(self, item, watched_ts=None, account=None):
        """account: the one the action was issued under when it was not the moment of queuing (a file identified first)."""
        with self.lock:
            entry = self._new(MARK, item, account)
            self._supersede(item['key'], entry['account'], (MARK, UNMARK))
            self._forget(item['key'])
            entry['watched_at'] = utils.utc_stamp(watched_ts) if watched_ts else None
            self._append(entry)
            self._save_later()
        self._hold()

    def add_unmark(self, item, explicit=False, account=None, arrived=None, siblings=()):
        """explicit = from the context menu, applied at once. A library unmark first waits in a window of HOLD seconds:
        a burst of them (a season, a show) is a bulk unmark, which is neither sent nor allowed to touch what is queued.
        arrived: when Kodi announced it (the burst is judged by Kodi's timing, not by how fast the events were handled).
        siblings: the other episodes of the item's file, unmarked with it once the window settles it as a single. A
        movie is first asked about (removed, moved to Plan to watch, or kept on Simkl). Kodi's echo of this add-on's
        own write for an explicit unmark queues nothing: the ledger has it, and a window entry would supersede the
        asked entry and ask again."""
        asks = []
        with self.lock:
            entry = self._new(UNMARK, item, account)
            if explicit:
                self._supersede(item['key'], entry['account'], (MARK, UNMARK, WATCH))
                entry['explicit'] = True
                if item.get('kind') == 'movie':
                    entry['asking'] = True
                    asks.append(entry['id'])
            else:
                if any(e['kind'] == UNMARK and e.get('explicit') and e['key'] == item['key'] and _owned(e, entry['account']) for e in self.entries):
                    return
                entry['window'] = arrived or time.time()
                if siblings:
                    entry['siblings'] = list(siblings)
                self.window_unmarks.append(entry['id'])
                self.window_last = entry['window']
            self._append(entry)
            self._save_later()
        self._ask(asks)
        self._hold()

    def asking_label(self, entry_id):
        """The label of an unmarked movie whose question is open, None once it is answered or gone (marked again)."""
        with self.lock:
            return next((e['item'].get('label') or '' for e in self.entries if e['id'] == entry_id and e.get('asking')), None)

    def answer_unmark(self, entry_id, choice):
        """The user's word on an unmarked movie: 'remove' or 'plan' sends it at the next flush, anything else keeps it
        on Simkl (the unmark stays in the ledger). The entry, or None when it is gone (the movie was marked again)."""
        with self.lock:
            entry = next((e for e in self.entries if e['id'] == entry_id), None)
            if entry is None:
                return None
            entry.pop('asking', None)
            if choice in ('remove', 'plan'):
                entry['action'] = choice
            else:
                self._remember([entry])
                self.entries = [e for e in self.entries if e is not entry]
            self._save()
        if entry.get('action'):
            self.due = time.time()
        return entry

    def note_folder_unmark(self):
        with self.lock:
            self.window_folder = True
            self.window_last = time.time()
        self._hold()

    def add_rating(self, target, rating, account=None):
        """(bucket, ids, label) rated 1-10, or 0 to remove the rating: queued like a mark, the latest rating of a title wins."""
        bucket, ids, label = target
        item = {'kind': 'rating', 'key': 'rate:%s:%s' % (bucket, json.dumps(ids, sort_keys=True)), 'bucket': bucket, 'ids': ids, 'label': label}
        with self.lock:
            entry = self._new(RATE, item, account)
            entry['rating'] = int(rating or 0)
            self._supersede(item['key'], entry['account'], (RATE,))
            self._append(entry)
            self._save_later()
        self._hold()

    def pending_ratings(self):
        """The ids of the titles whose rating is still to be delivered: the sync leaves their Kodi rating alone meanwhile."""
        with self.lock:
            return [e['item']['ids'] for e in self.entries if e['kind'] == RATE]

    def live_watch_succeeded(self, key, watched_ts, account=None):
        """A watch Simkl just recorded drops the unmarks queued before it; a later unmark still goes out."""
        with self.lock:
            changed = self._supersede(key, account or settings.account_id(), (UNMARK,), watched_ts)
            if self.unmarked.get(key, 0) <= watched_ts and self._forget(key):
                changed = True
            if changed:
                self._save()

    def ack(self, entry_id):
        with self.lock:
            before = len(self.entries)
            self.entries = [e for e in self.entries if e['id'] != entry_id]
            if len(self.entries) != before:
                self._save()

    def release(self, entry_id, toast=True, error=None):
        """A stop that failed: its watch goes out with the queue instead. error: what Simkl answered, when a limit it
        named sets the wait instead of the outage back-off."""
        with self.lock:
            for entry in self.entries:
                if entry['id'] == entry_id:
                    entry['inflight'] = False
                    entry['attempts'] += 1
            self._save()
        if error is None or not self._wait_out(error):
            self._retry_later(toast)

    # ---------- the sync's view ----------

    def library_unmarks(self):
        """key -> time of the library items the user unmarked in Kodi: the delivered, the bulk and the still queued ones."""
        with self.lock:
            ledger = {key: ts for key, ts in self.unmarked.items() if _library_key(key)}
            for entry in self.entries:
                if entry['kind'] == UNMARK and _library_key(entry['key']):
                    ledger[entry['key']] = max(ledger.get(entry['key'], 0), entry['time'])
            return ledger

    def forget_unmarks(self, ledger):
        """Drops the ledger entries the sync settled ({key: the unmark time it saw}), each only while no newer unmark of
        that key came in meanwhile."""
        with self.lock:
            dropped = [key for key, when in ledger.items() if 0 < self.unmarked.get(key, 0) <= when and self._forget(key)]
            if dropped:
                self._save_later()

    def removed_on_simkl(self, ledger):
        """The ledger keys whose last unmark Simkl applied (delivered as a removal or a move): for those a later watched
        row of any date is the user's new word and the sync may mark them again."""
        with self.lock:
            return set(key for key, when in ledger.items() if self.sent_unmarks.get(key) == when)

    def note_library_state(self, key, played, when):
        """Kodi's own watched state of a library item changed, whatever the switches say: the ledger follows it, so the
        sync neither re-marks what the user unmarked nor keeps unwatched what they marked again."""
        with self.lock:
            if played:
                changed = self._forget(key)
            else:
                changed = self.unmarked.get(key, 0) < when
                if changed:
                    self.unmarked[key] = when
            if changed:
                self._save_later()

    # ---------- scheduling ----------

    def _hold(self):
        self.due = time.time() + HOLD

    def on_login(self, previous, current):
        """A login to another account (or the first verified one) drops what was recorded under the old or an unknown
        one. The ledger goes only with a real change of account: a reconnect after a rejected token, or a sign-out and
        a sign-in to the same account, keeps the unmarks."""
        if previous != current:
            with self.lock:
                kept = [e for e in self.entries if e['account'] == current]
                dropped = len(self.entries) - len(kept)
                self.entries = kept
                if self.unmarked_account and self.unmarked_account != current:
                    self.unmarked = {}
                    self.sent_unmarks = {}
                self.unmarked_account = current
                self._save()
            if dropped:
                utils.log('%d queued history writes of the previous login dropped' % dropped)
        self.backoff = BACKOFF_MIN
        self.due = time.time() + START_DELAY

    def on_logout(self):
        """The entries belonged to that login; the ledger stays with its owner."""
        with self.lock:
            self.entries = []
            self.window_unmarks = []
            self.window_folder = False
            self._save()
        self.due = None
        self.waiting_toast = False
        self.quota_toast = False

    def tick(self, now, sender):
        """The unmark window closes by its own clock; nothing goes out while the connected account is unverified, the
        flush simply waits for the id."""
        if self.reask:
            asks, self.reask = self.reask, []
            self._ask(asks)
        self._settle_window(now)
        self.save_if_dirty()
        if self.due is None or now < self.due or self.flushing or not settings.account_id():
            return
        self.due = None
        if not self._eligible():
            self.due = self._next_retry()
            return
        self.flushing = True
        sender.submit(self._flush)

    def _next_retry(self):
        """When the earliest entry held back for a retry of its own comes due, None without one."""
        with self.lock:
            later = [e['retry_at'] for e in self.entries if e.get('retry_at', 0) > time.time()]
        return min(later) if later else None

    def _settle_window(self, now):
        """Once the library-unmark window has been quiet for HOLD: the unmarks of a burst (a season, a show, a set, a
        folder) are dropped, each other one supersedes what it overrides and goes out; the rest of the queue stays."""
        if (not self.window_unmarks and not self.window_folder) or now - self.window_last < HOLD:
            return
        asks = []
        with self.lock:
            ids = set(self.window_unmarks)
            waiting = [e for e in self.entries if e['id'] in ids]
            bulk = ids if self.window_folder else _bulk(waiting)
            if bulk:
                self._remember(e for e in waiting if e['id'] in bulk)
                self.entries = [e for e in self.entries if e['id'] not in bulk]
                utils.log('%d items unmarked at once in the library, nothing is sent to Simkl for a bulk unmark, the sync leaves them unwatched' % max(len(bulk), 2))
            for single in waiting:
                if single['id'] in bulk:
                    continue
                single.pop('window', None)
                # the other episodes of its file go with it, as entries of their own (the burst was judged per Kodi action)
                companions = [dict(self._new(UNMARK, sibling, single['account']), time=single['time']) for sibling in single.pop('siblings', [])]
                for companion in companions:
                    self._append(companion)
                for entry in [single] + companions:
                    self.entries = [e for e in self.entries if e is entry
                                    or not (e['key'] == entry['key'] and _owned(e, entry['account']) and e['kind'] in (MARK, UNMARK, WATCH) and e['time'] <= entry['time'])]
                if single['item'].get('kind') == 'movie':
                    single['asking'] = True
                    asks.append(single['id'])
            self.window_unmarks = []
            self.window_folder = False
            self._save()
        self._ask(asks)

    def _eligible(self):
        """What the flush may send now. On the way the entries too old or of another account are dropped, the old ones
        with one toast; an entry with a wait of its own (a failed file search) sits it out."""
        now = time.time()
        account = settings.account_id()
        with self.lock:
            keep = []
            aged = foreign = 0
            for entry in self.entries:
                if now - entry['time'] > MAX_AGE:
                    aged += 1
                    continue
                if account and entry.get('account') and entry['account'] != account:
                    foreign += 1
                    continue
                keep.append(entry)
            stale = [key for key, ts in self.unmarked.items() if now - ts > MAX_AGE and not _library_key(key)]
            stale += [key for key in self.sent_unmarks if key not in self.unmarked]
            for key in stale:
                self._forget(key)
            if aged or foreign or stale:
                self.entries = keep
                self._save()
            if aged or foreign:
                utils.log('%d queued history writes dropped: %d older than %d days, %d of another account' % (aged + foreign, aged, MAX_AGE // 86400, foreign))
            eligible = [e for e in keep if not e['inflight'] and not e.get('window') and not e.get('asking') and e.get('retry_at', 0) <= now]
        if aged:
            utils.notify(utils.get_str(32311).format(aged))
        return eligible

    def _retry_later(self, toast=True):
        self.due = time.time() + self.backoff
        self.backoff = min(BACKOFF_MAX, self.backoff * 2)
        if toast and not self.waiting_toast:
            self.waiting_toast = True
            utils.notify(utils.get_str(32241))

    def _wait_out(self, exc):
        """A limit Simkl named is waited out as it says, with no back-off growth and no outage toast: the daily quota
        until its reset (one toast), a short limit (the per-user write lock) a few seconds. False for anything else."""
        if exc.quota:
            self.due = time.time() + (exc.retry_after or QUOTA_WAIT)
            if not self.quota_toast:
                self.quota_toast = True
                utils.notify(utils.get_str(32245))
            return True
        if exc.rate_limited:
            self.due = time.time() + RATE_RETRY
            return True
        return False

    # ---------- delivery (sender thread) ----------

    def _flush(self):
        self.reported = []
        try:
            if not self.auth.logged_in():
                return
            # no look at Kodi's "internet state": its probe runs under the GUI lock and tests Microsoft's and w3.org's
            # hosts, not Simkl; an unreachable Simkl backs the flush off through the transport error itself
            account = settings.account_id()
            pending = self._named(self._eligible(), account)
            if pending is None:
                return
            removes = [e for e in pending if e['kind'] == UNMARK]
            plain = [e for e in pending if e['kind'] == MARK or (e['kind'] == WATCH and not e['rewatch'])]
            rewatch = sorted([e for e in pending if e['kind'] == WATCH and e['rewatch']], key=lambda e: e['time'])
            ok = not removes or self._unmarks(removes, account)
            if ok and plain:
                ok = all(self._send(part, '/sync/history', True, account) for part in _parts(plain))
            if ok and rewatch:
                # apart from the plain ones: allow_rewatch is request-wide and would turn an already watched item of theirs
                # into a rewatch; one show entry per episode (no merge) is the shape the server's rewatch detection needs
                ok = all(self._send(part, '/sync/history?allow_rewatch=yes', False, account) for part in _parts(rewatch))
            ratings = [e for e in pending if e['kind'] == RATE]
            if ok and ratings:
                ok = (all(self._send(part, '/sync/ratings/remove', False, account) for part in _parts([e for e in ratings if not e['rating']]))
                      and all(self._send(part, '/sync/ratings', False, account) for part in _parts([e for e in ratings if e['rating']])))
            if ok:
                self.backoff = BACKOFF_MIN
                self.waiting_toast = False
                self.quota_toast = False
                self.due = time.time() + HOLD if self._eligible() else self._next_retry()
        except Exception:
            # a defect here must not freeze the queue: logged, and the entries wait for the next retry
            utils.error('flush failed: %s' % traceback.format_exc())
            self._retry_later()
        finally:
            self.flushing = False
            self._toast_recorded()

    def _toast_recorded(self):
        """One toast for the watches Simkl recorded in this flush: the one by name, several by their count; none over
        a playing video."""
        recorded, self.reported = self.reported, []
        if not recorded or not settings.get_bool(settings.BUBBLE, True) or xbmc.getCondVisibility('Player.HasVideo'):
            return
        utils.notify(utils.get_str(32028).format(recorded[0]['item'].get('label') or '') if len(recorded) == 1 else utils.get_str(32303).format(len(recorded)))

    def _named(self, pending, account):
        """Entries recorded before the file search could name their file (Simkl unreachable at the time) are named now;
        None when a limit Simkl named holds the batch, or when Simkl is not answering (transport, 5xx: the queue backs
        off as a whole). A file Simkl does not know is dropped: nothing to deliver. A search Simkl refused (a coded 4xx)
        keeps its entry out of this flush with a wait of its own, and the rest goes on."""
        for entry in pending:
            item = entry['item']
            if item.get('ids') or item.get('episode_ids'):
                continue
            try:
                resolved = playerlib.search_file(self.api, self.auth, account, item)
            except InvalidToken:
                self.due = None
                return None
            except ApiError as exc:
                if self._wait_out(exc):
                    return None
                if exc.transport or exc.status >= 500:
                    # Simkl is not answering: the flush backs off as a whole (every further search would sit out its
                    # full timeout, with the live scrobbles waiting behind them), like a write that failed
                    utils.warn('cannot name %s (%s), the queue waits' % (item.get('label'), exc.error or 'HTTP %s' % exc.status))
                    self._retry_later()
                    return None
                with self.lock:
                    wait = _held_back(entry)
                    self._save()
                utils.warn('Simkl refused to name %s (%s), again in %d s' % (item.get('label'), exc.error or 'HTTP %s' % exc.status, wait))
                continue
            with self.lock:
                if resolved is None or not settings.tracked(resolved['kind']):
                    utils.log('%s, the watch of %s is dropped' % ('Simkl does not know it' if resolved is None else resolved['kind'] + ' tracking is off', item.get('label')))
                    self.entries = [e for e in self.entries if e['id'] != entry['id']]
                else:
                    entry['item'] = resolved
                    entry['key'] = resolved['key']
                    entry.pop('retry_wait', None)
                    entry.pop('retry_at', None)
                self._save()
        return [e for e in pending if e['item'].get('ids') or e['item'].get('episode_ids')]

    def _unmarks(self, removes, account):
        """Episodes leave the Simkl history. A movie does what its answer said: removed, unless Simkl has rewatch
        sessions of it (then kept, a toast says so), or moved to Plan to watch (the row keeps its rating, memo and
        sessions, loses its watch date); a movie Simkl does not have as completed has nothing to undo. False when Simkl
        could not be asked about the movies now (the batch waits)."""
        episodes = [e for e in removes if e['item']['kind'] != 'movie']
        movies = [e for e in removes if e['item']['kind'] == 'movie']
        listed = rewatched = []
        refused = False
        if movies:
            lists = self._movie_lists(movies, account)
            if lists is None:
                return False
            listed, rewatched, refused = lists
            if refused == 'retry':
                # a refusal that may pass later: the movies wait with a wait of their own, the episodes go now
                with self.lock:
                    waits = [_held_back(e) for e in movies]
                    self._save()
                utils.warn('the list check before %d movie unmarks failed, again in %d s' % (len(movies), max(waits)))
                movies = []
        sends = {'/sync/history/remove': episodes, '/sync/add-to-list': []}
        dropped = []
        with self.lock:
            queued = set(e['id'] for e in self.entries)
            cleared = False
            for entry in movies:
                if entry['id'] not in queued:
                    # marked again while the lists were fetched: neither sent nor remembered as an unmark
                    continue
                # the list check answered: a wait of its own left by earlier failed checks is over, on disk too (a
                # restart after a failed removal must not bring it back)
                cleared = entry.pop('retry_wait', None) is not None or cleared
                entry.pop('retry_at', None)
                ids = entry['item'].get('ids') or {}
                completed = any(same_item(ids, other) for other in listed)
                sessions = any(same_item(ids, other) for other in rewatched)
                if completed and entry.get('action') == 'plan':
                    sends['/sync/add-to-list'].append(entry)
                elif completed and not sessions and entry.get('action') == 'remove':
                    sends['/sync/history/remove'].append(entry)
                else:
                    dropped.append((entry, sessions))
            if dropped:
                self._remember(e for e, _ in dropped)
                gone = set(e['id'] for e, _ in dropped)
                self.entries = [e for e in self.entries if e['id'] not in gone]
            if dropped or cleared:
                self._save()
        for entry, sessions in dropped:
            label = entry['item'].get('label') or ''
            if sessions:
                utils.log('%s has rewatch sessions on Simkl, kept there' % label)
                utils.notify(utils.get_str(32309).format(label))
            elif refused:
                utils.log('%s stays unmarked in Kodi only, Simkl refused the list check' % label)
            else:
                utils.log('Simkl does not have %s as watched, nothing to change' % label)
                if entry.get('explicit'):
                    utils.notify(utils.get_str(32310).format(label))
        return all(self._send(part, path, True, account) for path, batch in sends.items() for part in _parts(batch))

    def _movie_lists(self, movies, account):
        """(the ids Simkl has as completed, those with rewatch sessions, the refusal: False, True for one that is final
        (a coded 4xx), 'retry' for a transport failure, a server error or a malformed answer) among these movies, from
        one /sync/watched call carrying their ids: Simkl resolves them whatever list it keeps them in (a movie Kodi has
        may be an anime movie there), and with allow_rewatch counts the sessions of each. An answer without the count
        (an older server) is taken as sessions: a movie is never removed on a guess. None when a limit Simkl named holds
        the batch."""
        try:
            answer = self.auth.authorized(lambda token: self.api.call('POST', '/sync/watched?allow_rewatch=yes', [{'ids': e['item'].get('ids') or {}} for e in movies], token=token), account)
        except InvalidToken:
            self.due = None
            return None
        except ApiError as exc:
            if self._wait_out(exc):
                return None
            if exc.transport or exc.status >= 500:
                return [], [], 'retry'
            utils.warn('Simkl refused the watched check (%s), the movies stay unmarked in Kodi only' % (exc.error or 'HTTP %s' % exc.status))
            return [], [], True
        if not isinstance(answer, list) or len(answer) != len(movies):
            utils.warn('the watched check answered %s rows for %d movies, asked again later' % (len(answer) if isinstance(answer, list) else 'no', len(movies)))
            return [], [], 'retry'
        listed, rewatched = [], []
        for entry, row in zip(movies, answer):
            if not isinstance(row, dict) or row.get('result') is not True or row.get('list') != 'completed':
                continue
            listed.append(entry['item'].get('ids') or {})
            if row.get('rewatches', 1):
                rewatched.append(listed[-1])
        return listed, rewatched, False

    def _queued(self, batch):
        """What of a batch is still queued: an entry the user cancelled while the batch was being prepared (an unmark
        re-marked during the list check) must not go out."""
        with self.lock:
            ids = set(e['id'] for e in self.entries)
        return [e for e in batch if e['id'] in ids]

    def _send(self, batch, path, merge, account):
        batch = self._queued(batch)
        if not batch:
            return True
        unmark = '/history/remove' in path or '/add-to-list' in path
        request = _request_for(path, batch, merge)
        try:
            answer = self.auth.authorized(lambda token: self.api.call('POST', path, request, token=token), account)
        except InvalidToken:
            self.due = None
            return False
        except ApiError as exc:
            # a refusal is a 400 with Simkl's error code; a 400 without one (a proxy's page, an empty body) proves nothing
            if exc.status == 400 and exc.error and not exc.rate_limited:
                if len(batch) == 1:
                    utils.warn('Simkl refused a history write (%s %s), dropping it: %s' % (exc.error, exc.message, batch[0]['key']))
                    self.ack(batch[0]['id'])
                    return True
                # the refusal names no entry: bisected, a good half goes out whole and the bad entry is found in log2(n) requests
                half = len(batch) // 2
                return self._send(batch[:half], path, merge, account) and self._send(batch[half:], path, merge, account)
            if self._wait_out(exc):
                return False
            utils.warn('history write failed (%s), retrying later' % (exc.error or 'HTTP %s' % exc.status))
            self._retry_later()
            return False
        self._delivered(batch, unmark)
        self.reported.extend(self._report(batch, answer, path))
        return True

    def _delivered(self, batch, unmark):
        with self.lock:
            sent = set(e['id'] for e in batch)
            self.entries = [e for e in self.entries if e['id'] not in sent]
            if unmark:
                self._remember(batch)
                # applied by Simkl: a later watched row of it, whatever its date, is the user's new word for the sync
                for entry in batch:
                    self.sent_unmarks[entry['key']] = self.unmarked[entry['key']]
            else:
                # a delivered watch or mark is the user's later word than an unmark before it
                for entry in batch:
                    if self.unmarked.get(entry['key'], 0) <= entry['time']:
                        self._forget(entry['key'])
            self._save()

    def _report(self, batch, answer, path):
        """Logs what Simkl made of the batch and returns the watches it recorded (announced to the other add-ons)."""
        not_found = (answer or {}).get('not_found') or {}
        missing = sum(len(not_found.get(k) or []) for k in ('movies', 'shows', 'episodes'))
        suffix = (', %d not found on Simkl' % missing) if missing else ''
        if '/add-to-list' in path or '/history/remove' in path:
            # the word on an explicit movie unmark comes once Simkl applied the answer (an episode's came at the action)
            for entry in batch:
                if entry.get('explicit') and entry['item'].get('kind') == 'movie' and not _unfound(entry['item'], not_found):
                    utils.notify(utils.get_str(32254 if '/add-to-list' in path else 32256).format(entry['item'].get('label') or ''))
        if '/add-to-list' in path:
            utils.log('history: %d movies moved to Plan to watch%s' % (len(((answer or {}).get('added') or {}).get('movies') or []), suffix))
            return []
        if '/sync/ratings' in path:
            utils.log('ratings %s: %d%s' % ('removed' if '/remove' in path else 'sent', max(0, len(batch) - missing), suffix))
            for bucket in ('movies', 'shows'):
                for lost in not_found.get(bucket) or []:
                    ids = (lost if isinstance(lost, dict) else {}).get('ids') or {}
                    label = next((e['item']['label'] for e in batch if same_item(e['item']['ids'], ids)), '')
                    if label:
                        utils.notify(utils.get_str(32263).format(label))
            return []
        remove = '/history/remove' in path
        counts = (answer or {}).get('deleted' if remove else 'added') or {}
        utils.log('history %s: %s movies, %s episodes%s' % ('removed' if remove else 'added', counts.get('movies', 0), counts.get('episodes', 0), suffix))
        if remove:
            return []
        recorded = [e for e in batch if e['kind'] == WATCH and not _unfound(e['item'], not_found)]
        for entry in recorded:
            playerlib.announce('scrobbled', entry['item'])
        return recorded
