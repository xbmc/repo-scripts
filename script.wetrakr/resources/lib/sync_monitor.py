"""
sync_monitor.py — xbmc.Monitor that feeds the library sync with what happens
in Kodi, and sends manual marks to WeTrakr live.

  VideoLibrary.OnUpdate      the user marked something watched / unwatched
                             (data carries `playcount` ONLY when it changed),
                             or changed a rating / reset a resume point (no
                             playcount in data). Traps:
                               - our own JSON-RPC writes raise it too, and the
                                 sender is always "xbmc": the engine registers
                                 what it is about to write (`expect`) and the
                                 matching echo is dropped;
                               - Kodi raises it when playback ends, before
                                 Player.OnStop: the item being played, or just
                                 stopped, is ignored (the scrobble already
                                 reported that play);
                               - during a library scan it comes in bursts with
                                 `transaction`/`added`: ignored, the scan end
                                 triggers a pass.
  VideoLibrary.OnScanFinished / OnCleanFinished   library changed: rebuild the
                             index; after a scan that added items, re-read the
                             WeTrakr snapshot so the new items get their state.
  System.OnWake              check for changes soon.
  Other.wetrakr_sync_now     "Sync now" from the add-on settings (script.py).
"""

import json
import threading
import time

import xbmc

from resources.lib import library as lib
from resources.lib import sync_state as store
from resources.lib import utils
from resources.lib.api import WeTrakrAPI
from resources.lib.player import _dispatch_async

ECHO_WINDOW_S = 30
STOPPED_WINDOW_S = 120
LIVE_WINDOW_S = 24 * 3600


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log("[WeTrakr] Monitor: {}".format(msg), level)


class SyncMonitor(xbmc.Monitor):

    def __init__(self, player=None):
        xbmc.Monitor.__init__(self)
        self.player = player
        self._lock = threading.Lock()
        self._expected = {}       # (kind, dbid) -> (playcount, userrating, until)
        self._live = {}           # (kind, dbid) -> unix ts of a play we sent live
        self._dirty_ids = set()   # (kind, dbid) touched without playcount (rating, resume)
        self.library_changed_at = time.time()
        self.scan_added = False
        self.dirty_at = None          # something changed locally: Local pass due
        self.check_requested = False  # a Check pass as soon as possible
        self.full_requested = False   # "Sync now"
        self.resnapshot_requested = False
        self.reset_requested = False

    # ─── Used by the engine / player ───────────────────────────────

    def expect(self, kind, dbid, playcount, userrating):
        with self._lock:
            self._expected[(kind, dbid)] = (playcount, userrating, time.time() + ECHO_WINDOW_S)

    def note_live_play(self, kind, dbid):
        """The scrobbler (or a live mark) already sent this play."""
        if kind and dbid:
            with self._lock:
                self._live[(kind, dbid)] = time.time()

    def live_played_since(self, kind, dbid, since_ts):
        with self._lock:
            ts = self._live.get((kind, dbid))
        return bool(ts and ts >= since_ts and ts >= time.time() - LIVE_WINDOW_S)

    def take_dirty_ids(self):
        with self._lock:
            ids, self._dirty_ids = self._dirty_ids, set()
        return ids

    def mark_dirty(self):
        if self.dirty_at is None:
            self.dirty_at = time.time()

    # ─── Kodi callbacks ─────────────────────────────────────────────

    def onScanFinished(self, library):
        if library == "video":
            self.library_changed_at = time.time()
            if self.scan_added:
                self.scan_added = False
                self.resnapshot_requested = True
            self.mark_dirty()

    def onCleanFinished(self, library):
        if library == "video":
            self.library_changed_at = time.time()

    def onNotification(self, sender, method, data):
        try:
            if method == "VideoLibrary.OnUpdate" and sender == "xbmc":
                self._on_update(self._parse(data))
            elif method == "System.OnWake":
                self.check_requested = True
            elif method == "Other.wetrakr_sync_now":
                self.full_requested = "local"
            elif method == "Other.wetrakr_sync_reset":
                self.reset_requested = True
        except Exception as e:
            _log("onNotification error: {}".format(e), xbmc.LOGWARNING)

    @staticmethod
    def _parse(data):
        try:
            return json.loads(data) if data else {}
        except ValueError:
            return {}

    def _on_update(self, data):
        if data.get("transaction") or data.get("added"):
            if data.get("added"):
                self.scan_added = True
            return
        item = data.get("item") if isinstance(data.get("item"), dict) else data
        kind = item.get("type")
        dbid = item.get("id")
        if kind not in ("movie", "episode") or not dbid:
            return

        # Our own write coming back.
        with self._lock:
            exp = self._expected.pop((kind, dbid), None)
        if exp:
            playcount, userrating, until = exp
            if time.time() <= until and ("playcount" not in data or data.get("playcount") == playcount or playcount is None):
                return

        # The item being played, or just stopped: the scrobble handles it.
        p = self.player
        if p is not None:
            if getattr(p, "current_kind", None) == kind and getattr(p, "current_dbid", None) == dbid:
                return
            stopped = getattr(p, "last_stopped", None)
            if stopped and stopped[0] == kind and stopped[1] == dbid and time.time() - stopped[2] <= STOPPED_WINDOW_S:
                return

        if "playcount" in data:
            _dispatch_async(self._live_mark, kind, dbid, int(data.get("playcount") or 0))
        else:
            with self._lock:
                self._dirty_ids.add((kind, dbid))
            self.mark_dirty()

    # ─── Live marks ─────────────────────────────────────────────────

    def _live_mark(self, kind, dbid, playcount):
        """Send a manual watched / unwatched mark to the webhook and remember
        it in the local state so the next scan does not upload it again."""
        import xbmcaddon
        addon = xbmcaddon.Addon("script.wetrakr")
        if addon.getSetting("sync_enabled") == "false" or addon.getSetting("sync_upload") == "false":
            return
        token = addon.getSetting("api_token")
        if not token:
            return
        item = lib.get_movie(dbid) if kind == "movie" else lib.get_episode(dbid)
        if not item:
            return
        if lib.is_excluded(item, addon.getSetting("sync_exclude_plugin") != "false"):
            return
        show = lib.get_show(item.get("tvshowid")) if kind == "episode" else None
        event = "watched" if playcount > 0 else "unwatched"
        payload = utils.build_payload(event, item, show, progress=100.0 if playcount > 0 else 0.0)
        ok = WeTrakrAPI(addon.getSetting("api_url") or "https://api.wetrakr.com", token).send_event(payload, debug=addon.getSetting("debug") == "true")
        _log("{} {} #{} -> {}".format(event, kind, dbid, "sent" if ok else "FAILED"))
        if ok and kind == "episode":
            from resources.lib import widgets
            widgets.invalidate()

        state = store.load()
        pos, total = (item.get("resume") or {}).get("position") or 0, 0
        fields = {
            "pc": int(item.get("playcount") or 0),
            "lp": lib.kodi_date_to_iso(item.get("lastplayed")),
            "ur": int(item.get("userrating") or 0),
            "pos": int(pos),
            "unw": playcount == 0,
            "fp": store.fingerprint(item),
        }
        store.set_item(state, kind, dbid, fields)
        store.save(state)
        if playcount > 0:
            self.note_live_play(kind, dbid)
