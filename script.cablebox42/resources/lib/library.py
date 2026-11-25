"""Turns channel 'sources' into pools of playable programmes.

A pool is {"series": [ {key, title, episodes:[item]} ], "singles": [item]}
and an item is {"path", "title", "dur", "show", "label"}.

Supported source types (all built from Kodi's own library or the VFS, so any
SMB/NFS/local path that Kodi can read works):

  {"type": "tvshow",   "value": "Show title"}
  {"type": "tvgenre",  "value": "Comedy"}
  {"type": "tvdecade", "value": 1980}
  {"type": "movies",   "genre": "Horror", "years": [1980, 1989], "set": "", "tag": ""}
  {"type": "folder",   "path": "smb://...", "mode": "shows"|"random"|"sequential"}
  {"type": "playlist", "path": "special://profile/playlists/video/x.xsp"}
"""
import json
import re
import threading
import time

import xbmc
import xbmcvfs

import os

from .kodiutil import rpc, load_json, save_json, DURATIONS_FILE, PROFILE, log, setting_int
from . import probe
from . import titles as tnames

VIDEO_EXT = (".mkv", ".mp4", ".m4v", ".avi", ".ts", ".m2ts", ".mts", ".mov",
             ".webm", ".mpg", ".mpeg", ".wmv", ".flv", ".vob", ".divx", ".ogv")
AUDIO_EXT = (".mp3", ".flac", ".ogg", ".m4a", ".wav", ".aac", ".wma", ".opus")

EP_PROPS = ["file", "title", "runtime", "streamdetails", "season", "episode", "showtitle"]
MOVIE_PROPS = ["file", "title", "runtime", "streamdetails", "year"]

_POOL_CACHE = {}
_POOL_TTL = 1800
# A refresh in one Kodi process (the service, after a library scan) clears the
# library caches of the others too (the TV): it bumps this file, and every cached
# read first checks it (at most every few seconds).
GEN_FILE = os.path.join(PROFILE, "library.gen")
_GEN = [0.0, 0.0]          # [generation seen, last checked]


def _check_gen():
    now = time.time()
    if now - _GEN[1] < 3:
        return
    _GEN[1] = now
    try:
        g = os.path.getmtime(GEN_FILE)
    except OSError:
        return
    if g != _GEN[0]:
        if _GEN[0]:
            _POOL_CACHE.clear()
            _AIR_CACHE.clear()
            _EXISTS.clear()
            _SHOWS[1] = None
            listing_clear()
        _GEN[0] = g


def new_generation():
    """The library changed: every process reads it afresh."""
    clear_cache()
    try:
        with open(GEN_FILE, "w") as f:
            f.write("%.3f" % time.time())
        _GEN[0] = os.path.getmtime(GEN_FILE)
    except (IOError, OSError) as exc:
        log("library.gen: %s" % exc)


def fingerprint():
    """A cheap summary of the video library (shows and their episode counts, the
    newest episode and movie added, totals): a scan or clean that changed nothing
    gives the same value, so it refreshes nothing."""
    import hashlib
    shows = sorted((s.get("title", ""), s.get("episode", 0)) for s in
                   rpc("VideoLibrary.GetTVShows", {"properties": ["title", "episode"]}).get("tvshows", []))

    def newest(method, key):
        r = rpc(method, {"properties": ["dateadded", "file"], "limits": {"start": 0, "end": 1},
                         "sort": {"method": "dateadded", "order": "descending"}})
        items = r.get(key, [])
        return [r.get("limits", {}).get("total", 0)] + ([items[0].get("dateadded"), items[0].get("file")]
                                                         if items else [])
    data = [shows, newest("VideoLibrary.GetEpisodes", "episodes"), newest("VideoLibrary.GetMovies", "movies")]
    return hashlib.md5(json.dumps(data).encode("utf-8")).hexdigest()


def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


CODECS_FILE = os.path.join(PROFILE, "codecs.json")
CHAPTERS_FILE = os.path.join(PROFILE, "chapters.json")
CHAPTER_MODES_FILE = os.path.join(PROFILE, "chapter_shows.json")
_AV1_OK = None
SKIPPED = {}        # resolve key -> titles skipped because the box can't decode them


def av1_blocked():
    """Should AV1 videos be skipped?  Setting: 0 automatic, 1 always skip, 2 always play.
    Automatic asks the Amlogic driver which codecs it decodes in hardware; other
    devices are assumed to cope (PCs, Shield, newer boxes)."""
    mode = setting_int("av1_mode", 0)
    if mode in (1, 2):
        return mode == 1
    global _AV1_OK
    if _AV1_OK is None:
        try:
            with open("/sys/class/amstream/vcodec_profile") as f:
                _AV1_OK = "av1" in f.read().lower()
        except (IOError, OSError):
            _AV1_OK = True
    return not _AV1_OK


def item_codec(it):
    if it.get("codec") is None:
        it["codec"] = durations().codec(it["path"])
    return it["codec"]


def _stream_codec(entry):
    vids = (entry.get("streamdetails") or {}).get("video") or []
    return (vids[0].get("codec") or "").lower() if vids else None


class Durations(object):
    """Persistent cache of probed media durations (path -> seconds)."""

    def __init__(self):
        self.data = load_json(DURATIONS_FILE, {})
        self.dirty = False
        self.lock = threading.Lock()
        self.codecs = load_json(CODECS_FILE, {})
        self.codecs_dirty = False

    def codec(self, path):
        c = self.codecs.get(path)
        if c is None:
            c = probe.video_codec(path)
            self.codecs[path] = c
            self.codecs_dirty = True
        return c

    def get(self, path, probe_if_missing=True):
        d = self.data.get(path)
        if d:
            return d
        if not probe_if_missing:
            return 0
        d = round(probe.duration(path), 2)
        if d > 0:
            self.data[path] = d
            self.dirty = True
        return d

    # Frame rates of the guide's top-half clips (trailers, Extras promos, commercials),
    # measured by the service's background reader: "fps|<path>" -> fps, or minus the
    # reader version (probe.FPS_READER) when no frame rate could be read; a plain 0
    # was saved before versions, so that file is read again by a newer reader.
    # Same file, so every value stays a number for the tools that read durations.json.
    FPS = "fps|"

    def fps(self, path):
        """The measured frame rate, 0 if the file couldn't be read, None if not measured
        yet (or only by a reader that didn't know its container)."""
        v = self.data.get(self.FPS + path)
        if v is None:
            return None
        v = float(v)
        if v <= 0:
            return 0.0 if -v >= probe.FPS_READER else None
        return v

    def set_fps(self, path, fps):
        fps = round(float(fps or 0), 3)
        self.data[self.FPS + path] = fps if fps > 0 else -probe.FPS_READER
        self.dirty = True

    def learn(self, path, seconds):
        if seconds and seconds > 0 and abs(self.data.get(path, 0) - seconds) > 1:
            self.data[path] = round(seconds, 2)
            self.dirty = True

    def save(self):
        with self.lock:
            if self.dirty:
                self.dirty = False
                save_json(DURATIONS_FILE, dict(self.data))
            if self.codecs_dirty:
                self.codecs_dirty = False
                save_json(CODECS_FILE, dict(self.codecs))


DURATIONS = None


def durations():
    global DURATIONS
    if DURATIONS is None:
        DURATIONS = Durations()
    return DURATIONS


def _lib_duration(entry):
    """Real running time of a library item.

    The scraper 'runtime' is the *broadcast* length (a 22 minute sitcom is
    often listed as 30), so it is only a last resort: stream details first,
    then what we probed/learned from the file itself.
    """
    sd = entry.get("streamdetails") or {}
    vids = sd.get("video") or []
    if vids and vids[0].get("duration"):
        return float(vids[0]["duration"])
    d = durations().get(entry.get("file", ""))
    if d:
        return d
    if entry.get("runtime"):
        return float(entry["runtime"])
    return 0


def _episode_item(ep):
    label = ""
    if ep.get("season", -1) >= 0 and ep.get("episode", -1) >= 0:
        label = "S%02dE%02d" % (ep["season"], ep["episode"])
    return {"path": ep["file"], "title": ep.get("showtitle") or ep.get("title", ""),
            "sub": ep.get("title", ""), "label": label, "dur": _lib_duration(ep), "codec": _stream_codec(ep)}


def _movie_item(m):
    title = m.get("title", "")
    if m.get("year"):
        title = "%s (%s)" % (title, m["year"])
    return {"path": m["file"], "title": title, "sub": "", "label": "", "dur": _lib_duration(m),
            "codec": _stream_codec(m)}


# ------------------------------------------------------------- library helpers
def all_tvshows():
    res = rpc("VideoLibrary.GetTVShows", {"properties": ["title", "genre", "year", "episode", "rating"]})
    return res.get("tvshows", [])


def all_movies(props=None):
    res = rpc("VideoLibrary.GetMovies", {"properties": props or ["title", "genre", "year"]})
    return res.get("movies", [])


def episodes_for(tvshowid):
    res = rpc("VideoLibrary.GetEpisodes", {
        "tvshowid": tvshowid, "properties": EP_PROPS,
        "sort": {"method": "episode", "order": "ascending"}})
    eps = [e for e in res.get("episodes", []) if e.get("file")]
    # specials (season 0) last
    eps.sort(key=lambda e: (e.get("season", 0) == 0, e.get("season", 0), e.get("episode", 0)))
    return eps


_EXISTS = {}               # path -> (checked at, exists); folders too.  Cleared with the pools
_STALE_LOGGED = set()


