"""Holiday programming: Halloween, Thanksgiving, Christmas and the viewer's own seasons.

Each season has a run-up ("trickle": a growing share of holiday programmes)
and its big days ("full": holiday programming all day, wherever the channel
has any).  Holiday material always comes from the channel's own programming,
so a kids' channel never suddenly airs a slasher film.

When a season is on (the format of the specials' date rules, specials.py: a date,
the n-th weekday of a month, Easter +- days, each with a shift):
    from     the first big day (a date rule)
    days     how many big days, 1-14 (past 31 December: into the next year)
    run_up   None (no run-up), {"type": "before", "days": N} (N days before the big
             days) or a date rule (its latest date before them: a run-up from
             26 December leads into New Year's Day); it ends the day before the big days
The built-ins' rules (RULES) reproduce the dates CableBox has always used; the
season editor (seasons_editor.py) stores changes to them, and the viewer's own
seasons, in seasons.json (apply_file).  No file = exactly the built-ins.

Which season is on: a big day beats any run-up, and between two big days the
season higher in the list wins (Thanksgiving, Halloween, Christmas, then the
viewer's own in their order).  Between two run-ups, the one whose big days come
first wins (Festivus's two days of run-up inside Christmas's), then the list.

What counts as holiday material (in this order of importance):
  * Kodi tags on movies and TV shows - any tag containing one of the season's
    words, any capitalisation ("Halloween", "halloween classics", "XMAS")
  * Kodi genres (Horror for Halloween by default; plain Mystery was too broad)
  * as a safety net, titles of movies and episodes ("Treehouse of Horror",
    "A Charlie Brown Christmas"), since Kodi can't tag single episodes; the
    viewer's extra title words are added to the built-in ones
The tag and genre words are editable per season (main menu > Holidays & events >
Holiday seasons).
"""
import datetime
import json
import os
import re
import time

from . import library
from . import specials
from .kodiutil import log

FULL = 1.0
DAY = datetime.timedelta(days=1)

# default tag / genre words (the season editor and Settings can change them)
DEFAULT_TAGS = {"halloween": "halloween, spooky, horror", "thanksgiving": "thanksgiving",
                "christmas": "christmas, xmas, holiday"}
DEFAULT_GENRES = {"halloween": "Horror", "thanksgiving": "", "christmas": "Christmas, Holiday"}
# a tag containing one of these marks an item as belonging *only* to that
# holiday (kept back the rest of the year); horror and mystery are fine all year
HOLIDAY_WORDS = {"halloween": ["halloween"], "thanksgiving": ["thanksgiving"], "christmas": ["christmas", "xmas"]}

SEASONS = {
    "halloween": {
        # clearly Halloween or horror only (~all10): 'ghost', 'witch', 'boo', 'mummy', 'scary',
        # 'creepy', 'pumpkin' and 'costume party' matched hundreds of ordinary episodes
        "words": ["halloween", "treehouse of horror", "trick or treat", "trick-or-treat",
                  "jack-o-lantern", "haunted", "haunting", "ghoul", "ghouls",
                  "vampire", "vampires", "dracula", "frankenstein", "werewolf", "zombie", "zombies",
                  "monster mash", "spooky", "headless horseman",
                  "sleepy hollow", "great pumpkin", "hocus pocus", "beetlejuice", "addams family",
                  "munsters", "goosebumps"],
    },
    "thanksgiving": {
        "tags": ["thanksgiving"],
        "genres": [],
        "words": ["thanksgiving", "turkey", "pilgrim", "pilgrims", "mayflower", "planes, trains",
                  "gobble", "harvest feast"],
    },
    "christmas": {
        "tags": ["christmas", "xmas", "holiday", "holidays"],
        "genres": [],
        "words": ["christmas", "xmas", "x-mas", "santa", "santa claus", "noel", "jingle", "sleigh", "reindeer",
                  "rudolph", "frosty", "grinch", "scrooge", "christmas carol", "nutcracker", "mistletoe",
                  "yule", "yuletide", "nativity", "north pole", "snowman", "elves", "stocking",
                  "miracle on 34th street", "wonderful life", "home alone", "holiday inn", "white christmas",
                  "deck the halls", "silent night", "winter wonderland", "kringle", "feliz navidad"],
    },
}

