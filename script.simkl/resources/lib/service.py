#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""The service: one worker loop for the player events, the position sampler, the history flushes and the import
schedule; one sender thread for the HTTP calls of the scrobbler and the queue, so one account's calls stay in order."""

import base64
import collections
import json
import os
import queue
import threading
import time
import traceback

import xbmc
import xbmcgui

from resources.lib import player as playerlib
from resources.lib import focus, settings, utils
from resources.lib.api import Api, ApiError
from resources.lib.auth import Auth, InvalidToken
from resources.lib.history import History
from resources.lib.importer import Importer
from resources.lib.marks import Marks
from resources.lib.scrobbler import Scrobbler

PLAYER_EVENTS = ('av_started', 'paused', 'resumed', 'seek', 'speed', 'stopped', 'ended', 'error', 'upnext')
UPNEXT_SIGNAL = 'NEXTUPWATCHEDSIGNAL'
CONTEXT_ACTIONS = ('ctx_mark', 'ctx_unmark', 'ctx_plantowatch', 'ctx_rate')
# Kodi's information dialog, the one place a user rates a library item; Kodi announces nothing for it
INFO_DIALOG = 'Window.IsVisible(movieinformation)'
RATED_TYPES = ('movie', 'tvshow')
IMPORT_CHECK_EVERY = 60
# a legacy login whose account is still unknown asks for it again with a wait growing from a minute to five
ACCOUNT_RETRY_MIN = 60
ACCOUNT_RETRY_MAX = 300
# the loop turns fast while a playback is tracked (sampling, seek holds) and slowly when there is nothing to watch
LOOP_WAIT = 0.25
IDLE_WAIT = 1.0
# Kodi gives a stopping script 5 s before it injects an exit into every thread: the sender's backlog gets less, so the
# stop flags are set inside that window and a request still reading gives up at its next chunk
SHUTDOWN_WAIT = 3
# the question for an unmarked movie closes by itself after this, which counts as "keep it watched on Simkl"
QUESTION_MS = 30000


def _payload(data):
    """The item of a context action, as context.py / script.py sent it along with the notification."""
    try:
        return json.loads(base64.b64decode(json.loads(data)['data']).decode('utf-8'))
    except (ValueError, TypeError, KeyError):
        return {}


class Sender:
    """One thread, one FIFO: the order Simkl sees is the order the jobs were submitted in."""

    def __init__(self):
        self.jobs = queue.Queue()
        self.stopping = False
        self.thread = threading.Thread(target=self._run, name='simkl-sender')
        self.thread.daemon = True
        self.thread.start()

    def submit(self, job):
        self.jobs.put(job)

    def _run(self):
        while True:
            try:
                job = self.jobs.get(timeout=1)
            except queue.Empty:
                if self.stopping:
                    return
                continue
            if job is None or self.stopping:
                return
            try:
                job()
            except Exception:
                utils.error('request failed: %s' % traceback.format_exc())

    def stop(self, wait):
        """The jobs queued so far get `wait` seconds; a backlog still there after that is left behind (Kodi is leaving)."""
        self.jobs.put(None)
        self.thread.join(wait)
        self.stopping = True


