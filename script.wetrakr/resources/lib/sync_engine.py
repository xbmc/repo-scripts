"""
sync_engine.py — one pass of the library sync between Kodi and WeTrakr.

  1. Upload (Kodi -> WeTrakr). The first time, everything played, in progress
     or rated; afterwards only what changed since the last pass, compared with
     the local state (sync_state.py). It never sends "not watched": that only
     happens live, from VideoLibrary.OnUpdate (sync_monitor.py).
  2. Download (WeTrakr -> Kodi). The first time the full snapshot; afterwards
     the changes since the cursor. Rows are STATES, so applying one twice is
     harmless. Before each write the monitor is told what to expect, so our own
     OnUpdate echo is not mistaken for a change made by the user.
  3. Resume points and the "WeTrakr Watchlist" tag (Planning).

Upload goes before download: otherwise a change made in Kodi since the last
pass would be overwritten by WeTrakr's older state.

Three modes, to spend as few requests as possible (see scheduler.py):
  Check  one call to /changes; if WeTrakr says `unchanged` it ends there. The
         library is not even read. This is what the heartbeat runs.
  Local  something changed in Kodi (the monitor or the player said so): upload
         the diff. Zero requests if the diff is empty.
  Full   everything, no shortcuts: first sync, "Sync now", the daily pass. The
         daily pass also re-reads the snapshot, so items added to the library
         since the last one get their WeTrakr state.

Same design as the official Emby plugin (SyncEngine.cs); the semantics of
"who wins" are identical so both behave the same for a user.
"""

import os
import random
import re
import threading
import time
from xml.sax.saxutils import escape as xml_escape

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib import library as lib
from resources.lib import sync_state as store
from resources.lib import utils
from resources.lib import widgets
from resources.lib.sync_api import SyncApi, InvalidToken, ApiError

MODE_CHECK = "check"
MODE_LOCAL = "local"
MODE_FULL = "full"

WATCHLIST_TAG = "WeTrakr Watchlist"
LIST_TAG_PREFIX = "WeTrakr: "
PLAYLISTS_DIR = "special://profile/playlists/video/"
XSP_PREFIX = "WeTrakr - "
SNAPSHOT_SECTIONS = ("tracks", "ratings")
REPLAY_GAP_S = 60          # a later lastplayed past this gap is a new play
RESUME_MIN_DIFF_S = 30
SCAN_MARGIN_S = 300        # incremental scans look a bit further back
MAX_CHANGES_PAGES = 100

_run_lock = threading.Lock()


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log("[WeTrakr] Sync: {}".format(msg), level)


def _settings():
    addon = xbmcaddon.Addon("script.wetrakr")
    g = addon.getSetting
    return {
        "api_url": g("api_url") or "https://api.wetrakr.com",
        "token": g("api_token") or "",
        "enabled": g("sync_enabled") != "false",
        "upload": g("sync_upload") != "false",
        "download": g("sync_download") != "false",
        "exclude_plugin": g("sync_exclude_plugin") != "false",
        "watchlist_tag": g("sync_watchlist_tag") != "false",
        "debug": g("debug") == "true",
    }


def _int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _resume(item):
    r = item.get("resume") or {}
    return float(r.get("position") or 0), float(r.get("total") or 0)


class Result(object):
    def __init__(self):
        self.uploaded = 0
        self.applied = 0
        self.progress = 0
        self.tagged = 0
        self.unchanged = False
        self.error = None

    @property
    def changed(self):
        return bool(self.uploaded or self.applied or self.progress or self.tagged)

    def __str__(self):
        if self.error:
            return self.error
        if self.unchanged and not self.changed:
            return "unchanged"
        return "uploaded {} / applied {} / resume {} / tagged {}".format(self.uploaded, self.applied, self.progress, self.tagged)


# =====================================================================
# Library index (what the download needs to find a WeTrakr title in Kodi)
# =====================================================================

