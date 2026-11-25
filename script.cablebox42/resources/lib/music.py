"""Music channels: DMX-style audio channels from the viewer's own music.

Read-only.  Songs come from Kodi's music library (JSON-RPC) and, for a music
folder, from the files' own tags as Kodi reads them (Files.GetFileDetails).
Nothing is ever looked up online and no tag, NFO, artwork or library entry is
written.  The only file written is CableBox's own cache of folder tags
(musicfiles.json in the add-on's data).

Song items (compact, they go into schedules):
    p path, d seconds, a artist, ak artist key, t title, al album, y year,
    tr track, g genre, r sample rate (Hz, 0 unknown), aid album id, arid artist ids
"""
import json
import os
import re
import threading
import time

import xbmcvfs

from . import kodiutil as K
from .kodiutil import _

AUDIO_EXT = (".mp3", ".flac", ".ogg", ".m4a", ".wav", ".aac", ".wma", ".opus", ".ape", ".wv", ".mka", ".alac")
SONG_PROPS = ["title", "artist", "displayartist", "album", "albumid", "artistid", "year", "genre",
              "track", "duration", "file", "samplerate", "displaycomposer"]
FILE_PROPS = ["title", "artist", "album", "year", "track", "duration", "genre"]
FILES_CACHE = os.path.join(K.PROFILE, "musicfiles.json")
MIN_SONG = 30                     # shorter files (jingles, skits) don't air
MIN_SONGS = 5                     # a channel needs at least this many songs
CACHE_TTL = 1800
_CACHE = {}                       # source key -> (when, [songs])
_LOCK = threading.Lock()
_JUNK = ("[missing tag]", "unknown", "unknown artist", "unknown album", "various", "<unknown>", "untitled")

SOURCE_KINDS = ("mgenre", "mdecade", "martist", "malbum", "mplaylist", "mfolder")


def is_music_source(src):
    return (src or {}).get("type") in SOURCE_KINDS


# ------------------------------------------------------------------ names
def clean(v):
    """A tag value, or '' for the placeholders Kodi and taggers use."""
    if isinstance(v, list):
        v = " / ".join(x for x in (clean(x) for x in v) if x)
    v = (v or "").strip() if isinstance(v, str) else ("" if v is None else str(v))
    return "" if v.lower() in _JUNK else v


def from_filename(path):
    """('Artist', 'Title') from a file name like '03 - Artist - Title.flac'
    or 'Artist - Title (Remastered).mp3'.  Artist may be ''."""
    base = os.path.splitext(re.split(r"[\\/]", path.rstrip("\\/"))[-1])[0]
    base = re.sub(r"[_]+", " ", base).strip()
    base = re.sub(r"^\s*(\d{1,3}|[A-D]\d{1,2})(\s*[-.)]\s*|\s+)", "", base)     # track number
    parts = [x.strip() for x in re.split(r"\s+-\s+", base) if x.strip()]
    if len(parts) >= 2:
        return parts[0], " - ".join(parts[1:])
    return "", base


def artist_key(song):
    a = (song.get("a") or "").strip().lower()
    return a or "#" + song["p"]      # no artist: never counts as a repeat


def _item(s):
    """Library / file details -> song item (None if it can't air)."""
    p = s.get("file") or ""
    d = int(s.get("duration") or 0)
    if not p or d < MIN_SONG:
        return None
    artist = clean(s.get("displayartist")) or clean(s.get("artist"))
    title = clean(s.get("title"))
    fa, ft = from_filename(p)
    if not title or title == os.path.splitext(os.path.basename(p))[0]:
        title = ft or title          # Kodi gives the bare file name when there's no title tag
        artist = artist or fa
    genre = clean(s.get("genre"))
    try:
        year = int(s.get("year") or 0)
    except (TypeError, ValueError):
        year = 0
    it = {"p": p, "d": d, "a": artist, "t": title or ft, "al": clean(s.get("album")), "y": year if year > 0 else 0,
          "tr": int(s.get("track") or 0), "g": genre, "r": int(s.get("samplerate") or 0),
          "aid": int(s.get("albumid") or 0), "arid": [int(x) for x in (s.get("artistid") or []) if x],
          "cp": clean(s.get("displaycomposer"))}
    it["ak"] = artist_key(it)
    return it