def _exists(path):
    hit = _EXISTS.get(path)
    if hit and time.time() - hit[0] < _POOL_TTL:
        return hit[1]
    try:
        ok = bool(xbmcvfs.exists(path))
    except Exception:
        ok = True                 # can't tell: don't hide it
    _EXISTS[path] = (time.time(), ok)
    return ok


def stale(path):
    """The library lists this file but it isn't there (renamed or deleted, and
    the library not cleaned since), while its folder is: never plan it.  A whole
    folder gone (a drive or share offline) doesn't count - that is the TV's
    missing-file case.  Cached per library generation (or 30 min); logs once."""
    if not path or "://" in path and not path.startswith(("smb://", "nfs://")):
        return False
    if _exists(path):
        return False
    folder = path.replace("\\", "/").rsplit("/", 1)[0] + "/"
    if not folder.strip("/") or not _exists(folder):
        return False
    if path not in _STALE_LOGGED:
        _STALE_LOGGED.add(path)
        log("Library lists a missing file (run Clean library): %s" % path, level=xbmc.LOGWARNING)
    return True


def _dedupe_episodes(eps):
    """The same season + episode listed more than once (an old file name the
    library still has next to the renamed file): keep the entry whose file is
    there, so the episode airs once and never from the missing file.  Only these
    duplicates are checked here; planning checks the episodes it picks (stale)."""
    groups = {}
    for e in eps:
        if e.get("season", -1) >= 0 and e.get("episode", -1) >= 0:
            groups.setdefault((e["season"], e["episode"]), []).append(e)
    drop = set()
    for grp in groups.values():
        files = []
        for e in grp:
            if e["file"] not in files:
                files.append(e["file"])
        if len(files) < 2:
            continue                       # one file listed twice: nothing to choose
        there = [f for f in files if not stale(f)]
        keep = there[0] if there else files[0]
        drop.update(f for f in files if f != keep)
    if not drop:
        return eps
    return [e for e in eps if e["file"] not in drop]


def _series_from_show(show):
    eps = _dedupe_episodes(episodes_for(show["tvshowid"]))
    if not eps:
        return None
    return {"key": "tv:%s" % show["title"], "title": show["title"],
            "episodes": [_episode_item(e) for e in eps]}


def _shows_matching(pred):
    return [s for s in all_tvshows() if pred(s)]


# ------------------------------------------------------------- resolvers
def _resolve_tvshow(src, pool):
    names = src.get("value")
    names = names if isinstance(names, list) else [names]
    wanted = set(n.lower() for n in names if n)
    for s in _shows_matching(lambda s: s["title"].lower() in wanted):
        ser = _series_from_show(s)
        if ser:
            pool["series"].append(ser)


def _resolve_tvgenre(src, pool):
    g = (src.get("value") or "").lower()
    for s in _shows_matching(lambda s: g in [x.lower() for x in s.get("genre", [])]):
        ser = _series_from_show(s)
        if ser:
            pool["series"].append(ser)


def _resolve_tvdecade(src, pool):
    d0 = int(src.get("value", 1980))
    for s in _shows_matching(lambda s: d0 <= int(s.get("year") or 0) < d0 + 10):
        ser = _series_from_show(s)
        if ser:
            pool["series"].append(ser)


def _filtered_shows(field, operator, value):
    res = rpc("VideoLibrary.GetTVShows", {"properties": ["title"],
                                          "filter": {"field": field, "operator": operator, "value": value}})
    return res.get("tvshows", [])


def _filtered_movies(field, operator, value):
    res = rpc("VideoLibrary.GetMovies", {"properties": MOVIE_PROPS,
                                         "filter": {"field": field, "operator": operator, "value": value}})
    return [m for m in res.get("movies", []) if m.get("file")]


def _resolve_by_field(field, operator):
    """Movies AND TV shows sharing a studio / tag / title word."""
    def fn(src, pool):
        vals = src.get("value", "")
        vals = vals if isinstance(vals, list) else [vals]
        what = src.get("what", "both")
        for val in vals:
            if what in ("both", "tv"):
                for s in _filtered_shows(field, operator, val):
                    ser = _series_from_show(s)
                    if ser:
                        pool["series"].append(ser)
            if what in ("both", "movies"):
                for m in _filtered_movies(field, operator, val):
                    pool["singles"].append(_movie_item(m))
    return fn


def _genres_ok(show, not_genres):
    """False when the show has one of these genres (any capitalisation)."""
    if not not_genres:
        return True
    bad = set(g.lower() for g in not_genres)
    return not bad.intersection(g.lower() for g in show.get("genre", []))


def _on_networks(show, wanted):
    return any((x or "").lower() in wanted for x in show.get("studio", []))


def _resolve_network(src, pool):
    """TV shows that aired on a network (Kodi keeps a show's network in its
    Studio field).  Exact name, any capitalisation - "NBC" must not catch MSNBC.
    not_genres on the source: shows with any of those genres are left out."""
    vals = src.get("value") or []
    wanted = set(v.lower() for v in (vals if isinstance(vals, list) else [vals]) if v)
    bad = src.get("not_genres")
    for s in all_tvshows_with("studio", "genre") if bad else all_tvshows_with("studio"):
        if not _on_networks(s, wanted) or not _genres_ok(s, bad):
            continue
        ser = _series_from_show(s)
        if ser:
            pool["series"].append(ser)


def _in_ranges(ch, ranges):
    o = ord(ch)
    return any(a <= o <= b for a, b in ranges)


HANGUL = ((0xAC00, 0xD7A3), (0x1100, 0x11FF), (0x3130, 0x318F), (0xA960, 0xA97F), (0xD7B0, 0xD7FF))
HAN = ((0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0xF900, 0xFAFF), (0x20000, 0x2FA1F))
KANA = ((0x3040, 0x30FF), (0x31F0, 0x31FF), (0xFF66, 0xFF9F))


def in_script(text, scripts):
    """Is a title written in one of these scripts?  "hangul": any Korean letter;
    "han": Chinese characters and no Japanese kana (so not a Japanese title)."""
    text = text or ""
    if "hangul" in scripts and any(_in_ranges(c, HANGUL) for c in text):
        return True
    if "han" in scripts and any(_in_ranges(c, HAN) for c in text) and \
            not any(_in_ranges(c, KANA) for c in text):
        return True
    return False


def _resolve_origtitle(src, pool):
    """TV shows whose original title (Kodi's originaltitle) is in a script:
    Korean and Chinese dramas whatever network the library names (Netflix, Viki...)."""
    scripts = src.get("value") or []
    scripts = scripts if isinstance(scripts, list) else [scripts]
    for s in all_tvshows_with("originaltitle", "genre"):
        if not in_script(s.get("originaltitle"), scripts) or not _genres_ok(s, src.get("not_genres")):
            continue
        ser = _series_from_show(s)
        if ser:
            pool["series"].append(ser)


def station_titles(networks, scripts=None, not_genres=None, studios=None):
    """Titles a station would get: TV shows from its networks or with original
    titles in its scripts, and shows and movies whose studio contains one of
    its studios, minus not_genres.  One library call per kind; files aren't checked."""
    wanted = set(n.lower() for n in networks or [])
    stud = [s.lower() for s in studios or []]

    def by_studio(it):
        return any(b in (x or "").lower() for x in it.get("studio", []) for b in stud)
    out = set()
    for s in all_tvshows_with("studio", "genre", "originaltitle"):
        hit = _on_networks(s, wanted) or by_studio(s) or \
            bool(scripts and in_script(s.get("originaltitle"), scripts))
        if hit and _genres_ok(s, not_genres):
            out.add(s["title"])
    if stud:
        for m in all_movies(["title", "studio", "genre", "year"]):
            if by_studio(m) and _genres_ok(m, not_genres):
                out.add("%s (%s)" % (m["title"], m["year"]) if m.get("year") else m["title"])
    return out


def network_counts():
    """{network as Kodi spells it: number of TV shows}."""
    out = {}
    for s in all_tvshows_with("studio"):
        for x in set(s.get("studio", [])):
            if x:
                out[x] = out.get(x, 0) + 1
    return out


def share(sources, part=None, own=None, not_genres=None):
    """A broadcast network's pool: its share of the sources (see partition),
    plus its own network's shows in full.  not_genres: kept out of the share
    (no cartoons in prime time) - its own shows excepted."""
    pool = resolve(sources)
    if not_genres:
        bad = set(g.lower() for g in not_genres)
        kids = set(s["title"] for s in all_tvshows() if bad & set(g.lower() for g in s.get("genre", [])))
        pool = {"series": [s for s in pool["series"] if s["title"] not in kids], "singles": pool["singles"]}
    pool = partition(pool, part)
    if not own:
        return pool
    mine = resolve(own)
    keys = set(s["key"] for s in pool["series"])
    return {"series": pool["series"] + [s for s in mine["series"] if s["key"] not in keys],
            "singles": pool["singles"]}


def _resolve_movie_titles(src, pool):
    wanted = set(t.lower() for t in (src.get("value") or []))
    for m in all_movies(MOVIE_PROPS):
        if not m.get("file"):
            continue
        it = _movie_item(m)
        if it["title"].lower() in wanted or m.get("title", "").lower() in wanted:
            pool["singles"].append(it)


def all_studios():
    out = {}
    for kind, items in (("tv", all_tvshows_with("studio")), ("movies", all_movies(["title", "studio"]))):
        for it in items:
            for s in it.get("studio", []):
                out.setdefault(s, [0, 0])[0 if kind == "tv" else 1] += 1
    return out