class LibraryIndex(object):
    """All movies, shows and episodes with their ids, kept in memory between
    passes and rebuilt when the monitor says the library changed. Items are
    updated in place after each write so a second row in the same pass sees
    the new values."""

    def __init__(self):
        self.built_at = 0
        self.movies = {}        # movieid -> item
        self.shows = {}         # tvshowid -> item
        self.episodes = {}      # episodeid -> item
        self._movies_by_id = {}     # "tmdb:1" -> [movieid]
        self._shows_by_id = {}
        self._episodes_by_se = {}   # (tvshowid, season, episode) -> [episodeid]
        self._episodes_by_id = {}   # "imdb:tt1" -> [episodeid]

    def build(self, should_stop=None):
        self.__init__()
        for m in lib.iter_movies(should_stop=should_stop):
            self.movies[m["movieid"]] = m
            self._index(self._movies_by_id, utils.extract_ids(m), m["movieid"])
        for sid, s in lib.get_shows().items():
            self.shows[sid] = s
            self._index(self._shows_by_id, utils.extract_ids(s), sid)
        for e in lib.iter_episodes(should_stop=should_stop):
            self.episodes[e["episodeid"]] = e
            key = (e.get("tvshowid"), e.get("season"), e.get("episode"))
            self._episodes_by_se.setdefault(key, []).append(e["episodeid"])
            self._index(self._episodes_by_id, utils.extract_ids(e), e["episodeid"])
        self.built_at = time.time()
        _log("index: {} movies, {} shows, {} episodes".format(len(self.movies), len(self.shows), len(self.episodes)))

    @staticmethod
    def _index(table, ids, dbid):
        for k in ("tmdb", "imdb", "tvdb"):
            if ids.get(k):
                table.setdefault("{}:{}".format(k, ids[k]), []).append(dbid)

    @staticmethod
    def _lookup(table, ids):
        for k in ("tmdb", "imdb", "tvdb"):
            if ids and ids.get(k):
                found = table.get("{}:{}".format(k, ids[k]))
                if found:
                    return list(found)
        return []

    def find(self, row_type, ids, series_ids=None, season=None, episode=None):
        """[(kind, dbid, item)] of the library items of a WeTrakr title row."""
        out = []
        if row_type == "movie":
            for mid in self._lookup(self._movies_by_id, ids):
                out.append(("movie", mid, self.movies[mid]))
        elif row_type == "show":
            for sid in self._lookup(self._shows_by_id, ids):
                out.append(("tvshow", sid, self.shows[sid]))
        elif row_type == "episode":
            seen = set()
            if season is not None and episode is not None:
                for sid in self._lookup(self._shows_by_id, series_ids):
                    for eid in self._episodes_by_se.get((sid, season, episode), []):
                        seen.add(eid)
            for eid in self._lookup(self._episodes_by_id, ids):
                seen.add(eid)
            for eid in seen:
                out.append(("episode", eid, self.episodes[eid]))
        return out


# =====================================================================
# Engine
# =====================================================================

