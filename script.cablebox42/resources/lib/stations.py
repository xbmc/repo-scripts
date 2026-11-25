"""Stations: a channel's on-air identity - name, call letters and logo - which
can change through the day (CAM Jr. in the morning, Chameleon in the daytime,
Cam O Nite at night).

Two sources, the second overriding the first:
  * built-in station kits (resources/stations) that the automatic setup gives
    to matching channels;
  * the viewer's own stations folder (Settings > Channels):
        <Stations folder>/<channel name, call letters or number>/
            logo.png              the channel's logo
            bumps/ ids/ commercials/    clips used all day (optional)
            <block name>/         e.g. "CAM Jr." - the same, for that time block
A channel's branding blocks live in channels.json ("brand_blocks") so they can
be edited later in the channel manager.
"""
import os
import re
import time

import xbmcvfs

from . import kodiutil as K
from . import logos

STATION_DIR = os.path.join(K.ADDON_PATH, "resources", "stations")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp")

# Built-in fictional stations.  "match": which automatic channel gets it
# (first unclaimed channel that fits, in this order).
STATIONS = [
    # the three broadcast networks on 3, 4 and 5
    {"id": "keystone", "name": "Keystone", "call": "KEY", "logo": "keystone.png", "match": {"broadcast": 1},
     "networks": ["NBC", "The WB", "WB"]},
    {"id": "beacon", "name": "Beacon", "call": "BCN", "logo": "beacon.png", "match": {"broadcast": 2},
     "networks": ["CBS", "UPN", "The CW"]},
    {"id": "horizon", "name": "Horizon", "call": "HZN", "logo": "horizon.png", "match": {"broadcast": 3},
     "networks": ["ABC", "FOX", "Fox"]},
    {"id": "retrocast_weather", "name": "Retrocast Weather", "call": "RCW", "logo": "retrocast_weather.png",
     "match": {"type": "weather"}},
    {"id": "animation_station", "name": "Animation Station", "call": "ANI", "logo": "animation_station.png",
     "match": {"genres": ["Animation"]},
     "networks": ["Cartoon Network", "Adult Swim", "[adult swim]", "Boomerang", "Toonami"]},
    {"id": "chameleon", "name": "Chameleon", "call": "CAM", "logo": "chameleon.png",
     "match": {"genres": ["Children", "Kids", "Family"]},
     "networks": ["Nickelodeon", "Nick Jr.", "Nick Jr", "Nick", "TeenNick", "Noggin", "Nick at Nite", "Nicktoons"],
     "blocks": [{"name": "CAM Jr.", "call": "CAMJ", "start": "06:00", "end": "12:00", "logo": "cam_jr.png"},
                {"name": "Cam O Nite", "call": "CAMN", "start": "20:00", "end": "06:00", "logo": "cam_o_nite.png"}]},
    # stands in for the Disney Channel: Disney's (and Pixar's) shows and movies,
    # by studio ("Walt Disney Pictures", "Disney+"...), and Disney's own networks
    {"id": "dexter", "name": "The Dexter Channel", "call": "DEX", "logo": "dexter.png",
     "match": {"genres": ["Family"]},
     "networks": ["Disney Channel", "Disney Junior", "Disney XD", "Toon Disney", "Playhouse Disney", "ABC Family", "Freeform", "The Family Channel"],
     "studios": ["Disney", "Pixar"]},
    {"id": "exploration", "name": "The Exploration Channel", "call": "EXP", "logo": "exploration.png",
     "match": {"movie_genres": ["Documentary"]}},
    # public educational TV: documentary series plus anything tagged educational in
    # Kodi (tag Mister Rogers' Neighborhood "educational" and it airs here)
    {"id": "pes", "name": "PES", "call": "PES", "logo": "pes.png",
     "match": {"genres": ["Documentary", "Educational"]},
     "networks": ["PBS", "PBS Kids", "PBS KIDS", "PBS Kids Go!", "NET", "Discovery", "Discovery Channel", "National Geographic", "National Geographic Channel", "Nat Geo", "History", "The History Channel", "Smithsonian Channel", "Science Channel", "Animal Planet", "The Learning Channel"],
     "add_tags": ["educational", "pbs", "public tv", "public television"]},
    {"id": "comedy_corner", "name": "Comedy Corner", "call": "LOL", "logo": "comedy_corner.png",
     "match": {"genres": ["Comedy", "Sitcom"]},
     "networks": ["Comedy Central"]},
    {"id": "whodunit", "name": "Whodunit", "call": "WHO", "logo": "whodunit.png",
     "match": {"genres": ["Mystery"]},
     "networks": ["Hallmark Movies & Mysteries", "Hallmark Mystery"]},
    {"id": "tumbleweed_tv", "name": "Tumbleweed TV", "call": "WEST", "logo": "tumbleweed_tv.png",
     "match": {"genres": ["Western"]},
     "networks": ["INSP", "Grit", "GRIT"]},
    {"id": "curtain_call", "name": "Curtain Call", "call": "ACT", "logo": "curtain_call.png",
     "match": {"genres": ["Drama"]}},
    {"id": "news_42", "name": "News 42", "call": "NEWS", "logo": "news_42.png",
     "match": {"genres": ["News"]},
     "networks": ["CNN", "MSNBC", "Fox News", "Fox News Channel", "CNBC", "HLN", "Headline News", "C-SPAN"]},
    {"id": "siren_tv", "name": "Siren TV", "call": "SRN", "logo": "siren_tv.png",
     "match": {"genres": ["Crime"]},
     "networks": ["Court TV", "truTV", "Investigation Discovery", "ID"]},
    # Korean and Chinese (incl. Taiwanese) dramas: no genre of their own, so by
    # network, or by an original title in Hangul or Chinese characters (dramas a
    # streaming service made); dramas only, never cartoons, documentaries or variety
    {"id": "red_thread_tv", "name": "Red Thread TV", "call": "RED", "logo": "red_thread_tv.png",
     "bug": "red_thread_tv_bug.png", "match": {},
     "networks": ["KBS1", "KBS2", "KBS", "MBC", "SBS", "tvN", "JTBC", "OCN", "ENA", "Channel A", "MBN",
                  "TV Chosun", "Mnet",
                  "CCTV", "CCTV-8", "Hunan TV", "Zhejiang TV", "Dragon TV", "Jiangsu TV", "Beijing TV",
                  "Tencent Video", "iQiyi", "iQIYI", "Youku", "Mango TV", "Bilibili",
                  "CTV", "CTS", "TTV", "FTV", "SET Metro", "SET TV", "GTV"],
     "scripts": ["hangul", "han"],
     "not_genres": ["Animation", "Kids", "Documentary", "Reality", "News", "Talk"]},
    {"id": "heartstrings_tv", "name": "Heartstrings TV", "call": "LUV", "logo": "heartstrings_tv.png",
     "match": {"genres": ["Soap"]},
     "networks": ["SOAPnet", "Lifetime", "Hallmark Channel"]},
    {"id": "high_octane_tv", "name": "High Octane TV", "call": "HOT", "logo": "high_octane_tv.png",
     "match": {"genres": ["Action & Adventure", "Action"]},
     "networks": ["Spike", "Spike TV", "TNN"]},
    {"id": "unscripted", "name": "Unscripted", "call": "REC", "logo": "unscripted.png",
     "match": {"genres": ["Reality"]},
     "networks": ["Bravo", "E!", "TLC", "Oxygen", "VH1"]},
    {"id": "jackpot_tv", "name": "Jackpot TV", "call": "WIN", "logo": "jackpot_tv.png",
     "match": {"genres": ["Game Show", "Game-Show"]},
     "networks": ["Game Show Network", "GSN", "Buzzr"]},
    {"id": "popcorn_tv", "name": "Popcorn TV", "call": "POP", "logo": "popcorn_tv.png",
     "match": {"all_movies": True}},
    {"id": "picture_show", "name": "Picture Show", "call": "PIX", "logo": "picture_show.png",
     "match": {"classic_movies": True}},
    # science fiction and fantasy: TMDB gives TV shows one genre for both
    # ("Sci-Fi & Fantasy"; "Science Fiction" is for movies), so fantasy airs here too
    {"id": "orbit_tv", "name": "Orbit TV", "call": "ORB", "logo": "orbit_tv.png",
     "match": {"genres": ["Science Fiction", "Sci-Fi & Fantasy"]},
     "networks": ["Syfy", "SyFy", "Sci Fi Channel", "SCI FI", "Sci-Fi Channel", "Sci Fi"]},
    # the music video channel (Build my lineup offers it from 30 music videos)
    {"id": "boombox_tv", "name": "Boombox TV", "call": "BOOM", "logo": "boombox_tv.png",
     "match": {"type": "musicvideos"}},
    # the Behind the scenes channel (movie Extras); its corner bug is a simpler picture
    {"id": "backlot", "name": "BACKLOT", "call": "LOT", "logo": "backlot.png", "bug": "backlot_bug.png",
     "match": {"type": "extras"}},
]
BY_ID = {s["id"]: s for s in STATIONS}

