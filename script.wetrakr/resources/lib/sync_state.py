"""
sync_state.py — last synced state of every library item, per device.

Lives in special://profile/addon_data/script.wetrakr/sync_state.json. It is
what lets the add-on upload only what changed in Kodi, tell its own writes
from the user's, and remember what came from WeTrakr (resume points, the
watchlist tag) so only that gets undone later.

Keys: "m<movieid>" / "e<episodeid>" / "s<tvshowid>".
Item fields (short on purpose, the file holds one row per library item):
  pc   playcount          lp   lastplayed (UTC ISO)   pos  resume position (s)
  ur   userrating         wpos resume written by the sync (from WeTrakr)
  unw  unmarked in Kodi on purpose: WeTrakr's watched does not re-mark it
  fp   fingerprint of the file (crc32 of its path): Kodi REUSES database ids
       after a clean or a re-scan, so a row whose fingerprint does not match
       belongs to another item and is dropped (see get_item)
"""

import json
import zlib
import os
import threading

import xbmc
import xbmcaddon
import xbmcvfs

VERSION = 1
_lock = threading.Lock()


def _path():
    addon = xbmcaddon.Addon("script.wetrakr")
    folder = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
    if not os.path.exists(folder):
        try:
            os.makedirs(folder)
        except OSError:
            pass
    return os.path.join(folder, "sync_state.json")


def empty():
    return {
        "version": VERSION,
        "initial_done": False,      # first Kodi -> WeTrakr upload done
        "snapshot_done": False,     # first WeTrakr -> Kodi snapshot applied
        "cursor_since": None,       # /changes cursor (UTC ISO)
        "last_scan_at": None,       # last upload scan (unix seconds)
        "last_full_at": None,       # last full pass (unix seconds)
        "last_check_at": None,
        "last_result": None,
        "settings": None,           # sync settings as WeTrakr sent them
        "max_batch": 1000,
        "items": {},
        "planning": [],             # WeTrakr Planning title keys ("movie:tmdb:1")
        "tagged": [],               # items that carry OUR watchlist tag
        "in_progress": {},          # title key -> {percent, position_ms, updated_at}
        "sync_request_seen": None,  # last "Sync now" from the web already honoured
        "lists_rev": None,          # revision of the WeTrakr lists last applied
        "lists": {},                # list id -> {name, tag, keys: [title keys]}
        "list_tags": [],            # every "WeTrakr: ..." tag this sync ever wrote
        "xsp_files": [],            # smart playlists this sync created
    }


def load():
    path = _path()
    try:
        with open(path, "r") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or data.get("version") != VERSION:
            return empty()
        base = empty()
        base.update(data)
        return base
    except (IOError, OSError, ValueError):
        return empty()


def save(state):
    path = _path()
    tmp = path + ".tmp"
    with _lock:
        try:
            with open(tmp, "w") as fh:
                json.dump(state, fh)
            if os.path.exists(path):
                os.remove(path)
            os.rename(tmp, path)
        except (IOError, OSError) as e:
            xbmc.log("[WeTrakr] sync_state save failed: {}".format(e), xbmc.LOGWARNING)


def reset():
    try:
        os.remove(_path())
    except OSError:
        pass


def item_key(kind, dbid):
    return {"movie": "m", "episode": "e", "tvshow": "s"}[kind] + str(dbid)


def fingerprint(item):
    """crc32 of the item's file path, or None when Kodi gives no path."""
    f = (item or {}).get("file")
    if not f:
        return None
    return zlib.crc32(str(f).encode("utf-8")) & 0xffffffff


def get_item(state, kind, dbid, fp=None):
    """Last synced state of a library item. With `fp`, a row recorded for a
    different file (Kodi reused the dbid) is forgotten and {} returned."""
    key = item_key(kind, dbid)
    st = state["items"].get(key) or {}
    if st and fp is not None and st.get("fp") != fp:
        state["items"].pop(key, None)
        return {}
    return st


def set_item(state, kind, dbid, fields):
    key = item_key(kind, dbid)
    st = state["items"].get(key) or {}
    st.update(fields)
    state["items"][key] = st
    return st


def title_key(row_type, ids, series_ids=None, season=None, episode=None):
    """Stable key of a WeTrakr title row (as in the Emby plugin): the first id
    available, tmdb > imdb > tvdb; episodes hang from their series."""
    def first(d):
        d = d or {}
        for k in ("tmdb", "imdb", "tvdb"):
            if d.get(k):
                return "{}:{}".format(k, d[k])
        return None
    if row_type == "episode":
        s = first(series_ids)
        if s is None or season is None or episode is None:
            e = first(ids)
            return "episode:{}".format(e) if e else None
        return "episode:{}:{}:{}".format(s, season, episode)
    t = first(ids)
    return "{}:{}".format(row_type, t) if t else None