class SyncEngine(object):

    def __init__(self, monitor, player=None):
        self.monitor = monitor      # sync_monitor.SyncMonitor (expectations, live plays, dirty ids)
        self.player = player        # WeTrakrPlayer (what is playing now)
        self.index = LibraryIndex()
        self.running = False

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run(self, mode, resnapshot=False, dialog=None):
        """One pass. Returns a Result; never raises."""
        res = Result()
        if not _run_lock.acquire(False):
            res.error = "already running"
            return res
        self.running = True
        try:
            self._run(mode, resnapshot, dialog, res)
        except InvalidToken:
            res.error = "WeTrakr rejected the token"
            _log(res.error + ": re-login required", xbmc.LOGWARNING)
            try:
                xbmcaddon.Addon("script.wetrakr").setSetting("auth_invalid", "true")
            except Exception:
                pass
        except ApiError as e:
            res.error = str(e)
            _log("API error: {}".format(e), xbmc.LOGWARNING)
        except Exception as e:
            res.error = "sync failed: {}".format(e)
            _log(res.error, xbmc.LOGERROR)
        finally:
            self.running = False
            _run_lock.release()
        return res

    def _run(self, mode, resnapshot, dialog, res):
        cfg = _settings()
        if not cfg["enabled"] or not cfg["token"]:
            res.error = "sync disabled"
            return
        state = store.load()
        api = SyncApi(cfg["api_url"], cfg["token"])
        self._cfg = cfg
        self._seen_lists_rev = None
        self._stop = lambda: xbmc.Monitor().abortRequested()

        if state.get("settings") is None:
            status = api.status()
            self._remember_settings(state, status.get("settings"), status.get("max_batch"))
            self._note_sync_request(state, status)
            self._note_lists_rev(status)

        if dialog:
            dialog.update(5, message="Reading the Kodi library")

        if cfg["upload"] and (mode != MODE_CHECK or not state["initial_done"]):
            res.uploaded = self._upload(api, state, mode, dialog)
            store.save(state)

        if mode != MODE_LOCAL and cfg["download"]:
            if resnapshot:
                state["snapshot_done"] = False
            pull = self._pull(api, state, full=(mode == MODE_FULL), dialog=dialog)
            res.unchanged = pull["unchanged"]
            res.applied = pull["applied"]
            if not pull["unchanged"]:
                res.progress = self._apply_progress(state, pull["in_progress"])
            if pull["planning_changed"] or mode == MODE_FULL:
                res.tagged = self._sync_watchlist_tag(state)
            rev = self._seen_lists_rev
            if rev is not None and (rev != state.get("lists_rev") or mode == MODE_FULL):
                res.tagged += self._sync_lists(api, state, rev)
            # The playlists depend on which items carry each tag: only when
            # the library index is loaded (an `unchanged` check skips it).
            if self.index.built_at:
                self._sync_playlists(state)

        if mode == MODE_FULL:
            state["last_full_at"] = time.time()
        state["last_check_at"] = time.time()
        state["last_result"] = str(res)
        store.save(state)
        _log("{} pass: {}".format(mode, res), xbmc.LOGINFO if (mode == MODE_FULL or res.changed) else xbmc.LOGDEBUG)
        if res.uploaded or res.applied:
            widgets.invalidate()

    @staticmethod
    def _remember_settings(state, settings, max_batch):
        if isinstance(settings, dict):
            state["settings"] = settings
        if max_batch:
            state["max_batch"] = max(1, min(int(max_batch), 1000))

    def _note_lists_rev(self, payload):
        """Remember the lists revision WeTrakr sent ('' = no lists chosen)."""
        if isinstance(payload, dict) and "lists_rev" in payload and payload["lists_rev"] is not None:
            self._seen_lists_rev = payload["lists_rev"]

    def _note_sync_request(self, state, payload):
        """"Sync now" pressed in the WeTrakr web: WeTrakr cannot reach the
        device, so the request rides on /status and /changes. Each request is
        honoured once, with a full pass right after this one."""
        requested = (payload or {}).get("sync_requested_at")
        if not requested or requested == state.get("sync_request_seen"):
            return
        state["sync_request_seen"] = requested
        if lib.iso_to_ts(requested) and lib.iso_to_ts(requested) > (state.get("last_full_at") or 0):
            _log("full sync requested from the web at {}".format(requested))
            self.monitor.full_requested = True

    def _sync_settings(self, state):
        return (state.get("settings") or {}).get("sync") or {}

    def _playing_key(self):
        p = self.player
        if p is not None and getattr(p, "current_dbid", None) and getattr(p, "current_kind", None):
            return store.item_key(p.current_kind, p.current_dbid)
        return None

    # ------------------------------------------------------------------
    # Upload: Kodi -> WeTrakr
    # ------------------------------------------------------------------

    def _upload(self, api, state, mode, dialog):
        initial = not state["initial_done"]
        shows = lib.get_shows()
        items = []
        now = time.time()

        if initial or mode == MODE_FULL:
            # First pass: only what is interesting (played, in progress, rated);
            # later full passes read everything to catch unmarks and removed
            # ratings against the local state.
            movies = lib.iter_movies(touched_only=initial, should_stop=self._stop)
            episodes = lib.iter_episodes(touched_only=initial, should_stop=self._stop)
            for it in movies:
                self._collect(items, "movie", it, shows, state, initial)
            for it in episodes:
                self._collect(items, "episode", it, shows, state, initial)
        else:
            since = (state.get("last_scan_at") or now) - SCAN_MARGIN_S
            since_local = lib.local_filter_date(since)
            seen = set()
            for it in lib.iter_movies(touched_only=True, since_local=since_local, should_stop=self._stop):
                seen.add(("movie", it["movieid"]))
                self._collect(items, "movie", it, shows, state, False)
            for it in lib.iter_episodes(touched_only=True, since_local=since_local, should_stop=self._stop):
                seen.add(("episode", it["episodeid"]))
                self._collect(items, "episode", it, shows, state, False)
            # Ratings and resume resets leave no date to filter by: the monitor
            # hands over the ids it saw in VideoLibrary.OnUpdate.
            for kind, dbid in self.monitor.take_dirty_ids():
                if (kind, dbid) in seen:
                    continue
                it = lib.get_movie(dbid) if kind == "movie" else lib.get_episode(dbid)
                if it:
                    self._collect(items, kind, it, shows, state, False)

        state["last_scan_at"] = now
        if not items:
            if initial:
                state["initial_done"] = True
            return 0

        if dialog:
            dialog.update(15, message="Sending {} items to WeTrakr".format(len(items)))
        sent = self._send_batches(api, items, "initial" if initial else "incremental", state["max_batch"], dialog)
        if initial:
            state["initial_done"] = True
        return sent

    def _collect(self, items, kind, it, shows, state, initial):
        if lib.is_excluded(it, self._cfg["exclude_plugin"]):
            return
        dbid = it["movieid"] if kind == "movie" else it["episodeid"]
        data = self._item_data(it)
        st = store.get_item(state, kind, dbid, data["fp"])
        payload = self._import_item(kind, it, shows)
        if payload is None:
            return

        if initial:
            interesting = data["pc"] > 0 or data["pos"] > 0 or data["ur"] > 0
            if interesting:
                if data["ur"] > 0:
                    payload["rating"] = data["ur"]
                items.append(payload)
        else:
            changed = False
            if data["pc"] > 0:
                replay = st.get("pc", 0) > 0 and self._ts(data["lp"]) > self._ts(st.get("lp")) + REPLAY_GAP_S
                if not st.get("pc", 0) or replay:
                    since = self._ts(st.get("lp")) if st.get("lp") else 0
                    if not self.monitor.live_played_since(kind, dbid, since):
                        payload["new_play"] = True
                        changed = True
            if data["ur"] != st.get("ur", 0):
                payload["rating"] = data["ur"] if data["ur"] > 0 else None
                changed = True
            if data["pc"] == 0 and data["pos"] > 0 and data["pos"] != st.get("pos", 0):
                changed = True
            if changed:
                items.append(payload)

        self._remember(state, kind, dbid, data)

    @staticmethod
    def _ts(iso):
        return lib.iso_to_ts(iso) or 0

    @staticmethod
    def _item_data(it):
        pos, total = _resume(it)
        return {
            "pc": _int(it.get("playcount")),
            "lp": lib.kodi_date_to_iso(it.get("lastplayed")),
            "ur": _int(it.get("userrating")),
            "pos": int(pos),
            "total": int(total) or _int(it.get("runtime")),
            "fp": store.fingerprint(it),
        }

    @staticmethod
    def _remember(state, kind, dbid, data):
        st = store.get_item(state, kind, dbid, data.get("fp"))
        fields = {"pc": data["pc"], "lp": data["lp"], "ur": data["ur"], "pos": data["pos"], "fp": data.get("fp")}
        # Played -> not played seen in Kodi: on purpose (the sync only unmarks
        # from _apply_row, which forgets the flag right after).
        if st.get("pc", 0) > 0 and data["pc"] == 0:
            fields["unw"] = True
        if data["pc"] > 0:
            fields["unw"] = False
        if st.get("pos", 0) != data["pos"]:
            fields["wpos"] = False
        store.set_item(state, kind, dbid, fields)

    def _import_item(self, kind, it, shows):
        """Row of POST /integrations/kodi/import for a library item, or None
        when it has no usable id."""
        ids = utils.extract_ids(it)
        data = self._item_data(it)
        row = {
            "type": kind,
            "ids": ids,
            "title": it.get("title") or "",
            "played": data["pc"] > 0,
            "play_count": data["pc"],
            "last_played_at": data["lp"],
        }
        if data["pc"] == 0 and data["pos"] > 0:
            row["position_s"] = data["pos"]
            row["runtime_s"] = data["total"]
        if kind == "movie":
            row["year"] = _int(it.get("year")) or None
            if not utils._has_ids(ids):
                return None
        else:
            show = shows.get(it.get("tvshowid")) or {}
            row["series_ids"] = lib.series_ids(show)
            row["series_title"] = it.get("showtitle") or show.get("title") or ""
            row["season"] = it.get("season")
            row["episode"] = it.get("episode")
            source = utils.detect_show_id_source(show)
            if source:
                row["show_id_source"] = source
            aired = utils._aired_date(it.get("firstaired"))
            if aired:
                row["aired"] = aired
            if not utils._has_ids(ids) and not utils._has_ids(row["series_ids"]):
                return None
        return row

    def _send_batches(self, api, items, mode, max_batch, dialog):
        session_id = "{}-{}".format(int(time.time()), random.randint(100000, 999999))
        sent = 0
        total = len(items)
        for start in range(0, total, max_batch):
            if self._stop():
                break
            chunk = items[start:start + max_batch]
            final = start + max_batch >= total
            accepted = api.import_batch(session_id, mode, chunk, final)
            api.wait_for_batch(accepted)
            sent += len(chunk)
            if dialog:
                dialog.update(15 + int(35.0 * sent / total), message="Sent {} of {} items".format(sent, total))
        return sent

    # ------------------------------------------------------------------
    # Download: WeTrakr -> Kodi
    # ------------------------------------------------------------------

    def _ensure_index(self):
        if self.index.built_at < self.monitor.library_changed_at or not self.index.built_at:
            self.index.build(should_stop=self._stop)
        return self.index

    def _pull(self, api, state, full, dialog):
        out = {"unchanged": False, "applied": 0, "in_progress": [], "planning_changed": False}
        sync = self._sync_settings(state)
        writer = lib.Writer(expect=self.monitor.expect)

        if not state["snapshot_done"] or not state.get("cursor_since"):
            if dialog:
                dialog.update(55, message="Applying your WeTrakr library to Kodi")
            self._ensure_index()
            cursor_since = None
            planning = set()
            for section in SNAPSHOT_SECTIONS:
                cursor = None
                while True:
                    if self._stop():
                        return out
                    page = api.snapshot(section, cursor)
                    if cursor_since is None and page.get("cursor_since"):
                        cursor_since = page["cursor_since"]
                    for row in page.get("titles") or []:
                        out["applied"] += self._apply_row(state, sync, writer, row, from_changes=False)
                        if row.get("planning"):
                            key = store.title_key(row.get("type"), row.get("ids"))
                            if key:
                                planning.add(key)
                    cursor = page.get("next_cursor")
                    if not cursor:
                        break
            writer.flush()
            if set(state.get("planning") or []) != planning:
                out["planning_changed"] = True
            state["planning"] = sorted(planning)
            state["cursor_since"] = cursor_since or lib.now_iso()
            state["snapshot_done"] = True
            store.save(state)
            # After a snapshot the journal is read in full: what changed in the
            # meantime must arrive, and the in-progress list has not been applied.
            full = True

        pages = 0
        while True:
            if self._stop():
                break
            try:
                changes = api.changes(state["cursor_since"], full=full)
            except ApiError as e:
                if e.error in ("SNAPSHOT_REQUIRED", "JOURNAL_EXPIRED"):
                    # Too long without a sync: the journal does not go back that far.
                    state["snapshot_done"] = False
                    state["cursor_since"] = None
                    return self._pull(api, state, True, dialog)
                raise
            self._remember_settings(state, changes.get("settings"), changes.get("max_batch"))
            self._note_sync_request(state, changes)
            self._note_lists_rev(changes)
            sync = self._sync_settings(state)
            if changes.get("unchanged"):
                state["cursor_since"] = changes.get("next_since") or state["cursor_since"]
                out["unchanged"] = True
                return out
            titles = changes.get("titles") or []
            if titles:
                if dialog:
                    dialog.update(70, message="Applying {} changes from WeTrakr".format(len(titles)))
                self._ensure_index()
            planning = set(state.get("planning") or [])
            for row in titles:
                out["applied"] += self._apply_row(state, sync, writer, row, from_changes=True)
                key = store.title_key(row.get("type"), row.get("ids"))
                if key:
                    if row.get("planning"):
                        planning.add(key)
                    else:
                        planning.discard(key)
            if planning != set(state.get("planning") or []):
                out["planning_changed"] = True
                state["planning"] = sorted(planning)
            writer.flush()
            state["cursor_since"] = changes.get("next_since") or state["cursor_since"]
            out["in_progress"] = changes.get("in_progress") or []
            store.save(state)
            full = True
            pages += 1
            if not changes.get("has_more") or pages >= MAX_CHANGES_PAGES:
                break
        return out

    def _apply_row(self, state, sync, writer, row, from_changes):
        """Apply the state of one WeTrakr title to its Kodi items. Returns how
        many items were written."""
        applied = 0
        row_type = row.get("type")
        for kind, dbid, item in self.index.find(row_type, row.get("ids"), row.get("series_ids"), row.get("season"), row.get("episode")):
            if kind == "tvshow":
                continue    # shows only matter for the watchlist tag
            if lib.is_excluded(item, self._cfg["exclude_plugin"]):
                continue
            data = self._item_data(item)
            st = store.get_item(state, kind, dbid, data["fp"])
            fields = {}
            unwatch_from_wetrakr = False

            # Unmarked in Kodi since the last pass (to watch it again): remember
            # it so WeTrakr's watched does not mark it right back.
            if st.get("pc", 0) > 0 and data["pc"] == 0:
                st = store.set_item(state, kind, dbid, {"unw": True})

            watched = row.get("watched")
            if sync.get("push_watched", True) and watched and row_type != "show":
                if watched.get("is_watched") and data["pc"] == 0 and not self._keep_local_unwatch(st, watched):
                    fields["playcount"] = max(1, _int(watched.get("play_count")))
                    if not watched.get("unknown") and watched.get("last_watched_at"):
                        lp = lib.iso_to_kodi_date(watched["last_watched_at"])
                        if lp:
                            fields["lastplayed"] = lp
                    if data["pos"] > 0:
                        fields["resume"] = {"position": 0, "total": data["total"]}
                elif from_changes and row.get("explicit_unwatch") and data["pc"] > 0:
                    # Only if Kodi has not played it again since the last pass:
                    # the newer local watch wins.
                    unchanged_locally = st.get("pc", 0) > 0 and self._ts(data["lp"]) <= self._ts(st.get("lp"))
                    if unchanged_locally:
                        fields["playcount"] = 0
                        unwatch_from_wetrakr = True

            if sync.get("push_ratings", True):
                rating = row.get("rating")
                if rating is not None and (data["ur"] == 0 or abs(data["ur"] - float(rating)) >= 0.5):
                    fields["userrating"] = int(round(float(rating)))
                elif from_changes and rating is None and data["ur"] > 0 and st.get("ur", 0) == data["ur"]:
                    fields["userrating"] = 0

            if fields:
                if kind == "movie":
                    writer.set_movie(dbid, fields)
                else:
                    writer.set_episode(dbid, fields)
                applied += 1
                # Keep the in-memory index in step with what was written.
                if "playcount" in fields:
                    item["playcount"] = fields["playcount"]
                    if fields["playcount"] == 0:
                        item["lastplayed"] = item.get("lastplayed") or ""
                if "lastplayed" in fields:
                    item["lastplayed"] = fields["lastplayed"]
                if "userrating" in fields:
                    item["userrating"] = fields["userrating"]
                if "resume" in fields:
                    item["resume"] = fields["resume"]
                data = self._item_data(item)
            self._remember(state, kind, dbid, data)
            if unwatch_from_wetrakr:
                store.set_item(state, kind, dbid, {"unw": False})
        return applied

    def _keep_local_unwatch(self, st, watched):
        """A "not watched" made in Kodi on purpose wins over WeTrakr's watched
        while WeTrakr has no play later than the one Kodi knew about."""
        if not st.get("unw"):
            return False
        last = self._ts(watched.get("last_watched_at"))
        return bool(watched.get("unknown")) or last <= self._ts(st.get("lp"))

    # ------------------------------------------------------------------
    # Resume points
    # ------------------------------------------------------------------

    def _apply_progress(self, state, rows):
        sync = self._sync_settings(state)
        # Cache for the player: resume add-on items (no dbid) from WeTrakr.
        cache = {}
        for row in rows or []:
            key = store.title_key(row.get("type"), row.get("ids"), row.get("series_ids"), row.get("season"), row.get("episode"))
            if key:
                cache[key] = {"percent": row.get("percent"), "position_ms": row.get("position_ms"), "runtime_s": row.get("runtime_s"), "updated_at": row.get("updated_at")}
        state["in_progress"] = cache

        if not sync.get("push_progress", True) or rows is None:
            return 0
        self._ensure_index()
        writer = lib.Writer(expect=self.monitor.expect)
        playing = self._playing_key()
        wanted = set()
        written = 0

        for row in rows:
            for kind, dbid, item in self.index.find(row.get("type"), row.get("ids"), row.get("series_ids"), row.get("season"), row.get("episode")):
                if kind == "tvshow" or lib.is_excluded(item, self._cfg["exclude_plugin"]):
                    continue
                key = store.item_key(kind, dbid)
                wanted.add(key)
                if key == playing:
                    continue
                data = self._item_data(item)
                if data["pc"] > 0:
                    continue
                st = store.get_item(state, kind, dbid, data["fp"])
                total = data["total"] or _int(row.get("runtime_s"))
                if row.get("position_ms"):
                    position = int(row["position_ms"]) // 1000
                elif total and row.get("percent"):
                    position = int(total * float(row["percent"]) / 100.0)
                else:
                    continue
                if position <= 0 or not total:
                    continue
                ours = st.get("wpos") and data["pos"] == st.get("pos", 0)
                if data["pos"] > 0 and not ours:
                    continue    # Kodi's own resume point is not overwritten
                if abs(data["pos"] - position) < RESUME_MIN_DIFF_S:
                    continue
                fields = {"resume": {"position": position, "total": total}}
                if kind == "movie":
                    writer.set_movie(dbid, fields)
                else:
                    writer.set_episode(dbid, fields)
                item["resume"] = fields["resume"]
                self._remember(state, kind, dbid, self._item_data(item))
                store.set_item(state, kind, dbid, {"wpos": True})
                written += 1

        # What the sync wrote and is no longer in progress in WeTrakr leaves
        # "Continue watching" (if Kodi has not touched it).
        for key, st in list(state["items"].items()):
            if not st.get("wpos") or key in wanted or key == playing:
                continue
            kind = "movie" if key.startswith("m") else "episode" if key.startswith("e") else None
            if not kind:
                continue
            dbid = _int(key[1:])
            item = self.index.movies.get(dbid) if kind == "movie" else self.index.episodes.get(dbid)
            if not item:
                continue
            data = self._item_data(item)
            if data["pos"] == st.get("pos", 0) and data["pc"] == 0 and data["pos"] > 0:
                fields = {"resume": {"position": 0, "total": data["total"]}}
                if kind == "movie":
                    writer.set_movie(dbid, fields)
                else:
                    writer.set_episode(dbid, fields)
                item["resume"] = fields["resume"]
            self._remember(state, kind, dbid, self._item_data(item))
            store.set_item(state, kind, dbid, {"wpos": False})
        writer.flush()
        return written

    # ------------------------------------------------------------------
    # WeTrakr lists as tags (1.3.1)
    # ------------------------------------------------------------------

    @staticmethod
    def _list_tag(name):
        name = re.sub(r"\s+", " ", str(name or "")).strip()[:80] or "List"
        return LIST_TAG_PREFIX + name

    def _sync_lists(self, api, state, rev):
        """Movies and shows of the WeTrakr lists the user chose (in the web)
        carry a "WeTrakr: <list>" tag. Only tags this sync wrote are ever
        removed: a renamed or deselected list loses its old tag everywhere."""
        if rev:
            data = api.lists()
            lists = data.get("lists") or []
            rev = data.get("rev", rev)
        else:
            lists = []
        self._ensure_index()

        wanted = {}       # item key -> set of list tags
        new_state = {}
        for l in lists:
            tag = self._list_tag(l.get("name"))
            keys = []
            for it in l.get("items") or []:
                for kind, dbid, _item in self.index.find(it.get("type"), it.get("ids")):
                    key = store.item_key(kind, dbid)
                    wanted.setdefault(key, set()).add(tag)
                    keys.append(key)
            new_state[str(l.get("id"))] = {"name": l.get("name"), "tag": tag, "count": len(keys)}

        managed = set(state.get("list_tags") or [])
        managed.update(v["tag"] for v in new_state.values())
        writer = lib.Writer(expect=self.monitor.expect)
        changed = 0
        for kind, table, dbid_key in (("movie", self.index.movies, "movieid"), ("tvshow", self.index.shows, "tvshowid")):
            for dbid, item in table.items():
                if kind == "movie" and lib.is_excluded(item, self._cfg["exclude_plugin"]):
                    continue
                current = list(item.get("tag") or [])
                keep = [t for t in current if t not in managed]
                target = keep + sorted(wanted.get(store.item_key(kind, dbid), ()))
                if sorted(target) == sorted(current):
                    continue
                item["tag"] = target
                if kind == "movie":
                    writer.set_movie(dbid, {"tag": target})
                else:
                    writer.set_show(dbid, {"tag": target})
                changed += 1
        writer.flush()

        state["lists"] = new_state
        state["list_tags"] = sorted(v["tag"] for v in new_state.values())
        state["lists_rev"] = rev
        _log("lists: {} list(s), {} item(s) retagged".format(len(new_state), changed))
        return changed

    # ------------------------------------------------------------------
    # Smart playlists (Videos › Playlists, and skin widgets)
    # ------------------------------------------------------------------

    def _sync_playlists(self, state):
        """One smart playlist per tag this sync manages (Planning and each
        WeTrakr list), split by movies / shows when the tag is on both. Only
        files this sync created are ever deleted."""
        try:
            import xbmcvfs
            folder = xbmcvfs.translatePath(PLAYLISTS_DIR)
        except Exception:
            return
        if not os.path.isdir(folder):
            try:
                os.makedirs(folder)
            except OSError:
                return

        tags = []
        sync = self._sync_settings(state)
        if sync.get("push_planning", True) and self._cfg["watchlist_tag"]:
            tags.append((WATCHLIST_TAG, "Watchlist"))
        for v in (state.get("lists") or {}).values():
            tags.append((v["tag"], v["tag"][len(LIST_TAG_PREFIX):]))

        idx = self.index
        wanted = {}
        for tag, title in tags:
            has_movies = any(tag in (m.get("tag") or []) for m in idx.movies.values())
            has_shows = any(tag in (s.get("tag") or []) for s in idx.shows.values())
            kinds = [k for k, present in (("movies", has_movies), ("tvshows", has_shows)) if present]
            for kind in kinds:
                label = title if len(kinds) == 1 else "{} ({})".format(title, "Movies" if kind == "movies" else "Shows")
                fname = XSP_PREFIX + re.sub(r'[\\/:*?"<>|]+', "-", label).strip()[:90] + ".xsp"
                wanted[fname] = self._xsp(kind, XSP_PREFIX.strip(" -") + ": " + label, tag)

        for fname, body in wanted.items():
            path = os.path.join(folder, fname)
            try:
                old = open(path, "r").read() if os.path.exists(path) else None
                if old != body:
                    with open(path, "w") as fh:
                        fh.write(body)
            except (IOError, OSError) as e:
                _log("playlist {} not written: {}".format(fname, e), xbmc.LOGWARNING)
        for fname in set(state.get("xsp_files") or []) - set(wanted):
            try:
                os.remove(os.path.join(folder, fname))
            except OSError:
                pass
        state["xsp_files"] = sorted(wanted)

    @staticmethod
    def _xsp(kind, name, tag):
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n'
            '<smartplaylist type="{kind}">\n'
            '    <name>{name}</name>\n'
            '    <match>all</match>\n'
            '    <rule field="tag" operator="is">\n'
            '        <value>{tag}</value>\n'
            '    </rule>\n'
            '    <order direction="ascending">sorttitle</order>\n'
            '</smartplaylist>\n'
        ).format(kind=kind, name=xml_escape(name), tag=xml_escape(tag))

    # ------------------------------------------------------------------
    # Watchlist tag (Planning)
    # ------------------------------------------------------------------

    def _sync_watchlist_tag(self, state):
        """Movies and shows in WeTrakr's Planning carry the WATCHLIST_TAG tag,
        which any skin shows as a widget through a smart playlist. Only the
        tags this sync added are ever removed."""
        sync = self._sync_settings(state)
        if not sync.get("push_planning", True) or not self._cfg["watchlist_tag"]:
            return 0
        self._ensure_index()
        planning = set(state.get("planning") or [])
        wanted = set()
        for mid, m in self.index.movies.items():
            if store.title_key("movie", utils.extract_ids(m)) in planning:
                wanted.add(store.item_key("movie", mid))
        for sid, s in self.index.shows.items():
            if store.title_key("show", utils.extract_ids(s)) in planning:
                wanted.add(store.item_key("tvshow", sid))
        tagged = set(state.get("tagged") or [])
        writer = lib.Writer(expect=self.monitor.expect)
        changed = 0
        for key in wanted - tagged:
            if self._set_tag(writer, key, True):
                changed += 1
        for key in tagged - wanted:
            if self._set_tag(writer, key, False):
                changed += 1
        writer.flush()
        state["tagged"] = sorted(wanted)
        return changed

    def _set_tag(self, writer, key, present):
        kind = "movie" if key.startswith("m") else "tvshow"
        dbid = _int(key[1:])
        item = self.index.movies.get(dbid) if kind == "movie" else self.index.shows.get(dbid)
        if not item:
            return False
        tags = [t for t in (item.get("tag") or []) if t != WATCHLIST_TAG]
        if present:
            tags.append(WATCHLIST_TAG)
        elif WATCHLIST_TAG not in (item.get("tag") or []):
            return False
        item["tag"] = tags
        if kind == "movie":
            writer.set_movie(dbid, {"tag": tags})
        else:
            writer.set_show(dbid, {"tag": tags})
        return True


