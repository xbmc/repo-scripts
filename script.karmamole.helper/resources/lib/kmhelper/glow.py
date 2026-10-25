# KarmaMole Skin Helper (script.karmamole.helper)
# Copyright (C) 2026 Omar Kamel
# SPDX-License-Identifier: GPL-2.0-or-later
"""Colours + soft art for one image, and the Window(Home) properties they are published under.

Published names (prefix 'Groove' for the focused item, 'Groove.Player' for the playing album):
  <prefix>.Color.Main / .Accent / .Shadow / .Average   AARRGGBB
  <prefix>.Art.Soft    dark-room wash PNG (16:9)        <prefix>.Art.SoftLight  light-room pastel wash PNG (16:9)
  <prefix>.Art.Halo    halo PNG (art aspect)
  Color.Main / .Accent step from the old to the new colour (8 writes over 400 ms); the A/B fields switch at once.
  <prefix>.Art.Source  the art URL the values belong to (gate on it to never show a neighbour's colours)
  <prefix>.Slot        A or B, flips on every change; <prefix>.A.* / <prefix>.B.* hold the same fields per slot, so a
                       skin can cross-fade two layers (the outgoing layer keeps its old values while it fades)."""
import hashlib
import os
import threading
import time
from collections import OrderedDict

import xbmc

from . import artload, colours
from .colours import argb
from .common import TEMP, TEMP_SPECIAL, get_pil, log, prop, set_prop, write_atomic

SOFT_DIR = os.path.join(TEMP, 'soft')
SOFT_SPECIAL = TEMP_SPECIAL + 'soft/'
FIELDS = ('Color.Main', 'Color.Accent', 'Color.Shadow', 'Color.Average', 'Art.Soft', 'Art.SoftLight', 'Art.Halo')
FADE_FIELDS = ('Color.Main', 'Color.Accent')  # stepped by the Fader; the other fields switch at once
FADE_MS = 400
FADE_STEPS = 8
KEEP_FILES = 450   # soft-art files kept after a prune (three per item)
PRUNE_AT = 900


class Renderer(object):
    """url -> {field: value}. Memory LRU first; files on disk are reused by name (hash of the image version).
    soft=False (the skin has 'colours' without 'softart'): colours only, no PNG is written and the Art.* fields stay
    empty."""

    def __init__(self, soft=True):
        self.mem = OrderedDict()
        self._pil = None
        self.writes = 0
        self.soft = soft
        self.prune()

    def set_soft(self, soft):
        if soft != self.soft:
            self.soft = soft
            self.mem.clear()

    def pil(self):
        if self._pil is None:
            self._pil = get_pil() or False
        return self._pil

    def render(self, url):
        if url in self.mem:
            self.mem.move_to_end(url)
            return self.mem[url]
        pil = self.pil()
        if not pil:
            return None
        data, stamp = artload.load(url)
        if not data:
            log('no bytes for %s' % url)
            return None
        try:
            im = colours.open_image(data, pil[0])
            pal = colours.palette(im, pil[0])
            key = hashlib.md5(('%d|%s' % (colours.ALGO, stamp)).encode('utf-8')).hexdigest()[:20]
            names = {}
            for kind in (('w', 'l', 'h') if self.soft else ()):
                name = '%s_%s.png' % (key, kind)
                path = os.path.join(SOFT_DIR, name)
                if os.path.isfile(path):
                    os.utime(path, None)  # keeps it young for the prune
                else:
                    if kind == 'w':
                        img = colours.wash_image(im, pil)
                    elif kind == 'l':
                        img = colours.wash_light_image(im, pil)
                    else:
                        img = colours.halo_image(im, pal['main'], pil)
                    write_atomic(path, colours.png_bytes(img))
                    self.writes += 1
                names[kind] = SOFT_SPECIAL + name
        except Exception as e:  # noqa: BLE001 - a bad image must never stop the service
            log('render failed for %s: %s' % (url, e), xbmc.LOGWARNING)
            return None
        values = {
            'Color.Main': colours.argb(pal['main']),
            'Color.Accent': colours.argb(pal['accent']),
            'Color.Shadow': colours.argb(pal['shadow']),
            'Color.Average': colours.argb(pal['average']),
            'Art.Soft': names.get('w'),
            'Art.SoftLight': names.get('l'),
            'Art.Halo': names.get('h'),
        }
        self.mem[url] = values
        while len(self.mem) > 300:
            self.mem.popitem(last=False)
        if self.writes >= 100:
            self.writes = 0
            self.prune()
        return values

    def prune(self):
        try:
            files = [os.path.join(SOFT_DIR, f) for f in os.listdir(SOFT_DIR) if f.endswith('.png')]
        except OSError:
            return
        if len(files) <= PRUNE_AT:
            return
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        for p in files[KEEP_FILES:]:
            try:
                os.remove(p)
            except OSError:
                pass
        self.mem.clear()  # some remembered names may point at removed files
        log('pruned soft art to %d files' % KEEP_FILES)


