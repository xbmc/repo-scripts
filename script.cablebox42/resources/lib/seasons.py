"""Holiday programming: Halloween, Thanksgiving and Christmas.

Each season has a run-up ("trickle": a growing share of holiday programmes)
and its big days ("full": holiday programming all day, wherever the channel
has any).  Holiday material always comes from the channel's own programming,
so a kids' channel never suddenly airs a slasher film.

What counts as holiday material (in this order of importance):
  * Kodi tags on movies and TV shows - any tag containing one of the season's
    words, any capitalisation ("Halloween", "halloween classics", "XMAS")
  * Kodi genres (Horror and Mystery for Halloween by default)
  * as a safety net, titles of movies and episodes ("Treehouse of Horror",
    "A Charlie Brown Christmas"), since Kodi can't tag single episodes
The tag and genre words are editable per season in Settings > Seasons.
"""
import calendar
import datetime
import os
import re
import time

from . import library
from .kodiutil import log

FULL = 1.0

# default tag / genre words (Settings > Seasons can change them)
DEFAULT_TAGS = {"halloween": "halloween, spooky, horror", "thanksgiving": "thanksgiving",
                "christmas": "christmas, xmas, holiday"}
DEFAULT_GENRES = {"halloween": "Horror, Mystery", "thanksgiving": "", "christmas": "Christmas, Holiday"}
# a tag containing one of these marks an item as belonging *only* to that
# holiday (kept back the rest of the year); horror and mystery are fine all year
HOLIDAY_WORDS = {"halloween": ["halloween"], "thanksgiving": ["thanksgiving"], "christmas": ["christmas", "xmas"]}

