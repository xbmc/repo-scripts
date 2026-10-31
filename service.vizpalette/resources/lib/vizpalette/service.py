# Visualizer Palette (service.vizpalette)
# Copyright (C) 2026 Omar Kamel
# SPDX-License-Identifier: GPL-2.0-or-later
"""service.vizpalette - album-art colours for skins and for a Shadertoy visualizer pack.

While music plays, watch for album changes. On each change, take the cover from the player and compute a 4-colour
palette (same algorithm as visualizers/preview/index.html). Then:
- always publish it as Window(Home).Property(VizPalette.Color1..4) (AARRGGBB: 1 dominant, 2 second distinct,
  3 accent = most vivid, 4 shadow = darkest) plus VizPalette.Source (the art URL), for any skin;
- if a Shadertoy pack is installed (presets.json in the "pack folder" setting), write palette.png (4x1) + art.png
  (128x128) next to it and, if the Shadertoy visualisation is on screen, relaunch its preset once, because Shadertoy
  only reads textures when a preset launches.
With no art, or once the music stops, the properties are cleared and the pack gets the alpha-0 defaults.

Idle cost: with nothing playing (or video playing) the loop only checks a flag that Player callbacks set.
"""
import json
import os
import time
from urllib.parse import unquote

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from . import palette as P

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')

SHADERTOY_DATA = 'special://profile/addon_data/visualization.shadertoy/'  # searched when the "packdir" setting is empty
HOME = xbmcgui.Window(10000)
PROPS = ['VizPalette.Color%d' % i for i in range(1, 5)] + ['VizPalette.Source']
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
VIS_WINDOW = 'visualisation'  # 12006
VIS_NAME = 'Shadertoy'
ART_LABELS = ('Player.Art(thumb)', 'Player.Art(album.thumb)', 'MusicPlayer.Cover')
POLL = 1.0
RETRY_DELAYS = (5, 15, 30, 60, 120)  # s after a failed cover load / texture write for the same album; then give up


# Debug lines go to LOGDEBUG. To read them without turning on Kodi's debug log, create an empty file named
# "debug" in addon_data/service.vizpalette/; it is checked once at start, and the lines are then logged at INFO.
VERBOSE = os.path.isfile(os.path.join(PROFILE, 'debug'))


def log(msg, level=xbmc.LOGDEBUG):
    if VERBOSE and level == xbmc.LOGDEBUG:
        level = xbmc.LOGINFO
    xbmc.log('[%s] %s' % (ADDON_ID, msg), level)


def info(label):
    return xbmc.getInfoLabel(label)


def cond(expr):
    return xbmc.getCondVisibility(expr)


# --------------------------------------------------------------------------------------------- reading the cover
def _read(path):
    """Bytes of a VFS path, or b''. xbmcvfs.File understands image://, special://, smb://, http(s)://, local paths."""
    try:
        f = xbmcvfs.File(path, 'rb')
        try:
            return bytes(f.readBytes())
        finally:
            f.close()
    except Exception as e:  # noqa: BLE001
        log('read failed %s: %s' % (path, e))
        return b''


def load_cover(url):
    """Resolve and read a player art URL the way TMDb Helper does (lib/monitor/images.py _openimage):
    1) Kodi's texture cache (Thumbnails/<h>/<hash>.jpg|png, hash of the unwrapped and of the wrapped URL);
    2) the URL itself through the VFS (image:// is served by Kodi's image loader, which caches it);
    3) a VFS copy to our profile folder (TMDb's fallback for sources a direct open can't stream)."""
    inner = unquote(url[len('image://'):]) if url.startswith('image://') else url
    if inner.endswith('/'):
        inner = inner[:-1]
    for key in (inner, url):
        name = xbmc.getCacheThumbName(key)  # 'xxxxxxxx.tbn'
        for cached in ('special://profile/Thumbnails/%s/%s.jpg' % (name[0], name[:-4]),
                       'special://profile/Thumbnails/%s/%s.png' % (name[0], name[:-4])):
            if xbmcvfs.exists(cached):
                data = _read(cached)
                if data:
                    log('cover from cache %s' % cached)
                    return data
    for path in (url, inner) if inner != url else (url,):
        data = _read(path)
        if data:
            log('cover from %s' % path)
            return data
    tmp = os.path.join(PROFILE, 'cover.tmp')
    try:
        xbmcvfs.mkdirs(PROFILE)
        if xbmcvfs.copy(url, tmp):
            with open(tmp, 'rb') as f:
                return f.read()
    except Exception as e:  # noqa: BLE001
        log('copy failed %s: %s' % (url, e))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return b''