class SimklService(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        settings.migrate()
        utils.VERBOSE = settings.get_bool(settings.DEBUG)
        self.events = collections.deque()
        self.api = Api()
        self.auth = Auth(self.api)
        self.sender = Sender()
        self.history = History(self.api, self.auth, ask=lambda entry_id: self.events.append(('ask_unmark', entry_id)))
        # the unmarked movies waiting for their question, asked one at a time, never over a playing video
        self.questions = collections.deque()
        self.question_open = False
        self.marks = Marks(self.auth, self.history, lambda kind, dbid: self.scrobbler.is_open(kind, dbid))
        self.player = playerlib.Player(self.events.append)
        self.scrobbler = Scrobbler(self.api, self.auth, self.player, self.sender, self.history, self.marks, self._after_watch)
        self.importer = Importer(self.api, self.auth, self.marks, self.history)
        self.continue_watching = settings.get_bool(settings.CONTINUE_WATCHING)
        # the item shown by the information dialog: [(dbtype, dbid), rating when it opened, rating now]
        self.info_item = None

    def run(self):
        utils.log('service %s started on Kodi %s' % (utils.ADDON_VERSION, utils.KODI_VERSION))
        settings.put(settings.LOG_PATH, utils.kodi_log_path())
        self.auth.update_status()
        if self.auth.logged_in():
            self.sender.submit(self._refresh_account)
        elif not settings.get_bool(settings.LOGIN_HINT_SHOWN):
            settings.put(settings.LOGIN_HINT_SHOWN, True)
            utils.notify(utils.get_str(32203), time_ms=10000)
        if self.player.isPlayingVideo():
            # the service (re)started during a playback (an add-on update): track it from here
            self.player.onAVStarted()
        # the first scheduled sync waits a minute: at start the box may not have its network yet
        last_import_check = time.time()
        account_due = time.time() + ACCOUNT_RETRY_MIN
        account_wait = ACCOUNT_RETRY_MIN
        try:
            while not self.abortRequested():
                now = time.time()
                self._drain()
                try:
                    self.scrobbler.tick(now)
                    self.history.tick(now, self.sender)
                    self._ask_next()
                    self._watch_rating()
                    self.importer.start_due()
                except Exception:
                    # a defect in one turn must not end the service
                    utils.error('turn failed: %s' % traceback.format_exc())
                if now - last_import_check >= IMPORT_CHECK_EVERY:
                    last_import_check = now
                    # a scheduled sync waits for an idle minute: no library writes or big JSON parses behind a playback
                    if not self.player.isPlayingVideo():
                        self.importer.auto_check()
                if settings.account_id():
                    account_wait = ACCOUNT_RETRY_MIN
                elif now >= account_due and self.auth.logged_in():
                    # nothing recorded under an unknown account goes out until the lookup succeeds
                    self.sender.submit(self._refresh_account)
                    account_due = now + account_wait
                    account_wait = min(ACCOUNT_RETRY_MAX, account_wait * 2)
                if self.waitForAbort(LOOP_WAIT if self.scrobbler.active() or self.events else IDLE_WAIT):
                    break
        finally:
            # also on the exception Kodi injects into a script that outstays its exit: a rating still on screen is
            # taken (Kodi stops the services before it closes its windows), the open playback is closed, the queue
            # saved and the sender stopped, else it waits on its queue for good and holds Kodi's exit. Each step on its
            # own, so that the exit landing in one skips neither the others nor the stop
            self._shutdown_step(self._flush_rating)
            self._shutdown_step(self.scrobbler.close_all)
            self._shutdown_step(self.history.save_if_dirty)
            self.sender.stop(SHUTDOWN_WAIT)
            # a request still in flight after the wait gives up at its next chunk instead of holding Kodi's exit
            self.api.abort = True
            # what a sender job recorded during the wait (a mark, an unmark of a file) is on disk before the exit
            self._shutdown_step(self.history.save_if_dirty)
            utils.log('service stopped')

    @staticmethod
    def _shutdown_step(step):
        try:
            step()
        except BaseException:
            utils.error('shutdown: %s' % traceback.format_exc())

    def _refresh_account(self):
        try:
            self.auth.fetch_account()
        except (ApiError, InvalidToken) as exc:
            utils.log('account refresh skipped: %s' % exc)

    # ---------- ratings made in Kodi ----------

    def _watch_rating(self):
        """While the information dialog is open, the shown item's user rating is read each turn (two info labels, no
        library query); when the dialog closes, or shows another item, a changed rating goes to Simkl."""
        if not xbmc.getCondVisibility(INFO_DIALOG):
            self._flush_rating()
            return
        key = (xbmc.getInfoLabel('ListItem.DBTYPE').lower(), int(xbmc.getInfoLabel('ListItem.DBID') or 0))
        if not key[0]:
            # a dialog on top of the information dialog (the rating pick itself) answers the labels instead: the item stays
            return
        rating = int(xbmc.getInfoLabel('ListItem.UserRating') or 0)
        if self.info_item is None or self.info_item[0] != key:
            self._flush_rating()
            self.info_item = [key, rating, rating]
        else:
            self.info_item[2] = rating

    def _flush_rating(self):
        if self.info_item is None:
            return
        (dbtype, dbid), before, after = self.info_item
        self.info_item = None
        if dbtype not in RATED_TYPES or dbid <= 0 or not settings.get_bool(settings.SYNC_RATINGS, True) or not self.auth.logged_in():
            return
        # the labels are a turn behind a pick made just before the dialog closed; the library holds the final rating
        # once the dialog is closed (Kodi writes it then). While the dialog is still open (the stop at Kodi's exit)
        # the library still holds the opening value, and the sampled one stands
        method, key = ('VideoLibrary.GetMovieDetails', 'movieid') if dbtype == 'movie' else ('VideoLibrary.GetTVShowDetails', 'tvshowid')
        details = (utils.jsonrpc(method, {key: dbid, 'properties': ['userrating']}) or {}).get(dbtype + 'details') or {}
        stored = int(details.get('userrating') or 0) if 'userrating' in details else before
        if stored != before:
            after = stored
        if after == before:
            return
        payload = {'dbtype': dbtype, 'dbid': dbid}
        movie = self._library_movie(payload) if after else None
        if movie is not None and movie['playcount'] == 0:
            utils.notify(utils.get_str(32299).format(movie['label']))
            return
        target = self._show_target(payload)
        if target is None:
            return
        # recorded here, not on the sender: a rating waits for no request, and one handed to a sender held by a slow
        # request would be left behind at Kodi's exit
        self._rate(target, after, settings.account_id())

    def _after_watch(self, item, account):
        """A movie Simkl just recorded live: the rating prompt, on its own thread so that no dialog holds the sender,
        and not when the next item of a playlist is already playing."""
        if item.get('kind') != 'movie' or not item.get('ids') or not settings.get_bool(settings.RATE_PROMPT, True):
            return
        if int(item.get('userrating') or 0) > 0 or int(item.get('playcount') or 0) > 0:
            # rated in Kodi already (a stray OK would resend a copy that simkl.com may have changed since), or a rewatch
            return

        def ask():
            if self.player.isPlayingVideo():
                return
            rating = focus.pick_rating(utils.addon(), item.get('label') or '', skip=True)
            if rating is not None:
                self._rate(('movies', item['ids'], item.get('label') or ''), rating, account)

        thread = threading.Thread(target=ask, name='simkl-rating')
        thread.daemon = True
        thread.start()

    def _drain(self):
        while self.events:
            event = self.events.popleft()
            try:
                if event[0] in PLAYER_EVENTS:
                    if event[0] == 'av_started':
                        self.importer.note_use()
                    self.scrobbler.on_event(event)
                elif event[0] == 'library':
                    self.marks.on_update(event[1], event[2])
                elif event[0] == 'action':
                    self._action(event[1], event[2])
                elif event[0] == 'ask_unmark':
                    self.questions.append(event[1])
                elif event[0] == 'unmark_answer':
                    # the toast comes from the flush, once Simkl applied the answer
                    self.question_open = False
                    self.history.answer_unmark(event[1], event[2])
            except Exception:
                utils.error('%s failed: %s' % (event[0], traceback.format_exc()))

    # ---------- the question for an unmarked movie ----------

    def _ask_next(self):
        """One question at a time, on its own thread (a dialog must not hold the loop), and not over a playing video;
        a movie marked again meanwhile is not asked about."""
        if self.question_open or self.player.isPlayingVideo():
            return
        while self.questions:
            entry_id = self.questions.popleft()
            label = self.history.asking_label(entry_id)
            if label is None:
                continue
            self.question_open = True
            thread = threading.Thread(target=self._ask, args=(entry_id, label), name='simkl-question')
            thread.daemon = True
            thread.start()
            return

    def _ask(self, entry_id, label):
        """Remove (yes), Plan to watch (the custom button) or keep watched (no, the close, the timeout, an error)."""
        choice = 'keep'
        try:
            answer = xbmcgui.Dialog().yesnocustom('Simkl', utils.get_str(32305).format(label), utils.get_str(32307), utils.get_str(32308), utils.get_str(32306), QUESTION_MS)
            choice = {1: 'remove', 2: 'plan'}.get(answer, 'keep')
        finally:
            self.events.append(('unmark_answer', entry_id, choice))

    # ---------- Kodi callbacks (only hand events to the loop) ----------

    def onNotification(self, sender, method, data):
        if method == 'VideoLibrary.OnUpdate':
            self.events.append(('library', data, time.time()))
        elif sender == utils.ADDON_ID and method.startswith('Other.'):
            self.events.append(('action', method[6:], data))
        elif method.split('.')[-1].upper() == UPNEXT_SIGNAL:
            self.events.append(('upnext', self.player.playback_id))

    def onSettingsChanged(self):
        utils.reload_addon()
        utils.VERBOSE = settings.get_bool(settings.DEBUG)
        wanted = settings.get_bool(settings.CONTINUE_WATCHING)
        if wanted and not self.continue_watching:
            self.importer.request_playback_full()
        self.continue_watching = wanted

    # ---------- actions from the settings buttons and the context menu ----------

    def _after_login(self, previous, current):
        self.history.on_login(previous, current)
        self.scrobbler.on_login(previous, current)

    def _action(self, name, data):
        if name == 'login':
            self.auth.login(on_success=self._after_login)
        elif name == 'logout':
            self.history.on_logout()
            self.scrobbler.on_logout()
            grant = self.auth.logout()
            self.sender.submit(lambda: self.auth.revoke(grant))
            utils.notify(utils.get_str(32211))
        elif name == 'import_check':
            self.importer.start('check', manual=True)
        elif name == 'import_reset':
            self.importer.start('reset', manual=True)
        elif name in CONTEXT_ACTIONS:
            self._context(name, _payload(data))

    def _context(self, name, payload):
        if not self.auth.logged_in():
            utils.notify(utils.get_str(32224))
            return
        dbtype = payload.get('dbtype') or ''
        library = int(payload.get('dbid') or 0) > 0
        if not library and not dbtype and not payload.get('ids'):
            # a video outside the library (Kodi tells add-ons nothing about marks on those): Simkl's file search names
            # it, as for a playing file
            path = payload.get('file') or ''
            if not playerlib.is_local(path):
                utils.notify(utils.get_str(32257))
                return
            account = settings.account_id()
            self.sender.submit(lambda: self._file_action(name, path, payload, account))
            return
        if not library and dbtype == 'episode' and not utils.ids_from(payload.get('show_ids')):
            # an add-on episode's uniqueid names the episode, not its show; the show's ids come from the item's properties
            utils.notify(utils.get_str(32271))
            return
        if name in ('ctx_plantowatch', 'ctx_rate'):
            # both act on the show or the movie, whatever row the cursor is on
            rating = int(payload.get('rating') or 0)
            movie = self._library_movie(payload)
            if movie is not None and name == 'ctx_rate' and rating and movie['playcount'] == 0:
                # Simkl files a rated movie it does not have as watched, and the next sync would mark it so in Kodi
                utils.notify(utils.get_str(32299).format(movie['label']))
                return
            if movie is not None and name == 'ctx_plantowatch' and movie['playcount'] > 0:
                # a move to Plan to watch takes a watched movie out of the watched list on Simkl, with its date
                utils.notify(utils.get_str(32314).format(movie['label']))
                return
            target = (('movies', movie['ids'], movie['label']) if movie['ids'] else None) if movie is not None else self._show_target(payload)
            if target is None:
                utils.notify(utils.get_str(32257))
                return
            account = settings.account_id()
            if name == 'ctx_rate':
                self._rate(target, rating, account)
            else:
                self.sender.submit(lambda: self._plan_to_watch(target, account))
            return
        if not library and dbtype in ('tvshow', 'season'):
            utils.notify(utils.get_str(32270))
            return
        items = [item for item in self._episode_targets(payload) if item.get('ids') or item.get('episode_ids')]
        if not items:
            utils.notify(utils.get_str(32257))
            return
        label = items[0]['label'] if len(items) == 1 else utils.get_str(32262).format(len(items))
        for item in items:
            if name == 'ctx_mark':
                self.history.add_mark(item)
            else:
                self.history.add_unmark(item, explicit=True)
        if library:
            # Kodi follows: an entry in its own menu must not leave the item in the other state there; the echo is guarded
            for item in items:
                self.marks.guard(item['kind'], item['dbid'])
            refused = playerlib.set_watched(items, name == 'ctx_mark')
            if refused:
                utils.warn('%d library items kept their play state, Kodi refused the write' % refused)
        if name == 'ctx_mark' or items[0]['kind'] != 'movie':
            # an unmarked movie gets its question instead; the toast follows the answer
            utils.notify(utils.get_str(32255 if name == 'ctx_mark' else 32256).format(label))

    @staticmethod
    def _episode_targets(payload):
        """The movies and episodes an action applies to: a show or a season fans out to the episodes Kodi has."""
        dbtype = payload.get('dbtype') or ''
        dbid = int(payload.get('dbid') or 0)
        if dbid > 0:
            if dbtype in ('movie', 'episode'):
                item = playerlib.library_item(dbtype, dbid)
                # the other episodes of a multi-episode file share Kodi's play state: the action covers them too
                return ([item] + playerlib.file_siblings(item)) if item else []
            if dbtype == 'tvshow':
                return playerlib.show_episodes(dbid)
            if dbtype == 'season':
                season = playerlib.season_details(dbid)
                return playerlib.show_episodes(season['tvshowid'], season.get('season')) if season.get('tvshowid') else []
            return []
        ids = utils.ids_from(payload.get('ids'))
        if dbtype == 'movie' and ids:
            return [playerlib.remote_movie(ids, payload.get('title'), payload.get('year') or None)]
        show_ids = utils.ids_from(payload.get('show_ids'))
        if dbtype == 'episode' and show_ids and int(payload.get('number') or 0) > 0:
            # an add-on's episode row: the show's ids from its properties, its own uniqueid is the episode's (Kodi's convention)
            return [playerlib.remote_episode(show_ids, payload.get('showtitle'), payload.get('title'), payload.get('year') or None, payload.get('season'),
                                             payload.get('number'), payload.get('file') or '', episode_ids=playerlib.episode_ids_from(payload.get('ids')))]
        return []

    @staticmethod
    def _library_movie(payload):
        """The library movie a row is about, with Kodi's play state; None for any other row or one Kodi has no row for."""
        if (payload.get('dbtype') or '') != 'movie' or int(payload.get('dbid') or 0) <= 0:
            return None
        return playerlib.library_item('movie', int(payload['dbid']))

    @staticmethod
    def _show_target(payload):
        """(bucket, ids, label) for Plan to watch: a movie, or the show of an episode, season or show item."""
        dbtype = payload.get('dbtype') or ''
        dbid = int(payload.get('dbid') or 0)
        if dbid > 0:
            if dbtype == 'movie':
                item = playerlib.library_item('movie', dbid)
                return ('movies', item['ids'], item['label']) if item and item['ids'] else None
            if dbtype == 'episode':
                item = playerlib.library_item('episode', dbid)
                return ('shows', item['ids'], item['showtitle']) if item and item['ids'] else None
            tvshowid = playerlib.season_details(dbid).get('tvshowid') if dbtype == 'season' else dbid
            if dbtype not in ('tvshow', 'season') or not tvshowid:
                return None
            show = playerlib.show_details(tvshowid)
            ids = utils.ids_from(show.get('uniqueid'))
            return ('shows', ids, show.get('title') or payload.get('label') or '') if ids else None
        if dbtype == 'episode':
            show_ids = utils.ids_from(payload.get('show_ids'))
            return ('shows', show_ids, payload.get('showtitle') or payload.get('label') or '') if show_ids else None
        ids = utils.ids_from(payload.get('ids'))
        if not ids or dbtype not in ('movie', 'tvshow', 'season'):
            return None
        if dbtype == 'movie':
            return 'movies', ids, payload.get('title') or payload.get('label') or ''
        return 'shows', ids, payload.get('showtitle') or payload.get('title') or payload.get('label') or ''

    def _file_action(self, name, path, payload, account):
        item = {'kind': None, 'dbid': None, 'file': path, 'title': payload.get('title') or '', 'showtitle': payload.get('showtitle') or ''}
        try:
            resolved = playerlib.search_file(self.api, self.auth, account, item)
        except InvalidToken:
            return
        except ApiError as exc:
            utils.notify(utils.get_str(32210) if exc.transport else utils.get_str(32264).format(exc.message or exc.error or exc.status))
            return
        if resolved is None:
            utils.notify(utils.get_str(32263).format(os.path.basename(path)))
            return
        if name in ('ctx_plantowatch', 'ctx_rate'):
            target = ('movies' if resolved['kind'] == 'movie' else 'shows', resolved['ids'], resolved.get('showtitle') or resolved['label'])
            if name == 'ctx_rate':
                self._rate(target, int(payload.get('rating') or 0), account)
            else:
                self._plan_to_watch(target, account)
        elif name == 'ctx_mark':
            # bound to the account the action was issued under: a login that landed during the file search must not inherit it
            self.history.add_mark(resolved, account=account)
            playerlib.set_file_watched(path, True)
            utils.notify(utils.get_str(32255).format(resolved['label']))
        else:
            self.history.add_unmark(resolved, explicit=True, account=account)
            playerlib.set_file_watched(path, False)
            if resolved['kind'] != 'movie':
                utils.notify(utils.get_str(32256).format(resolved['label']))

    def _plan_to_watch(self, target, account):
        bucket, ids, label = target
        self._post_item('/sync/add-to-list', bucket, {'ids': ids, 'to': 'plantowatch'}, account, label, utils.get_str(32254).format(label))

    def _rate(self, target, rating, account):
        """1-10 rates the show or the movie on Simkl, 0 removes the rating. Queued, from whichever thread (the queue
        takes its lock): a send that fails is tried again, the latest rating of a title wins, and the sync leaves the
        title's Kodi rating alone until it is delivered."""
        label = target[2]
        self.history.add_rating(target, rating, account)
        utils.notify(utils.get_str(32277).format(label, rating) if rating else utils.get_str(32278).format(label))

    def _post_item(self, path, bucket, entry, account, label, done):
        """One item to a /sync endpoint (movies or shows); Simkl's not_found names what it could not place."""
        try:
            answer = self.auth.authorized(lambda token: self.api.call('POST', path, {bucket: [entry]}, token=token), account)
        except InvalidToken:
            return
        except ApiError as exc:
            utils.notify(utils.get_str(32210) if exc.transport else utils.get_str(32264).format(exc.message or exc.error or exc.status))
            return
        if ((answer or {}).get('not_found') or {}).get(bucket):
            utils.notify(utils.get_str(32263).format(label))
            return
        utils.notify(done)