def all_tvshows_with(*props):
    res = rpc("VideoLibrary.GetTVShows", {"properties": ["title"] + list(props)})
    return res.get("tvshows", [])


def tag_counts():
    """{tag: [shows, movies]} - one library call per media type."""
    out = {}
    for idx, items in ((0, all_tvshows_with("tag")), (1, all_movies(["title", "tag"]))):
        for it in items:
            for t in it.get("tag", []):
                out.setdefault(t, [0, 0])[idx] += 1
    return out


def all_tags():
    tags = set()
    for t in ("movies", "tvshows"):
        res = rpc("VideoLibrary.GetTags", {"type": "movie" if t == "movies" else "tvshow"})
        tags.update(x.get("label") for x in res.get("tags", []))
    return sorted(x for x in tags if x)


def _resolve_movies(src, pool):
    rules = []
    if src.get("genre"):
        rules.append({"field": "genre", "operator": "is", "value": src["genre"]})
    if src.get("set"):
        rules.append({"field": "set", "operator": "is", "value": src["set"]})
    if src.get("tag"):
        rules.append({"field": "tag", "operator": "is", "value": src["tag"]})
    yrs = src.get("years")
    if yrs:
        rules.append({"field": "year", "operator": "greaterthan", "value": str(int(yrs[0]) - 1)})
        rules.append({"field": "year", "operator": "lessthan", "value": str(int(yrs[1]) + 1)})
    params = {"properties": MOVIE_PROPS}
    if len(rules) == 1:
        params["filter"] = rules[0]
    elif rules:
        params["filter"] = {"and": rules}
    res = rpc("VideoLibrary.GetMovies", params)
    for m in res.get("movies", []):
        if m.get("file"):
            pool["singles"].append(_movie_item(m))


def _walk(path, exts, depth=0):
    if depth > 6:
        return []
    if not path.endswith(("/", "\\")):
        path += "/"
    try:
        dirs, files = xbmcvfs.listdir(path)
    except Exception:
        return []
    out = [path + f for f in sorted(files, key=natural_key) if f.lower().endswith(exts)]
    for d in sorted(dirs, key=natural_key):
        if d.startswith("."):
            continue
        out.extend(_walk(path + d, exts, depth + 1))
    return out


def _basename(p):
    """The last part of a path, whichever slashes it uses (Windows paths use backslashes)."""
    return tnames.basename(p)


def _file_item(p, show=""):
    """A file Kodi's library doesn't have (clips, folder channels): its NFO's
    <title>, else its cleaned name (titles.py).  show: the folder show it belongs
    to - then the title is the show and sub the episode's own name."""
    name = _basename(p)
    label = ""
    m = re.search(r"[Ss](\d{1,2})[Ee](\d{1,3})", name)
    if m:
        label = "S%02dE%02d" % (int(m.group(1)), int(m.group(2)))
    if show:
        return {"path": p, "title": show, "sub": tnames.episode_title(p, show, log), "label": label,
                "dur": durations().get(p)}
    return {"path": p, "title": tnames.file_title(p, log), "sub": "", "label": label,
            "dur": durations().get(p)}


_SHOWS = [0, None]          # (when, (shared names, {title lower: year})) of the library's shows


def on_air(title):
    """A programme's title as the TV shows it: no trailing '(1993)' (display only),
    except for shows whose names two library shows share ("Doctor Who")."""
    if not title:
        return title or ""
    _check_gen()
    if _SHOWS[1] is None or time.time() - _SHOWS[0] > _POOL_TTL:
        try:
            shows = all_tvshows()
        except Exception:
            shows = []
        _SHOWS[0] = time.time()
        _SHOWS[1] = (tnames.shared_names(s["title"] for s in shows),
                     dict((s["title"].lower(), str(s.get("year") or "")) for s in shows))
    keep, years = _SHOWS[1]
    return tnames.on_air(title, keep, years)


def folder_files(path, exts=VIDEO_EXT):
    return _walk(path, exts)


def _resolve_folder(src, pool):
    path = src.get("path", "")
    mode = src.get("mode", "shows")
    if not path:
        return
    if mode == "shows":
        if not path.endswith("/"):
            path += "/"
        try:
            dirs, files = xbmcvfs.listdir(path)
        except Exception:
            dirs, files = [], []
        for d in sorted(dirs, key=natural_key):
            show = tnames.folder_title(path + d, log)      # tvshow.nfo, else the cleaned folder name
            eps = [_file_item(p, show) for p in _walk(path + d, VIDEO_EXT)]
            eps = [e for e in eps if e["dur"] > 0]
            if eps:
                pool["series"].append({"key": "dir:" + path + d, "title": show, "episodes": eps})
        for f in sorted(files, key=natural_key):
            if f.lower().endswith(VIDEO_EXT):
                it = _file_item(path + f)
                if it["dur"] > 0:
                    pool["singles"].append(it)
    else:
        items = [it for it in (_file_item(p) for p in _walk(path, VIDEO_EXT)) if it["dur"] > 0]
        if mode == "sequential":
            if items:
                pool["series"].append({"key": "seq:" + path, "title": tnames.folder_title(path, log),
                                       "episodes": items})
        else:
            pool["singles"].extend(items)


def _resolve_playlist(src, pool):
    res = rpc("Files.GetDirectory", {"directory": src.get("path", ""), "media": "video",
                                     "properties": EP_PROPS})
    shows = {}
    for f in res.get("files", []):
        if f.get("filetype") == "directory" or not f.get("file"):
            continue
        if f.get("type") == "episode" or f.get("showtitle"):
            it = _episode_item(f)
            shows.setdefault(it["title"], []).append((f.get("season", 0), f.get("episode", 0), it))
        else:
            pool["singles"].append(_movie_item(f))
    for title in sorted(shows, key=natural_key):
        eps = [x[2] for x in sorted(shows[title], key=lambda x: (x[0], x[1]))]
        pool["series"].append({"key": "tv:%s" % title, "title": title, "episodes": eps})


def _resolve_alltv(src, pool):
    for show in all_tvshows():
        ser = _series_from_show(show)
        if ser:
            pool["series"].append(ser)


RESOLVERS = {
    "alltv": _resolve_alltv,
    "tvshow": _resolve_tvshow,
    "network": _resolve_network,
    "origtitle": _resolve_origtitle,
    "tvgenre": _resolve_tvgenre,
    "tvdecade": _resolve_tvdecade,
    "movies": _resolve_movies,
    "folder": _resolve_folder,
    "playlist": _resolve_playlist,
    "studio": _resolve_by_field("studio", "contains"),
    "tag": _resolve_by_field("tag", "is"),
    "keyword": _resolve_by_field("title", "contains"),
    "movie": _resolve_movie_titles,
}


def without(pool, exclude):
    """Copy of a pool minus excluded show/movie titles (case-insensitive)."""
    if not exclude:
        return pool
    ex = set(x.lower() for x in exclude)
    return {"series": [s for s in pool["series"] if s["title"].lower() not in ex],
            "singles": [i for i in pool["singles"] if i["title"].lower() not in ex]}


def titles(pool):
    return [s["title"] for s in pool["series"]] + [i["title"] for i in pool["singles"]]


def _resolve_one(src):
    """Pool for a single source (cached).  Channel pools are merged from these,
    so the one-channel-per-show logic can see where each title came from."""
    _check_gen()
    key = json.dumps(src, sort_keys=True)
    hit = _POOL_CACHE.get(key)
    if hit and time.time() - hit[0] < _POOL_TTL:
        return hit[1]
    pool = {"series": [], "singles": []}
    fn = RESOLVERS.get(src.get("type"))
    if fn:
        try:
            fn(src, pool)
        except Exception as exc:  # never let one bad source kill the channel
            log("Source %s failed: %s" % (src, exc))
    series, seen = [], set()
    for ser in pool["series"]:
        if ser["key"] in seen:
            continue
        seen.add(ser["key"])
        ser["episodes"] = [e for e in ser["episodes"] if e["dur"] > 0]
        if ser["episodes"]:
            series.append(ser)
    singles, seen_paths = [], set()
    for i in pool["singles"]:
        if i["dur"] > 0 and i["path"] not in seen_paths:
            seen_paths.add(i["path"])
            singles.append(i)
    skipped = []
    if av1_blocked():
        for ser in series:
            keep = [e for e in ser["episodes"] if item_codec(e) != "av1"]
            if len(keep) != len(ser["episodes"]):
                skipped.append("%s (%d)" % (ser["title"], len(ser["episodes"]) - len(keep)))
            ser["episodes"] = keep
        series = [ser for ser in series if ser["episodes"]]
        keep = [i for i in singles if item_codec(i) != "av1"]
        skipped += [i["title"] for i in singles if i not in keep]
        singles = keep
        if skipped:
            log("Skipping AV1 videos this device can't decode: %s" % ", ".join(skipped[:20]))
    SKIPPED[key] = skipped
    pool = {"series": series, "singles": singles}
    durations().save()
    _POOL_CACHE[key] = (time.time(), pool)
    return pool