# ------------------------------------------------------------------ JSON-RPC
def _rpc(method, params):
    return K.rpc(method, params) or {}


_NO_COMPOSER = []         # [True] once Kodi refused displaycomposer


def _with_props(method, params):
    """Kodi 21 fails the whole request (SQL 'AND ()', Internal error) when
    displaycomposer is asked for and no song in the library has a composer:
    ask again without it, and leave it out from then on."""
    props = [p for p in SONG_PROPS if not (_NO_COMPOSER and p == "displaycomposer")]
    res = _rpc(method, dict(params, properties=props))
    if not res and "displaycomposer" in props:      # {} = an error (a result has at least 'limits')
        _NO_COMPOSER.append(True)
        res = _rpc(method, dict(params, properties=[p for p in props if p != "displaycomposer"]))
    return res


def _songs(filt=None):
    params = {}
    if filt is not None:
        params["filter"] = filt
    return _with_props("AudioLibrary.GetSongs", params).get("songs", []) or []


def library_has_music():
    res = _rpc("AudioLibrary.GetSongs", {"limits": {"start": 0, "end": 1}})
    return bool(res.get("songs"))


def genres():
    """[(genre, songs)] of the music library, most songs first."""
    res = _rpc("AudioLibrary.GetGenres", {})
    out = []
    for g in res.get("genres", []) or []:
        label = clean(g.get("label"))
        if not label:
            continue
        n = _rpc("AudioLibrary.GetSongs", {"filter": {"field": "genre", "operator": "is", "value": label},
                                           "limits": {"start": 0, "end": 1}}).get("limits", {}).get("total", 0)
        if n:
            out.append((label, n))
    return sorted(out, key=lambda x: (-x[1], x[0].lower()))


