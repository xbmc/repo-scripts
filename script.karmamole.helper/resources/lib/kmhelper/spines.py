# KarmaMole Skin Helper (script.karmamole.helper)
# Copyright (C) 2026 Omar Kamel
# SPDX-License-Identifier: GPL-2.0-or-later
"""Pre-rendered album spines for Groove's Shelf of spines view.

Per album: its main colour (cached in addon_data/script.karmamole.helper/spines.json by cover URL, so only new or changed
covers are decoded), rendered as two tiny PNGs:
  special://temp/script.karmamole.helper/spines/<gen>/dark/<albumid>.png    (L 0.36, for white ink)
  special://temp/script.karmamole.helper/spines/<gen>/light/<albumid>.png   (L 0.80, for dark ink)
Every build writes a new <gen> folder, then publishes Window(Home).Property(Groove.Spines.Path) and only then deletes
the old folder, so a path the skin holds is never half-written and a texture can never be served stale.
Runs on first start, after music library scans/cleans, and on request (NotifyAll(script.karmamole.helper,spines_rebuild)).
"""
import os
import shutil
import threading
import time

import xbmc

from . import artload, colours, library
from .common import (PROFILE, TEMP, TEMP_SPECIAL, cond, get_pil, log, read_json, set_prop, skin_is_groove,
                     write_atomic, write_json)

INDEX = os.path.join(PROFILE, 'spines.json')
ROOT = os.path.join(TEMP, 'spines')
VERSION = 1


def _set_ready():
    if skin_is_groove():  # Skin.SetBool writes into the running skin's settings: only ever Groove's
        xbmc.executebuiltin('Skin.SetBool(Groove.SpinesReady)')


class SpineBuilder(object):
    def __init__(self, monitor):
        self.monitor = monitor
        self.event = threading.Event()
        self.force = False
        self.not_before = 0.0
        self.gen = None
        self.count = 0
        self.stopping = threading.Event()
        self.thread = None  # started by the first request: a skin without 'spines' never gets the worker

    def _start(self):
        if self.thread is None and not self.stopping.is_set():
            self.thread = threading.Thread(target=self._run, name='kmhelper.spines')
            self.thread.daemon = True  # Kodi still waits for daemon threads when it stops a script: stop() ends it
            self.thread.start()

    def stop(self, timeout=1.0):
        """Service shutdown: the worker leaves within ~0.1 s, also mid-build (the half-written generation folder is
        never published and the next build deletes it)."""
        self.stopping.set()
        self.event.set()
        if self.thread is not None and self.thread is not threading.current_thread():
            self.thread.join(max(0.0, timeout))

    def _aborted(self):
        return self.stopping.is_set() or self.monitor.abortRequested()

    def _wait(self, seconds):
        """Sleep in short slices; True as soon as Kodi asks us to stop (then return at once)."""
        end = time.time() + seconds
        while True:
            if self._aborted():
                return True
            left = end - time.time()
            if left <= 0:
                return False
            if self.monitor.waitForAbort(min(0.1, left)):
                return True

    # ------------------------------------------------------------------------------------------- requests
    def request(self, delay=0.0, force=False):
        self.not_before = max(self.not_before, time.time() + delay)
        self.force = self.force or force
        self._start()
        self.event.set()

    def republish(self):
        """After a skin switch: the path property survives, but Groove's SpinesReady bool may not be set yet."""
        if self.gen:
            _set_ready()

    # ------------------------------------------------------------------------------------------- worker
    def _run(self):
        while not self._aborted():
            if not self.event.wait(0.25):
                continue
            if self._aborted():
                return
            while time.time() < self.not_before:  # a request during the wait may push not_before later
                if self._wait(min(0.5, self.not_before - time.time())):
                    return
            self.event.clear()
            force, self.force = self.force, False
            if 'spines' not in getattr(self.monitor, 'features', ()):
                continue  # the skin switched away (or opted out) while the request waited
            try:
                self.build(force)
            except Exception as e:  # noqa: BLE001
                log('spine build failed: %s' % e, xbmc.LOGERROR)

    def _busy(self):
        """Never compete with video playback or a running scan."""
        return cond('Player.HasVideo | Library.IsScanningMusic')

    def build(self, force):
        sig = library.signature()
        index = read_json(INDEX, {})
        if index.get('v') != VERSION:
            index = {}
        gen = index.get('gen')
        on_disk = bool(gen) and os.path.isdir(os.path.join(ROOT, str(gen)))
        if not force and sig and index.get('sig') == sig and on_disk:
            self._publish(gen, index.get('count', 0))
            return
        while self._busy():
            if self._wait(5):
                return
        if self._aborted():
            return
        albums = library.albums(sig)
        old = {} if force else index.get('colours', {})
        new = {}
        pil = None
        decoded = 0
        for a in albums:
            if self._aborted():
                return
            url = a.get('thumb') or ''
            if not artload.usable(url):
                continue
            aid = str(a['id'])
            prev = old.get(aid)
            if prev and prev.get('url') == url:
                new[aid] = prev
                continue
            if pil is None:
                pil = get_pil() or False
            if not pil:
                break
            while self._busy():
                if self._wait(5):
                    return
            data, _ = artload.load(url)
            if not data:
                continue
            try:
                im = colours.open_image(data, pil[0])
                new[aid] = {'url': url, 'main': list(colours.palette(im, pil[0])['main'])}
            except Exception as e:  # noqa: BLE001
                log('spine colour failed for album %s: %s' % (aid, e))
                continue
            decoded += 1
            if self._wait(0.03):  # yield: a full first build of 229 albums takes ~15-30 s
                return
        if not new:
            log('no spines (no covers or no PIL)')
            return
        gen = str(int(time.time()))
        base = os.path.join(ROOT, gen)
        for aid, c in new.items():
            if self._aborted():
                return  # not published; the next build removes the partial folder
            for room in ('dark', 'light'):
                write_atomic(os.path.join(base, room, aid + '.png'), colours.spine_png(c['main'], room))
        write_json(INDEX, {'v': VERSION, 'sig': sig, 'gen': gen, 'count': len(new), 'colours': new})
        self._publish(gen, len(new))
        # old generations: Kodi has already loaded what it shows, so they can go now
        for d in os.listdir(ROOT):
            if d != gen:
                shutil.rmtree(os.path.join(ROOT, d), ignore_errors=True)
        log('spines built: %d albums (%d decoded), gen %s' % (len(new), decoded, gen), xbmc.LOGINFO)

    def _publish(self, gen, count):
        self.gen, self.count = gen, count
        set_prop('Groove.Spines.Path', '%sspines/%s/' % (TEMP_SPECIAL, gen))
        set_prop('Groove.Spines.Count', count)
        _set_ready()
