"""Glue between the Sendspin client and Kodi's player / GUI."""

import logging
import os
import queue
import socket
import threading
import time
import urllib.parse
import uuid

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from sendspin import __version__
from sendspin.audio import AudioPipeline, WavStreamServer
from sendspin.client import Listener, SendspinClient
from sendspin.clock import ClockSync, now_us
from sendspin.discovery import discover

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ICON = ADDON.getAddonInfo("icon")
log = logging.getLogger("sendspin.kodi")


class KodiLogHandler(logging.Handler):
    """Route Python logging into kodi.log."""

    def __init__(self, debug):
        super().__init__()
        self.debug = debug

    def emit(self, record):
        if record.levelno >= logging.ERROR:
            level = xbmc.LOGERROR
        elif self.debug:
            level = xbmc.LOGINFO  # opt-in via the add-on's debug setting, no global debug mode needed
        else:
            level = xbmc.LOGDEBUG
        xbmc.log("[%s] %s: %s" % (ADDON_ID, record.name, self.format(record)), level)


def setup_logging(debug):
    root = logging.getLogger("sendspin")
    root.handlers[:] = [KodiLogHandler(debug)]
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    root.propagate = False


def _setting_str(key):
    try:
        return ADDON.getSettingString(key).strip()
    except Exception:  # noqa: BLE001 - very old Kodi
        return (ADDON.getSetting(key) or "").strip()


def _setting_bool(key, default):
    try:
        return ADDON.getSettingBool(key)
    except Exception:  # noqa: BLE001
        return default


def _setting_int(key, default):
    try:
        return ADDON.getSettingInt(key)
    except Exception:  # noqa: BLE001
        return default


def client_id():
    """Stable per-installation id, stored in the add-on profile folder."""
    profile = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
    os.makedirs(profile, exist_ok=True)
    path = os.path.join(profile, "client_id")
    try:
        with open(path) as f:
            cid = f.read().strip()
            if cid:
                return cid
    except OSError:
        pass
    cid = "kodi-" + uuid.uuid4().hex[:12]
    with open(path, "w") as f:
        f.write(cid)
    return cid


def device_name():
    name = _setting_str("player_name")
    if name:
        return name
    friendly = xbmc.getInfoLabel("System.FriendlyName")
    if friendly and "System.FriendlyName" not in friendly:
        return friendly
    return "Kodi (%s)" % socket.gethostname()


def L(string_id):
    return ADDON.getLocalizedString(string_id)


def notify(message, ms=4000):
    if _setting_bool("notifications", True):
        # sound=False: never make a noise, even for toasts
        xbmcgui.Dialog().notification(ADDON.getAddonInfo("name"), message, ICON, ms, False)


class SendspinPlayer(xbmc.Player):
    """Kodi player that knows which item is ours and reports user actions."""

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge

    def onPlayBackPaused(self):  # noqa: N802
        if self.bridge.is_our_item():
            self.bridge.user_action("pause")

    def onPlayBackResumed(self):  # noqa: N802
        if self.bridge.is_our_item():
            self.bridge.user_action("play")

    def onPlayBackStopped(self):  # noqa: N802
        self.bridge.on_kodi_stopped()

    def onPlayBackEnded(self):  # noqa: N802
        self.bridge.on_kodi_ended()

    def onPlayBackError(self):  # noqa: N802
        self.bridge.on_kodi_ended()


