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

TYPES = ("network", "movies", "loop", "guide", "weather", "extras", "musicvideos", "music")

DEFAULTS = {
    "network": {"commercials": True, "midroll": True, "bumps": True, "lineup": "strip", "slot": 30},
    "movies": {"commercials": True, "midroll": False, "bumps": True, "lineup": "shuffle", "slot": 30},
    "loop": {"commercials": False, "midroll": False, "bumps": False, "lineup": "shuffle", "slot": 0},
    "guide": {"commercials": False, "midroll": False, "bumps": False, "lineup": "shuffle", "slot": 30},
    "weather": {"commercials": False, "midroll": False, "bumps": False, "lineup": "shuffle", "slot": 30},
    # Behind the scenes: movie Extras in per-film blocks; breaks only between segments
    "extras": {"commercials": True, "midroll": True, "bumps": True, "lineup": "shuffle", "slot": 30},
    # Boombox: music videos on the real clock, breaks only between videos, video captions on
    "musicvideos": {"commercials": True, "midroll": True, "bumps": True, "lineup": "shuffle", "slot": 30,
                    "mv_captions": True},
    # Music channels (DMX-style): songs around the clock, no breaks of any kind; never in the wizard
    "music": {"commercials": False, "midroll": False, "bumps": False, "lineup": "shuffle", "slot": 60},
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


def signoff_mode(ch):
    """How the channel signs off at the start of its off-air hours: "card" (the
    built-in sign-off card, the default), "none", or "folder" (a clip from
    signoff_path).  Channels from before 1.3 have no signoff_mode: a sign-off
    folder makes them "folder", otherwise the card.  (Not written on load, so an
    update doesn't change every channel's config_hash.)"""
    mode = ch.get("signoff_mode")
    if mode == "folder" and not ch.get("signoff_path"):
        return "card"
    if mode in ("card", "none", "folder"):
        return mode
    return "folder" if ch.get("signoff_path") else "card"


def save(chans):
    keep = [dict((k, v) for k, v in c.items() if not k.startswith("_")) for c in chans]   # wizard-only notes
    save_json(CHANNELS_FILE, {"version": 2, "channels": sorted(keep, key=lambda c: c["number"])})


def config_hash(ch):
    """Hash of everything that affects the schedule (not name/number)."""
    # Empty/unset fields are ignored, so adding new options in an update does
    # not throw away every channel's schedule.
    keep = {k: v for k, v in ch.items()
            if k not in ("name", "number", "callsign", "logo", "station", "brand_blocks", "mv_captions",
                         "home_guard")
            and not k.startswith("_") and v not in ([], {}, None, "")}
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
    # other spellings of a station's genres share its channel
    "Sitcom": _("Comedy Channel"), "Action": _("Action Channel"), "Game-Show": _("Game Show Channel"),
    "Educational": _("Documentary 42"),
}


def auto_lineup(progress=None, min_shows=5, min_movies=8, max_tv=14, mv_paths=None):
    """Build a sensible lineup from the Kodi library.

    Only channels a built-in station brands (its name and logo) are made, plus
    the TV Guide; anything else (a studio, a movie genre with no station) is the
    viewer's to add in the Channel manager.

    mv_paths: the music video folder the viewer chose in Build my lineup (when
    the library has no music videos).  Returns a list of channel dicts (not
    saved), or None if progress(msg, pct) returned True (the viewer pressed Cancel).
    """
    chans = [new_channel(2, _("TV Guide"), "guide")]
    weather = new_channel(WEATHER_NUMBER, _("Weather Channel"), "weather")
    num = 3

    def step(msg, pct):
        return bool(progress and progress(msg, pct))

    if step(_("Reading TV shows"), 5):
        return None
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
    # only genres a built-in station stands for (Comedy Corner, Orbit TV...)
    station_genres = set(g for st in stations.STATIONS for g in st["match"].get("genres", []))
    by_name = {}
    for n, name, gs in sized:
        if n < min_shows or len(by_name) >= max_tv or not station_genres.intersection(gs):
            continue
        by_name[name] = new_channel(num, name, "network", [{"type": "tvgenre", "value": g} for g in gs],
                                    _genre=True)
        chans.append(by_name[name])
        num += 1

    make_nets = len(shows) >= 12
    if shows and not by_name:
        # a small library: no genre has enough shows, so one channel airs them all
        chans.append(new_channel(num, _("Channel %d") % num, "network", [{"type": "alltv"}]))
        num += 1

    # no automatic decade channels (they only repeated the genre channels);
    # a decade is still a source you can pick in the channel editor
    if step(_("Reading movies"), 60):
        return None
    movies = library.all_movies()
    mg = Counter()
    for m in movies:
        for g in m.get("genre", []):
            mg[g] += 1
    if len(movies) >= min_movies:
        chans.append(new_channel(num, _("Movie Channel"), "movies", [{"type": "movies"}]))
        num += 1
    # movie genres only where a station stands for them (documentaries: The
    # Exploration Channel); no studio showcases - Disney is The Dexter Channel's
    movie_genres = set(g for st in stations.STATIONS for g in st["match"].get("movie_genres", []))
    for g, n in mg.most_common():
        if n < min_movies or g not in movie_genres:
            continue
        chans.append(new_channel(num, _("%s Movies") % g, "movies", [{"type": "movies", "genre": g}]))
        num += 1
    old = [m for m in movies if 0 < int(m.get("year") or 0) < 1990]
    if len(old) >= min_movies:
        chans.append(new_channel(num, _("Classic Movies"), "movies",
                                 [{"type": "movies", "years": [1900, 1989]}]))
        num += 1
    if step(_("Looking for music videos"), 92):
        return None
    mv = music_channel(num, mv_paths)
    if mv:
        chans.append(mv)
        num += 1
    # broadcast networks on the low numbers, right after the guide
    if make_nets:
        chans[1:1] = broadcast_networks(gcount, len(movies))
    if step(_("Done"), 100):
        return None
    chans.append(weather)
    stations.assign(chans)
    stations.extra_channels(chans, min_shows)
    without_station(chans)
    for c in chans:
        if c.get("type") in ("network", "movies", "loop"):
            c["home_guard"] = True      # topping up leaves a show's first-genre / network home alone
    drop_hollow(chans, min_shows)
    place_orphans(chans, shows, make_nets)
    renumber(chans)
    return chans


