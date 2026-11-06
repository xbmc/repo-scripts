"""Stations: a channel's on-air identity - name, call letters and logo - which
can change through the day (CAM Jr. in the morning, Chameleon in the daytime,
Cam O Nite at night).

Two sources, the second overriding the first:
  * built-in station kits (resources/stations) that the automatic setup gives
    to matching channels;
  * the viewer's own stations folder (Settings > Viewing):
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
    {"id": "dexter", "name": "The Dexter Channel", "call": "DEX", "logo": "dexter.png",
     "match": {"genres": ["Family"]},
     "networks": ["Disney Channel", "Disney Junior", "Disney XD", "Toon Disney", "Playhouse Disney", "ABC Family", "Freeform", "The Family Channel"]},
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
    # science fiction only ("Sci-Fi & Fantasy" alone doesn't qualify)
    {"id": "orbit_tv", "name": "Orbit TV", "call": "ORB", "logo": "orbit_tv.png",
     "match": {"genres": ["Science Fiction"]},
     "networks": ["Syfy", "SyFy", "Sci Fi Channel", "SCI FI", "Sci-Fi Channel", "Sci Fi"]},
    {"id": "boombox_tv", "name": "Boombox TV", "call": "BOOM", "logo": "boombox_tv.png",
     "match": {"name_words": ["music"]},
     "networks": ["MTV", "MTV2", "CMT"]},
]
BY_ID = {s["id"]: s for s in STATIONS}


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


def apply(ch, station):
    """Give a channel a built-in station's identity (name, call letters, blocks)."""
    ch.setdefault("generic_name", ch["name"])
    ch["station"] = station["id"]
    ch["name"] = station["name"]
    ch["callsign"] = station["call"]
    ch["brand_blocks"] = [dict(b) for b in station.get("blocks", [])]
    if station.get("add_tags"):
        tags = _library_tags(station["add_tags"])
        if tags:
            ch.setdefault("sources", []).append({"type": "tag", "value": tags, "what": "both", "station_extra": True})
    nets = _library_networks(station.get("networks"))
    if nets:
        src = {"type": "network", "value": nets, "station_extra": True}
        if ch.get("broadcast"):
            # a broadcast network's own shows (Keystone <- NBC): in full in its
            # prime time and its general programming, not dealt out like the rest
            ch["own"] = [src]
            for dp in ch.get("dayparts", []):
                if dp.get("prime"):
                    dp["own"] = [dict(src)]
        else:
            ch.setdefault("sources", []).append(src)


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
            nets_lib = _library_networks(st["networks"])
            if nets_lib:
                cable |= set(s["title"] for s in library.resolve([{"type": "network", "value": nets_lib}])["series"])
    for c in nets:
        others = (set().union(*[t for cid, t in own.items() if cid != c["id"]]) | cable) - own[c["id"]]
        if others:
            c["exclude"] = sorted(set(c.get("exclude", [])) | others)


def extra_channels(chans, min_shows=5):
    """A station whose real networks you have plenty of shows from gets its own
    channel even when no genre channel suited it (6 Nickelodeon shows, no
    Children channel: Chameleon anyway)."""
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


def drop(ch):
    """Back to the channel's plain name (e.g. the station is already used elsewhere)."""
    if ch.get("station"):
        ch["name"] = ch.pop("generic_name", ch["name"])
        for k in ("station", "brand_blocks", "callsign", "own"):
            ch.pop(k, None)
        ch["sources"] = [x for x in ch.get("sources", []) if not x.get("station_extra")]
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
    """{name, call, logo, folder} for the channel at ts.  The viewer's own folder
    beats the built-in kit; a block's own folder beats the channel's."""
    ts = time.time() if ts is None else ts
    base = BY_ID.get((ch or {}).get("station") or "")
    folder = channel_folder(ch)
    b = block_at(ch, ts)
    name = ch.get("name", "") if ch else ""
    call = (ch or {}).get("callsign", "")
    logo_own = (ch or {}).get("logo") or ""
    logo, src = "", ""
    bfolder = ""
    if b:
        name = b.get("name") or name
        call = b.get("call") or call
        bfolder = _subfolder(folder, b.get("name"), b.get("call"), loose=True) if folder else ""
        for path, where in ((_image_in(bfolder), "block_folder"), (b.get("logo_path") or "", "block_picked"),
                            (builtin_logo(b.get("logo")) if base and b.get("logo") else "", "builtin")):
            if path:
                logo, src = path, where
                break
    if not logo:
        if logo_own and logo_own != "none":
            logo, src = logo_own, "picked"
        elif logo_own != "none":
            logo = _image_in(folder)
            src = "folder" if logo else ""
            if not logo and base:
                logo, src = builtin_logo(base["logo"]), "builtin"
        else:
            src = "none"
    return {"name": name, "call": call, "logo": logo, "logo_from": src, "folder": folder,
            "block_folder": bfolder, "block": b.get("name") if b else ""}


# a channel's clip folders, and other names the viewer might give them
KIND_NAMES = {"bumps": ("bumps", "bumpers"), "ids": ("ids", "station ids", "idents"),
              "commercials": ("commercials", "ads")}
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