def resolve(sources):
    """Resolve a list of sources into one pool (cached for a while)."""
    _check_gen()
    key = json.dumps(sources, sort_keys=True)
    hit = _POOL_CACHE.get(key)
    if hit and time.time() - hit[0] < _POOL_TTL:
        return hit[1]
    series, singles, seen, seen_paths, skipped = [], [], set(), set(), []
    for src in sources or []:
        one = _resolve_one(src)
        skipped += SKIPPED.get(json.dumps(src, sort_keys=True), [])
        for ser in one["series"]:
            if ser["key"] not in seen:
                seen.add(ser["key"])
                series.append(ser)
        for it in one["singles"]:
            if it["path"] not in seen_paths:
                seen_paths.add(it["path"])
                singles.append(it)
    SKIPPED[key] = skipped
    pool = {"series": series, "singles": singles}
    _POOL_CACHE[key] = (time.time(), pool)
    return pool


def partition(pool, part, min_each=2):
    """One network's share of a pool: part = [i, n] deals the titles out like
    cards (sorted by title, every n-th from i), so n networks each get their
    own shows.  Too few titles to go round (fewer than min_each apiece): all
    of them, and the clash rules keep networks from airing one at once."""
    if not part:
        return pool
    i, n = int(part[0]), max(1, int(part[1]))

    def deal(items):
        if len(items) < n * min_each:
            return items
        ranked = sorted(items, key=lambda x: (x["title"].lower(), x.get("key", x.get("path", ""))))
        mine = set(id(x) for x in ranked[i % n::n])
        return [x for x in items if id(x) in mine]
    return {"series": deal(pool["series"]), "singles": deal(pool["singles"])}


def keep_titles(pool, allowed):
    """Copy of a pool limited to titles for which allowed(title_lower) is True."""
    return {"series": [s for s in pool["series"] if allowed(s["title"].lower(), False)],
            "singles": [i for i in pool["singles"] if allowed(i["title"].lower(), True)]}


def filler_pool(path):
    """Commercials / bumps from a folder: list of {path, dur}."""
    if not path:
        return []
    _check_gen()
    key = "filler:" + path
    hit = _POOL_CACHE.get(key)
    if hit and time.time() - hit[0] < _POOL_TTL:
        return hit[1]
    out = []
    skip_av1 = av1_blocked()
    for p in _walk(path, VIDEO_EXT):
        d = durations().get(p)
        if 0 < d <= 600 and not (skip_av1 and durations().codec(p) == "av1") and not is_bad(p):
            out.append({"path": p, "dur": d, "title": _file_item(p)["title"]})
    durations().save()
    _POOL_CACHE[key] = (time.time(), out)
    return out


def filler_report(path):
    """(usable durations, unreadable paths, too-long paths, AV1 paths) for a clip folder."""
    ok, bad, long_, av1 = [], [], [], []
    skip_av1 = av1_blocked()
    for p in _walk(path, VIDEO_EXT):
        d = durations().get(p)
        if skip_av1 and durations().codec(p) == "av1":
            av1.append(p)
        elif d <= 0:
            bad.append(p)
        elif d > 600:
            long_.append(p)
        else:
            ok.append(d)
    durations().save()
    return ok, bad, long_, av1


# ------------------------------------------------------------- unplayable files
BAD_FILE = os.path.join(PROFILE, "unplayable.json")
BAD_RETRY = 3 * 86400        # give a bad file another chance after 3 days (it may have been fixed)
_BAD = None


def _bad():
    global _BAD
    if _BAD is None:
        data = load_json(BAD_FILE, {})
        _BAD = data if isinstance(data, dict) else {}
    return _BAD


def mark_bad(path, reason=""):
    """A file Kodi couldn't open: keep it off the schedule for a few days."""
    _bad()[path] = {"at": time.time(), "why": reason}
    try:
        save_json(BAD_FILE, _bad())
    except Exception as exc:
        log("unplayable save: %s" % exc)


def is_bad(path):
    hit = _bad().get(path)
    return bool(hit) and time.time() - float(hit.get("at") or 0) < BAD_RETRY


def bad_files():
    """[(path, when, reason)] of files currently kept off the air."""
    return sorted(((p, v.get("at", 0), v.get("why", "")) for p, v in _bad().items() if is_bad(p)),
                  key=lambda x: -x[1])


def forget_bad():
    global _BAD
    _BAD = {}
    try:
        save_json(BAD_FILE, {})
    except Exception:
        pass


def clear_cache():
    _POOL_CACHE.clear()
    _AIR_CACHE.clear()
    _EXISTS.clear()
    listing_clear()
    from . import seasons          # holiday matches follow library changes too
    seasons.clear_cache()


# ------------------------------------------------------------- movie Extras
# Kodi's convention: a folder named 'Extras' next to the movie's file, or in
# VIDEO_TS / BDMV for disc rips.  Movies only.  Read-only: listdir, Stat and the
# probe's header reads; listing and probing happen only in the background
# (extras_refresh), Check extras just reads the cache.
EXTRAS_FILE = os.path.join(PROFILE, "extras.json")
EXTRAS_RECHECK = 6 * 3600           # look at a folder's dates at most this often
EXTRAS_RELIST = 7 * 86400           # relist anyway when the dates can't be read
_NO_FS = ("plugin://", "http://", "https://", "pvr://", "rtmp", "rtsp", "upnp://", "videodb://")
_DISC_DIRS = ("VIDEO_TS", "BDMV")


def _psep(p):
    return "\\" if "\\" in p and "/" not in p.split("://", 1)[-1] else "/"


def _pdir(p):
    """Parent folder, with its trailing separator ('' at the top)."""
    s = _psep(p)
    p = p.rstrip("/\\")
    i = p.rfind(s)
    return p[:i + 1] if i >= 0 else ""


def _pname(p):
    return p.rstrip("/\\").split(_psep(p))[-1]


def movie_folders(path):
    """(movie folder, disc folder or '') for a library movie's file."""
    if path.startswith("stack://"):
        path = path[8:].split(" , ")[0]
    d = _pdir(path)
    if _pname(d).upper() == "STREAM" and _pname(_pdir(d)).upper() == "BDMV":
        d = _pdir(d)
    if _pname(d).upper() in _DISC_DIRS:
        return _pdir(d), d
    return d, ""


def _mtime(p):
    for q in (p, p.rstrip("/\\")):
        try:
            t = int(xbmcvfs.Stat(q).st_mtime())
            if t:
                return t
        except Exception:
            pass
    return 0


def _find_extras(folder):
    try:
        dirs, _files = xbmcvfs.listdir(folder)
    except Exception:
        return ""
    for d in dirs:
        if d.lower() == "extras":
            return folder + d + _psep(folder)
    return ""


def _list_extras(top):
    """(files relative to top with '/', {relative folder: mtime})."""
    files, dates = [], {}

    def walk(path, rel, depth):
        dates[rel] = _mtime(path)
        try:
            dirs, names = xbmcvfs.listdir(path)
        except Exception:
            return
        files.extend(rel + n for n in sorted(names, key=natural_key) if n.lower().endswith(VIDEO_EXT))
        if depth >= 4:
            return
        for d in sorted(dirs, key=natural_key):
            if d.startswith(".") or d.upper() in _DISC_DIRS:      # no disc structures inside Extras
                continue
            walk(path + d + _psep(path), rel + d + "/", depth + 1)

    walk(top, "", 0)
    return files, dates


def _extras_movies():
    """{movie folder: [movie, ...]} for every library movie on a file system,
    leaving out anything that sits inside an Extras folder itself."""
    out = {}
    for m in all_movies(["file", "title", "year"]):
        f = m.get("file") or ""
        if not f or f.lower().startswith(_NO_FS) or "extras" in [x.lower() for x in re.split(r"[\/]", f)[:-1]]:
            continue
        folder, disc = movie_folders(f)
        if folder:
            m["disc"] = disc
            out.setdefault(folder, []).append(m)
    return out


def _extras_fresh(entry, folder, now, recheck=False):
    if not entry:
        return False
    if not recheck and now - entry.get("checked", 0) < EXTRAS_RECHECK:
        return True
    base = dict(entry.get("base") or {})
    cur = {p: _mtime(p) for p in base}
    if base and all(cur.values()) and cur == base:
        top = entry.get("extras")
        dates = entry.get("dates") or {}
        now_dates = {r: _mtime(top + r.replace("/", _psep(top))) for r in dates} if top else {}
        if all(now_dates.values()) and now_dates == dates:
            entry["checked"] = now
            return True
    elif not all(cur.values()) and now - entry.get("listed", 0) < EXTRAS_RELIST:
        entry["checked"] = now
        return True
    return False


EXTRAS_UNREADABLE_RETRY = 3 * 86400  # a file whose length couldn't be read is tried again after this


EXTRAS_LAST = {"changed": 0}           # folders whose list of extras changed in the last scan


def extras_refresh(abort=lambda: False, progress=None, retry=False, dates=False):
    """Find and list movie Extras folders that changed, then measure the files
    not measured yet.  Runs in the background while the TV is off, or from
    'Look for movie extras' (progress(fraction, line) drives its dialog; retry=True also
    tries again the files whose length couldn't be read).  Saves as it goes, so
    a cancelled or interrupted run carries on next time.  Returns True when it
    finished.  dates=True: look at every Extras folder's dates now, not just the
    ones not looked at for EXTRAS_RECHECK (after a library scan or clean: a clip
    added to an Extras folder changes that folder's date, not the movie's)."""
    home = _home()
    busy = home.getProperty(_X_BUSY)
    if busy and time.time() - float(busy or 0) < 900:
        log("extras: a scan is already running")
        return False
    home.setProperty(_X_BUSY, str(time.time()))
    stop = abort
    abort = lambda: stop() or home.getProperty(_X_STOP) == "1"
    try:
        return _extras_refresh(abort, progress, retry, dates)
    finally:
        home.clearProperty(_X_BUSY)