# The station ID card's tagline (the bottom strip): original lines, English here,
# looked up in strings.po.  A block's own line beats its station's.  Channels
# without a built-in station have none (the strip stays empty).
TAGLINES = {
    "keystone": "Your hometown station",
    "beacon": "Shining bright every night",
    "horizon": "Look ahead to great TV",
    "retrocast_weather": "Your forecast, around the clock",
    "animation_station": "Cartoons all day, every day",
    "chameleon": "Every color of fun",
    "dexter": "Fun for the whole family",
    "exploration": "See the world from your couch",
    "pes": "Learning never looked so good",
    "comedy_corner": "Laughs around the clock",
    "whodunit": "Every clue, every night",
    "tumbleweed_tv": "Saddle up for the classics",
    "curtain_call": "Great stories, beautifully told",
    "news_42": "The news, whenever you want it",
    "siren_tv": "Crime and justice, all night long",
    "red_thread_tv": "Stories that tie hearts together",
    "heartstrings_tv": "Stories straight from the heart",
    "high_octane_tv": "Turn it up",
    "unscripted": "Real people. Real TV.",
    "jackpot_tv": "Everybody plays, everybody wins",
    "popcorn_tv": "Movies, all night long",
    "picture_show": "The golden age of the movies",
    "orbit_tv": "Out of this world",
    "boombox_tv": "Turn up the music",
    "backlot": "Behind the scenes, all day",
}
BLOCK_TAGLINES = {
    ("chameleon", "CAM Jr."): "Big fun for little viewers",
    ("chameleon", "Cam O Nite"): "Classic TV after dark",
}