NAMES = {"halloween": "Halloween", "thanksgiving": "Thanksgiving", "christmas": "Christmas"}
BUILTIN = ("thanksgiving", "halloween", "christmas")        # list order: Thanksgiving Day beats the Christmas run-up

# the built-ins' dates as rules (what _window hard-coded before seasons.json)
THANKSGIVING_US = {"type": "nth", "n": 4, "weekday": 3, "month": 11}
THANKSGIVING_CA = {"type": "nth", "n": 2, "weekday": 0, "month": 10}
RULES = {
    "halloween": {"run_up": {"type": "date", "month": 10, "day": 1},
                  "from": {"type": "date", "month": 10, "day": 31}, "days": 1},
    "thanksgiving": {"run_up": None, "from": THANKSGIVING_US, "days": 1},
    "christmas": {"run_up": dict(THANKSGIVING_US, shift=1),
                  "from": {"type": "date", "month": 12, "day": 24}, "days": 2},
}
RULE_KEYS = ("run_up", "from", "days")
MAX_DAYS = 14
MAX_BEFORE = 90

# share of programmes in the run-up: (first day, last day), by intensity setting
RAMPS = {0: (0.05, 0.25), 1: (0.10, 0.45), 2: (0.25, 0.70)}


def thanksgiving(year):
    """US Thanksgiving: fourth Thursday of November."""
    return specials.date_for(THANKSGIVING_US, year)


# ------------------------------------------------------------ seasons.json
def path():
    from .kodiutil import PROFILE
    return os.path.join(PROFILE, "seasons.json")


def _rule_ok(rule, may_be_none=False):
    return (rule is None and may_be_none) or specials.valid(rule)


def _run_up_ok(rule):
    if isinstance(rule, dict) and rule.get("type") == "before":
        return isinstance(rule.get("days"), int) and 1 <= rule["days"] <= MAX_BEFORE
    return _rule_ok(rule, True)


def _days_ok(n):
    return isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= MAX_DAYS


def _name_ok(n):
    return isinstance(n, str) and n.strip() != ""


def _words_ok(w):
    return isinstance(w, list) and all(isinstance(x, str) for x in w)


def clean(data):
    """{'builtin': {name: overrides}, 'custom': [seasons]} with anything broken left
    out (never an exception: a bad seasons.json means the built-ins, not no TV)."""
    out = {"builtin": {}, "custom": []}
    if not isinstance(data, dict):
        return out
    for name, ov in (data.get("builtin") or {}).items() if isinstance(data.get("builtin"), dict) else ():
        if name not in BUILTIN or not isinstance(ov, dict):
            continue
        keep = {}
        if "run_up" in ov and _run_up_ok(ov["run_up"]):
            keep["run_up"] = ov["run_up"]
        if _rule_ok(ov.get("from")):
            keep["from"] = ov["from"]
        if _days_ok(ov.get("days")):
            keep["days"] = ov["days"]
        if _name_ok(ov.get("name")):
            keep["name"] = ov["name"].strip()
        if ov.get("intensity") in (0, 1, 2):
            keep["intensity"] = ov["intensity"]
        if _words_ok(ov.get("words")) and ov["words"]:
            keep["words"] = ov["words"]
        if isinstance(ov.get("hold"), bool):
            keep["hold"] = ov["hold"]
        if keep:
            out["builtin"][name] = keep
    seen = set()
    for c in data.get("custom") or () if isinstance(data.get("custom"), list) else ():
        if not isinstance(c, dict) or not isinstance(c.get("id"), str) or not c["id"].startswith("s_") \
                or c["id"] in seen or not _rule_ok(c.get("from")) or not _run_up_ok(c.get("run_up")):
            continue
        seen.add(c["id"])
        out["custom"].append({
            "id": c["id"], "name": c.get("name") if isinstance(c.get("name"), str) else "",
            "on": c.get("on") is not False, "run_up": c.get("run_up"), "from": c["from"],
            "days": c["days"] if _days_ok(c.get("days")) else 1,
            "intensity": c.get("intensity") if c.get("intensity") in (0, 1, 2) else None,
            "tags": c.get("tags") if isinstance(c.get("tags"), str) else "",
            "genres": c.get("genres") if isinstance(c.get("genres"), str) else "",
            "words": c.get("words") if _words_ok(c.get("words")) else [],
            "ads": c.get("ads") if isinstance(c.get("ads"), str) else "",
            "bumps": c.get("bumps") if isinstance(c.get("bumps"), str) else "",
            "hold": c.get("hold") is True})
    return out


