# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
"""WatchNPlay-Dienst: laeuft ab Kodi-Start im Hintergrund."""

import json
import threading

import xbmc

from resources.lib import library, player, util
from resources.lib.api import Api
from resources.lib.store import Store
from resources.lib.sync import SyncEngine

STARTUP_DELAY = 30
# Wiedergabeposition: eigener Takt, unabhaengig von laufenden Anfragen
SAMPLE_EVERY = 1


class Ui(object):
    def notify(self, string_id, *args):
        text = util.lang(string_id)
        if args:
            text = text % args
        util.notify(text)

    def status(self, paired, user, device, pro_paused):
        util.set_status(paired, user, device, pro_paused)

    def log(self, msg):
        util.log(msg)

    def warn(self, msg):
        util.warn(msg)


def make_api(token):
    return Api(util.api_base(), util.user_agent(), token)


class Service(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.store = Store(util.profile_dir())
        self.tracker = None
        self.engine = SyncEngine(self.store, library, Ui(), make_api,
                                 wait=self._wait, min_percent=util.watched_threshold,
                                 is_playing=self._is_playing)
        self.tracker = player.Tracker(self.engine.queue_play)

    def _is_playing(self):
        return self.tracker is not None and self.tracker.isPlayingVideo()

    def _wait(self, seconds):
        """Pause zwischen Abgleich-Haeppchen."""
        return self.waitForAbort(seconds)

    def _sample(self):
        """Position der Wiedergabe jede Sekunde mitschreiben, auch waehrend eine Anfrage haengt.

        Nach dem Stopp ist sie nicht mehr lesbar, und Kodi ruft onPlayBackStopped erst auf,
        wenn der Dienst-Thread wieder wartet."""
        while not self.abortRequested():
            try:
                self.tracker.update()
            except Exception as exc:
                util.warn('position sampling failed: %s' % exc)
            if self.waitForAbort(SAMPLE_EVERY):
                break

    def onNotification(self, sender, method, data):
        try:
            if method == 'VideoLibrary.OnScanFinished':
                self.engine.request_full()
            elif method == 'VideoLibrary.OnUpdate':
                payload = json.loads(data or '{}')
                if 'playcount' not in payload:
                    return
                item = payload.get('item') or {}
                if item.get('type') in ('movie', 'episode') and (item.get('id') or 0) > 0:
                    self.engine.on_library_update('%s:%d' % (item['type'], item['id']),
                                                  payload.get('playcount'))
            elif sender == util.ADDON_ID:
                if method == 'Other.paired':
                    self.engine.on_paired()
                elif method == 'Other.unpaired':
                    self.engine.on_unpaired()
                elif method == 'Other.syncnow':
                    self.engine.sync_now()
        except Exception as exc:
            util.warn('notification %s not handled: %s' % (method, exc))

    def run(self):
        util.log('service started')
        sampler = threading.Thread(target=self._sample, name='watchnplay-position')
        sampler.daemon = True
        sampler.start()
        if not self.waitForAbort(STARTUP_DELAY):
            self.engine.refresh_ui()
            while not self.abortRequested():
                try:
                    self.engine.tick()
                except Exception as exc:
                    util.warn('sync tick failed: %s' % exc)
                if self.waitForAbort(1):
                    break
        try:
            self.store.save_if_dirty()
        except OSError as exc:
            util.warn('queue not saved: %s' % exc)
        sampler.join(5)
        util.log('service stopped')