def tagline(ch, ts=None):
    """The station's tagline at ts ('' for a channel without a built-in station)."""
    base = BY_ID.get((ch or {}).get("station") or "")
    if not base:
        return ""
    b = block_at(ch, time.time() if ts is None else ts)
    line = BLOCK_TAGLINES.get((base["id"], b.get("name"))) if b else None
    line = line or TAGLINES.get(base["id"], "")
    return K._(line) if line else ""


def builtin_logo(fname):
    return os.path.join(STATION_DIR, fname) if fname else ""


# ------------------------------------------------------------------ automatic setup
def _channel_genres(ch):
    return [s.get("value") for s in ch.get("sources", []) if s.get("type") == "tvgenre"]


def _fits(station, ch):
    m = station["match"]
    if ch.get("broadcast") or m.get("broadcast"):
        return bool(m.get("broadcast")) and ch.get("broadcast") == m["broadcast"]
    if m.get("type"):
        return ch.get("type") == m["type"]
    if ch.get("type") in ("guide", "weather"):
        return False
    if m.get("alltv"):
        return any(s.get("type") == "alltv" for s in ch.get("sources", []))
    if m.get("genres"):
        g = _channel_genres(ch)
        return any(x in g for x in m["genres"])
    if m.get("classic_movies"):        # old movies only (Classic Movies: before 1990)
        return ch.get("type") == "movies" and any(
            s.get("type") == "movies" and s.get("years") and int(s["years"][1]) < 2000 and not s.get("genre")
            for s in ch.get("sources", []))
    if m.get("all_movies"):            # the main movie channel: every movie, no filter
        return ch.get("type") == "movies" and any(
            s.get("type") == "movies" and not any(s.get(k) for k in ("genre", "years", "set", "tag"))
            for s in ch.get("sources", []))
    if m.get("movie_genres"):
        return any(s.get("type") == "movies" and s.get("genre") in m["movie_genres"] for s in ch.get("sources", []))
    if m.get("name_words"):
        return any(w in ch.get("name", "").lower() for w in m["name_words"])
    return False