def decades():
    """[(1990, songs)] of the music library."""
    count = {}
    for s in _rpc("AudioLibrary.GetSongs", {"properties": ["year"]}).get("songs", []) or []:
        try:
            y = int(s.get("year") or 0)
        except (TypeError, ValueError):
            y = 0
        if y > 1900:
            count[y // 10 * 10] = count.get(y // 10 * 10, 0) + 1
    return sorted(count.items())


def artists():
    """[(artistid, name)] - every song artist, sorted by name."""
    res = _rpc("AudioLibrary.GetArtists", {"albumartistsonly": False, "properties": [],
                                           "sort": {"method": "artist", "ignorearticle": True}})
    return [(a["artistid"], a["label"]) for a in res.get("artists", []) or [] if clean(a.get("label"))]


def albums():
    """[(albumid, 'Artist - Album (Year)')] sorted by artist."""
    res = _rpc("AudioLibrary.GetAlbums", {"properties": ["displayartist", "year"],
                                          "sort": {"method": "artist", "ignorearticle": True}})
    out = []
    for a in res.get("albums", []) or []:
        name = clean(a.get("label"))
        if not name:
            continue
        who = clean(a.get("displayartist"))
        lab = "%s - %s" % (who, name) if who else name
        if a.get("year"):
            lab += " (%s)" % a["year"]
        out.append((a["albumid"], lab))
    return out


# ------------------------------------------------------------------ folder tags (cached)
_FILES = [None, False]            # [cache dict, dirty]


def _files_cache():
    if _FILES[0] is None:
        _FILES[0] = K.load_json(FILES_CACHE, {})
    return _FILES[0]


def _stamp(path):
    try:
        st = xbmcvfs.Stat(path)
        return "%d:%d" % (st.st_mtime(), st.st_size())
    except Exception:
        return ""


def _file_details(path):
    """Tags of a file Kodi's library doesn't have, as Kodi reads them (cached by date and size)."""
    cache = _files_cache()
    stamp = _stamp(path)
    hit = cache.get(path)
    if hit and hit[0] == stamp:
        return hit[1]
    res = _rpc("Files.GetFileDetails", {"file": path, "media": "music", "properties": FILE_PROPS})
    det = dict(res.get("filedetails") or {}, file=path)
    keep = {k: det.get(k) for k in FILE_PROPS + ["file"] if det.get(k) not in (None, "", [], 0)}
    cache[path] = [stamp, keep]
    _FILES[1] = True
    return keep


def save_files_cache():
    if _FILES[1] and _FILES[0] is not None:
        K.save_json(FILES_CACHE, _FILES[0])
        _FILES[1] = False


def _walk(path, depth=0):
    if depth > 8:
        return []
    if not path.endswith(("/", "\\")):
        path += "/"
    try:
        dirs, files = xbmcvfs.listdir(path)
    except Exception:
        return []
    out = [path + f for f in sorted(files) if f.lower().endswith(AUDIO_EXT)]
    for d in sorted(dirs):
        if not d.startswith("."):
            out.extend(_walk(path + d, depth + 1))
    return out


# ------------------------------------------------------------------ sources -> songs
def _source_songs(src):
    t = src.get("type")
    v = src.get("value")
    if t == "mgenre":
        return [_item(s) for s in _songs({"field": "genre", "operator": "is", "value": v})]
    if t == "mdecade":
        d = int(v)
        return [_item(s) for s in _songs({"and": [{"field": "year", "operator": "greaterthan", "value": str(d - 1)},
                                                   {"field": "year", "operator": "lessthan", "value": str(d + 10)}]})]
    if t == "martist":
        return [_item(s) for s in _songs({"artistid": int(src.get("id"))})]
    if t == "malbum":
        return [_item(s) for s in _songs({"albumid": int(src.get("id"))})]
    if t == "mplaylist":
        res = _with_props("Files.GetDirectory", {"directory": src.get("path", ""), "media": "music"})
        return [_item(f) for f in res.get("files", []) or [] if f.get("filetype") != "directory"]
    if t == "mfolder":
        path = src.get("path", "")
        lib = {}
        for s in _songs({"field": "path", "operator": "startswith", "value": path}):
            lib[s.get("file")] = s
        out = []
        for f in _walk(path):
            out.append(_item(lib.get(f) or _file_details(f)))
        save_files_cache()
        return out
    return []


def songs_for(sources):
    """The channel's songs (deduplicated, cached for half an hour)."""
    key = json.dumps(sources or [], sort_keys=True)
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and time.time() - hit[0] < CACHE_TTL:
            return hit[1]
    out, seen = [], set()
    for src in sources or []:
        try:
            for it in _source_songs(src):
                if it and it["p"] not in seen:
                    seen.add(it["p"])
                    out.append(it)
        except Exception as exc:               # one bad source never costs the channel
            K.log_err("music source %s: %s" % (src, exc))
    with _LOCK:
        _CACHE[key] = (time.time(), out)
    return out


def clear_cache():
    with _LOCK:
        _CACHE.clear()


def describe_source(s):
    t = s.get("type")
    if t == "mgenre":
        return _("Genre: %s") % s.get("value")
    if t == "mdecade":
        return _("Songs from the %ss") % s.get("value")
    if t == "martist":
        return _("Artist: %s") % s.get("value")
    if t == "malbum":
        return _("Album: %s") % s.get("value")
    if t == "mplaylist":
        return _("Smart playlist: %s") % os.path.basename(s.get("path", ""))
    if t == "mfolder":
        return _("Music folder: %s") % s.get("path", "")
    return t or ""


# ------------------------------------------------------------------ sample-rate groups
RATE_GROUPS = False       # Step 0: switch on if mixed rates make the audio output reopen (see CLAUDE.md)
RATE_MIN_SHARE = 0.15     # a rate with fewer songs joins the largest group


def rate_groups(songs):
    """{path: group}: one group per sample rate; small ones join the largest.
    Without RATE_GROUPS everything is one group."""
    if not RATE_GROUPS:
        return dict((s["p"], "all") for s in songs)
    count = {}
    for s in songs:
        count[s["r"]] = count.get(s["r"], 0) + 1
    known = dict((r, n) for r, n in count.items() if r)
    if not known:
        return dict((s["p"], "all") for s in songs)
    largest = max(known, key=lambda r: known[r])
    total = float(sum(count.values()))
    big = set(r for r, n in known.items() if n / total >= RATE_MIN_SHARE) | {largest}
    return dict((s["p"], str(s["r"] if s["r"] in big else largest)) for s in songs)


# ------------------------------------------------------------------ info panel
FACT_MAX = 150            # characters: one sentence that fits the panel without scrolling


def first_sentence(text):
    """The first sentence of a biography or review, or '' if it is too long to fit."""
    t = re.sub(r"\s+", " ", re.sub(r"\[/?[A-Za-z]+[^\]]*\]", "", text or "")).strip()
    if not t:
        return ""
    m = re.match(r"(.+?[.!?])(\s+[A-Z\"'(]|$)", t)
    s = m.group(1) if m else t
    return s if len(s) <= FACT_MAX else ""


def _years_active(v):
    v = clean(v)
    return v.replace(" ", "") if v else ""


def panel_pages(song, album=None, artist=None, track_total=0, also=None):
    """[(heading, text)] for the info panel: the file's tags first, then the music
    library's facts when there are any.  Never an empty heading or 'Unknown'."""
    pages = []
    al = song.get("al")
    if al:
        line = "%s (%d)" % (al, song["y"]) if song.get("y") else al
        if song.get("tr"):
            line += "[CR]" + (_("Track %d of %d") % (song["tr"], track_total) if track_total >= song["tr"]
                              else _("Track %d") % song["tr"])
        pages.append((_("From the album"), line))
    label = clean((album or {}).get("label"))
    if label:
        pages.append((_("Label"), label))
    if song.get("cp") and song["cp"] != song.get("a"):
        pages.append((_("Written by"), song["cp"]))
    if song.get("g"):
        pages.append((_("Genre"), song["g"]))
    if also:
        pages.append((_("Also on this album"), "[CR]".join(also[:3])))
    if artist:
        bits = []
        for key, fmt in (("formed", _("Formed %s")), ("born", _("Born %s"))):
            v = clean(artist.get(key))
            if v:
                bits.append(fmt % v)
                break
        ya = _years_active(artist.get("yearsactive"))
        if ya:
            bits.append(_("Active %s") % ya)
        st = clean(artist.get("style"))
        if st:
            bits.append(st)
        if bits:
            pages.append((song.get("a") or _("The artist"), "[CR]".join(bits[:3])))
        fact = first_sentence(artist.get("description"))
        if fact:
            pages.append((_("About %s") % song["a"] if song.get("a") else _("About the artist"), fact))
    review = first_sentence((album or {}).get("description"))
    if review and al:
        pages.append((_("About %s") % al, review))
    return pages


def song_details(song, channel_paths=None):
    """(album details, artist details, track total, also-on-album titles) for the
    song now playing.  A few small library reads, in the TV's own thread."""
    album = artist = None
    total = 0
    also = []
    if song.get("aid"):
        album = _rpc("AudioLibrary.GetAlbumDetails", {"albumid": song["aid"],
                                                      "properties": ["label", "description", "year"]}
                     ).get("albumdetails")
        tracks = _songs({"albumid": song["aid"]})
        total = max([int(s.get("track") or 0) for s in tracks] + [0])
        if channel_paths is not None:
            for s in sorted(tracks, key=lambda x: int(x.get("track") or 0)):
                if s.get("file") != song["p"] and s.get("file") in channel_paths and clean(s.get("title")):
                    also.append(clean(s.get("title")))
    if song.get("arid"):
        artist = _rpc("AudioLibrary.GetArtistDetails", {"artistid": song["arid"][0],
                                                        "properties": ["formed", "born", "yearsactive",
                                                                       "style", "description"]}
                      ).get("artistdetails")
        if artist:
            for k in ("yearsactive", "style"):
                if isinstance(artist.get(k), list):
                    artist[k] = ", ".join(x for x in artist[k][:3] if x)
    return album, artist, total, also