_X_BUSY = "cablebox42.extras_busy"      # one scan at a time (the service and Look for movie extras are separate)
_X_STOP = "cablebox42.extras_stop"


def _home():
    import xbmcgui
    return xbmcgui.Window(10000)


def extras_take_over(wait=15.0):
    """Look for movie extras: ask a background scan that's running to stop, and wait for it."""
    home = _home()
    if not home.getProperty(_X_BUSY):
        return True
    home.setProperty(_X_STOP, "1")
    mon = xbmc.Monitor()
    end = time.time() + wait
    while home.getProperty(_X_BUSY) and time.time() < end:
        if mon.waitForAbort(0.2):
            break
    home.clearProperty(_X_STOP)
    return not home.getProperty(_X_BUSY)


def _extras_refresh(abort, progress, retry, dates=False):
    t0 = time.time()
    cache = load_json(EXTRAS_FILE, {})
    folders = cache.get("folders") or {}
    unreadable = cache.get("unreadable") or {}
    movies = _extras_movies()
    listed = changed = 0
    for n, (folder, ms) in enumerate(movies.items()):
        if abort():
            break
        if progress and n % 10 == 0:
            progress(0.3 * n / max(1, len(movies)), "list", n, len(movies))
        now = time.time()
        entry = folders.get(folder)
        if _extras_fresh(entry, folder, now, recheck=retry or dates):   # dates: every folder's dates, now
            continue
        disc = ms[0].get("disc", "")
        base = {folder: _mtime(folder)}
        top = _find_extras(folder)
        if not top and disc:
            base[disc] = _mtime(disc)
            top = _find_extras(disc)
        files, fdates = _list_extras(top) if top else ([], {})
        if not entry or entry.get("files") != files or entry.get("extras") != top:
            changed += 1
        folders[folder] = {"extras": top, "files": files, "dates": fdates, "base": base,
                           "listed": now, "checked": now}
        listed += 1
    for gone in [f for f in folders if f not in movies]:
        del folders[gone]
        changed += 1
    EXTRAS_LAST["changed"] = changed
    cache["folders"] = folders
    save_json(EXTRAS_FILE, cache)
    t1 = time.time()
    durs = durations()
    todo = []
    for folder, entry in folders.items():
        top = entry.get("extras")
        if not top or len(movies.get(folder) or []) != 1:
            continue
        for rel in entry.get("files") or []:
            p = top + rel.replace("/", _psep(top))
            if durs.data.get(p):
                continue
            if not retry and t1 - unreadable.get(p, 0) < EXTRAS_UNREADABLE_RETRY:
                continue
            todo.append(p)
    probed = 0
    for p in todo:
        if abort():
            break
        if progress:
            progress(0.3 + 0.7 * probed / max(1, len(todo)), "measure", probed, len(todo))
        if durs.get(p) > 0:
            unreadable.pop(p, None)
        else:
            unreadable[p] = time.time()
        probed += 1
        if probed % 20 == 0:
            durs.save()
    durs.save()
    present = set(top + r.replace("/", _psep(top)) for e in folders.values() if e.get("extras")
                  for top in (e["extras"],) for r in e.get("files") or [])
    cache["unreadable"] = dict((p, t) for p, t in unreadable.items() if p in present)
    save_json(EXTRAS_FILE, cache)
    done = probed == len(todo) and not abort()
    _AIR_CACHE.clear()
    log("extras: %d movie folders, %d listed (%d changed) in %.1f s, %d of %d new files measured in %.1f s%s" % (
        len(movies), listed, changed, t1 - t0, probed, len(todo), time.time() - t1, "" if done else " (stopped early)"),
        level=xbmc.LOGINFO)
    return done


def extras_unreadable():
    """Paths of Extras whose length couldn't be read (from the cache)."""
    return set(load_json(EXTRAS_FILE, {}).get("unreadable") or {})


def extras_scanned():
    """True once the Extras folders have been looked through (cache only, cheap)."""
    return bool(load_json(EXTRAS_FILE, {}).get("folders"))


def extras_status():
    """(scanned, measured, total, unreadable) over the files of every movie's own
    Extras folder, from the cache only: scanned is False until the folders have
    been looked through once."""
    cache = load_json(EXTRAS_FILE, {})
    folders = cache.get("folders") or {}
    unreadable = cache.get("unreadable") or {}
    measured = total = bad = 0
    for f in extras_films():
        if f["shared"]:
            continue
        for _rel, p, d in f["files"]:
            total += 1
            if d:
                measured += 1
            elif p in unreadable:
                bad += 1
    return bool(folders), measured, total, bad


def extras_films():
    """What the cache knows, for Check extras: [{title, year, folder, extras,
    shared, files: [(relative path, full path, seconds or 0)]}], films with
    an Extras folder only.  Never lists or probes."""
    folders = (load_json(EXTRAS_FILE, {}).get("folders") or {})
    if not folders:
        return []
    movies = _extras_movies()
    durs = durations()
    out = []
    for folder, entry in folders.items():
        top = entry.get("extras")
        ms = movies.get(folder) or []
        if not top or not ms:
            continue
        m = ms[0]
        out.append({"title": m.get("title", ""), "year": m.get("year") or "", "folder": folder,
                    "extras": top, "shared": len(ms) > 1,
                    "files": [(r, top + r.replace("/", _psep(top)),
                               durs.get(top + r.replace("/", _psep(top)), probe_if_missing=False))
                              for r in entry.get("files") or []]})
    out.sort(key=lambda f: natural_key(f["title"]))
    return out


_AIR_CACHE = {}
_AIR_TTL = 600


def extras_programme(loose=False):
    """What the Behind the scenes channel can air, from the cache only (never lists
    or probes, so it's safe on a channel change): [{key, title, year, segs:
    [{path, title, dur, group}]}] - each film's qualifying, measured segments in
    block order.  Films whose Extras folder is shared by several movies are left out."""
    hit = _AIR_CACHE.get(bool(loose))
    if hit and time.time() - hit[0] < _AIR_TTL:
        return hit[1]
    from . import extras
    out = []
    for f in extras_films():
        if f["shared"]:
            continue
        segs = []
        for rel, path, dur in f["files"]:
            info = extras.classify(rel, f["title"], f["year"], dur, loose)
            if info["air"] and dur > 0:
                # the clip's own NFO title first (read-only, cached), else extras' cleaned name
                name = tnames.nfo_title(re.sub(r"\.[^./\\]+$", "", path) + ".nfo", log) or info["title"]
                segs.append((info["group"], natural_key(rel), {"path": path, "title": name,
                                                              "dur": float(dur), "group": info["group"]}))
        segs.sort(key=lambda s: (s[0], s[1]))
        if segs:
            out.append({"key": f["folder"], "title": f["title"], "year": f["year"], "segs": [s[2] for s in segs]})
    _AIR_CACHE[bool(loose)] = (time.time(), out)
    return out


# ------------------------------------------------------------- music videos (Boombox)
# Kodi's music videos plus every other video file in their folders (TheAudioDB
# only adds songs it can match online).  Read-only: listdir, Stat and the probe's
# header reads.  Files are measured (length, frame rate, audio, tags) only in
# the background (musicvideos_refresh); resolving reads the cache.
MV_PROPS = ["file", "title", "artist", "album", "year", "studio", "runtime", "streamdetails"]
MVINFO_FILE = os.path.join(PROFILE, "musicvideos.json")
MV_UNREADABLE_RETRY = 86400        # a file that couldn't be read is tried again a day later
MV_SKIPPED = {}            # source key -> [(file name, reason)] for the log and Check music videos
_MV_CACHE = [None, 0]


def _mv_cache():
    """The measurements (re-read when the service has written new ones)."""
    try:
        mt = os.path.getmtime(MVINFO_FILE)
    except OSError:
        mt = 0
    if _MV_CACHE[0] is None or mt != _MV_CACHE[1]:
        c = load_json(MVINFO_FILE, {})
        c.setdefault("files", {})
        c.setdefault("unreadable", {})
        _MV_CACHE[0], _MV_CACHE[1] = c, mt
    return _MV_CACHE[0]


def _mv_save(cache):
    save_json(MVINFO_FILE, cache)
    try:
        _MV_CACHE[1] = os.path.getmtime(MVINFO_FILE)
    except OSError:
        pass


def _mv_key(p):
    return p.replace("\\", "/").lower()


def all_musicvideos():
    res = rpc("VideoLibrary.GetMusicVideos", {"properties": MV_PROPS})
    return [m for m in res.get("musicvideos", []) if m.get("file") and not m["file"].startswith("stack://")]


def musicvideo_folders(items):
    """The folders Kodi's music videos live in (a folder inside another one
    listed is covered by it)."""
    dirs = sorted(set(_pdir(m["file"]) for m in items if not m["file"].lower().startswith(_NO_FS)) - {""},
                  key=len)
    out = []
    for d in dirs:
        if not any(_mv_key(d).startswith(_mv_key(o)) for o in out):
            out.append(d)
    return out


def _mv_walk(top, depth=0):
    """Video files under a folder and its subfolders (no hidden folders, no disc structures)."""
    if depth > 6:
        return []
    sep = _psep(top)
    if not top.endswith(("/", "\\")):
        top += sep
    try:
        dirs, files = xbmcvfs.listdir(top)
    except Exception:
        return []
    out = [top + f for f in sorted(files, key=natural_key) if f.lower().endswith(VIDEO_EXT)]
    for d in sorted(dirs, key=natural_key):
        if d.startswith(".") or d.upper() in _DISC_DIRS:
            continue
        out.extend(_mv_walk(top + d + sep, depth + 1))
    return out


