"""One home channel per show.

Every title a channel's sources can produce is scored for that channel; the
best-scoring channel becomes the title's *home*.  Automatic programming only
plays a title on its home channel - unless the user explicitly chose it for
another channel too (picked by name, or ticked in 'Move shows between
channels').  Pinned slots and time blocks are the user's own choice and are
never filtered.

The result is saved to assign.json so the TV can use it instantly; it is
recomputed by the background builder / service.
"""
import hashlib
import json
import os

from .kodiutil import PROFILE, load_json, save_json, setting_int, log
from . import library

ASSIGN_FILE = os.path.join(PROFILE, "assign.json")
PROGRAM_TYPES = ("network", "movies", "loop")
EXPLICIT = 100
BROAD_LIST = 20          # a hand-made show list longer than this counts as "broad"
MIN_SHOWS = 5            # a channel is topped up to at least this many titles

MODE_TV_ONLY, MODE_ALL, MODE_OFF = 0, 1, 2


def mode():
    """0: TV shows on one channel each (movies can repeat) - default
       1: everything on one channel each
       2: allow repeats everywhere (no filtering)"""
    m = setting_int("share_mode", 0)
    return m if m in (0, 1, 2) else 0


def _genre_score(genres, wanted, base):
    wanted = (wanted or "").lower()
    if wanted not in genres:
        return base - 15
    pos = genres.index(wanted)
    return base - min(pos, 2) * 10          # predominant genre first: 50 / 40 / 30


def score(src, title, is_movie, meta, n_titles):
    t = src.get("type")
    if src.get("explicit"):
        return EXPLICIT
    genres = meta.get(title, [])
    if t in ("tvshow", "movie"):
        return EXPLICIT if n_titles <= BROAD_LIST else 10
    if t == "folder":
        return 90
    if t == "movies":
        if src.get("set"):
            return 85
        if src.get("tag"):
            return 80
        if src.get("genre"):
            return _genre_score(genres, src["genre"], 50)
        if src.get("years"):
            return 22
        return 5                              # all movies: the catch-all movie channel
    if t == "tag":
        return 80
    if t == "playlist":
        return 75
    if t == "studio":
        return 70
    if t == "keyword":
        return 60
    if t == "tvgenre":
        return _genre_score(genres, src.get("value"), 50)
    if t == "tvdecade":
        return 25
    if t == "alltv":
        return 5                              # the 'everything' station gets the leftovers
    return 20


def _metadata():
    meta = {}
    for s in library.all_tvshows():
        meta[s["title"].lower()] = [g.lower() for g in s.get("genre", [])]
    for m in library.all_movies(["title", "genre", "year"]):
        key = ("%s (%s)" % (m["title"], m["year"]) if m.get("year") else m["title"]).lower()
        meta[key] = [g.lower() for g in m.get("genre", [])]
    return meta


def compute(channels, md=None):
    """{'home': {title: cid}, 'explicit': {cid: [titles]}, 'digest': {cid: str}, 'mode': md}"""
    md = mode() if md is None else md
    progs = sorted([c for c in channels if c.get("type") in PROGRAM_TYPES], key=lambda c: c["number"])
    meta = _metadata()
    cands = {}          # title -> {cid: score}
    movies = set()
    explicit = {}
    for ch in progs:
        cid = ch["id"]
        excluded = set(x.lower() for x in ch.get("exclude", []))
        for src in ch.get("sources", []):
            pool = library.resolve([src])
            titles = [(s["title"].lower(), False) for s in pool["series"]] + \
                     [(i["title"].lower(), True) for i in pool["singles"]]
            for tl, is_movie in titles:
                if tl in excluded:
                    continue
                if is_movie and md == MODE_TV_ONLY:
                    continue                 # movies may repeat: no home needed
                if is_movie:
                    movies.add(tl)
                sc = score(src, tl, is_movie, meta, len(titles))
                if sc >= EXPLICIT:
                    explicit.setdefault(cid, set()).add(tl)
                cur = cands.setdefault(tl, {})
                cur[cid] = max(cur.get(cid, 0), sc)
    order = dict((c["id"], c["number"]) for c in progs)
    home = {}
    for tl, cs in cands.items():
        home[tl] = max(cs, key=lambda cid: (cs[cid], -order[cid]))
    _balance(home, cands, order, movies, md)
    allowed = {}
    for tl, cid in home.items():
        allowed.setdefault(cid, set()).add(tl)
    for cid, ts in explicit.items():
        allowed.setdefault(cid, set()).update(ts)
    # Channels still short (no donor could spare a show) borrow their best few
    # matches as *shared* titles, rather than airing their whole list.
    shared = {}
    for ch in progs:
        cid = ch["id"]
        have = allowed.get(cid, set())
        mine = sorted(((cs[cid], tl) for tl, cs in cands.items() if cid in cs and tl not in have), reverse=True)
        need = min(MIN_SHOWS, len(have) + len(mine)) - len(have)
        if need > 0:
            take = [tl for _sc, tl in mine[:need]]
            shared[cid] = take
            allowed.setdefault(cid, set()).update(take)
    open_ = []
    digest = {}
    for ch in progs:
        ts = sorted(allowed.get(ch["id"], set()))
        digest[ch["id"]] = hashlib.md5(("%d|%d|" % (md, ch["id"] in open_) + "\n".join(ts)).encode("utf-8")).hexdigest()[:10]
    return {"home": home, "explicit": dict((k, sorted(v)) for k, v in explicit.items()),
            "digest": digest, "mode": md, "open": open_, "shared": shared}


def _balance(home, cands, order, movies, md):
    """Top up channels that would be left with (almost) nothing, taking the
    titles whose current home loses the least."""
    for _round in range(200):
        counts = {}
        for tl, cid in home.items():
            counts[cid] = counts.get(cid, 0) + 1
        starving = None
        for cid in order:
            have = counts.get(cid, 0)
            possible = sum(1 for cs in cands.values() if cid in cs)
            if have < min(MIN_SHOWS, possible):
                starving = cid
                break
        if not starving:
            return
        best = None
        for tl, cs in cands.items():
            if starving not in cs or home[tl] == starving:
                continue
            donor = home[tl]
            if counts.get(donor, 0) <= MIN_SHOWS:
                continue
            loss = cs[donor] - cs[starving]
            if best is None or loss < best[0]:
                best = (loss, tl)
        if not best:
            return
        home[best[1]] = starving


def allowed_fn(assignment, cid):
    """Function(title_lower, is_movie) -> may this channel air it automatically?"""
    if not assignment:
        return lambda t, m: True
    md = assignment.get("mode", 0)
    if md == MODE_OFF or cid in assignment.get("open", []):
        return lambda t, m: True
    home = assignment.get("home", {})
    mine = set(assignment.get("explicit", {}).get(cid, [])) | set(assignment.get("shared", {}).get(cid, []))

    def ok(title, is_movie):
        if is_movie and md == MODE_TV_ONLY:
            return True
        if title in mine:
            return True
        return home.get(title, cid) == cid
    return ok


def load():
    return load_json(ASSIGN_FILE, {})


def save(assignment):
    save_json(ASSIGN_FILE, assignment)


def refresh(channels):
    """Recompute and persist; returns (assignment, changed)."""
    old = load()
    try:
        new = compute(channels)
    except Exception as exc:
        log("assignment failed: %s" % exc)
        return old, False
    changed = json.dumps(new, sort_keys=True) != json.dumps(old, sort_keys=True)
    if changed:
        save(new)
    return new, changed