# --------------------------------------------------------------------------------------------- writing the textures
def pack_dir():
    try:
        d = xbmcaddon.Addon().getSettingString('packdir')
    except Exception:  # noqa: BLE001
        d = ''
    if d:
        return xbmcvfs.translatePath(d)
    # Empty setting: use the first folder under Shadertoy's add-on data that holds a presets.json
    base = xbmcvfs.translatePath(SHADERTOY_DATA)
    try:
        for name in sorted(os.listdir(base)):
            if os.path.isfile(os.path.join(base, name, 'presets.json')):
                return os.path.join(base, name, '')
    except OSError:
        pass
    return base


def publish(pal, source):
    """Window(Home).Property(VizPalette.Color1..4) as AARRGGBB, VizPalette.Source = the art URL. None clears them."""
    if pal is None:
        for name in PROPS:
            HOME.clearProperty(name)
        return
    for i, c in enumerate(pal, 1):
        HOME.setProperty('VizPalette.Color%d' % i, 'FF%02X%02X%02X' % (c[0], c[1], c[2]))
    HOME.setProperty('VizPalette.Source', source)


class Pack(object):
    def __init__(self):
        self.dir = pack_dir()
        self._names, self._mtime = [], None

    def exists(self):
        return os.path.isfile(os.path.join(self.dir, 'presets.json'))

    def write(self, name, data):
        """Atomic: temp file in the same folder, then rename over the old one. Shadertoy refuses the whole preset
        list if a texture is missing, so the target file is never deleted. Skips identical content."""
        dst = os.path.join(self.dir, name)
        try:
            with open(dst, 'rb') as f:
                if f.read() == data:
                    return False
        except OSError:
            pass
        tmp = os.path.join(self.dir, '.%s.tmp' % name)
        with open(tmp, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, dst)
        return True

    def preset_names(self):
        """Preset names in presets.json order (re-read only when the file changes)."""
        path = os.path.join(self.dir, 'presets.json')
        try:
            m = os.path.getmtime(path)
            if m != self._mtime:
                with open(path, 'r', encoding='utf-8') as f:
                    self._names = [p[0] for p in json.load(f)['presets']]
                self._mtime = m
        except Exception as e:  # noqa: BLE001
            log('presets.json unreadable: %s' % e, xbmc.LOGERROR)
            self._names, self._mtime = [], None
        return self._names


# --------------------------------------------------------------------------------------------- the service
class Player(xbmc.Player):
    def __init__(self, svc):
        super(Player, self).__init__()
        self.svc = svc

    def onAVStarted(self):
        self.svc.dirty = True

    def onPlayBackStarted(self):
        self.svc.dirty = True

    def onPlayBackStopped(self):
        self.svc.dirty = True

    def onPlayBackEnded(self):
        self.svc.dirty = True

    def onPlayBackError(self):
        self.svc.dirty = True