def _under(path, folders):
    k = _mv_key(path)
    return any(k.startswith(_mv_key(f if f.endswith(("/", "\\")) else f + _psep(f))) for f in folders)


def musicvideo_files(src):
    """(library items {key: entry}, folders, [paths]) for a Music videos source:
    the library's music videos (only those in the chosen folders when the viewer
    picked folders) and every other video file in those folders."""
    lib = all_musicvideos()
    folders = list(src.get("paths") or [])
    if folders:
        lib = [m for m in lib if _under(m["file"], folders)]
    else:
        folders = musicvideo_folders(lib)
    by_key = dict((_mv_key(m["file"]), m) for m in lib)
    on_disk = {}
    for f in folders:
        for p in _mv_walk(f):
            on_disk.setdefault(_mv_key(p), p)
    # the name on disk wins: a file renamed after the library scan ('9 to 5' -> '9 To 5')
    # still opens on Windows, but not through every part of Kodi
    paths = [on_disk.get(_mv_key(m["file"]), m["file"]) for m in lib]
    paths += [p for k, p in on_disk.items() if k not in by_key]
    return by_key, folders, paths


def musicvideo_survey(paths=None):
    """For Build my lineup: how many music videos there are, without measuring
    anything.  {"total", "lib", "extra", "folders"}."""
    from . import musicvideos as MV
    src = {"type": "musicvideos"}
    if paths:
        src["paths"] = list(paths)
    lib, folders, files = musicvideo_files(src)
    cache = _mv_cache()["files"]
    n_lib = n_extra = 0
    for p in files:
        c = cache.get(p) or {}
        if MV.skip_reason(p, c.get("d"), c.get("a")):
            continue
        if _mv_key(p) in lib:
            n_lib += 1
        else:
            n_extra += 1
    return {"total": n_lib + n_extra, "lib": n_lib, "extra": n_extra, "folders": folders}


def _lib_has_audio(entry):
    sd = (entry or {}).get("streamdetails") or {}
    if not sd.get("video"):
        return None                  # Kodi hasn't read the file's streams yet
    return bool(sd.get("audio"))


def _resolve_musicvideos(src, pool):
    from . import musicvideos as MV
    lib, _folders, files = musicvideo_files(src)
    cache = _mv_cache()["files"]
    durs = durations()
    skipped = []
    for p in files:
        entry = lib.get(_mv_key(p))
        c = cache.get(p) or {}
        dur = (_lib_duration(entry) if entry else 0) or c.get("d") or durs.get(p, probe_if_missing=False)
        audio = c.get("a") if c.get("a") is not None else _lib_has_audio(entry)
        why = MV.skip_reason(p, dur, audio)
        if why:
            skipped.append((_pname(p), why))
            continue
        if not dur:
            continue                 # not measured yet: airs once the background has read it
        info = MV.merge(entry, c.get("t"), p)
        pool["singles"].append({"path": p, "title": MV.label(info), "sub": "", "label": "", "dur": float(dur),
                                "codec": (_stream_codec(entry) if entry else None) or c.get("c") or "",
                                "fps": c.get("f") or 0, "mv": info})
    key = json.dumps(src, sort_keys=True)
    if skipped and MV_SKIPPED.get(key) != skipped:
        log("Music videos skipped: %s" % "; ".join("%s (%s)" % s for s in skipped[:40]), level=xbmc.LOGINFO)
    MV_SKIPPED[key] = skipped


RESOLVERS["musicvideos"] = _resolve_musicvideos


def mv_cache_entry(path):
    """The measurements of one file: {"d", "f", "a", "c", "t"}, or {}."""
    return _mv_cache()["files"].get(path) or {}


def mv_measured():
    """True once any music video has been measured (the Boombox schedule rebuilds
    once when the first ones arrive)."""
    return bool(_mv_cache()["files"])


def _mv_sources():
    from . import channels as C
    out = []
    for c in C.load():
        for s in c.get("sources", []):
            if s.get("type") == "musicvideos" and s not in out:
                out.append(s)
    return out


def _size(p):
    try:
        return int(xbmcvfs.Stat(p).st_size())
    except Exception:
        return 0


def musicvideos_refresh(abort=lambda: False, pause=None, sources=None, recheck=False):
    """Measure the music videos not measured yet: length, frame rate, audio
    track and tags in one read-only pass per file (recheck: also files whose
    size changed).  Runs in the background; saves as it goes.  Returns the
    number measured."""
    srcs = sources if sources is not None else _mv_sources()
    if not srcs:
        return 0
    t0 = time.time()
    cache = _mv_cache()
    files, bad = cache["files"], cache["unreadable"]
    todo, present = [], set()
    for src in srcs:
        _lib, _f, paths = musicvideo_files(src)
        for p in paths:
            if p in present:
                continue
            present.add(p)
            c = files.get(p)
            if c and (not recheck or c.get("s") == _size(p)) and \
                    (c.get("f") or c.get("r", 1) >= probe.FPS_READER):
                continue                 # (no frame rate from an older reader: read it again)
            if not c and t0 - bad.get(p, 0) < MV_UNREADABLE_RETRY:
                continue
            todo.append(p)
    done = 0
    durs = durations()
    for p in todo:
        if abort():
            break
        info = probe.media_info(p)
        if not (info and info.get("dur")) and not abort():
            xbmc.sleep(500)              # a file that was busy a moment ago (copying, scanning): once more
            info = probe.media_info(p)
        if info and info.get("dur"):
            files[p] = {"s": _size(p), "d": round(info["dur"], 2), "f": info.get("fps") or 0,
                        "a": info.get("audio"), "c": info.get("codec") or "", "t": info.get("tags") or {},
                        "r": probe.FPS_READER}
            durs.learn(p, info["dur"])
            bad.pop(p, None)
        else:
            files.pop(p, None)
            bad[p] = time.time()
        done += 1
        if done % 25 == 0:
            _mv_save(cache)
            durs.save()
        if pause:
            pause()
    gone = [p for p in list(files) + list(bad) if p not in present]
    if todo or gone:
        if done == len(todo):        # a complete pass: forget files that are gone or renamed
            for p in gone:
                files.pop(p, None)
                bad.pop(p, None)
        _mv_save(cache)
        durs.save()
        _POOL_CACHE.clear()
        log("music videos: %d of %d new files measured in %.1f s%s" % (
            done - len([p for p in todo if p in bad]), len(todo), time.time() - t0,
            "; couldn't read: " + ", ".join(_pname(p) for p in todo if p in bad) if any(p in bad for p in todo) else ""),
            level=xbmc.LOGINFO)
    return done


def musicvideos_report(src):
    """For Check music videos (cache only): {"airs": [items], "skipped":
    [(file name, why)], "waiting": not measured yet, "unreadable": [file names],
    "lib": from the library, "total": files found, "folders": [...]}."""
    pool = _resolve_one(src)
    lib, folders, paths = musicvideo_files(src)
    cache = _mv_cache()
    airs = set(it["path"] for it in pool["singles"])
    skipped = list(MV_SKIPPED.get(json.dumps(src, sort_keys=True), []))
    names = set(n for n, _w in skipped)
    waiting = [p for p in paths if p not in airs and _pname(p) not in names and p not in cache["unreadable"]]
    return {"airs": pool["singles"], "skipped": skipped, "waiting": len(waiting),
            "unreadable": [_pname(p) for p in paths if p in cache["unreadable"]],
            "lib": len(lib), "total": len(paths), "folders": folders}


# ------------------------------------------------------------------ chapter marks
# Commercial breaks at chapter marks (chapters.py): each episode file's chapters are
# read once, in the background (chapters_refresh, service), and kept in
# chapters.json - "no chapters" too, so nothing is read twice.  Planning only looks
# here: a file not read yet gets today's timed breaks, the next planning the marks.
class Chapters(object):
    def __init__(self):
        self.data = load_json(CHAPTERS_FILE, {}) or {}
        self.dirty = False
        self.lock = threading.Lock()
        self._info = {}

    def known(self, path):
        return path in self.data

    def raw(self, path):
        return self.data.get(path)

    def info(self, path):
        """chapters.analyze() of a file already read (cached), else None."""
        d = self.data.get(path)
        if not d or not d.get("ch"):
            return None if not d else {"v": "none", "m": [], "cr": None, "why": "no chapters"}
        hit = self._info.get(path)
        if hit is None:
            from . import chapters as C
            hit = C.analyze(d.get("d") or 0, d.get("ch"))
            self._info[path] = hit
        return hit

    def read(self, path):
        """Read one file's chapters now (background only).  False if unreadable."""
        r = probe.chapters(path)
        with self.lock:
            # unreadable: noted with the time, tried again after a few days
            self.data[path] = {"d": r["dur"], "ch": r["ch"]} if r else {"x": int(time.time())}
            self._info.pop(path, None)
            self.dirty = True
        return r is not None

    def save(self):
        """Written merged with the file as it is now: the service's reader and Check
        chapters' Read now (another Kodi process) both add to it."""
        with self.lock:
            if not self.dirty:
                return
            self.dirty = False
            disk = load_json(CHAPTERS_FILE, {}) or {}
            for k, v in disk.items():
                self.data.setdefault(k, v)
            data = dict(self.data)
        save_json(CHAPTERS_FILE, data)


