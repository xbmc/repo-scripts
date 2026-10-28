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
import time

import xbmcvfs

from .kodiutil import rpc, load_json, save_json, DURATIONS_FILE, log
from . import probe

VIDEO_EXT = (".mkv", ".mp4", ".m4v", ".avi", ".ts", ".m2ts", ".mts", ".mov",
             ".webm", ".mpg", ".mpeg", ".wmv", ".flv", ".vob", ".divx", ".ogv")
AUDIO_EXT = (".mp3", ".flac", ".ogg", ".m4a", ".wav", ".aac", ".wma", ".opus")

EP_PROPS = ["file", "title", "runtime", "streamdetails", "season", "episode", "showtitle"]
MOVIE_PROPS = ["file", "title", "runtime", "streamdetails", "year"]

_POOL_CACHE = {}
_POOL_TTL = 1800


def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


class Durations(object):
    """Persistent cache of probed media durations (path -> seconds)."""

    def __init__(self):
        self.data = load_json(DURATIONS_FILE, {})
        self.dirty = False

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

    def learn(self, path, seconds):
        if seconds and seconds > 0 and abs(self.data.get(path, 0) - seconds) > 1:
            self.data[path] = round(seconds, 2)
            self.dirty = True

    def save(self):
        if self.dirty:
            save_json(DURATIONS_FILE, self.data)
            self.dirty = False


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
            "sub": ep.get("title", ""), "label": label, "dur": _lib_duration(ep)}


def _movie_item(m):
    title = m.get("title", "")
    if m.get("year"):
        title = "%s (%s)" % (title, m["year"])
    return {"path": m["file"], "title": title, "sub": "", "label": "", "dur": _lib_duration(m)}


# ------------------------------------------------------------- library helpers
def all_tvshows():
    res = rpc("VideoLibrary.GetTVShows", {"properties": ["title", "genre", "year", "episode"]})
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


def _series_from_show(show):
    eps = episodes_for(show["tvshowid"])
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


def _file_item(p, show=""):
    name = p.rstrip("/").split("/")[-1]
    title = re.sub(r"\.[^.]+$", "", name).replace(".", " ").replace("_", " ")
    label = ""
    m = re.search(r"[Ss](\d{1,2})[Ee](\d{1,3})", name)
    if m:
        label = "S%02dE%02d" % (int(m.group(1)), int(m.group(2)))
    return {"path": p, "title": show or title, "sub": title if show else "", "label": label,
            "dur": durations().get(p)}


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
            eps = [_file_item(p, d) for p in _walk(path + d, VIDEO_EXT)]
            eps = [e for e in eps if e["dur"] > 0]
            if eps:
                pool["series"].append({"key": "dir:" + path + d, "title": d, "episodes": eps})
        for f in sorted(files, key=natural_key):
            if f.lower().endswith(VIDEO_EXT):
                it = _file_item(path + f)
                if it["dur"] > 0:
                    pool["singles"].append(it)
    else:
        items = [it for it in (_file_item(p) for p in _walk(path, VIDEO_EXT)) if it["dur"] > 0]
        if mode == "sequential":
            if items:
                pool["series"].append({"key": "seq:" + path, "title": path.rstrip("/").split("/")[-1],
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


RESOLVERS = {
    "tvshow": _resolve_tvshow,
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


def resolve(sources):
    """Resolve a list of sources into a pool (cached for a while)."""
    key = json.dumps(sources, sort_keys=True)
    hit = _POOL_CACHE.get(key)
    if hit and time.time() - hit[0] < _POOL_TTL:
        return hit[1]
    pool = {"series": [], "singles": []}
    seen = set()
    for src in sources or []:
        fn = RESOLVERS.get(src.get("type"))
        if not fn:
            continue
        try:
            fn(src, pool)
        except Exception as exc:  # never let one bad source kill the channel
            log("Source %s failed: %s" % (src, exc))
    # de-duplicate series and drop items without duration
    series = []
    for s in pool["series"]:
        if s["key"] in seen:
            continue
        seen.add(s["key"])
        s["episodes"] = [e for e in s["episodes"] if e["dur"] > 0]
        if s["episodes"]:
            series.append(s)
    pool["series"] = series
    singles, seen_paths = [], set()
    for i in pool["singles"]:
        if i["dur"] > 0 and i["path"] not in seen_paths:
            seen_paths.add(i["path"])
            singles.append(i)
    pool["singles"] = singles
    durations().save()
    _POOL_CACHE[key] = (time.time(), pool)
    return pool


def filler_pool(path):
    """Commercials / bumps from a folder: list of {path, dur}."""
    if not path:
        return []
    key = "filler:" + path
    hit = _POOL_CACHE.get(key)
    if hit and time.time() - hit[0] < _POOL_TTL:
        return hit[1]
    out = []
    for p in _walk(path, VIDEO_EXT):
        d = durations().get(p)
        if 0 < d <= 600:
            out.append({"path": p, "dur": d, "title": _file_item(p)["title"]})
    durations().save()
    _POOL_CACHE[key] = (time.time(), out)
    return out


def filler_report(path):
    """(usable items, unreadable paths, too-long paths) for a commercials/bumps folder."""
    ok, bad, long_ = [], [], []
    for p in _walk(path, VIDEO_EXT):
        d = durations().get(p)
        if d <= 0:
            bad.append(p)
        elif d > 600:
            long_.append(p)
        else:
            ok.append(d)
    durations().save()
    return ok, bad, long_


def clear_cache():
    _POOL_CACHE.clear()