def load():
    try:
        with open(path(), "r", encoding="utf-8") as f:
            return clean(json.load(f))
    except (IOError, OSError, ValueError):
        return clean(None)


def save(data):
    data = clean(data)
    file = path()
    tmp = file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    os.replace(tmp, file)
    return data


def apply_file(sc, data):
    """Add seasons.json (loaded, or None) to the settings' seasons config: the
    built-ins' overrides and the viewer's own seasons.  No file: sc unchanged."""
    if data is None:
        return sc
    data = clean(data)
    for name, ov in data["builtin"].items():
        sc.setdefault(name, {}).update(ov)
    if data["custom"]:
        for c in data["custom"]:
            sc[c["id"]] = dict(c, custom=True)
        sc["order"] = list(BUILTIN) + [c["id"] for c in data["custom"]]
    return sc


# ------------------------------------------------------------ when
def order(sc):
    return sc.get("order") or BUILTIN


def rules(name, d):
    """(run_up, from, days) of a season's config d: its own, or the built-in's."""
    base = RULES.get(name, {})
    return tuple(d[k] if k in d else base.get(k) for k in RULE_KEYS)


_WIN = {}


def window(run_up, frm, days, year):
    """(run-up start, run-up end, first big day, last big day) for the big days that
    start in `year`, as dates (end inclusive); run-up None when there is none; None
    when the year has no such date.  The run-up ends the day before the big days."""
    key = (json.dumps([run_up, frm, days], sort_keys=True), year)
    if key in _WIN:
        return _WIN[key]
    out = None
    f0 = specials.date_for(frm, year)
    if f0 is not None:
        f1 = f0 + DAY * (max(1, min(MAX_DAYS, days or 1)) - 1)
        t0 = t1 = None
        if isinstance(run_up, dict) and run_up.get("type") == "before":
            t0 = f0 - DAY * run_up["days"]
        elif run_up:
            t0 = specials.date_for(run_up, year)
            if t0 is not None and t0 >= f0:
                t0 = specials.date_for(run_up, year - 1)
        if t0 is not None and t0 < f0:
            t1 = f0 - DAY
        else:
            t0 = None
        out = (t0, t1, f0, f1)
    _WIN[key] = out
    return out


_WINS = {}


def windows(name, d, year):
    """The season's windows that can touch `year` (a window across New Year starts
    the year before).  Kept per config dict: phase() runs for every planned slot."""
    key = (id(d), name, year)
    hit = _WINS.get(key)
    if hit is not None and hit[0] is d:
        return hit[1]
    r = rules(name, d)
    out = [w for w in (window(r[0], r[1], r[2], y) for y in (year - 1, year, year + 1)) if w]
    if len(_WINS) > 2000:
        _WINS.clear()
    _WINS[key] = (d, out)
    return out


def _day(ts, sc):
    return datetime.date.fromtimestamp(ts + (sc.get("shift") or 0))


def phase(ts, cfg):
    """(season, level) for this moment: level 1.0 on the big days, a growing
    fraction in the run-up; (None, 0) when no season is on."""
    sc = (cfg or {}).get("seasons") or {}
    if not sc.get("on"):
        return None, 0.0
    day = _day(ts, sc)
    run = None
    for name in order(sc):
        d = sc.get(name) or {}
        if not d.get("on"):
            continue
        for t0, t1, f0, f1 in windows(name, d, day.year):
            if f0 <= day <= f1:
                return name, FULL
            if t0 and t0 <= day <= t1 and (run is None or f0 < run[0]):
                intensity = d.get("intensity")
                lo, hi = RAMPS.get(sc.get("intensity", 1) if intensity is None else intensity, RAMPS[1])
                span = max(1, (t1 - t0).days)
                run = (f0, name, lo + (hi - lo) * (day - t0).days / float(span))
    return run[1:] if run else (None, 0.0)


def describe(name, d, year):
    """(run-up start, run-up end, first big day, last big day) of the season's next
    big days from 1 January of `year` on (for the editor's words); None if none."""
    for y in (year, year + 1):
        r = rules(name, d)
        w = window(r[0], r[1], r[2], y)
        if w:
            return w
    return None