CHAPTERS = None
_CHAPTERS_SEEN = {"mtime": 0.0, "checked": 0.0}


def chapter_cache():
    """The chapters cache; reloaded when another Kodi process (the service's
    background reader) has written chapters.json since (looked at once a minute)."""
    global CHAPTERS
    now = time.time()
    if CHAPTERS is not None and now - _CHAPTERS_SEEN["checked"] > 60 and not CHAPTERS.dirty:
        _CHAPTERS_SEEN["checked"] = now
        try:
            m = os.path.getmtime(CHAPTERS_FILE)
        except OSError:
            m = 0.0
        if m != _CHAPTERS_SEEN["mtime"]:
            CHAPTERS = None
    if CHAPTERS is None:
        CHAPTERS = Chapters()
        _CHAPTERS_SEEN["checked"] = now
        try:
            _CHAPTERS_SEEN["mtime"] = os.path.getmtime(CHAPTERS_FILE)
        except OSError:
            _CHAPTERS_SEEN["mtime"] = 0.0
    return CHAPTERS


def chapter_reload():
    """Saved, then read back from chapters.json (another process added to it)."""
    global CHAPTERS
    if CHAPTERS is not None:
        CHAPTERS.save()
    CHAPTERS = None


def chapter_info(path):
    """The file's chapter verdict if it has been read (planning never reads files)."""
    try:
        return chapter_cache().info(path)
    except Exception as exc:
        log("chapters %s: %s" % (path, exc))
        return None


def chapter_mode(title):
    """A show's own choice in Tools > Check chapters: "auto" (default), "always", "never"."""
    return (load_json(CHAPTER_MODES_FILE, {}) or {}).get(title, "auto")


def set_chapter_mode(title, mode):
    d = load_json(CHAPTER_MODES_FILE, {}) or {}
    if mode == "auto":
        d.pop(title, None)
    else:
        d[title] = mode
    save_json(CHAPTER_MODES_FILE, d)


def _share(path):
    """The share or drive a file lives on (smb://host/share, E:, /mnt/disk)."""
    p = (path or "").replace("\\", "/")
    if "://" in p:
        scheme, rest = p.split("://", 1)
        return scheme + "://" + "/".join(rest.split("/")[:2]).lower()
    if len(p) > 1 and p[1] == ":":
        return p[:2].lower()
    return "/".join(p.split("/")[:3])


CHAPTER_RETRY = 3 * 86400
CHAPTER_SOON = 6 * 3600                  # "airs soon": in the next 6 hours
_EP_FILES = {"t": 0.0, "files": []}      # the library's episode files (10 min)
_PLANNED = {"sig": None, "t": 0.0, "list": []}
CHAPTERS_NEW = {"n": 0, "first": 0.0}   # planned files read since the last re-plan (service), the first's time


def planned_files(now=None):
    """[(airs at, file)] of every programme still to air in the planned schedules,
    soonest first, each file once.  Re-read only when a schedule file changed
    (looked at once a minute at most)."""
    now = now or time.time()
    if now - _PLANNED["t"] < 60 and _PLANNED["sig"] is not None:
        return [x for x in _PLANNED["list"] if x[2] > now]
    _PLANNED["t"] = now
    from .kodiutil import SCHEDULE_DIR
    try:
        names = sorted(f for f in os.listdir(SCHEDULE_DIR) if f.endswith(".json"))
    except OSError:
        names = []
    sig = []
    for f in names:
        try:
            sig.append((f, os.path.getmtime(os.path.join(SCHEDULE_DIR, f))))
        except OSError:
            pass
    if sig != _PLANNED["sig"]:
        first = {}
        for f, _m in sig:
            for e in (load_json(os.path.join(SCHEDULE_DIR, f), {}) or {}).get("entries", []):
                pth, end = e.get("p"), e.get("e", 0)
                if e.get("k") != "show" or not pth or end <= now:
                    continue
                if pth not in first or e.get("s", 0) < first[pth][0]:
                    first[pth] = (e.get("s", 0), pth, end)
        _PLANNED.update(sig=sig, list=sorted(first.values()))
    return [x for x in _PLANNED["list"] if x[2] > now]


def chapters_todo(now=None):
    """(planned, rest): the episode files whose chapters aren't read yet - the ones
    in the planned schedules as [(airs at, file)] soonest first, then the rest of
    the library in its own order."""
    cache = chapter_cache()
    now = now or time.time()
    if now - _EP_FILES["t"] > 600:
        res = rpc("VideoLibrary.GetEpisodes", {"properties": ["file"]})
        _EP_FILES.update(t=now, files=[e.get("file") or "" for e in res.get("episodes", []) or []])

    def need(f):
        if not f or f.startswith(("stack://", "plugin://")):
            return False
        d = cache.raw(f)
        return d is None or ("x" in d and now - d["x"] > CHAPTER_RETRY)
    eps = set(_EP_FILES["files"])
    planned = [(s, f) for s, f, _e in planned_files(now) if f in eps and need(f)]
    seen = set(f for _s, f in planned)
    return planned, [f for f in _EP_FILES["files"] if f not in seen and need(f)]


def chapters_status():
    """(read, total): the library's episode files whose chapters have been read."""
    planned, rest = chapters_todo()
    total = len([f for f in _EP_FILES["files"] if f and not f.startswith(("stack://", "plugin://"))])
    return max(0, total - len(planned) - len(rest)), total


def _readable_counts(cache, f):
    """True when a planned file's chapters change its breaks (a re-plan is worth it)."""
    info = cache.info(f)
    return bool(info and (info.get("v") in ("act", "dense") or info.get("cr") is not None))


class ChapterReader(object):
    """The background chapter reader's queue and pace (the service's thread).

    Pace from measured read times: about one file a second to start, faster while
    reads stay fast (up to 5 a second idle), at once much slower when one is slow
    (a busy disk, a drive waking up, a slow share), then creeping back.  The TV on:
    the planned episodes airing in the next 6 hours, soonest first, at most one a
    second; the rest of the library then too, never from the share that's playing."""
    FAST = 0.15               # s: a read this quick lets the pace speed up
    SLOW = 1.0                # s: a read this slow (or 5x the usual) backs off at once
    MIN_IDLE, MIN_TV, MAX_WAIT = 0.2, 1.0, 60.0

    def __init__(self):
        self.wait = 1.0
        self.avg = None
        self.queue, self.soon, self.built = [], set(), 0.0
        self.stats = {"n": 0, "secs": 0.0, "since": time.time()}
        self.left = 0

    def _build(self, now):
        planned, rest = chapters_todo(now)
        self.soon = set(f for s, f in planned if s <= now + CHAPTER_SOON)
        self.queue = [f for _s, f in planned] + rest
        self.left = len(self.soon)
        self.built = now

    def next(self, tv_on, playing=""):
        """The next file to read, or None (nothing to read now)."""
        now = time.time()
        if not self.queue or now - self.built > 60:
            self._build(now)
        cache = chapter_cache()
        busy = _share(playing) if playing else None
        for i, f in enumerate(self.queue):
            if cache.raw(f) is not None and "x" not in cache.raw(f):
                continue                       # read meanwhile (Read now)
            if tv_on and f not in self.soon and busy and _share(f) == busy:
                continue
            del self.queue[:i + 1]
            return f
        self.queue = []
        return None

    def read(self, f, tv_on):
        """Read one file; returns how long to wait before the next."""
        cache = chapter_cache()
        t0 = time.time()
        cache.read(f)
        took = time.time() - t0
        if f in self.soon:
            self.soon.discard(f)
            self.left = len(self.soon)
            if _readable_counts(cache, f):
                if not CHAPTERS_NEW["n"]:
                    CHAPTERS_NEW["first"] = time.time()
                CHAPTERS_NEW["n"] += 1
        self.stats["n"] += 1
        self.stats["secs"] += took
        slow = took >= self.SLOW or (self.avg is not None and took > 5 * self.avg and took > 0.3)
        if slow:
            self.wait = min(self.MAX_WAIT, max(self.wait * 4, took * 10))
        elif took < self.FAST:
            self.wait *= 0.8
        self.avg = took if self.avg is None else 0.8 * self.avg + 0.2 * took
        self.wait = max(self.MIN_TV if tv_on else self.MIN_IDLE, min(self.MAX_WAIT, self.wait))
        if self.stats["n"] % 50 == 0:
            cache.save()
        return self.wait

    def minute(self, force=False):
        """The once-a-minute summary line (and the cache saved).  True when logged."""
        st, now = self.stats, time.time()
        if not st["n"] or (now - st["since"] < 60 and not force):
            return False
        chapter_cache().save()
        _r, total = chapters_status()
        log("chapters: read %d files in the last %d s (%.3f s a file on average, pace now %.1f a second); "
            "%d planned for the next 6 h and %d others still to read" % (
                st["n"], now - st["since"], st["secs"] / st["n"], 1.0 / self.wait, self.left,
                max(0, total - _r - self.left)), level=xbmc.LOGINFO)
        self.stats = {"n": 0, "secs": 0.0, "since": now}
        return True


def load_too_high():
    """Linux (CoreELEC, LibreELEC, a Pi): the 1-minute load over 0.9 per CPU."""
    try:
        with open("/proc/loadavg") as f:
            load = float(f.read().split()[0])
        return load > 0.9 * (os.cpu_count() or 1)
    except (OSError, ValueError, IndexError):
        return False