def is_kit_block(b):
    """A time-of-day name that came with a built-in station (CAM Jr.), not one the
    viewer made.  Kits mark theirs "kit"; ones saved before that carry the kit's
    logo file name ("logo"), which the viewer's own never have (theirs is "logo_path")."""
    return bool(b.get("kit") or b.get("logo"))


def _plain(src):
    """A source without the notes a station leaves on it (to compare two)."""
    return dict((k, v) for k, v in src.items() if k not in ("station_extra", "core"))


def _has_source(sources, src):
    want = _plain(src)
    return any(_plain(s) == want for s in sources or [])


def _brings(station):
    """The sources a station adds to a channel's programming (its tags first)."""
    out = []
    if station.get("add_tags"):
        tags = _library_tags(station["add_tags"])
        if tags:
            out.append({"type": "tag", "value": tags, "what": "both", "station_extra": True})
    return out + station_sources(station)


def changes(ch, station):
    """What choosing this station would change on the channel, for the question:
    {name, call, blocks: [names], adds: [sources], removes: [sources]}."""
    old = BY_ID.get(ch.get("station") or "")
    removes = []
    if old and old["id"] != station["id"]:
        removes = [s for s in ch.get("sources", []) if s.get("station_extra")] + list(ch.get("own") or [])
    kept = [s for s in ch.get("sources", []) if not s.get("station_extra")]
    if ch.get("broadcast"):         # a network's own shows air in full; they aren't a source
        adds = station_sources(station)[:1]
    else:
        adds = [s for s in _brings(station) if not _has_source(kept, s)]
    return {"name": station["name"], "call": station["call"],
            "blocks": [b["name"] for b in station.get("blocks", [])], "adds": adds, "removes": removes}


def apply(ch, station):
    """Give a channel a built-in station: its brand (name, call letters, logo,
    time-of-day names) and its shows.  A station the channel already had goes
    first, brand and shows, so switching never piles up; time-of-day names the
    viewer made and programming the viewer added stay."""
    generic = ch.get("generic_name")
    if ch.get("station"):
        drop(ch, keep_shows=False)
    ch["generic_name"] = generic or ch["name"]
    ch["station"] = station["id"]
    ch["name"] = station["name"]
    ch["callsign"] = station["call"]
    mine = [b for b in ch.get("brand_blocks") or [] if not is_kit_block(b)]
    ch["brand_blocks"] = mine + [dict(b, kit=True) for b in station.get("blocks", [])]
    brings = _brings(station)
    if ch.get("broadcast"):
        extra = station_sources(station)
        if extra:
            # a broadcast network's own shows (Keystone <- NBC): in full in its
            # prime time and its general programming, not dealt out like the rest
            src = extra[0]
            ch["own"] = [src]
            for dp in ch.get("dayparts", []):
                if dp.get("prime"):
                    dp["own"] = [dict(src)]
        brings = [s for s in brings if s.get("type") == "tag"]
    for src in brings:
        if not _has_source(ch.setdefault("sources", []), src):      # never the same source twice
            ch["sources"].append(src)


