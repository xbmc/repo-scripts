"""Leave the viewer's watch progress exactly as it was.

Kodi saves a resume point (and may bump the play count / last-played date)
whenever a video stops - including every show CableBox airs and every
channel you surf past.  We snapshot a file's state before CableBox first plays
it and put it back after CableBox moves on.  Pending restores are written to
disk, so a crash or power cut is repaired at the next start.
"""
import os
import threading

from . import kodiutil as K

PENDING_FILE = os.path.join(K.PROFILE, "progress_restore.json")
_lock = threading.Lock()


def enabled():
    return K.setting_bool("keep_progress", True)


def snapshot(path):
    """Current resume/playcount/lastplayed of a file (library item or plain file)."""
    res = K.rpc("Files.GetFileDetails", {"file": path, "media": "video",
                                         "properties": ["resume", "playcount", "lastplayed"]})
    d = res.get("filedetails") or {}
    if not d:
        return None
    r = d.get("resume") or {}
    return {"path": path, "type": d.get("type") or "", "id": d.get("id"),
            "position": float(r.get("position") or 0), "total": float(r.get("total") or 0),
            "playcount": int(d.get("playcount") or 0), "lastplayed": d.get("lastplayed") or ""}


def _set(method, idkey, item, params):
    """Kodi's set call; if it rejects the whole update, retry the parts that matter
    most separately (resume point first)."""
    full = dict(params, **{idkey: item}) if idkey else dict(params)
    if K.rpc(method, full) == "OK":
        return True
    ok = K.rpc(method, dict({idkey: item} if idkey else {}, **{k: v for k, v in params.items()
                                                              if k in ("resume", "file", "media")})) == "OK"
    for extra in ("playcount", "lastplayed"):
        K.rpc(method, dict({idkey: item} if idkey else {}, **{k: v for k, v in params.items()
                                                              if k in (extra, "file", "media")}))
    return ok


def restore(snap):
    resume = {"position": snap["position"], "total": snap["total"]}
    common = {"playcount": snap["playcount"], "lastplayed": snap["lastplayed"], "resume": resume}
    kind, item = snap.get("type"), snap.get("id")
    if kind == "episode" and item is not None:
        return _set("VideoLibrary.SetEpisodeDetails", "episodeid", item, common)
    if kind == "movie" and item is not None:
        return _set("VideoLibrary.SetMovieDetails", "movieid", item, common)
    if kind == "musicvideo" and item is not None:
        return _set("VideoLibrary.SetMusicVideoDetails", "musicvideoid", item, common)
    return _set("Files.SetFileDetails", None, None, dict(common, file=snap["path"], media="video"))


def matches(snap):
    """Is the file back to its original state (resume point and play count)?"""
    now = snapshot(snap["path"])
    if now is None:
        return True
    return abs(now["position"] - snap["position"]) < 2 and now["playcount"] == snap["playcount"]


def fix(snap):
    """Restore and confirm.  Returns True once the file is verified back to normal."""
    try:
        restore(snap)
        return matches(snap)
    except Exception as exc:
        K.log_err("progress restore %s: %s" % (snap.get("path"), exc))
        return False


RETRY_DELAYS = (8, 30, 120)


class Guard(object):
    """Used by the TV: remember() before playing, release() once playback moved on.

    A restore only counts once it's verified: if Kodi writes its own resume point
    after ours (slow disk), we try again a few times; anything still unconfirmed
    stays in progress_restore.json for the background service."""

    def __init__(self):
        self.snaps = {}            # path -> original state (first time seen this session)
        self.pending = {}          # path -> snap still to restore
        self._load_pending()

    def _load_pending(self):
        for snap in K.load_json(PENDING_FILE, []):
            self.snaps.setdefault(snap["path"], snap)
            self.pending[snap["path"]] = snap

    def _save_pending(self):
        try:
            K.save_json(PENDING_FILE, list(self.pending.values()))
        except Exception as exc:
            K.log_err("progress save: %s" % exc)

    def remember(self, path):
        if not enabled() or not path:
            return
        with _lock:
            if path not in self.snaps:
                snap = snapshot(path)
                if snap is None:
                    return
                self.snaps[path] = snap
            self.pending[path] = self.snaps[path]
            self._save_pending()

    def release(self, keep=None, delay=2.5, attempt=0):
        """Restore everything pending except `keep` (the file playing now), after
        Kodi has had time to write its own resume point."""
        with _lock:
            todo = [s for p, s in self.pending.items() if p != keep]
        if not todo:
            return
        t = threading.Timer(delay, self._restore, [todo, keep, attempt])
        t.daemon = True
        t.start()

    def release_now(self):
        with _lock:
            todo = list(self.pending.values())
        self._restore(todo, None, len(RETRY_DELAYS))

    def _restore(self, todo, keep=None, attempt=0):
        done = [snap for snap in todo if fix(snap)]
        with _lock:
            for snap in done:
                if self.pending.get(snap["path"]) is snap:
                    self.pending.pop(snap["path"], None)
            self._save_pending()
            left = [s for s in todo if s not in done and s["path"] in self.pending]
        if left and attempt < len(RETRY_DELAYS):
            self.release(keep=keep, delay=RETRY_DELAYS[attempt], attempt=attempt + 1)


def repair_pending():
    """Restore anything left unconfirmed (TV switched off, crash, power cut).
    Called by the service at start-up and shortly after the TV is turned off."""
    todo = K.load_json(PENDING_FILE, [])
    if not todo:
        return 0
    left = [snap for snap in todo if not fix(snap)]
    K.save_json(PENDING_FILE, left)
    return len(todo) - len(left)


# ------------------------------------------------------------------ clean-up tool
def in_progress_items():
    """[(label, kind, id)] for every movie/episode Kodi lists as in progress."""
    flt = {"field": "inprogress", "operator": "true", "value": ""}
    out = []
    res = K.rpc("VideoLibrary.GetMovies", {"filter": flt, "properties": ["title", "year", "resume"]})
    for m in res.get("movies", []):
        out.append(("%s (%s)" % (m.get("title", ""), m.get("year", "")), "movie", m["movieid"], m.get("resume") or {}))
    res = K.rpc("VideoLibrary.GetEpisodes", {"filter": flt,
                                            "properties": ["showtitle", "season", "episode", "title", "resume"]})
    for e in res.get("episodes", []):
        out.append(("%s S%02dE%02d %s" % (e.get("showtitle", ""), e.get("season", 0), e.get("episode", 0),
                                          e.get("title", "")), "episode", e["episodeid"], e.get("resume") or {}))
    return out


def clear_resume(kind, item):
    resume = {"position": 0, "total": 0}
    if kind == "movie":
        K.rpc("VideoLibrary.SetMovieDetails", {"movieid": item, "resume": resume})
    else:
        K.rpc("VideoLibrary.SetEpisodeDetails", {"episodeid": item, "resume": resume})
