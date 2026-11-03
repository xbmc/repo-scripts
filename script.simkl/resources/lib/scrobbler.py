#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""One playback session at a time: start, pause, resume, seek and stop go to /scrobble as they happen; a finished
playback is written ahead to the history queue before its stop goes out. A playback Kodi dies in is simply lost, like
in every other client: the user saw the crash."""

import os
import time

from resources.lib import player as playerlib
from resources.lib import settings, utils
from resources.lib.api import ApiError
from resources.lib.auth import InvalidToken
from resources.lib.history import scrobble_payload

SEEK_QUIET = 2.0
# seeks add up until they moved the position this far (milliseconds, Kodi's unit): only then a start carries the new
# position, as Simkl's Emby and Jellyfin plugins do; a chapter jump counts as far
SEEK_FAR = 30000
# Kodi applies a resume point with a silent seek right after playback begins: the first start waits it out, so it
# carries the real position instead of 0 followed by a correction (Trakt's add-on sleeps a second for the same reason)
START_GRACE = 2.0
TOTAL_WAIT = 20.0
SAMPLE_EVERY = 1.0
# a sample whose duration moved by more than this is another file's (an in-place switch to the next item)
TOTAL_TOLERANCE = 5.0
# a playback much shorter than the movie it is reported under is a trailer or a clip
CLIP_RATIO = 0.5
# a stop asks Simkl to count a rewatch only after this share of the runtime was really watched: a minute of the ending
# of a watched item is not one (whether it is a rewatch at all, Simkl decides from the history)
REWATCH_SHARE = 0.10
# Up Next moves on from an episode near its end; a signal for a playback under this share is one some Up Next versions
# send when their popup closes, after the next episode has started: not about that playback
UPNEXT_MIN_PROGRESS = 50.0


class Session:
    def __init__(self, playback_id):
        self.playback_id = playback_id
        self.account = settings.account_id()
        self.item = None
        self.path = ''
        self.resolve_first = False
        # an identified library item: the minimum length never applies to it (short anime, web episodes)
        self.library = False
        # the other episodes of a multi-episode file, watched with this one
        self.siblings = []
        self.ignored = False
        self.unmatched = False
        self.resolved = None
        self.resolved_item = None
        self.started = False
        self.paused = False
        self.speed = 1
        self.position = 0.0
        self.total = 0.0
        # the total is the item's runtime because Kodi reports no duration for this stream
        self.assumed = False
        self.sampled_at = 0.0
        # seconds really watched: unpaused, not fast-forwarding, the position advancing; seeks add nothing
        self.played = 0.0
        self.rewatch = False
        self.created = time.time()
        self.stopped_at = None
        self.seek_due = None
        self.seeked = 0
        self.closed = False
        # the home-window properties as they were when this playback began: only those values are cleared at its end
        self.window = {}


class Scrobbler:
    def __init__(self, api, auth, player, sender, history, marks, on_watched=None):
        """on_watched(item, account): called on the sender after Simkl recorded a watch live (the rating prompt)."""
        self.api = api
        self.auth = auth
        self.player = player
        self.sender = sender
        self.history = history
        self.marks = marks
        self.on_watched = on_watched
        self.session = None
        # from what share on Kodi's own play-count bump follows a stop (its advancedsettings, read once as Kodi does)
        self.watched_percent = playerlib.kodi_watched_percent()

    # ---------- events (worker thread) ----------

    def on_event(self, event):
        kind = event[0]
        playback_id = event[1]
        if kind == 'av_started':
            self._start_session(playback_id)
            return
        session = self.session
        if kind in ('ended', 'stopped', 'error'):
            # the values that were this playback's go; what an add-on wrote since is the next item's (its plugin runs
            # for the next playlist item before Kodi announces the end of this one). An end announced for an earlier
            # playback than the session's was settled when that session began
            if session is None:
                playerlib.clear_ids()
            elif session.playback_id == playback_id:
                playerlib.clear_ids(session.window)
        if session is None or session.closed or session.playback_id != playback_id:
            return
        if kind == 'paused':
            session.paused = True
            session.seek_due = None
            if session.started:
                self._submit(session, 'pause')
        elif kind == 'resumed':
            session.paused = False
            if session.started:
                self._submit(session, 'start')
        elif kind == 'seek':
            offset = event[2] if len(event) > 2 else None
            session.seeked += SEEK_FAR if offset is None else abs(int(offset or 0))
            if session.seeked >= SEEK_FAR:
                session.seek_due = time.time() + SEEK_QUIET
        elif kind == 'speed':
            speed = event[2]
            if speed == 1 and session.speed != 1:
                session.seek_due = time.time() + SEEK_QUIET
            session.speed = speed
        elif kind == 'ended':
            self._stop(session, self._end_progress(session))
        elif kind in ('stopped', 'error'):
            self._stop(session, self._progress(session))
        elif kind == 'upnext':
            # Up Next moved on to the next episode: the current one counts as watched to the end, as Trakt's add-on does
            if session.started and self._progress(session) >= UPNEXT_MIN_PROGRESS:
                self._stop(session, 100.0)
            else:
                utils.log('Up Next signal ignored: the playback has just begun (%d%%)' % self._progress(session))

    def _start_session(self, playback_id):
        previous = self.session
        if previous is not None and not previous.closed:
            # an in-place switch: no end is announced for the previous item, so its window values go here
            self._stop(previous, self._progress(previous))
            playerlib.clear_ids(previous.window)
        session = Session(playback_id)
        session.window = playerlib.window_ids()
        self.session = session
        if not self.auth.logged_in():
            session.ignored = True
            return
        self.auth.nudge()
        status, payload = playerlib.identify(self.player)
        if status == 'skip':
            utils.log('not tracked: %s' % payload)
            session.ignored = True
            kind, dbid = playerlib.library_identity()
            if dbid:
                # Kodi's own play-count bump at the end of this playback is not a mark of the user's either
                session.item = {'kind': kind, 'dbid': dbid}
            return
        session.item = payload
        session.resolve_first = status == 'file'
        session.library = status == 'ok' and bool(payload.get('dbid'))
        if status == 'ok' and not settings.tracked(payload['kind']):
            utils.log('%s tracking is off' % payload['kind'])
            session.ignored = True
            return
        if session.library:
            session.siblings = playerlib.file_siblings(payload)
        session.path = self.player.playing_file()
        session.paused = playerlib.is_paused()
        sample = self._sample(session)
        if sample:
            session.position, session.total = sample
            session.sampled_at = time.time()
        self._maybe_start(session)

    @staticmethod
    def _rewatch():
        return settings.get_bool(settings.ALLOW_REWATCH) and settings.is_pro()

    def _sample(self, session):
        """The player's position for this session. Kodi switches to the next item of a playlist in place, without a stop
        for the old one: until the new item's av_started arrives, the player reports the new file (first with no duration,
        then with its own); such a sample is not this session's and must not overwrite its last good position."""
        sample = self.player.sample()
        if not sample:
            return None
        position, total = sample
        if session.assumed and total <= 0:
            total = session.total
        elif session.assumed:
            # Kodi learned the duration after all: it replaces the runtime
            session.assumed = False
        elif total <= 0 or (session.total > 0 and abs(total - session.total) > TOTAL_TOLERANCE):
            return None
        if session.path and self.player.playing_file() != session.path:
            return None
        return position, total

    def _maybe_start(self, session):
        """The start waits for Kodi to report the duration: the minimum-length and the clip rules need it. The minimum
        applies to add-on streams and to files the search has to name, never to an identified library item. A stream
        Kodi never reports a duration for plays under the item's own runtime when it has one (the position still counts up)."""
        if session.started or session.ignored or time.time() - session.created < START_GRACE:
            return
        runtime = int(session.item.get('runtime') or 0)
        if session.total <= 0:
            if time.time() - session.created <= TOTAL_WAIT:
                return
            if not runtime:
                utils.log('no duration after %d s, not tracked' % TOTAL_WAIT)
                session.ignored = True
                return
            utils.log('no duration after %d s, the runtime of %d s stands in' % (TOTAL_WAIT, runtime))
            session.total = float(runtime)
            session.assumed = True
        if not session.library and session.total < settings.min_length_seconds():
            utils.log('shorter than the minimum length, not tracked')
            session.ignored = True
            return
        if session.item.get('kind') == 'movie' and runtime and session.total < runtime * CLIP_RATIO:
            utils.log('%d s playing under a movie of %d s: a trailer or a clip, not tracked' % (session.total, runtime))
            session.ignored = True
            return
        session.started = True
        if session.paused:
            # paused before the duration was known: the resume sends the start
            return
        self._submit(session, 'start')

    def tick(self, now):
        session = self.session
        if session is None or session.closed:
            return
        # a playback left alone is still sampled when it is a library item: whether Kodi will count it watched at its
        # stop, and so whether its own play-count bump is to be expected, only the position tells
        if session.ignored and not (session.item or {}).get('dbid'):
            return
        if now - session.sampled_at >= SAMPLE_EVERY:
            sample = self._sample(session)
            if sample:
                session.played += self._watched_since(session, sample[0], now)
                session.position, session.total = sample
                session.sampled_at = now
        if session.ignored:
            return
        if not session.started:
            self._maybe_start(session)
            return
        if session.seek_due and now >= session.seek_due:
            session.seek_due = None
            if not session.paused and session.speed == 1:
                self._submit(session, 'start')

    def close_all(self):
        session = self.session
        if session is not None and not session.closed:
            self._stop(session, self._progress(session))

    def active(self):
        """A playback is being tracked (or still waiting for its duration), so the service loop should turn fast."""
        session = self.session
        return session is not None and not session.closed and not session.ignored

    def is_open(self, kind, dbid):
        """Whether that library item is the playback in progress, tracked or left alone (a clip, another account's
        login): its own play-count bump is Kodi's, not a mark of the user's."""
        session = self.session
        return (session is not None and not session.closed and session.item is not None
                and session.item.get('kind') == kind and session.item.get('dbid') == dbid)

    def on_login(self, previous, current):
        """A login to another account: the running playback is not its business."""
        session = self.session
        if previous != current and session is not None and not session.closed and session.account != current:
            session.ignored = True

    def on_logout(self):
        """The running playback belonged to the login that just ended: nothing more is recorded for it."""
        session = self.session
        if session is not None and not session.closed:
            session.ignored = True

    @staticmethod
    def _watched_since(session, position, now):
        """The seconds really watched since the last sample: none before the first one, while paused or fast-forwarding,
        and none across a seek (the position moved backwards or by more than twice the elapsed time)."""
        elapsed = now - session.sampled_at
        moved = position - session.position
        if not session.sampled_at or session.paused or session.speed >= 2 or moved <= 0 or moved > 2 * elapsed:
            return 0.0
        return elapsed

    @staticmethod
    def _progress(session):
        if session.total <= 0:
            return 0.0
        return max(0.0, min(100.0, 100.0 * session.position / session.total))

    @staticmethod
    def _end_progress(session):
        """A natural end is 100 whatever the last sample said, so a threshold of 100 still marks it; a stream or a file
        that ran out early keeps its real position."""
        if session.total > 0 and session.total - session.position <= max(2 * SAMPLE_EVERY, 0.02 * session.total):
            return 100.0
        return Scrobbler._progress(session)

    @staticmethod
    def _recorded(session):
        """The item a watch is recorded under: what the file search resolved, else the item itself when it has ids."""
        if session.resolved_item is not None:
            return session.resolved_item
        if session.item is not None and (session.item.get('ids') or session.item.get('episode_ids')):
            return session.item
        return None

    def _stop(self, session, progress):
        session.closed = True
        session.seek_due = None
        if session.item is not None and session.item.get('dbid') and 0 < self.watched_percent <= 100 and progress >= self.watched_percent:
            # Kodi's own playcount bump follows a playback it counts as watched: not a mark of the user's. A stop
            # before that share (or any stop when Kodi is set never to count one: 0, or over 100) sets no guard,
            # since Kodi then announces no count and a mark made within the guard's seconds would be taken for the
            # bump and lost
            self.marks.guard(session.item['kind'], session.item['dbid'])
        if session.ignored or session.unmatched or session.item is None or not session.started:
            return
        session.stopped_at = time.time()
        event_id = None
        if progress >= settings.threshold():
            session.rewatch = self._rewatch() and session.played >= REWATCH_SHARE * session.total
            # written ahead even for a file the search has not named yet (Simkl was unreachable): the flush names it
            event_id = self.history.watch_event(self._recorded(session) or session.item, session.stopped_at, session.rewatch, account=session.account)
            for sibling in session.siblings:
                # Kodi shows the file's other episodes watched with this one; Simkl hears of them through the queue
                self.history.watch_event(sibling, session.stopped_at, session.rewatch, account=session.account, inflight=False)
        self._submit(session, 'stop', progress, event_id)

    def _submit(self, session, action, progress=None, event_id=None):
        if progress is None:
            progress = self._progress(session)
        if action == 'start':
            # a start carries the current position: the seeks so far are settled by it, whatever asked for it
            session.seeked = 0
            session.seek_due = None
        self.sender.submit(lambda: self._send(session, action, progress, event_id))

    # ---------- delivery (sender thread) ----------

    def _send(self, session, action, progress, event_id):
        item = session.item
        if item is None or session.unmatched or session.ignored:
            # ignored after it was submitted (a login to another account, a logout): the job is obsolete and touches nothing
            if event_id:
                self.history.ack(event_id)
            return
        if action != 'stop' and session.closed:
            return
        if session.resolve_first and session.resolved is None:
            try:
                resolved = self._resolve(session)
            except InvalidToken:
                if event_id:
                    self.history.release(event_id, toast=False)
                return
            except ApiError as exc:
                utils.warn('file search failed: %s' % (exc.error or 'HTTP %s' % exc.status))
                if event_id:
                    self.history.release(event_id, error=exc)
                return
            if not resolved:
                if event_id:
                    self.history.ack(event_id)
                return
        rewatch = action == 'stop' and session.rewatch
        path = '/scrobble/%s?min_progress=%d%s' % (action, settings.threshold(), '&allow_rewatch=yes' if rewatch else '')
        try:
            answer = self._deliver(session, path, progress)
        except InvalidToken:
            if event_id:
                self.history.release(event_id, toast=False)
            return
        except ApiError as exc:
            utils.warn('%s failed: %s' % (action, exc.error or 'HTTP %s' % exc.status))
            if event_id:
                self.history.release(event_id, error=exc)
            return
        if answer is None:
            # 409 (already watched within the hour) or nothing Simkl knows: nothing to deliver later either
            if event_id:
                self.history.ack(event_id)
            return
        utils.log('%s %s%% -> %s' % (action, round(progress), answer.get('action')))
        if action == 'start' and not session.closed:
            playerlib.set_playing(self._recorded(session) or item)
        if action != 'stop':
            return
        # with allow_rewatch Simkl answers both rewatch keys null exactly when the watch itself could not be recorded
        # (its list row was locked): then the queue delivers it
        recorded_by_simkl = not (rewatch and 'rewatch_status' in answer and answer['rewatch_status'] is None and answer.get('rewatch_id') is None)
        if event_id:
            if recorded_by_simkl:
                self.history.ack(event_id)
            else:
                self.history.release(event_id)
        if answer.get('action') == 'scrobble' and recorded_by_simkl:
            watched = session.resolved_item or item
            self.history.live_watch_succeeded(watched['key'], session.stopped_at, session.account)
            playerlib.announce('scrobbled', watched)
            if settings.get_bool(settings.BUBBLE, True):
                utils.notify(utils.get_str(32028).format(watched.get('label') or ''))
            if self.on_watched is not None:
                self.on_watched(watched, session.account)
        if answer.get('rewatch_status') == 'pro_required':
            settings.put(settings.ALLOW_REWATCH, False)
            utils.notify(utils.get_str(32214))

    def _deliver(self, session, path, progress):
        """One scrobble call; a 404 tries the file search once per playback; 409 and an unmatched item answer None."""
        def post():
            payload = dict(session.resolved) if session.resolved else scrobble_payload(session.item, progress)
            payload['progress'] = round(float(progress), 2)
            return self.auth.authorized(lambda token: self.api.call('POST', path, payload, token=token), session.account)

        try:
            return post()
        except ApiError as exc:
            if exc.status == 409:
                utils.log('already watched within the hour')
                return None
            if exc.status != 404:
                raise
        if session.resolved is not None:
            # Simkl refused what the file search named: nothing is recorded for this playback, by the queue either
            session.unmatched = True
            return None
        if not self._resolve(session):
            return None
        try:
            return post()
        except ApiError as exc:
            if exc.status in (404, 409):
                session.unmatched = exc.status == 404
                return None
            raise

    def _resolve(self, session):
        """Identifies an item Simkl does not know by ids through its file name, once per playback."""
        item = session.item
        path = item.get('file') or ''
        if not playerlib.is_local(path):
            session.unmatched = True
            return False
        resolved = playerlib.search_file(self.api, self.auth, session.account, item)
        if resolved is None:
            utils.log('Simkl does not know %s, not reported again during this playback' % os.path.basename(path))
            session.unmatched = True
            return False
        if not settings.tracked(resolved['kind']):
            utils.log('%s tracking is off (file search)' % resolved['kind'])
            session.unmatched = True
            return False
        session.resolved_item = resolved
        session.resolved = scrobble_payload(resolved, 0)
        utils.log('file search identified %s as %s' % (os.path.basename(path), resolved['label']))
        return True