def station_sources(station):
    """The sources a station brings to its channel: its networks as the library
    spells them, (The Dexter Channel) shows and movies whose studio contains a
    name, and (Red Thread TV) original titles in a script.  A station's not_genres
    ride along, so Red Thread TV never picks up a cartoon or a documentary."""
    out = []
    bad = {"not_genres": list(station["not_genres"])} if station.get("not_genres") else {}
    nets = _library_networks(station.get("networks"))
    if nets:
        out.append(dict({"type": "network", "value": nets, "station_extra": True}, **bad))
    if station.get("studios"):
        out.append({"type": "studio", "value": list(station["studios"]), "what": "both", "station_extra": True})
    if station.get("scripts"):
        out.append(dict({"type": "origtitle", "value": list(station["scripts"]), "station_extra": True}, **bad))
    return out


_NETS = [0, {}]


def _network_counts():
    import time as _t
    if _t.time() - _NETS[0] > 60:
        try:
            from . import library
            _NETS[1] = library.network_counts()
        except Exception:
            _NETS[1] = {}
        _NETS[0] = _t.time()
    return _NETS[1]


def _library_networks(names):
    """The library's spellings of these networks ('Nick Jr.', 'PBS Kids'), exact names only."""
    want = set(n.lower() for n in (names or []))
    return sorted(n for n in _network_counts() if n.lower() in want)


def network_shows(station):
    """How many titles a station would get from its networks (and its studios'
    shows and movies, its original-title scripts)."""
    if station.get("scripts") or station.get("not_genres") or station.get("studios"):
        # each title once, cartoons etc. left out (one library call per kind)
        try:
            from . import library
            return len(library.station_titles(_library_networks(station.get("networks")),
                                              station.get("scripts"), station.get("not_genres"),
                                              station.get("studios")))
        except Exception:
            return 0
    nets = set(n.lower() for n in _library_networks(station.get("networks")))
    return sum(c for n, c in _network_counts().items() if n.lower() in nets)


def _library_tags(words):
    """Kodi tags containing any of the words, any capitalisation ('Educational', 'PBS Kids')."""
    try:
        from . import library
        return [t for t in library.all_tags() if any(w in t.lower() for w in words)]
    except Exception:
        return []


def assign(chans):
    """Automatic setup: each built-in station goes to the first channel that fits it.
    Genre preference follows the station's own order (Chameleon prefers a
    Children channel to a Family one)."""
    taken = set()
    for st in STATIONS:
        prefs = st["match"].get("genres")
        order = []
        if prefs:
            for g in prefs:
                order += [c for c in chans if g in _channel_genres(c)]
        order += chans
        for ch in order:
            if id(ch) in taken or ch.get("station") or not _fits(st, ch):
                continue
            apply(ch, st)
            taken.add(id(ch))
            break
    _separate_networks(chans)
    return chans


def _separate_networks(chans):
    """Each broadcast network keeps its own shows: Seinfeld (NBC) is on Keystone,
    never dealt out to Beacon or Horizon."""
    nets = [c for c in chans if c.get("broadcast")]
    if not nets:
        return
    from . import library
    own = {}
    for c in nets:
        own[c["id"]] = set(s["title"] for s in library.resolve(c.get("own") or [])["series"]) if c.get("own") else set()
    # and cable shows (Nickelodeon, Comedy Central...) never air on a network
    cable = set()
    for st in STATIONS:
        if st.get("networks") and not st["match"].get("broadcast"):
            srcs = station_sources(st)
            if srcs:
                cable |= set(s["title"] for s in library.resolve(srcs)["series"])
    for c in nets:
        others = (set().union(*[t for cid, t in own.items() if cid != c["id"]]) | cable) - own[c["id"]]
        if others:
            c["exclude"] = sorted(set(c.get("exclude", [])) | others)


def addable():
    """Built-in stations Add a channel offers: the ones that air shows or movies
    (the Guide, Weather, Boombox and BACKLOT are channel kinds of their own)."""
    return [s for s in STATIONS if not s["match"].get("type")]