# ------------------------------------------------------------ what
def _rx(words):
    words = [w for w in words if w]
    if not words:
        return None
    return re.compile(r"(?<![a-z])(" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
                      + r")(?![a-z])", re.I)


_RXS = {}


def _cached_rx(words):
    key = tuple(words)
    if key not in _RXS:
        _RXS[key] = _rx(words)
    return _RXS[key]


def title_words(name, sc):
    """The season's title words: the built-in list plus the viewer's extra words."""
    d = (sc or {}).get(name) or {}
    extra = [w.strip().lower() for w in d.get("words") or [] if w.strip()]
    base = SEASONS[name]["words"] if name in SEASONS else []
    return base + [w for w in extra if w not in base]


def season_rx(name, sc):
    return _cached_rx(title_words(name, sc))


_INDEX = {}
_INDEX_TTL = 1800


def words(text):
    return [w.strip().lower() for w in (text or "").split(",") if w.strip()]


def _season_words(name, cfg):
    sc = ((cfg or {}).get("seasons") or {}).get(name) or {}
    tags = sc.get("tags")
    genres = sc.get("genres")
    return (words(DEFAULT_TAGS.get(name, "") if tags is None else tags),
            words(DEFAULT_GENRES.get(name, "") if genres is None else genres))


def _library_labels(kind):
    """Every tag or genre label in the library (movies and TV shows)."""
    out = set()
    for media in ("movie", "tvshow"):
        res = library.rpc("VideoLibrary.Get%s" % ("Tags" if kind == "tag" else "Genres"), {"type": media})
        out.update(x.get("label") or "" for x in res.get("tags" if kind == "tag" else "genres", []))
    return sorted(x for x in out if x)


def matching_labels(kind, wanted):
    """Library tags/genres containing any of the wanted words, any capitalisation:
    'halloween' finds 'Halloween', 'Halloween Classics', 'kids-halloween'."""
    if not wanted:
        return []
    try:
        labels = _library_labels(kind)
    except Exception as exc:
        log("season labels: %s" % exc)
        labels = []
    hits = [l for l in labels if any(w in l.lower() for w in wanted)]
    # libraries without a tag list (or an old Kodi): still try the words themselves
    return hits or [w for w in wanted]


def _paths_with(field, labels):
    paths = set()
    for val in labels:
        for m in library._filtered_movies(field, "is", val):
            paths.add(m["file"])
        for show in library._filtered_shows(field, "is", val):
            for ep in library.episodes_for(show["tvshowid"]):
                paths.add(ep["file"])
    return paths


def tagged_paths(name, cfg=None):
    """Files of movies and TV shows carrying the season's tags or genres."""
    tags, genres = _season_words(name, cfg)
    key = (name, tuple(tags), tuple(genres))
    hit = _INDEX.get(key)
    if hit and time.time() - hit[0] < _INDEX_TTL:
        return hit[1]
    paths = set()
    try:
        paths |= _paths_with("tag", matching_labels("tag", tags))
        paths |= _paths_with("genre", matching_labels("genre", genres))
    except Exception as exc:
        log("season index %s: %s" % (name, exc))
    _INDEX[key] = (time.time(), paths)
    return paths


_MATCH = {}


def _text(item):
    return " ".join((item.get("title") or "", item.get("sub") or "",
                     os.path.splitext(os.path.basename(item.get("path") or ""))[0].replace(".", " ")
                     .replace("_", " ")))


def is_seasonal(item, name, tagged=None, cfg=None):
    if tagged is None:
        tagged = tagged_paths(name, cfg)
    if item.get("path") in tagged:
        return True
    rx = season_rx(name, (cfg or {}).get("seasons"))
    if rx is None:
        return False
    key = (rx, item.get("path"), item.get("title"), item.get("sub"))
    hit = _MATCH.get(key)
    if hit is not None:
        return hit
    _MATCH[key] = hit = bool(rx.search(_text(item)))
    return hit


def items(pool, name, cfg=None):
    """Every holiday episode/movie in a pool (flat list)."""
    tagged = tagged_paths(name, cfg)
    out = []
    for ser in pool["series"]:
        out += [e for e in ser["episodes"] if is_seasonal(e, name, tagged, cfg)]
    out += [i for i in pool["singles"] if is_seasonal(i, name, tagged, cfg)]
    return out