# =====================================================================
# Used by the player: resume from WeTrakr
# =====================================================================

def resume_position_for(item, show_item=None):
    """Seconds where WeTrakr left this title, from the last /changes, or None.
    Meant for items played from add-ons (no library resume point); library
    items get their resume point written by the sync."""
    try:
        state = store.load()
        cache = state.get("in_progress") or {}
        if not cache:
            return None
        ids = utils.extract_ids(item)
        if not utils._has_ids(ids):
            ids = utils.extract_ids_from_url(item.get("file"))
        if item.get("type") == "episode":
            key = store.title_key("episode", ids, lib.series_ids(show_item), item.get("season"), item.get("episode"))
        else:
            key = store.title_key("movie", ids)
        row = cache.get(key) if key else None
        if not row:
            return None
        if row.get("percent") is not None and float(row["percent"]) >= 90:
            return None
        if row.get("position_ms"):
            return int(row["position_ms"]) // 1000
        if row.get("runtime_s") and row.get("percent"):
            return int(float(row["runtime_s"]) * float(row["percent"]) / 100.0)
    except Exception as e:
        _log("resume_position_for error: {}".format(e), xbmc.LOGWARNING)
    return None


def run_in_thread(engine, mode, resnapshot=False, with_dialog=False, on_done=None):
    """Run a pass on a daemon thread; optional DialogProgressBG for manual syncs."""
    def _worker():
        dialog = None
        if with_dialog:
            try:
                dialog = xbmcgui.DialogProgressBG()
                dialog.create("WeTrakr", "Syncing your library")
            except Exception:
                dialog = None
        result = engine.run(mode, resnapshot=resnapshot, dialog=dialog)
        if dialog:
            try:
                dialog.update(100, message=str(result))
                xbmc.sleep(1500)
                dialog.close()
            except Exception:
                pass
        if on_done:
            on_done(result)
    t = threading.Thread(target=_worker)
    t.daemon = True
    t.start()
    return t