def chapters_read_all(abort=lambda: False, progress=None):
    """Check chapters' Read now: every episode file not read yet, the planned ones
    first, as fast as the drive goes; saved as it goes (Cancel keeps what's read).
    Returns (files read, planned files whose breaks change)."""
    cache = chapter_cache()
    planned, rest = chapters_todo()
    todo = [f for _s, f in planned] + rest
    first = set(f for _s, f in planned)
    n = got = 0
    last = time.time()
    for i, f in enumerate(todo):
        if abort():
            break
        cache.read(f)
        n += 1
        if f in first and _readable_counts(cache, f):
            got += 1
        if progress and time.time() - last > 0.2:
            last = time.time()
            progress(i + 1, len(todo))
        if n % 50 == 0:
            cache.save()
    cache.save()
    log("chapters: Read now read %d of %d files" % (n, len(todo)), level=xbmc.LOGINFO)
    return n, got


# ------------------------------------------------------------- guide listings and ratings
# Library data only (never opens a media file): year, content rating, genres,
# subtitle tracks and audio channels of every movie and episode, read once in a
# background thread (paged, so a big library doesn't hold Kodi up) and kept for
# _POOL_TTL.  Sidecar subtitle files: one folder listing per folder asked about,
# also in that thread.  The guide and the rating box never wait for it.
SUB_EXT = (".srt", ".ass", ".ssa", ".sub", ".smi", ".vtt", ".idx", ".sup")
_LISTING = {"t": 0, "files": None, "shows": None, "busy": False, "dirs": {}, "want": set()}
_LISTING_LOCK = threading.Lock()
_PAGE = 1000


def _sd_flags(sd):
    sd = sd or {}
    aud = sd.get("audio") or []
    return bool(sd.get("subtitle")), bool(aud) and max(int(a.get("channels") or 0) for a in aud) >= 2


def _paged(method, key, props):
    out, start = [], 0
    while True:
        r = rpc(method, {"properties": props, "limits": {"start": start, "end": start + _PAGE}})
        items = r.get(key) or []
        out.extend(items)
        total = (r.get("limits") or {}).get("total", 0)
        start += _PAGE
        if not items or start >= total:
            return out
        xbmc.sleep(30)


def _load_listing():
    try:
        shows = {}
        for s in rpc("VideoLibrary.GetTVShows", {"properties": ["mpaa", "genre"]}).get("tvshows", []):
            shows[s["tvshowid"]] = {"mpaa": s.get("mpaa") or "", "genre": s.get("genre") or []}
        files = {}
        for m in _paged("VideoLibrary.GetMovies", "movies", ["file", "year", "mpaa", "genre", "streamdetails"]):
            cc, st = _sd_flags(m.get("streamdetails"))
            if m.get("file"):
                files[m["file"]] = {"kind": "movie", "year": m.get("year") or 0, "mpaa": m.get("mpaa") or "",
                                    "genre": m.get("genre") or [], "cc": cc, "stereo": st}
        for e in _paged("VideoLibrary.GetEpisodes", "episodes", ["file", "tvshowid", "streamdetails"]):
            cc, st = _sd_flags(e.get("streamdetails"))
            sh = shows.get(e.get("tvshowid")) or {}
            if e.get("file"):
                files[e["file"]] = {"kind": "episode", "year": 0, "mpaa": sh.get("mpaa", ""),
                                    "genre": sh.get("genre", []), "cc": cc, "stereo": st}
        with _LISTING_LOCK:
            _LISTING.update(t=time.time(), files=files, shows=shows)
    except Exception as exc:
        log("listing details: %s" % exc)
    _listing_dirs()
    with _LISTING_LOCK:
        _LISTING["busy"] = False


def _listing_dirs():
    """Sidecar subtitles: list each folder asked about once (read-only)."""
    while True:
        with _LISTING_LOCK:
            todo = [d for d in _LISTING["want"] if d not in _LISTING["dirs"]]
            _LISTING["want"] = set()
        if not todo:
            return
        for d in todo[:200]:
            subs = set()
            try:
                _dirs, names = xbmcvfs.listdir(d)
                for n in names:
                    low = n.lower()
                    if low.endswith(SUB_EXT):
                        subs.add(low.rsplit(".", 1)[0])
            except Exception:
                pass
            with _LISTING_LOCK:
                _LISTING["dirs"][d] = subs
            xbmc.sleep(10)


def _listing_kick():
    with _LISTING_LOCK:
        if _LISTING["busy"]:
            return
        stale = _LISTING["files"] is None or time.time() - _LISTING["t"] > _POOL_TTL
        if not stale and not [d for d in _LISTING["want"] if d not in _LISTING["dirs"]]:
            return
        _LISTING["busy"] = True
    t = threading.Thread(target=_load_listing if stale else _listing_dirs_done, name="cb42-listing")
    t.daemon = True
    t.start()


def _listing_dirs_done():
    _listing_dirs()
    with _LISTING_LOCK:
        _LISTING["busy"] = False


def listing_clear():
    with _LISTING_LOCK:
        _LISTING.update(t=0, files=None, dirs={})


def listing_info(path):
    """{kind, year, mpaa, genre, cc, stereo} for a planned file, or None while the
    library data is still being read (or the file isn't in the library).  cc also
    counts a subtitle file next to the video once its folder has been listed."""
    if not path:
        return None
    _check_gen()
    with _LISTING_LOCK:
        files = _LISTING["files"]
        info = files.get(path) if files else None
        folder = _pdir(path) if not any(path.startswith(x) for x in _NO_FS) else ""
        subs = _LISTING["dirs"].get(folder) if folder else None
        if folder and subs is None:
            _LISTING["want"].add(folder)
    _listing_kick()
    if info is None:
        return None
    if not info["cc"] and subs:
        stem = _pname(path).lower().rsplit(".", 1)[0]
        if any(s == stem or s.startswith(stem + ".") for s in subs):
            info = dict(info, cc=True)
    return info


def listing_ready():
    """The listing data is read and no folder waits for its subtitle check."""
    with _LISTING_LOCK:
        return _LISTING["files"] is not None and not [d for d in _LISTING["want"] if d not in _LISTING["dirs"]]             and not _LISTING["busy"]


def listing_warm():
    """Start reading the listing data (TV start), so the first programme's rating is there."""
    _listing_kick()


_RATING_RX = re.compile(r"(TV-?(?:Y7-?FV|Y7|Y|G|PG|14|MA)|NC-17|PG-13|PG|G|R)\b", re.I)


def mpaa_code(text):
    """'Rated PG-13', 'US:PG-13', 'PG-13' -> 'PG-13'; 'TV-PG', 'US:TV-PG' -> 'TV-PG';
    anything else (other countries' systems, 'Not Rated') -> ''."""
    t = (text or "").strip()
    if not t:
        return ""
    if ":" in t:
        t = t.split(":", 1)[1] if t.split(":", 1)[0].strip().upper() in ("US", "USA") else ""
    t = re.sub(r"^\s*rated\s+", "", t, flags=re.I).strip()
    m = _RATING_RX.match(t)
    if not m:
        return ""
    code = m.group(1).upper()
    if code.startswith("TV") and not code.startswith("TV-"):
        code = "TV-" + code[2:]
    return code.replace("Y7FV", "Y7-FV")


_MOVIE_TV = {"G": "TV-G", "PG": "TV-PG", "PG-13": "TV-14", "R": "TV-MA", "NC-17": "TV-MA"}


def tv_rating(text):
    """The 1997 TV Parental Guidelines rating to show: TV ratings as they are,
    movie ratings mapped (PG-13 -> TV-14, R -> TV-MA)."""
    code = mpaa_code(text)
    if code.startswith("TV-"):
        return "TV-Y7" if code == "TV-Y7-FV" else code
    return _MOVIE_TV.get(code, "")


def rating_for(path):
    """TV rating of a planned file ('' when unknown): the listing data, or - while
    that is still being read - one lookup by file name."""
    info = listing_info(path)
    if info is not None:
        return tv_rating(info["mpaa"])
    name = _pname(path)
    try:
        flt = {"field": "filename", "operator": "is", "value": name}
        for m in rpc("VideoLibrary.GetMovies", {"filter": flt, "properties": ["file", "mpaa"]}).get("movies", []):
            if m.get("file") == path:
                return tv_rating(m.get("mpaa"))
        for e in rpc("VideoLibrary.GetEpisodes", {"filter": flt, "properties": ["file", "tvshowid"]}).get("episodes", []):
            if e.get("file") == path:
                s = rpc("VideoLibrary.GetTVShowDetails", {"tvshowid": e["tvshowid"], "properties": ["mpaa"]})
                return tv_rating((s.get("tvshowdetails") or {}).get("mpaa"))
    except Exception as exc:
        log("rating: %s" % exc)
    return ""


# ------------------------------------------------------------- the guide's trailers
_TRAILERS = [0, None]       # (when, {movie file: local trailer file})


def movie_trailers():
    """{movie file: trailer file} for library movies whose trailer is a local file
    (Kodi's 'trailer' field; plugin:// and web trailers are left out: network, ads,
    failures).  Cached like the pools."""
    _check_gen()
    if _TRAILERS[1] is not None and time.time() - _TRAILERS[0] < _POOL_TTL:
        return _TRAILERS[1]
    out = {}
    try:
        for m in all_movies(["file", "trailer"]):
            t = (m.get("trailer") or "").strip()
            if m.get("file") and t and not t.lower().startswith(_NO_FS):
                out[m["file"]] = t
    except Exception as exc:
        log("trailers: %s" % exc)
    _TRAILERS[0], _TRAILERS[1] = time.time(), out
    return out
