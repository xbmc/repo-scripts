"""Channel lineup storage and the automatic lineup builder."""
import hashlib
import json
import uuid
from collections import Counter

from .kodiutil import CHANNELS_FILE, load_json, save_json
from . import library
from . import stations
from .kodiutil import _

WEATHER_NUMBER = 25        # where the weather channel usually lived on cable
NEWS_NUMBER = 42           # the news channel (News 42)


def fixed_number(c):
    """The channel number a channel keeps whatever else is in the lineup, or None:
    weather on 25, the automatic news channel (TV genre News) on 42."""
    if c.get("type") == "weather":
        return WEATHER_NUMBER
    if c.get("type") == "network" and any(s.get("type") == "tvgenre" and s.get("value") == "News"
                                          for s in c.get("sources", [])):
        return NEWS_NUMBER
    return None

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
          "sources": sources or [], "dayparts": [], "offair": [], "slots": []}
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
        c.setdefault("slots", [])
        c.setdefault("sources", [])
    return sorted(chans, key=lambda c: c["number"])


def save(chans):
    save_json(CHANNELS_FILE, {"version": 2, "channels": sorted(chans, key=lambda c: c["number"])})


def config_hash(ch):
    """Hash of everything that affects the schedule (not name/number)."""
    # Empty/unset fields are ignored, so adding new options in an update does
    # not throw away every channel's schedule.
    keep = {k: v for k, v in ch.items()
            if k not in ("name", "number", "callsign", "logo", "station", "brand_blocks") and v not in ([], {}, None, "")}
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


# ----------------------------------------------------------------- broadcast networks
# A classic network day.  Each block is used only when the library has shows
# for it; otherwise the network's general programming fills that time.
# (label, days, start, end, genres, fallback genres, extra)
KIDS = ["Animation", "Children", "Kids"]
GENERAL = ["Comedy", "Sitcom", "Drama", "Crime", "Mystery", "Action & Adventure", "Action",
           "Science Fiction", "Sci-Fi & Fantasy", "Western", "Family"]
NETWORK_DAY = [
    (_("Saturday Morning Cartoons"), [5], "07:00", "12:00", KIDS, ["Family"], {}),
    (_("Sunday Movie"), [6], "13:00", "17:00", "movies", None, {}),
    (_("Morning News"), "weekdays", "06:00", "09:00", ["News", "Talk"], None, {}),
    (_("Daytime Game Shows"), "weekdays", "09:00", "12:00", ["Game Show", "Game-Show"], ["Reality"], {}),
    (_("Afternoon Soaps"), "weekdays", "12:00", "15:00", ["Soap"], ["Drama"], {}),
    (_("After School"), "weekdays", "15:00", "17:00", KIDS + ["Family"], None, {}),
    (_("Early Evening"), "all", "17:00", "20:00", ["Comedy", "Sitcom", "Family"], None, {"not_genres": KIDS}),
    (_("Prime Time"), "all", "20:00", "23:00", GENERAL, None, {"prime": True, "not_genres": KIDS}),
    (_("Late Night"), "all", "23:00", "00:00", ["Talk"], ["Comedy", "Sitcom"], {"not_genres": KIDS}),
]
NETWORKS = 3


def _genre_sources(genres, gcount):
    return [{"type": "tvgenre", "value": g} for g in genres if gcount.get(g)]


def broadcast_networks(gcount, n_movies, count=NETWORKS):
    """`count` network channels, each with the network day above and its own
    share (part i of count) of every block's shows."""
    nets = []
    for i in range(count):
        part = [i, count]
        dayparts = []
        for label, days, start, end, genres, fallback, extra in NETWORK_DAY:
            if genres == "movies":
                if n_movies < 8:
                    continue
                srcs = [{"type": "movies"}]
            else:
                srcs = _genre_sources(genres, gcount)
            fb = _genre_sources(fallback or [], gcount)
            if not srcs and fb:
                srcs, fb = fb, []
            if not srcs:
                continue
            dp = {"label": label, "start": start, "end": end, "days": days, "sources": srcs, "part": part}
            if fb:
                dp["fallback"] = fb
            dp.update(extra)
            dayparts.append(dp)
        base = _genre_sources(GENERAL, gcount)
        if not base:
            return []
        nets.append(new_channel(0, _("Network %d") % (i + 1), "network", base,
                                dayparts=dayparts, part=part, broadcast=i + 1, not_genres=KIDS))
    return nets