class Service(xbmc.Monitor):
    def __init__(self):
        super(Service, self).__init__()
        self.pack = Pack()
        self.player = Player(self)
        self.dirty = True       # set by player callbacks: re-check whether music is playing
        self.music = False      # audio playback in progress (loop polls every POLL s)
        self.key = None         # (album, art url) of the colours currently written
        self.pending = None     # a new key seen once, applied when the next poll confirms it
        self.pil = None
        self.pil_missing_logged = False
        self.retry_at = None    # time.time() when a failed apply() of self.key is tried again (None = nothing to retry)
        self.retries = 0        # failed attempts for self.key so far

    def onSettingsChanged(self):
        pack = Pack()
        if pack.dir == self.pack.dir:
            return
        self.pack = pack
        log('pack folder %s' % self.pack.dir)
        # the new folder needs textures too: re-apply what plays now (or write the defaults when idle) on the next pass
        self.key = self.pending = self.retry_at = None
        self.retries = 0
        self.dirty = True

    # PIL is optional (script.module.pil, optional="true" in addon.xml)
    def _pil(self):
        if self.pil is None:
            try:
                from PIL import Image, ImageOps
                self.pil = (Image, ImageOps)
            except Exception as e:  # noqa: BLE001
                self.pil = False
                if not self.pil_missing_logged:
                    self.pil_missing_logged = True
                    log('PIL (script.module.pil) not available, album colours off: %s' % e, xbmc.LOGWARNING)
        return self.pil

    def run(self):
        log('started')
        publish(None, '')  # nothing is playing yet: no stale colours from an earlier run of the service
        while not self.abortRequested():
            if self.dirty:
                self.dirty = False
                playing = self.player.isPlayingAudio()  # False for video and when stopped
                if not playing and self.music:
                    self.music = False
                    self.apply(None, None)
                elif playing:
                    self.music = True
                if not playing and self.key is None:  # first idle pass (stale colours from the last session) or
                    self.key = ('',)                  # a new pack folder: the default textures
                    try:
                        self.write_defaults()
                    except Exception as e:  # noqa: BLE001 - a read-only pack folder must not stop the skin colours
                        log('writing default textures failed: %s' % e, xbmc.LOGERROR)
            if self.music:
                self.tick()
            if self.waitForAbort(POLL):
                break
        publish(None, '')
        log('stopped')

    def tick(self):
        if not self.player.isPlayingAudio():
            self.dirty = True
            return
        art = ''
        for label in ART_LABELS:
            v = info(label)
            if v and not v.startswith('Default'):  # skin fallbacks like DefaultAlbumCover.png are not covers
                art = v
                break
        key = (info('MusicPlayer.Album'), art)  # not the artist: compilations change it every track
        if key == self.key:
            self.pending = None
            if self.retry_at is not None and time.time() >= self.retry_at:
                self.retry_at = None
                log('retrying %s (attempt %d)' % (key, self.retries + 1))
                self.apply(key, art, retry=True)
        elif key == self.pending:  # same new key on two polls in a row: settled (art can lag the track by a moment)
            self.pending = None
            self.apply(key, art)
        else:
            self.pending = key

    def apply(self, key, art, retry=False):
        """Publish the palette for `key` (None = music stopped); if the pack is installed, write its textures and
        relaunch Shadertoy once if it is on screen. Returns False when the cover could not be read / decoded or the
        textures could not be written; then the same album is tried again after RETRY_DELAYS (tick())."""
        if key is None and self.key in (None, ('',)):
            return True
        if not retry:  # a new album (or music stopped): a fresh retry budget
            self.retries, self.retry_at = 0, None
        self.key = key if key is not None else ('',)
        has_pack = self.pack.exists()
        pal = pal_png = art_png = None
        ok = True
        if art:
            pil = self._pil()  # no PIL is permanent (logged once), not a failure to retry
            data = load_cover(art) if pil else b''
            if data:
                try:
                    pal, pal_png, art_png = P.cover_pngs(data, *pil, with_art=has_pack)
                except Exception as e:  # noqa: BLE001
                    log('cover decode failed for %s: %s' % (art, e), xbmc.LOGERROR)
                    ok = False
            elif pil:
                log('no cover bytes for %s' % art)
                ok = False
        publish(pal, art)
        if not has_pack:
            log('palette %s for %s (no pack at %s)' % (pal, key, self.pack.dir))
            return self._done(ok, key)
        changed = False
        try:
            if pal is not None:
                changed = self.pack.write('palette.png', pal_png)
                changed = self.pack.write('art.png', art_png) or changed
                log('palette %s for %s' % (pal, key))
            else:
                changed = self.write_defaults()
                log('defaults for %s' % (key,))
        except Exception as e:  # noqa: BLE001
            log('writing textures failed: %s' % e, xbmc.LOGERROR)
            return self._done(False, key)
        if changed:
            self.reload_shadertoy()
        return self._done(ok, key)

    def _done(self, ok, key):
        """Schedule the next attempt for a failed album (never for 'music stopped'), RETRY_DELAYS apart."""
        if ok or key is None:
            self.retry_at = None
        elif self.retries < len(RETRY_DELAYS):
            self.retry_at = time.time() + RETRY_DELAYS[self.retries]
            self.retries += 1
        else:
            self.retry_at = None
            log('giving up on %s after %d attempts' % (key, self.retries + 1), xbmc.LOGWARNING)
        return ok

    def write_defaults(self):
        if not self.pack.exists():
            return False
        a = self.pack.write('palette.png', P.default_palette_png())
        b = self.pack.write('art.png', P.default_art_png())
        return a or b

    def reload_shadertoy(self):
        """Shadertoy only loads channel textures in Launch(). Next+previous relaunch the same preset. Its PrevPreset is
        (i - 1) % n in C++, which gives -1 (the 'own shader' slot) from index 0, so step forward first, except from
        the last preset, where next would wrap to 0 and previous would then go to -1: step back first there."""
        if not (cond('Window.IsActive(%s)' % VIS_WINDOW) and info('Visualisation.Name') == VIS_NAME):
            return
        if cond('Visualisation.Locked'):
            log('preset locked, skip reload')
            return
        names = self.pack.preset_names()
        cur = info('Visualisation.Preset')
        n = len(names)
        if n < 2 or cur not in names:
            log('reload skipped (preset %r not in pack)' % cur)
            return
        order = ('previouspreset', 'nextpreset') if names.index(cur) == n - 1 else ('nextpreset', 'previouspreset')
        for action in order:
            xbmc.executebuiltin('Action(%s,%s)' % (action, VIS_WINDOW))
        log('reloaded Shadertoy preset %r via %s' % (cur, '+'.join(order)))


def main():
    Service().run()
