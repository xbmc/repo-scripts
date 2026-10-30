# KarmaMole Skin Helper (script.karmamole.helper)
# Copyright (C) 2026 Omar Kamel
# SPDX-License-Identifier: GPL-2.0-or-later
"""KarmaMole Skin Helper service: browse-time colours + soft art, playing-album colours, album spines.

Cost model (NVIDIA Shield):
- Runs only the features the running skin asked for (features.py: the per-skin table, or
  Window(Home).Property(KarmaMole.Helper.Features)). No features: one skin id + one property check per second, no
  worker threads, no file access.
- Browsing: reads 2-3 infolabels every 0.15 s and compares strings. Work happens only when the focused item's art has
  been the same for REST seconds (fast scrolling costs nothing), and a repeat visit is a memory hit.
- Fullscreen video, slideshow and screensaver: browse polling drops to once a second and does no work.
- Playing album: checked once a second while audio plays; one render per album change.
- Spines: a background thread, only after library changes, paused while video plays or a scan runs.
"""
import time

import xbmc

from . import artload, features as feats
from .common import ADDON_ID, cond, infos, log, prop, set_prop, skin_is_groove
from .glow import Publisher, Renderer
from .spines import SpineBuilder

TICK = 0.15        # browse poll while active
IDLE_TICK = 1.0    # poll when disabled / fullscreen video / screensaver
REST = 0.4         # the focused art must rest this long before we render (spec: 400 ms)
PLAYER_EVERY = 1.0
SKIN_EVERY = 1.0
PAUSE_COND = ('Window.IsActive(fullscreenvideo) | Window.IsActive(slideshow) | System.ScreenSaverActive | '
              'Window.IsActive(startup)')
VIDEO_TYPES = ('movie', 'tvshow', 'season', 'episode', 'set', 'musicvideo', 'video')
VIDEO_ART = ('fanart', 'landscape', 'thumb', 'poster')
MUSIC_ART = ('thumb', 'album.thumb', 'fanart')
ART_KEYS = tuple(dict.fromkeys(VIDEO_ART + MUSIC_ART))  # one read covers both chains
PLAYER_ART = ('Player.Art(thumb)', 'Player.Art(album.thumb)', 'MusicPlayer.Cover')
START_DELAY = 20.0  # first spine check after login: let Home settle first
RUNNING = 'KarmaMole.Helper.Running'   # 'true' while the service runs (skins gate on it)
ACTIVE = 'KarmaMole.Helper.Active'     # the features running for the current skin, comma list (empty = idle)


class Player(xbmc.Player):
    def __init__(self, svc):
        super(Player, self).__init__()
        self.svc = svc

    def onAVStarted(self):
        self.svc.player_dirty = True

    def onPlayBackStarted(self):
        self.svc.player_dirty = True

    def onPlayBackStopped(self):
        self.svc.player_dirty = True

    def onPlayBackEnded(self):
        self.svc.player_dirty = True

    def onPlayBackError(self):
        self.svc.player_dirty = True