# ----------------------------------------------------------------- auto build
GENRE_RENAMES = {
    "Animation": _("Cartoon Corner"), "Comedy": _("Comedy Channel"), "Drama": _("Drama Net"),
    "Science Fiction": _("Sci-Fi Channel"), "Sci-Fi & Fantasy": _("Sci-Fi Channel"),
    "Documentary": _("Documentary 42"), "Children": _("Kids TV"), "Kids": _("Kids TV"), "Family": _("Family Channel"),
    "Reality": _("Reality TV"), "Action & Adventure": _("Action Channel"), "Crime": _("Crime & Justice"),
    "Mystery": _("Mystery Channel"), "Western": _("Western Channel"), "Game Show": _("Game Show Channel"),
    "Soap": _("Soap Channel"), "Talk": _("Talk TV"), "News": _("News 42"),
}


# (Nickelodeon, Cartoon Network and PBS shows go to Chameleon, Animation
# Station and PES instead - see stations.py)
STUDIO_BRANDS = ["Disney", "Pixar", "Hanna-Barbera", "Warner Bros. Animation",
                 "HBO", "BBC", "Amblin", "Lucasfilm", "Marvel", "DreamWorks",
                 "Studio Ghibli", "Jim Henson", "Rankin/Bass"]


def auto_lineup(progress=None, min_shows=5, min_movies=8, max_tv=14, max_movie=6):
    """Build a sensible lineup from the Kodi library.

    Returns a list of channel dicts (not saved).
    """
    chans = [new_channel(2, _("TV Guide"), "guide")]
    weather = new_channel(WEATHER_NUMBER, _("Weather Channel"), "weather")
    num = 3

    def step(msg, pct):
        if progress:
            progress(msg, pct)

    step(_("Reading TV shows"), 5)
    shows = library.all_tvshows()
    gcount = Counter()
    for s in shows:
        for g in s.get("genre", []):
            gcount[g] += 1

    # genre networks (no catch-all "everything" channel)
    # genres sharing a channel name count together (Children + Kids -> Kids TV)
    groups = {}
    for g, _n in gcount.most_common():
        groups.setdefault(GENRE_RENAMES.get(g, _("%s TV") % g), []).append(g)
    sized = []
    for name, gs in groups.items():
        n = sum(1 for s in shows if set(gs).intersection(s.get("genre", [])))
        sized.append((n, name, gs))
    sized.sort(key=lambda x: -x[0])
    by_name = {}
    for n, name, gs in sized:
        if n < min_shows or len(by_name) >= max_tv:
            continue
        by_name[name] = new_channel(num, name, "network", [{"type": "tvgenre", "value": g} for g in gs])
        chans.append(by_name[name])
        num += 1

    covered = set(s["value"] for c in by_name.values() for s in c["sources"])
    make_nets = len(shows) >= 12
    if make_nets:              # the networks' time blocks air these genres too
        covered |= set(GENERAL) | set(g for row in NETWORK_DAY if row[4] != "movies" for g in row[4])
    orphans = sorted(s["title"] for s in shows if not covered.intersection(s.get("genre", [])))
    if shows and not by_name:
        # a small library: no genre has enough shows, so one channel airs them all
        chans.append(new_channel(num, _("Channel %d") % num, "network", [{"type": "alltv"}]))
        num += 1
    elif orphans:
        # shows whose genres are all too thin for a channel: onto the biggest
        # genre network, by name (the channel manager can move them)
        biggest = next(iter(by_name.values()))
        biggest["sources"].append({"type": "tvshow", "value": orphans, "orphans": True})

    # no automatic decade channels (they only repeated the genre channels);
    # a decade is still a source you can pick in the channel editor
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
    # broadcast networks on the low numbers, right after the guide
    if make_nets:
        chans[1:1] = broadcast_networks(gcount, len(movies))
    step(_("Done"), 100)
    chans.append(weather)
    stations.assign(chans)
    stations.extra_channels(chans, min_shows)
    renumber(chans)
    return chans


def renumber(chans):
    """Number channels 2, 3, 4... in order, keeping weather on 25 and news on 42
    (and never giving those numbers to anything else while they're there)."""
    fixed = {}
    for c in chans:
        n = fixed_number(c)
        if n is not None and n not in fixed:
            fixed[n] = c
    taken = set(fixed)
    num = 2
    for c in chans:
        if any(c is f for f in fixed.values()):
            c["number"] = fixed_number(c)
            continue
        while num in taken:
            num += 1
        c["number"] = num
        num += 1
    chans.sort(key=lambda c: c["number"])
    return chans
