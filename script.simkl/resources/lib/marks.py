#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""Watched marks made by hand in the Kodi library (VideoLibrary.OnUpdate with a playcount) feed the history queue."""

import json
import threading
import time

from resources.lib import player as playerlib
from resources.lib import settings, utils

# Kodi's own watched bump follows the stop within a second or two; the sync's writes echo later when a big run holds
# up Kodi's GUI, so their guard lasts longer. A guard is consumed by the echo, so a mark the user makes right after
# still counts as theirs
GUARD_SECONDS = 10
IMPORT_GUARD_SECONDS = 600


class Marks:
    def __init__(self, auth, history, playing):
        """playing(kind, dbid): whether the scrobbler has that item open; Kodi's own playcount bump at the end of a
        playback arrives before the stop event, so the guard set at the stop would come too late for it."""
        self.auth = auth
        self.history = history
        self.playing = playing
        self.guarded = {}
        self.lock = threading.Lock()

    def guard(self, kind, dbid, seconds=GUARD_SECONDS):
        """Kodi's own playcount bump after a playback and the importer's writes must not come back as marks."""
        with self.lock:
            self.guarded['%s:%s' % (kind, dbid)] = time.time() + seconds

    def _is_guarded(self, kind, dbid):
        """True once per guard: the write it was set for announces itself once."""
        now = time.time()
        with self.lock:
            for key in [k for k, until in self.guarded.items() if until < now]:
                del self.guarded[key]
            return self.guarded.pop('%s:%s' % (kind, dbid), 0) > now

    def _unguard(self, kind, dbid):
        with self.lock:
            self.guarded.pop('%s:%s' % (kind, dbid), None)

    def on_update(self, data, arrived=None):
        """arrived: when Kodi announced it; the events of a bulk unmark are judged by Kodi's timing, not by the loop's."""
        try:
            params = json.loads(data) if data else {}
        except ValueError:
            return
        if 'playcount' not in params:
            return
        utils.log('library update: %s' % data)
        item = params.get('item') or {}
        kind = item.get('type')
        dbid = item.get('id')
        played = int(params.get('playcount') or 0) > 0
        when = arrived or time.time()
        if params.get('transaction'):
            # Kodi flags the play counts written while a scan or clean runs (its own, from NFO files; a mark made during
            # one as well, which it cannot tell apart): not the user's
            return
        sending = self.auth.logged_in() and settings.get_bool(settings.SYNC_MARKS, True)
        if kind in ('tvshow', 'season', 'set'):
            if not played and sending:
                self.history.note_folder_unmark()
            return
        if kind not in ('movie', 'episode') or not dbid:
            return
        if played and (self._is_guarded(kind, dbid) or self.playing(kind, dbid)):
            # a watched count that Kodi set itself (the bump at the end of a playback), or the sync's and this add-on's
            # own writes echoing back; Kodi never unmarks by itself, so an unmark is always the user's
            self.history.note_library_state('%s:%s' % (kind, dbid), True, when)
            utils.log('watched count of %s %s is the playback\'s own or this add-on\'s, not a mark' % (kind, dbid))
            return
        details = playerlib.library_item(kind, dbid)
        if details is None:
            return
        # the other episodes of a multi-episode file share Kodi's play state with this one
        items = [details] + playerlib.file_siblings(details)
        for item in items:
            # the ledger follows Kodi's own watched state whatever the switches say: the sync must not undo an unmark
            self.history.note_library_state(item['key'], played, when)
        if not sending:
            return
        if not played:
            # the user is at this item: a mark that follows is theirs, whatever guard was left on it
            self._unguard(kind, dbid)
            if self._eligible(details):
                self.history.add_unmark(details, arrived=arrived, siblings=[item for item in items[1:] if self._eligible(item)])
            return
        watched = utils.kodi_date_to_ts(details.get('lastplayed')) or time.time()
        for item in items:
            if self._eligible(item):
                self.history.add_mark(item, watched)

    @staticmethod
    def _eligible(item):
        if not (item.get('ids') or item.get('episode_ids')):
            return False
        if not settings.tracked(item['kind']):
            return False
        return not playerlib.excluded(item.get('file') or '')