class Service(xbmc.Monitor):
    def __init__(self):
        super(Service, self).__init__()
        # colour parts are made when a skin first asks for 'colours' (their fade threads and the soft-art prune
        # cost nothing until then); the spine worker starts on its first request
        self.renderer = self.browse = self.playing = None
        self.player = Player(self)
        self.spines = SpineBuilder(self)
        self.features = frozenset()
        self.enabled = False   # any feature on
        self.colours = False
        self.skin = None
        # browse state
        self.seen, self.seen_at, self.done = None, 0.0, None
        # player state
        self.player_dirty = True
        self.music = False
        self.player_key, self.player_pending = None, None
        self.next_player = 0.0
        self.next_skin = 0.0

    # ------------------------------------------------------------------------------------------- Kodi callbacks
    def onScanFinished(self, library):
        if library == 'music' and 'spines' in self.features:
            self.spines.request(delay=5.0)

    def onCleanFinished(self, library):
        if library == 'music' and 'spines' in self.features:
            self.spines.request(delay=5.0)

    def onNotification(self, sender, method, data):
        """NotifyAll(script.karmamole.helper,<message>) from a skin or from default.py."""
        if sender != ADDON_ID:
            return
        msg = method.split('.', 1)[-1]
        log('notification %s' % msg)
        if msg == 'spines_rebuild':
            if 'spines' in self.features:
                self.spines.request(force=True)
        elif msg == 'refresh':  # republish everything (e.g. after the skin reloaded)
            if self.colours:
                self.renderer.forget()  # else a URL memory hit keeps a replaced cover's old colours
                self.browse.source = self.playing.source = None
                self.done = self.player_key = None
            if 'spines' in self.features:
                self.spines.request()

    # ------------------------------------------------------------------------------------------- main loop
    def run(self):
        log('started')
        set_prop(RUNNING, 'true')
        try:
            self.loop()
        finally:
            self.shutdown()
        set_prop(RUNNING, None)
        set_prop(ACTIVE, None)
        log('stopped')

    def shutdown(self):
        """Kodi kills a service that hasn't ended within 5 s of the stop request, and it waits for EVERY Python thread
        (daemon or not). Stop the spine worker and both fade workers; all joins share one short budget."""
        end = time.time() + 2.0
        for worker in (self.spines, self.browse, self.playing):
            if worker is None:
                continue
            try:
                worker.stop(end - time.time())
            except Exception as e:  # noqa: BLE001
                log('stop failed: %s' % e, xbmc.LOGWARNING)

    def loop(self):
        while not self.abortRequested():
            now = time.time()
            if now >= self.next_skin:
                self.next_skin = now + SKIN_EVERY
                self.check_enabled()
            tick = IDLE_TICK
            if self.colours:
                if self.player_dirty or now >= self.next_player:
                    self.next_player = now + PLAYER_EVERY
                    self.player_tick()
                if prop('Groove.Helper.Browse').lower() != 'off' and not cond(PAUSE_COND):
                    self.browse_tick(now)
                    tick = TICK
            if self.waitForAbort(tick):
                break

    def check_enabled(self):
        skin = xbmc.getSkinDir()
        want = feats.resolve(skin, prop(feats.OPT_IN))
        if want != self.features:
            log('features for %s: %s' % (skin, ','.join(sorted(want)) or 'none (idle)'), xbmc.LOGINFO)
            set_prop(ACTIVE, ','.join(sorted(want)))
        colours = 'colours' in want
        if colours and not self.colours:
            if self.renderer is None:
                self.renderer = Renderer(soft='softart' in want, keep=self.published_files)
                self.browse = Publisher('Groove')
                self.playing = Publisher('Groove.Player')
            self.player_dirty = True
        elif self.colours and not colours:
            self.browse.clear()
            self.playing.clear()
            self.seen = self.done = self.player_key = self.player_pending = None
            self.music = False
        if colours and self.renderer.soft != ('softart' in want):
            self.renderer.set_soft('softart' in want)
            self.browse.source = self.playing.source = None  # republish without / with the soft-art files
            self.done = self.player_key = None
        spines = 'spines' in want
        if spines and 'spines' not in self.features:
            self.spines.request(delay=START_DELAY if self.skin is None else 2.0)
        elif spines and skin != self.skin and skin_is_groove():
            self.spines.republish()
        self.features, self.colours, self.enabled, self.skin = want, colours, bool(want), skin

    def published_files(self):
        """Soft-art files on Window(Home) right now: the renderer's prune keeps them."""
        out = set()
        for pub in (self.browse, self.playing):
            if pub is not None:
                out |= pub.files()
        return out

    # ------------------------------------------------------------------------------------------- browsing
    def focused_art(self):
        cid = prop('Groove.Helper.Container')
        base = 'Container(%s).ListItem' % cid if cid.isdigit() else 'ListItem'
        # one GUI-thread read of the type and every art key (common.infos: getInfoLabel on ListItem.* races a view
        # switch and crashed Kodi 21.2)
        names = [base + '.DBType'] + ['%s.Art(%s)' % (base, k) for k in ART_KEYS]
        got = infos(*names)
        keys = VIDEO_ART if got.get(names[0], '') in VIDEO_TYPES else MUSIC_ART
        for k in keys:
            v = got.get('%s.Art(%s)' % (base, k), '')
            if artload.usable(v):
                return v
        return ''

    def browse_tick(self, now):
        url = self.focused_art()
        if url != self.seen:
            self.seen, self.seen_at = url, now
            return
        if url == self.done or now - self.seen_at < REST:
            return
        self.done = url
        self.browse.publish(url, self.renderer.render(url) if url else None)

    # ------------------------------------------------------------------------------------------- playing album
    def player_tick(self):
        if self.player_dirty:
            self.player_dirty = False
            playing = self.player.isPlayingAudio()
            if not playing and self.music:
                self.music = False
                self.player_key = self.player_pending = None
                self.playing.clear()
            self.music = playing
        if not self.music:
            return
        art = ''
        got = infos('MusicPlayer.Album', *PLAYER_ART)  # GUI-thread read, see focused_art
        for label in PLAYER_ART:
            v = got.get(label, '')
            if artload.usable(v):
                art = v
                break
        key = (got.get('MusicPlayer.Album', ''), art)  # not the artist: compilations change it every track
        if key == self.player_key:
            self.player_pending = None
        elif key == self.player_pending:  # the same new key on two polls: settled (art can lag the track)
            self.player_pending = None
            self.player_key = key
            self.playing.publish(art, self.renderer.render(art) if art else None)
        else:
            self.player_pending = key


def main():
    Service().run()