# ------------------------------------------------------------ out of season
# Material that only makes sense in its season (a Christmas episode in July).
# Halloween is held back only when it's explicitly Halloween - horror and
# monsters are fine all year.  The viewer's extra title words are held for
# Thanksgiving and Christmas (whose held words are all their words), not for
# Halloween.  One of the viewer's own seasons with "save for its season" on
# holds everything it matches (tags, genres, title words).
STRICT = {
    "halloween": {"tags": HOLIDAY_WORDS["halloween"],
                  "words": ["halloween", "treehouse of horror", "trick or treat", "trick-or-treat",
                            "great pumpkin", "hocus pocus"]},
    "thanksgiving": {"tags": HOLIDAY_WORDS["thanksgiving"], "words": SEASONS["thanksgiving"]["words"]},
    "christmas": {"tags": HOLIDAY_WORDS["christmas"], "words": SEASONS["christmas"]["words"]},
}
HOLD_ORDER = ("christmas", "thanksgiving", "halloween")
_STRICT_TAGGED = {}
_HOLIDAY_OF = {}          # (path, held seasons and their words) -> season name or "" (cache)


def _strict_rx(name, sc):
    w = STRICT[name]["words"]
    if name != "halloween":
        w = title_words(name, sc)
    return _cached_rx(w)


def _strict_tagged(name):
    hit = _STRICT_TAGGED.get(name)
    if hit and time.time() - hit[0] < _INDEX_TTL:
        return hit[1]
    paths = set()
    try:
        paths = _paths_with("tag", matching_labels("tag", STRICT[name]["tags"]))
    except Exception as exc:
        log("season tags %s: %s" % (name, exc))
    _STRICT_TAGGED[name] = (time.time(), paths)
    return paths


def held(sc):
    """The seasons whose material is kept off the air outside them, in the order an
    item is matched: the built-ins (Settings' 'Save holiday episodes...', or their own
    choice in the editor), then the viewer's own with it on."""
    out = []
    for name in HOLD_ORDER:
        d = sc.get(name) or {}
        if (d.get("hold") if d.get("hold") is not None else sc.get("hold", True)):
            out.append(name)
    for name in order(sc):
        if name not in HOLD_ORDER and (sc.get(name) or {}).get("hold"):
            out.append(name)
    return out


_SIGS = {}


def _sig(sc, cfg, names):
    """What decides holiday_of for these seasons (their words), kept per config dict."""
    key = (id(sc), names)
    hit = _SIGS.get(key)
    if hit is not None and hit[0] is sc:
        return hit[1]
    sig = tuple((n, _strict_rx(n, sc) if n in STRICT else season_rx(n, sc),
                 tuple(tuple(x) for x in _season_words(n, cfg)) if n not in STRICT else None) for n in names)
    if len(_SIGS) > 200:
        _SIGS.clear()
    _SIGS[key] = (sc, sig)
    return sig


def holiday_of(item, cfg=None, names=HOLD_ORDER):
    """Which held holiday an episode/movie belongs to ('' if none)."""
    sc = (cfg or {}).get("seasons") or {}
    p = item.get("path") or ""
    sig = _sig(sc, cfg, names)
    key = (p, sig)
    if key in _HOLIDAY_OF:
        return _HOLIDAY_OF[key]
    text = _text(item)
    found = ""
    for n, rx, _w in sig:
        if n in STRICT:
            hit = p in _strict_tagged(n) or (rx is not None and rx.search(text))
        else:
            hit = is_seasonal(item, n, cfg=cfg)
        if hit:
            found = n
            break
    _HOLIDAY_OF[key] = found
    return found


def out_of_season(item, ts, cfg):
    """True if this is holiday material and its holiday isn't on now."""
    sc = (cfg or {}).get("seasons") or {}
    if not sc.get("on"):
        return False
    names = held(sc)
    if not names:
        return False
    h = holiday_of(item, cfg, tuple(names))
    return bool(h) and phase(ts, cfg)[0] != h


def clear_cache():
    _INDEX.clear()
    _STRICT_TAGGED.clear()
    _HOLIDAY_OF.clear()
    _MATCH.clear()
