"""Channel lineup storage and the automatic lineup builder."""
import hashlib
import json
import uuid
from collections import Counter

from .kodiutil import CHANNELS_FILE, load_json, save_json
from . import library
from .kodiutil import _

TYPES = ("network", "movies", "loop", "guide", "weather")

DEFAULTS = {
    "network": {"commercials": True, "midroll": True, "bumps": True, "lineup": "strip", "slot": 30},
    "movies": {"commercials": True, "midroll": False, "bumps": True, "lineup": "shuffle", "slot": 30},
    "loop": {"commercials": False, "midroll": False, "bumps": False, "lineup": "shuffle", "slot": 0},
    "guide": {"commercials": False, "midroll": False, "bumps": False, "lineup": "shuffle", "slot": 30},
    "weather": {"commercials": False, "midroll": False, "bumps": False, "lineup": "shuffle", "slot": 30},
}


def new_channel(number, name, ctype="network", sources=None, **extra):
    ch = {"id": uuid.uuid4().hex[:8], "number": int(number), "name": name, "type": ctype,
          "sources": sources or [], "dayparts": [], "offair": []}
    ch.update(DEFAULTS.get(ctype, DEFAULTS["network"]))
    ch.update(extra)
    return ch


def load():
    data = load_json(CHANNELS_FILE, {"channels": []})
    chans = data.get("channels", [])
    if data.get("version", 1) < 2:
        # 1.1: movie channels now run commercials between films by default
        for c in chans:
            if c.get("type") == "movies":
                c["commercials"] = True
    for c in chans:
        for k, v in DEFAULTS.get(c.get("type", "network"), {}).items():
            c.setdefault(k, v)
        c.setdefault("dayparts", [])
        c.setdefault("offair", [])
        c.setdefault("sources", [])
    return sorted(chans, key=lambda c: c["number"])


def save(chans):
    save_json(CHANNELS_FILE, {"version": 2, "channels": sorted(chans, key=lambda c: c["number"])})


def config_hash(ch):
    """Hash of everything that affects the schedule (not name/number)."""
    keep = {k: v for k, v in ch.items() if k not in ("name", "number", "callsign")}
    return hashlib.md5(json.dumps(keep, sort_keys=True).encode("utf-8")).hexdigest()[:12]


def callsign(name):
    words = [w for w in name.replace("-", " ").split() if w[0].isalnum()]
    if len(words) >= 2:
        cs = "".join(w[0] for w in words[:4])
    else:
        cs = name[:4]
    return cs.upper()


def next_free_number(chans, start=3):
    used = set(c["number"] for c in chans)
    n = start
    while n in used:
        n += 1
    return n


# ----------------------------------------------------------------- auto build
GENRE_RENAMES = {
    "Animation": _("Cartoon Corner"), "Comedy": _("Comedy Channel"), "Drama": _("Drama Net"),
    "Science Fiction": _("Sci-Fi Channel"), "Sci-Fi & Fantasy": _("Sci-Fi Channel"),
    "Documentary": _("Documentary 42"), "Children": _("Kids TV"), "Kids": _("Kids TV"), "Family": _("Family Channel"),
    "Reality": _("Reality TV"), "Action & Adventure": _("Action Channel"), "Crime": _("Crime & Justice"),
    "Mystery": _("Mystery Channel"), "Western": _("Western Channel"), "Game Show": _("Game Show Channel"),
    "Soap": _("Soap Channel"), "Talk": _("Talk TV"), "News": _("News 42"),
}


STUDIO_BRANDS = ["Disney", "Pixar", "Hanna-Barbera", "Warner Bros. Animation", "Nickelodeon",
                 "Cartoon Network", "HBO", "BBC", "Amblin", "Lucasfilm", "Marvel", "DreamWorks",
                 "Studio Ghibli", "Jim Henson", "Rankin/Bass", "PBS"]


def auto_lineup(progress=None, min_shows=3, min_movies=8, max_tv=14, max_movie=6):
    """Build a sensible lineup from the Kodi library.

    Returns a list of channel dicts (not saved).
    """
    chans = [new_channel(2, _("TV Guide"), "guide"), new_channel(3, _("Weather Channel"), "weather")]
    num = 4

    def step(msg, pct):
        if progress:
            progress(msg, pct)

    step(_("Reading TV shows"), 5)
    shows = library.all_tvshows()
    gcount = Counter()
    for s in shows:
        for g in s.get("genre", []):
            gcount[g] += 1

    # one "everything" channel first - the local independent station
    if shows:
        chans.append(new_channel(num, _("Channel %d") % num, "network",
                                 [{"type": "tvshow", "value": [s["title"] for s in shows]}]))
        num += 1

    used_names = set()
    for g, n in gcount.most_common():
        if len([c for c in chans if c["type"] == "network"]) > max_tv:
            break
        if n < min_shows:
            continue
        name = GENRE_RENAMES.get(g, _("%s TV") % g)
        if name in used_names:
            continue
        used_names.add(name)
        chans.append(new_channel(num, name, "network", [{"type": "tvgenre", "value": g}]))
        num += 1

    step(_("Grouping by decade"), 35)
    dec = Counter()
    for s in shows:
        y = int(s.get("year") or 0)
        if y > 1900:
            dec[y // 10 * 10] += 1
    for d in sorted(dec):
        if dec[d] >= max(min_shows, 4) and d < 2010:
            chans.append(new_channel(num, _("Retro %02ds") % (d % 100), "network",
                                     [{"type": "tvdecade", "value": d}]))
            num += 1

    step(_("Reading movies"), 60)
    movies = library.all_movies()
    mg = Counter()
    for m in movies:
        for g in m.get("genre", []):
            mg[g] += 1
    if len(movies) >= min_movies:
        chans.append(new_channel(num, _("Movie Channel"), "movies", [{"type": "movies"}]))
        num += 1
    made = 0
    for g, n in mg.most_common():
        if made >= max_movie or n < min_movies:
            continue
        chans.append(new_channel(num, _("%s Movies") % g, "movies", [{"type": "movies", "genre": g}]))
        num += 1
        made += 1
    step(_("Looking for studio channels"), 85)
    try:
        studio_items = library.all_tvshows_with("studio") + library.all_movies(["title", "studio"])
    except Exception:
        studio_items = []
    made = 0
    for brand in STUDIO_BRANDS:
        n = sum(1 for it in studio_items if any(brand.lower() in s.lower() for s in it.get("studio", [])))
        if n >= min_movies and made < 4:
            chans.append(new_channel(num, _("%s Showcase") % brand, "network",
                                     [{"type": "studio", "value": brand, "what": "both"}],
                                     lineup="shuffle"))
            num += 1
            made += 1
    old = [m for m in movies if 0 < int(m.get("year") or 0) < 1990]
    if len(old) >= min_movies:
        chans.append(new_channel(num, _("Classic Movies"), "movies",
                                 [{"type": "movies", "years": [1900, 1989]}]))
        num += 1
    step(_("Done"), 100)
    return chans