def starter(station):
    """(channel type, sources) a channel starts with before the station brings
    its own: the genres it stands for that the library has, or its movies."""
    m = station["match"]
    if m.get("all_movies"):
        return "movies", [{"type": "movies"}]
    if m.get("classic_movies"):
        return "movies", [{"type": "movies", "years": [1900, 1989]}]
    if m.get("movie_genres"):
        return "movies", [{"type": "movies", "genre": g} for g in m["movie_genres"]]
    have = set()
    if m.get("genres"):
        try:
            from . import library
            have = set(g for s in library.all_tvshows() for g in s.get("genre", []))
        except Exception:
            have = set()
    return "network", [{"type": "tvgenre", "value": g} for g in m.get("genres", []) if g in have]


def extra_channels(chans, min_shows=5):
    """A station whose real networks you have plenty of shows from gets its own
    channel even when no genre channel suited it (6 Nickelodeon shows, no
    Children channel: Chameleon anyway; 5 Disney movies: The Dexter Channel)."""
    from . import channels as C
    have = set(c.get("station") for c in chans if c.get("station"))
    made = []
    for st in STATIONS:
        if st["id"] in have or not st.get("networks") or st["match"].get("broadcast") or st["match"].get("type"):
            continue
        if network_shows(st) >= min_shows:
            ch = C.new_channel(0, st["name"], "network", [])
            apply(ch, st)
            if ch["sources"]:
                chans.append(ch)
                made.append(ch)
    return made


def own_name(ch):
    """The name the channel has once its built-in station's brand is gone: the
    viewer's rename if there is one, otherwise the plain name from before."""
    st = BY_ID.get(ch.get("station") or "")
    if st and ch.get("name") == st["name"]:
        return ch.get("generic_name") or ch["name"]
    return ch.get("name", "")


def own_callsign(ch):
    """Its call letters then: the ones the viewer typed, otherwise made from the name."""
    from . import channels as C
    st = BY_ID.get(ch.get("station") or "")
    cs = ch.get("callsign") or ""
    kit = set([st["call"]] + [b.get("call") for b in st.get("blocks", [])]) if st else set()
    return cs if cs and cs not in kit else C.callsign(own_name(ch))


def drop(ch, keep_shows=True):
    """Take the built-in station's brand off the channel: its logo, its
    time-of-day names and (unless the viewer renamed the channel or typed call
    letters) its name and call letters.  The viewer's rename, own time-of-day
    names and own programming always stay.

    keep_shows=True (Make this channel my own): the station's shows stay as
    ordinary programming.  False (another station takes over, or the station is
    already on another channel): they go with it."""
    if not ch.get("station"):
        return
    name, call = own_name(ch), own_callsign(ch)
    ch["name"], ch["callsign"] = name, call
    for k in ("station", "generic_name"):
        ch.pop(k, None)
    blocks = [b for b in ch.get("brand_blocks") or [] if not is_kit_block(b)]
    if blocks:
        ch["brand_blocks"] = blocks
    else:
        ch.pop("brand_blocks", None)
    if keep_shows:
        for src in list(ch.get("sources", [])) + list(ch.get("own") or []) + \
                [s for dp in ch.get("dayparts", []) for s in dp.get("own") or []]:
            if src.pop("station_extra", None) and src.get("type") == "studio":
                src["core"] = True          # still counts like a network when shows find their home
    else:
        ch["sources"] = [x for x in ch.get("sources", []) if not x.get("station_extra")]
        ch.pop("own", None)
        for dp in ch.get("dayparts", []):
            dp.pop("own", None)