class Bridge(Listener):
    """Owns pipeline + HTTP server + Sendspin client and drives Kodi."""

    SKIP_DEDUP_S = 2.0  # Kodi's probe + open of one sentinel arrive well within this

    def __init__(self):
        self.clock = ClockSync()
        self.pipeline = AudioPipeline(
            self.clock,
            lead_ms=_setting_int("lead_ms", 3000),
            static_delay_ms=_setting_int("static_delay_ms", 0),
        )
        timeline = None
        if os.environ.get("SENDSPIN_TIMELINE"):  # sync measurement (dev only), into special://temp
            timeline = os.path.join(xbmcvfs.translatePath("special://temp"), "sendspin_timeline")
        self.http = WavStreamServer(self.pipeline, timeline_dir=timeline)
        self.player = SendspinPlayer(self)
        self.client = None
        self.url_prefix = None
        self._current_url = None
        self._expect_stop = False
        self._lock = threading.Lock()
        self.metadata = {}
        self._restarts = []
        self._output_running = False
        self._last_skip_path = None
        self._last_skip_at = 0.0
        self._last_play_call = 0.0
        self._sync_gen, self._sync_since, self._sync_samples, self._sync_last = None, 0.0, [], 0.0
        self._queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._worker, name="sendspin-kodi", daemon=True)

    # -- lifecycle ---------------------------------------------------------
    def start(self, server_url):
        self._worker_thread.start()
        self.http.set_control_callback(self.on_remote_skip)
        self.http.start()
        self.url_prefix = "http://127.0.0.1:%d/stream/" % self.http.port
        self.client = SendspinClient(
            server_url, client_id(), device_name(), self.pipeline, self,
            version=__version__, product="Kodi %s" % xbmc.getInfoLabel("System.BuildVersion").split(" ")[0],
        )
        log.info("starting: name=%r id=%s url=%s http=%s", self.client.name, self.client.client_id,
                 server_url, self.url_prefix)
        self.client.start()

    def stop(self):
        if self.client:
            self.client.stop()
        self._stop_kodi_player()
        self._queue.put(None)
        self.http.stop()

    # -- helpers -----------------------------------------------------------
    def is_our_item(self):
        try:
            return self.player.isPlaying() and self.player.getPlayingFile().startswith(self.url_prefix or "\x00")
        except RuntimeError:
            return False

    def other_media_playing(self):
        try:
            return self.player.isPlaying() and not self.is_our_item()
        except RuntimeError:
            return False

    def _listitem(self, url):
        md = self.metadata
        title = md.get("title") or L(30203)
        li = xbmcgui.ListItem(label=title, path=url, offscreen=True)
        li.setMimeType("audio/wav")
        li.setContentLookup(False)
        tag = li.getMusicInfoTag()
        tag.setTitle(title)
        if md.get("artist"):
            tag.setArtist(md["artist"])
        if md.get("album"):
            tag.setAlbum(md["album"])
        if md.get("album_artist"):
            tag.setAlbumArtist(md["album_artist"])
        if md.get("year"):
            tag.setYear(int(md["year"]))
        if md.get("track"):
            tag.setTrack(int(md["track"]))
        progress = md.get("progress") or {}
        if progress.get("track_duration"):
            tag.setDuration(int(progress["track_duration"] // 1000))
        art = md.get("artwork_url")
        if art:
            li.setArt({"thumb": art, "icon": art, "fanart": art, "album.thumb": art})
        tag.setComment(L(30204) % (self.client.server_name if self.client else L(30203)))
        return li

    @staticmethod
    def _sentinel(action, url):
        label = L(30205) if action == "next" else L(30206)
        li = xbmcgui.ListItem(label=label, path=url, offscreen=True)
        li.setMimeType("audio/wav")
        li.setContentLookup(False)
        li.getMusicInfoTag().setTitle(label)
        return li

    def on_remote_skip(self, action, path=None):
        """HTTP thread: Kodi opened a sentinel -> skip in MA; MA then restarts our stream."""
        with self._lock:
            # Kodi opens a playlist item twice (probe + open) within a moment: one press = one skip
            now = time.monotonic()
            if path is not None and path == self._last_skip_path and now - self._last_skip_at < self.SKIP_DEDUP_S:
                return
            self._last_skip_path, self._last_skip_at = path, now
        log.info("Kodi %s button -> Music Assistant", action)
        with self._lock:
            self._expect_stop = True
            self._last_play_call = time.monotonic()  # Kodi will stop/err on the sentinel: not a user stop
        if self.client:
            self.client.send_controller(action)

    def _play_generation(self, generation):
        if _setting_bool("yield_to_video", True) and self.other_media_playing():
            log.info("Kodi is busy with other media - not taking over playback")
            return
        url = self.http.url(generation)
        # Kodi's play()/stop() block while PAPlayer closes the previous stream; closing it
        # needs our Python HTTP thread, so never call them while a reader is still open.
        if not self.http.broadcaster.wait_readers_closed(3.0):
            log.warning("previous stream still has readers - starting anyway")
        if self.pipeline.generation != generation or not self.pipeline.active:
            log.info("generation %d is stale - not starting Kodi", generation)
            return
        if _setting_bool("yield_to_video", True) and self.other_media_playing():
            log.info("other media started while waiting - not taking over playback")
            return
        with self._lock:
            self._current_url = url
            self._expect_stop = True  # play() stops the previous item first
            self._last_play_call = time.monotonic()
        log.info("Kodi play %s", url)
        if _setting_bool("remote_skip", True):
            # [previous-sentinel, live stream, next-sentinel]: Kodi's Next/Previous buttons
            # move to a sentinel, whose URL tells us to skip in Music Assistant.
            playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
            playlist.clear()
            for action, item_url in (("previous", self.http.control_url("previous", generation)),
                                     (None, url),
                                     ("next", self.http.control_url("next", generation))):
                li = self._listitem(url) if action is None else self._sentinel(action, item_url)
                playlist.add(item_url, li)
            self.player.play(playlist, startpos=1)
        else:
            self.player.play(url, self._listitem(url))
        self._output_running = True

    def _stop_kodi_player(self):
        try:
            playing = self.player.isPlaying()
            current = self.player.getPlayingFile() if playing else ""
        except RuntimeError:
            playing, current = False, ""
        ours = current.startswith(self.url_prefix or "\x00")
        # Kodi reports an empty file while its HTTP reader is reconnecting - still ours.
        if playing and (ours or (current == "" and self._current_url)):
            log.info("stopping Kodi playback (%s)", current or "reconnecting")
            with self._lock:
                self._expect_stop = True
            self.player.stop()

    # -- Sendspin events (client thread) ------------------------------------
    # Never call Kodi from the client thread: Player.play() blocks while Kodi opens
    # our HTTP stream, which would stall the WebSocket reader and make the server
    # drop the connection. Events are queued to the Kodi worker thread instead.
    def output_running(self):
        return self._output_running

    def on_connected(self, server_name):
        self._post(notify, L(30200) % server_name)

    def on_disconnected(self):
        self._post(self._stop_kodi_player)

    def on_stream_start(self, fmt, generation, continuous=False):
        if continuous:
            log.info("continuing Kodi playback across stream start (generation %d)", generation)
            self._post(self._refresh_infotag)
        else:
            self._post(self._play_generation, generation)

    def on_stream_clear(self, generation):
        pass  # same Kodi stream continues; queued audio was dropped by the pipeline

    def on_stream_end(self):
        # The HTTP stream is closed by the pump, so Kodi reaches end-of-stream and stops on
        # its own. Only fall back to Player.stop() once all readers are gone (no deadlock).
        def _end():
            with self._lock:
                self._current_url = None
                self._expect_stop = True
            if self.http.broadcaster.wait_readers_closed(5.0):
                time.sleep(0.5)
            if self.pipeline.active:
                return  # a new stream already started
            self._stop_kodi_player()
        self._post(_end)

    def on_metadata(self, metadata):
        self.metadata = metadata
        self._post(self._refresh_infotag)

    def on_volume(self, volume, muted):
        log.info("volume=%s muted=%s", volume, muted)

    # -- Kodi worker -------------------------------------------------------------
    def _post(self, fn, *args):
        self._queue.put((fn, args))

    def _worker(self):
        while True:
            item = self._queue.get()
            if item is None:
                return
            fn, args = item
            try:
                fn(*args)
            except Exception:  # noqa: BLE001
                log.exception("Kodi worker error in %s", getattr(fn, "__name__", fn))

    def _refresh_infotag(self):
        if self.is_our_item():
            try:
                self.player.updateInfoTag(self._listitem(self.player.getPlayingFile()))
            except (RuntimeError, AttributeError) as exc:  # updateInfoTag needs Kodi 20+
                log.debug("updateInfoTag failed: %s", exc)

    # -- Kodi events ----------------------------------------------------------
    def user_action(self, command):
        if self.client:
            self.client.send_controller(command)

    def _stop_is_ours(self):
        log.debug("stop check: expect_stop=%s since_play=%.1fs", self._expect_stop,
                  time.monotonic() - self._last_play_call)
        with self._lock:
            expected = self._expect_stop or (time.monotonic() - self._last_play_call) < 4.0
            self._expect_stop = False
        return expected

    def on_kodi_stopped(self):
        expected = self._stop_is_ours()
        was_running = self._output_running
        self._output_running = False
        with self._lock:
            ours = self._current_url is not None
        log.debug("Kodi stopped: expected=%s was_running=%s ours=%s active=%s", expected, was_running,
                  ours, self.pipeline.active)
        if ours and was_running and not expected and self.pipeline.active:
            log.info("user stopped playback in Kodi - asking Music Assistant to stop")
            self.user_action("stop")
            with self._lock:
                self._current_url = None

    def on_kodi_ended(self):
        """Kodi hit end-of-stream / an error on our live stream: restart, don't stop MA."""
        self._stop_is_ours()
        self._output_running = False
        with self._lock:
            ours = self._current_url is not None
        if not (ours and self.pipeline.active):
            return
        now = time.monotonic()
        self._restarts = [t for t in self._restarts if now - t < 60] + [now]
        if len(self._restarts) > 5:
            log.error("Kodi keeps ending the stream - giving up until the next stream")
            return
        log.warning("Kodi ended our live stream unexpectedly - restarting playback")
        threading.Timer(0.5, self._post, args=(self._play_generation, self.pipeline.generation)).start()

    def output_error_ms(self):
        """How late (ms, +) Kodi's output is vs the Sendspin timeline, from Player.getTime()."""
        b = self.http.broadcaster
        if not b.reader_starts or self.pipeline.fmt is None:
            return None
        try:
            pos_s = self.player.getTime()
        except RuntimeError:
            return None
        now = now_us()
        fmt = self.pipeline.fmt
        offset = b.reader_starts[-1] + fmt.bytes_for_us(int(pos_s * 1_000_000))
        intended = b.play_time_of(offset)
        if intended is None:
            return None
        return (now - intended) / 1000.0

    SYNC_SETTLE_S = 3.0  # let Kodi's player settle after (re)starting
    SYNC_THRESHOLD_MS = 35.0  # Player.getTime() jitters by about ±10-15 ms
    SYNC_INTERVAL_S = 5.0

    def _auto_sync(self):
        """Measure Kodi's output vs the Sendspin timeline and nudge it into place."""
        if not _setting_bool("auto_sync", True):
            return
        gen = self.pipeline.generation
        now = time.monotonic()
        if self._sync_gen != gen:
            self._sync_gen, self._sync_since, self._sync_samples, self._sync_last = gen, now, [], 0.0
            return
        if now - self._sync_since < self.SYNC_SETTLE_S:
            return
        err = self.output_error_ms()
        if err is None:
            return
        self._sync_samples = (self._sync_samples + [err])[-5:]
        log.debug("sync: Kodi output is %+.0f ms vs timeline", err)
        if len(self._sync_samples) < 5 or now - self._sync_last < self.SYNC_INTERVAL_S:
            return
        median = sorted(self._sync_samples)[2]
        if abs(median) >= self.SYNC_THRESHOLD_MS:
            self.pipeline.adjust_output(int(median * 1000))
            self._sync_last = now
            self._sync_samples = []
            self._sync_since = now  # wait for Kodi to settle again before re-measuring

    @property
    def connected(self):
        return bool(self.client and self.client.connected)

    def tick(self):
        """Called ~1/s from the service loop."""
        if self.client is None:
            return
        ours = self.is_our_item()
        if ours:
            self._auto_sync()
            with self._lock:
                # our item is up and settled: from now on a stop is the user's
                if time.monotonic() - self._last_play_call > 4.0:
                    self._expect_stop = False
        self._output_running = ours
        busy = _setting_bool("yield_to_video", True) and self.other_media_playing()
        self.client.set_available(not busy)


def normalise_server_url(text):
    """'host', 'host:port', 'host/path' or a full ws:// URL -> ws://host:port/path."""
    text = text.strip()
    if "://" not in text:
        text = "ws://" + text
    parts = urllib.parse.urlsplit(text)
    host = parts.hostname
    if not host:
        return None
    if ":" in host:
        host = "[%s]" % host  # IPv6 literal
    try:
        port = parts.port or 8927
    except ValueError:
        return None
    path = parts.path if parts.path not in ("", "/") else "/sendspin"
    return "ws://%s:%d%s" % (host, port, path)


def resolve_server_url():
    url = _setting_str("server_url")
    if url:
        return normalise_server_url(url)
    try:
        servers = discover()
    except Exception:  # noqa: BLE001 - discovery must never stop the service
        log.exception("discovery failed")
        servers = []
    if servers:
        log.info("discovered %s", servers)
        return servers[0]["url"]
    return None
