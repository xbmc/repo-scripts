"""Where each show is in its series: one bookmark per show, kept in series.json.

A show's bookmark is the episode last planned for it, so the next airing is the one
after it.  The show's home channel (assign.py) reads and moves the shared bookmark,
so a show that moves channel, or leaves the lineup and comes back, continues where it
was.  Other channels that air the show ('Shows on more than one channel', fill-ins)
keep their own run in their schedule file, and each pinned slot keeps its own, as
before.  Only Start series over clears bookmarks; a refresh moves them back to what
has aired (scheduler.ChannelSchedule.cut).

Both Kodi processes plan schedules (the TV and the background service), so a write
merges with the file on disk, key by key, newest change winning."""
import json
import os
import threading
import time

from .kodiutil import PROFILE, load_json, log

FILE = os.path.join(PROFILE, "series.json")
_lock = threading.RLock()
_data = None            # {"v": 1, "shows": {key: {"last": path or None, "w": time written}}}
_mtime = 0
_dirty = {}             # changed here and not on disk yet


def _empty():
    return {"v": 1, "shows": {}}


def _mt():
    try:
        return os.path.getmtime(FILE)
    except OSError:
        return 0


def _load():
    global _data, _mtime
    mt = _mt()
    if _data is None or mt != _mtime:
        d = load_json(FILE, None)
        if not isinstance(d, dict) or not isinstance(d.get("shows"), dict):
            d = _empty()
        d["shows"].update(_dirty)            # our changes not saved yet win
        _data, _mtime = d, mt
    return _data


def exists():
    return os.path.exists(FILE)


def get(key):
    """(known, last path): known is False when the show has no bookmark yet."""
    with _lock:
        v = _load()["shows"].get(key)
        return (v is not None), (v or {}).get("last")


def put(key, path):
    """Move a show's bookmark (path None: the show starts from its first episode)."""
    with _lock:
        v = {"last": path, "w": time.time()}
        _load()["shows"][key] = v
        _dirty[key] = v


def keys():
    with _lock:
        return list(_load()["shows"])


def forget(keys_=None):
    """Start series over: these shows (all of them when None) from their first episode."""
    with _lock:
        for k in (list(_load()["shows"]) if keys_ is None else keys_):
            put(k, None)


def flush():
    """Write our changes, merged with whatever the other process wrote meanwhile."""
    global _data, _mtime
    with _lock:
        _flush_labels()
        if not _dirty:
            return
        disk = load_json(FILE, None)
        if not isinstance(disk, dict) or not isinstance(disk.get("shows"), dict):
            disk = _empty()
        shows = disk["shows"]
        for k, v in _dirty.items():
            if v["w"] >= (shows.get(k) or {}).get("w", 0):
                shows[k] = v
        tmp = "%s.%d.tmp" % (FILE, os.getpid())
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(disk, f, separators=(",", ":"))
            os.replace(tmp, FILE)
        except (IOError, OSError) as exc:
            log("series bookmarks not saved: %s" % exc)
            return
        _dirty.clear()
        _data, _mtime = disk, _mt()


# ---- which episode a bookmarked file was (season/episode), for when it's gone
# A bookmark is a file path.  If that file leaves the library (deleted, renamed,
# replaced by a better copy), the run continues after the same season/episode
# instead of going back to S01E01 (scheduler._next_episode).
LABELS_FILE = os.path.join(PROFILE, "episode_labels.json")
_labels = None
_labels_dirty = {}


def _load_labels():
    global _labels
    if _labels is None:
        d = load_json(LABELS_FILE, None)
        _labels = d if isinstance(d, dict) else {}
    return _labels


def remember(path, label):
    """'S01E04' for a planned episode's file."""
    if not path or not label:
        return
    with _lock:
        if _load_labels().get(path) != label:
            _labels[path] = label
            _labels_dirty[path] = label


def label_of(path):
    with _lock:
        return _load_labels().get(path) if path else None


def _flush_labels():
    if not _labels_dirty:
        return
    disk = load_json(LABELS_FILE, None)
    disk = disk if isinstance(disk, dict) else {}
    disk.update(_labels_dirty)
    tmp = "%s.%d.tmp" % (LABELS_FILE, os.getpid())
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(disk, f, separators=(",", ":"))
        os.replace(tmp, LABELS_FILE)
        _labels_dirty.clear()
    except (IOError, OSError) as exc:
        log("episode labels not saved: %s" % exc)


def save_all(shows):
    """Replace every bookmark (the first run after updating: see scheduler.migrate)."""
    with _lock:
        now = time.time()
        for k, last in shows.items():
            put(k, last)
        for k in _dirty:
            _dirty[k]["w"] = now
        flush()