# ------------------------------------------------------------------ the viewer's folders
def _key(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


_DIR_CACHE = {}
_DIR_TTL = 120


def _listdir(path):
    hit = _DIR_CACHE.get(path)
    if hit and time.time() - hit[0] < _DIR_TTL:
        return hit[1]
    try:
        dirs, files = xbmcvfs.listdir(path)
    except Exception:
        dirs, files = [], []
    _DIR_CACHE[path] = (time.time(), (dirs, files))
    return dirs, files


def _join(folder, name):
    return folder + ("" if folder.endswith(("/", "\\")) else "/") + name


def _subfolder(folder, *names, **kw):
    """The subfolder of `folder` named like the first of `names` that has one
    (case and punctuation don't matter).  loose=True also accepts a folder
    whose name ends with it ("Morning - CAM Jr" for "CAM Jr."), for time blocks
    only - for channels that let "Disney Showcase 13" pass for channel 3."""
    if not folder:
        return ""
    dirs, _f = _listdir(folder)
    keyed = sorted((_key(d), d) for d in dirs)
    for n in names:
        w = _key(n)
        if not w:
            continue
        for k, d in keyed:
            if k == w:
                return _join(folder, d) + "/"
        if kw.get("loose") and len(w) >= 3:
            for k, d in keyed:
                if k.endswith(w):
                    return _join(folder, d) + "/"
    return ""


def folder_names(ch):
    """Folder names that count as this channel's, best first."""
    num = str(ch.get("number", "") or "")
    return [n for n in (ch.get("name"), ch.get("callsign"),
                        num and "Channel " + num, num and "CH " + num, num) if n]


def _image_in(folder):
    if not folder:
        return ""
    _d, files = _listdir(folder)
    for f in sorted(files):
        stem, ext = os.path.splitext(f)
        if ext.lower() in IMAGE_EXT and _key(stem) in ("logo", ""):
            return _join(folder, f)
    for f in sorted(files):
        if os.path.splitext(f)[1].lower() in IMAGE_EXT:
            return _join(folder, f)
    return ""


def channel_folder(ch):
    root = K.setting("stations_folder", "")
    if not root or not ch:
        return ""
    return _subfolder(root, *folder_names(ch))


# ------------------------------------------------------------------ identity at a moment
def _minutes(hm):
    try:
        h, m = hm.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return None


def block_at(ch, ts):
    """The branding block on air at ts (or None)."""
    blocks = (ch or {}).get("brand_blocks") or []
    if not blocks:
        return None
    lt = time.localtime(ts)
    now = lt.tm_hour * 60 + lt.tm_min
    for b in blocks:
        s, e = _minutes(b.get("start", "")), _minutes(b.get("end", ""))
        if s is None or e is None or s == e:
            continue
        if (s < e and s <= now < e) or (s > e and (now >= s or now < e)):
            return b
    return None


def brand(ch, ts=None):
    """{name, call, logo, bug, logo_from, folder...} for the channel at ts: the one
    place that decides which logo shows.  Anything the viewer supplies beats a
    built-in logo:
        a time block's folder image > its picked image > its logo-folder match
        > its built-in logo
        > the image picked in the editor > the station folder's logo
        > the logo folder (name, call letters, number) > the built-in station logo
    logo_from says which: block_folder, block_picked, block_logofolder, builtin,
    picked, folder, logofolder, none, or '' (no logo)."""
    ts = time.time() if ts is None else ts
    base = BY_ID.get((ch or {}).get("station") or "")
    folder = channel_folder(ch)
    b = block_at(ch, ts)
    name = ch.get("name", "") if ch else ""
    call = (ch or {}).get("callsign", "")
    logo_own = (ch or {}).get("logo") or ""
    logo, src = "", ""
    kit = None              # the built-in kit entry the logo came from (it may have its own corner bug)
    bfolder = ""
    if b:
        name = b.get("name") or name
        call = b.get("call") or call
        bfolder = _subfolder(folder, b.get("name"), b.get("call"), loose=True) if folder else ""
        for path, where in ((_image_in(bfolder), "block_folder"), (b.get("logo_path") or "", "block_picked"),
                            (logos.folder_logo(b.get("name"), b.get("call")) if logo_own != "none" else "",
                             "block_logofolder"),
                            (builtin_logo(b.get("logo")) if base and b.get("logo") else "", "builtin")):
            if path:
                logo, src = path, where
                kit = b if where == "builtin" else None
                break
    if not logo:
        if logo_own and logo_own != "none":
            logo, src = logo_own, "picked"
        elif logo_own != "none":
            logo = _image_in(folder)
            src = "folder" if logo else ""
            if not logo:
                logo = logos.folder_logo(ch.get("name"), ch.get("callsign"), str(ch.get("number", "")))
                src = "logofolder" if logo else ""
            if not logo and base:
                logo, src, kit = builtin_logo(base["logo"]), "builtin", base
        else:
            src = "none"
    # corner bug: a kit's simpler 'bug' image when it has one, else the logo itself
    bug = builtin_logo(kit["bug"]) if kit and kit.get("bug") else logo
    return {"name": name, "call": call, "logo": logo, "bug": bug, "logo_from": src, "folder": folder,
            "block_folder": bfolder, "block": b.get("name") if b else ""}


# a channel's clip folders, and other names the viewer might give them
KIND_NAMES = {"bumps": ("bumps", "bumpers"), "ids": ("ids", "station ids", "idents"),
              "commercials": ("commercials", "ads"), "promos": ("promos", "promo")}
VIDEO_EXT = (".mp4", ".mkv", ".avi", ".mov", ".m4v", ".mpg", ".mpeg", ".ts", ".wmv", ".webm", ".flv", ".divx")


def kind_folder(folder, kind):
    return _subfolder(folder, *KIND_NAMES.get(kind, (kind,)), loose=True) if folder else ""


def clip_folder(ch, ts, kind):
    """bumps / ids / commercials folder from the viewer's station folders for this
    moment (block folder first, then the channel's), or ''."""
    br = brand(ch, ts)
    for f in (br["block_folder"], br["folder"]):
        sub = kind_folder(f, kind)
        if sub:
            return sub
    return ""


def count_clips(folder):
    """Video files in a folder (not its subfolders) - a quick count, nothing probed."""
    if not folder:
        return 0
    _d, files = _listdir(folder)
    return sum(1 for f in files if f.lower().endswith(VIDEO_EXT))


# ------------------------------------------------------------------ folders on disk
def root():
    return K.setting("stations_folder", "")


def orphan_folders(chans):
    """Folders in the stations folder that belong to no channel (often a channel
    renamed since the folder was made)."""
    r = root()
    if not r:
        return []
    used = set()
    for c in chans:
        f = channel_folder(c)
        if f:
            used.add(_key(f.rstrip("/\\").replace("\\", "/").split("/")[-1]))
    dirs, _f = _listdir(r)
    return sorted(d for d in dirs if _key(d) not in used and not d.startswith("."))


def rename_folder(old_name, new_name):
    """Rename a channel's station folder (after the channel was renamed).
    Never overwrites: returns False if the new name is taken or it fails."""
    r = root()
    if not r or not old_name or not new_name:
        return False
    src, dst = _join(r, old_name) + "/", _join(r, new_name) + "/"
    if xbmcvfs.exists(dst):
        return False
    try:
        ok = bool(xbmcvfs.rename(src, dst))
    except Exception:
        ok = False
    clear_cache()
    return ok


def clear_cache():
    _DIR_CACHE.clear()

def clips_fingerprint(chans):
    """What the station folders hold for these channels (clip file names per kind,
    time-block folders too), read fresh: refresh-on-close compares it before and
    after (manager.refresh_if_changed)."""
    import hashlib
    import json
    clear_cache()
    out = []
    for ch in chans:
        f = channel_folder(ch)
        if not f:
            continue
        folders = [f] + [_subfolder(f, b.get("name"), b.get("call"), loose=True)
                         for b in ch.get("brand_blocks") or []]
        for folder in folders:
            for kind in sorted(KIND_NAMES):
                sub = kind_folder(folder, kind)
                if sub:
                    out.append([ch.get("id"), sub, sorted(x for x in _listdir(sub)[1]
                                                          if x.lower().endswith(VIDEO_EXT))])
    return hashlib.md5(json.dumps(out, sort_keys=True).encode("utf-8")).hexdigest()