SEASONS = {
    "halloween": {
        "words": ["halloween", "treehouse of horror", "trick or treat", "trick-or-treat", "pumpkin",
                  "jack-o-lantern", "haunted", "haunting", "ghost", "ghosts", "ghoul", "witch", "witches",
                  "vampire", "vampires", "dracula", "frankenstein", "werewolf", "zombie", "zombies", "mummy",
                  "monster mash", "spooky", "scary", "creepy", "costume party", "headless horseman",
                  "sleepy hollow", "great pumpkin", "hocus pocus", "beetlejuice", "addams family",
                  "munsters", "goosebumps", "boo"],
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

# share of programmes in the run-up: (first day, last day), by intensity setting
RAMPS = {0: (0.05, 0.25), 1: (0.10, 0.45), 2: (0.25, 0.70)}


def thanksgiving(year):
    """US Thanksgiving: fourth Thursday of November."""
    first = datetime.date(year, 11, 1)
    shift = (calendar.THURSDAY - first.weekday()) % 7
    return first + datetime.timedelta(days=shift + 21)


def _window(name, year):
    """(trickle start, trickle end, full start, full end) as dates, end inclusive; or None."""
    d = datetime.date
    if name == "halloween":
        return d(year, 10, 1), d(year, 10, 30), d(year, 10, 31), d(year, 10, 31)
    if name == "thanksgiving":
        tg = thanksgiving(year)
        return None, None, tg, tg
    if name == "christmas":
        tg = thanksgiving(year)
        return tg + datetime.timedelta(days=1), d(year, 12, 23), d(year, 12, 24), d(year, 12, 25)
    return None


def phase(ts, cfg):
    """(season, level) for this moment: level 1.0 on the big days, a growing
    fraction in the run-up; (None, 0) when no season is on."""
    sc = (cfg or {}).get("seasons") or {}
    if not sc.get("on"):
        return None, 0.0
    day = datetime.date.fromtimestamp(ts)
    lo, hi = RAMPS.get(sc.get("intensity", 1), RAMPS[1])
    for name in ("thanksgiving", "halloween", "christmas"):   # Thanksgiving Day beats the Christmas run-up
        if not sc.get(name, {}).get("on"):
            continue
        t0, t1, f0, f1 = _window(name, day.year)
        if f0 <= day <= f1:
            return name, FULL
        if t0 and t0 <= day <= t1:
            span = max(1, (t1 - t0).days)
            return name, lo + (hi - lo) * (day - t0).days / float(span)
    return None, 0.0


def _rx(words):
    return re.compile(r"(?<![a-z])(" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
                      + r")(?![a-z])", re.I)


_RX = {name: _rx(s["words"]) for name, s in SEASONS.items()}
_INDEX = {}
_INDEX_TTL = 1800


def words(text):
    return [w.strip().lower() for w in (text or "").split(",") if w.strip()]


def _season_words(name, cfg):
    sc = ((cfg or {}).get("seasons") or {}).get(name) or {}
    tags = sc.get("tags")
    genres = sc.get("genres")
    return (words(DEFAULT_TAGS[name] if tags is None else tags),
            words(DEFAULT_GENRES[name] if genres is None else genres))


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


def is_seasonal(item, name, tagged=None, cfg=None):
    if tagged is None:
        tagged = tagged_paths(name, cfg)
    if item.get("path") in tagged:
        return True
    key = (name, item.get("path"), item.get("title"), item.get("sub"))
    hit = _MATCH.get(key)
    if hit is not None:
        return hit
    _MATCH[key] = hit = _text_match(item, name)
    return hit


def _text_match(item, name):
    text = " ".join((item.get("title") or "", item.get("sub") or "",
                     os.path.splitext(os.path.basename(item.get("path") or ""))[0].replace(".", " ")
                     .replace("_", " ")))
    return bool(_RX[name].search(text))


def items(pool, name, cfg=None):
    """Every holiday episode/movie in a pool (flat list)."""
    tagged = tagged_paths(name, cfg)
    out = []
    for ser in pool["series"]:
        out += [e for e in ser["episodes"] if is_seasonal(e, name, tagged)]
    out += [i for i in pool["singles"] if is_seasonal(i, name, tagged)]
    return out


# ------------------------------------------------------------ out of season
# Material that only makes sense in its season (a Christmas episode in July).
# Halloween is held back only when it's explicitly Halloween - horror and
# monsters are fine all year.
STRICT = {
    "halloween": {"tags": HOLIDAY_WORDS["halloween"],
                  "words": ["halloween", "treehouse of horror", "trick or treat", "trick-or-treat",
                            "great pumpkin", "hocus pocus"]},
    "thanksgiving": {"tags": HOLIDAY_WORDS["thanksgiving"], "words": SEASONS["thanksgiving"]["words"]},
    "christmas": {"tags": HOLIDAY_WORDS["christmas"], "words": SEASONS["christmas"]["words"]},
}
_STRICT_RX = {name: _rx(v["words"]) for name, v in STRICT.items()}
_STRICT_TAGGED = {}
_HOLIDAY_OF = {}          # path -> season name or "" (cache)


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


def holiday_of(item):
    """Which holiday an episode/movie belongs to ('' if none)."""
    p = item.get("path") or ""
    if p in _HOLIDAY_OF:
        return _HOLIDAY_OF[p]
    text = " ".join((item.get("title") or "", item.get("sub") or "",
                     os.path.splitext(os.path.basename(p))[0].replace(".", " ").replace("_", " ")))
    found = ""
    for name in ("christmas", "thanksgiving", "halloween"):
        if p in _strict_tagged(name) or _STRICT_RX[name].search(text):
            found = name
            break
    _HOLIDAY_OF[p] = found
    return found


def out_of_season(item, ts, cfg):
    """True if this is holiday material and its holiday isn't on now."""
    sc = (cfg or {}).get("seasons") or {}
    if not sc.get("on") or not sc.get("hold", True):
        return False
    h = holiday_of(item)
    return bool(h) and phase(ts, cfg)[0] != h


def clear_cache():
    _INDEX.clear()
    _STRICT_TAGGED.clear()
    _HOLIDAY_OF.clear()
    _MATCH.clear()