def _parse(argb):
    try:
        v = int(argb, 16)
        return ((v >> 16) & 255, (v >> 8) & 255, v & 255)
    except (TypeError, ValueError):
        return None


class Fader(object):
    """Steps the plain <prefix>.Color.Main / .Accent properties from the shown colour to the new one: FADE_STEPS writes
    over FADE_MS (Kodi changes a colordiffuse instantly; only image swaps cross-fade). Runs in its own thread so the
    service keeps polling; a new target mid-fade starts from the colour on screen at that moment."""

    def __init__(self, prefix, threaded=True):
        self.prefix = prefix
        self.shown = {}      # field -> (r, g, b) currently written (seeded from Home, for short RunScript processes)
        for f in FADE_FIELDS:
            c = _parse(prop('%s.%s' % (prefix, f)))
            if c is not None:
                self.shown[f] = c
        self.target = {}
        self.start = {}
        self.cond = threading.Condition()
        self.gen = 0
        self.faded = 0       # last generation the worker picked up
        self.stopping = False
        self.threaded = threaded
        self.thread = None
        if threaded:
            self.thread = threading.Thread(target=self._run, name='kmhelper.fade.%s' % prefix)
            self.thread.daemon = True  # Kodi still waits for daemon threads when it stops a script: stop() ends it
            self.thread.start()

    def set(self, values):
        """values: {field: 'AARRGGBB'} or None (clear at once)."""
        with self.cond:
            self.gen += 1
            if not values:
                self.target, self.shown = {}, {}
                for f in FADE_FIELDS:
                    set_prop('%s.%s' % (self.prefix, f), None)
                return
            self.target = {f: _parse(values.get(f)) for f in FADE_FIELDS}
            start = {}
            for f, c in self.target.items():
                if c is None or f not in self.shown:  # first colour (or none): no fade, write it now
                    set_prop('%s.%s' % (self.prefix, f), values.get(f))
                    self.shown[f] = c
                    if c is None:
                        self.shown.pop(f, None)
                else:
                    start[f] = self.shown[f]
            self.start = start
            self.cond.notify()
        if not self.threaded:
            self._fade(self.gen)

    def stop(self, timeout=1.0):
        """End the worker thread (service shutdown). Kodi kills a script whose threads outlive the 5 s stop window."""
        with self.cond:
            self.stopping = True
            self.cond.notify_all()
        if self.thread is not None and self.thread is not threading.current_thread():
            self.thread.join(max(0.0, timeout))

    def _run(self):
        # Short waits plus a generation counter: never blocks for good (so stop() ends it at once) and a set() that
        # lands while a fade is running is not lost.
        while True:
            with self.cond:
                if not self.stopping and self.gen == self.faded:
                    self.cond.wait(0.5)
                if self.stopping:
                    return
                gen = self.gen
                if gen == self.faded:
                    continue
                self.faded = gen
            self._fade(gen)

    def _fade(self, gen):
        start = dict(self.start)
        if not start:
            return
        for k in range(1, FADE_STEPS + 1):
            t = k / float(FADE_STEPS)
            t = t * t * (3 - 2 * t)  # smoothstep: eases in and out like the image fades
            with self.cond:
                if gen != self.gen or self.stopping:
                    return  # a newer colour arrived (it fades from wherever we are now), or shutting down
                for f, a in start.items():
                    b = self.target.get(f)
                    if b is None:
                        continue
                    c = tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))
                    self.shown[f] = c
                    set_prop('%s.%s' % (self.prefix, f), argb(c))
            if k < FADE_STEPS:
                time.sleep(FADE_MS / 1000.0 / FADE_STEPS)


class Publisher(object):
    def __init__(self, prefix, threaded=True):
        self.prefix = prefix
        self.fader = Fader(prefix, threaded)
        self.source = None
        self.slot = 'A' if prop('%s.Slot' % prefix) == 'A' else 'B'  # carry on alternating across processes

    def publish(self, source, values):
        """values None = nothing to show (no art, no PIL, unreadable): clears the current names so the skin falls back."""
        if source == self.source:
            return
        self.source = source
        p = self.prefix
        self.slot = 'A' if self.slot == 'B' else 'B'
        for f in FIELDS:
            v = values.get(f) if values else None
            set_prop('%s.%s.%s' % (p, self.slot, f), v)
            if f not in FADE_FIELDS:
                set_prop('%s.%s' % (p, f), v)
        set_prop('%s.Art.Source' % p, source if values else None)
        set_prop('%s.Slot' % p, self.slot)
        self.fader.set(values)  # Color.Main / .Accent step over FADE_MS

    def stop(self, timeout=1.0):
        self.fader.stop(timeout)

    def clear(self):
        if self.source is None:
            return
        self.source = None
        self.fader.set(None)
        for f in FIELDS:
            for name in ('%s.%s' % (self.prefix, f), '%s.A.%s' % (self.prefix, f), '%s.B.%s' % (self.prefix, f)):
                set_prop(name, None)
        set_prop('%s.Art.Source' % self.prefix, None)
        set_prop('%s.Slot' % self.prefix, None)