def without_station(chans):
    """Leave out channels no built-in station took (two genre channels for one
    station, say): Build my lineup only makes channels with a station's name
    and logo.  The TV Guide and a small library's all-shows channel stay."""
    import xbmc
    from .kodiutil import log
    for c in [c for c in chans if c.get("type") in ("network", "movies") and not c.get("station")
              and not any(s.get("type") == "alltv" for s in c.get("sources", []))]:
        chans.remove(c)
        log("%s: dropped, no built-in station for it" % c["name"], level=xbmc.LOGINFO)


def place_orphans(chans, shows, make_nets):
    """Shows whose genres are all too thin for a channel (or whose channel was
    dropped): onto the biggest genre network, by name (the channel manager can
    move them).  With broadcast networks, the genres their time blocks air count
    as covered: those shows air there."""
    genre = [c for c in chans if c.get("_genre")]
    if not genre:
        return
    covered = set(s["value"] for c in genre for s in c["sources"] if s.get("type") == "tvgenre")
    if make_nets:
        covered |= set(GENERAL) | set(g for row in NETWORK_DAY if row[4] != "movies" for g in row[4])
    orphans = sorted(s["title"] for s in shows if not covered.intersection(s.get("genre", [])))
    if orphans:
        genre[0]["sources"].append({"type": "tvshow", "value": orphans, "orphans": True})


def drop_hollow(chans, min_shows=5):
    """Leave out genre channels that fewer than min_shows shows would call home
    (their best match once the stations' networks are in): Action & Adventure is
    listed by many shows but first for almost none.  Their shows go to their
    next-best channel.  One at a time, emptiest first, since a dropped channel's
    shows may fill another.  Returns the dropped channels."""
    import xbmc
    from . import assign
    from .kodiutil import log
    dropped = []
    while True:
        genre = [c for c in chans if c.get("_genre")]
        if len(genre) < 2:          # keep at least one genre channel
            return dropped
        renumber(chans)             # for now: home ties go to the lower number
        # movies count too: The Dexter Channel lives on Disney's movies as well as its shows
        first = assign.compute(chans, md=assign.MODE_ALL, explain=True)["first"]
        homes = Counter(first.values())
        n, _num, worst = min((homes.get(c["id"], 0), -c["number"], c) for c in genre)
        if n >= min_shows:
            return dropped
        chans.remove(worst)
        dropped.append(worst)
        log("%s: dropped, %d shows would live here" % (worst.get("generic_name", worst["name"]), n),
            level=xbmc.LOGINFO)


def music_channel(number, paths=None):
    """Boombox: a music video channel when there are at least MIN_VIDEOS of them
    (a file count, so nothing is measured).  The survey rides along in
    "_survey" for Build my lineup's screens; save() leaves it out."""
    import time
    import xbmc
    from . import musicvideos
    from .kodiutil import log
    t0 = time.time()
    try:
        sv = library.musicvideo_survey(paths)
    except Exception as exc:
        log("music video survey failed: %s" % exc)
        return None
    log("music videos for Build my lineup: %d (%d in the library) in %.1f s" % (
        sv["total"], sv["lib"], time.time() - t0), level=xbmc.LOGINFO)
    if sv["total"] < musicvideos.MIN_VIDEOS:
        return None
    src = {"type": "musicvideos"}
    if paths:
        src["paths"] = list(paths)
    ch = new_channel(number, _("Music Videos"), "musicvideos", [src])
    ch["_survey"] = sv
    return ch


def renumber(chans, start=2):
    """Number channels 2, 3, 4... (or from `start`) in order, keeping weather on
    25 and news on 42 (and never giving those numbers to anything else while
    they're there)."""
    fixed = {}
    for c in chans:
        n = fixed_number(c)
        if n is not None and n not in fixed:
            fixed[n] = c
    taken = set(fixed)
    num = max(1, int(start))
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
