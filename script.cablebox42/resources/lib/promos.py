"""Schedule promos: "Channel 7 - Seinfeld: The Contest - Up next".

Everything comes from the viewer's own library and is only ever *read*:
Kodi's own artwork and plot first (JSON-RPC), the files next to the episode
and in the show's folder as a fallback.  Nothing in the library is written,
moved or renamed.

    background  episode thumb > fanart > landscape > poster (letterboxed) > station card
    logo        clearlogo (only once it's in Kodi's texture cache) > the show's title
    music       the show's theme.mp3 > a small built-in bed
"""
import datetime
import os
import re
import threading
import time
from urllib.parse import unquote

import xbmc
import xbmcvfs

from . import library
from . import kodiutil as K
from .kodiutil import rpc, log, media, _

PROMO_LEN = 15.0            # seconds of an image promo in a break
EXTRAS_MAX = 120.0          # Extras clips longer than this never air as promos
BED = media("promo_bed.wav")     # WAV: the Kodi repository checker allows wav, not mp3

_CACHE = {}
_CACHE_TTL = 1800
_LOCK = threading.Lock()

_SEASON_DIR = re.compile(r"^(season\s*\d+|s\d+|specials?)$", re.I)
_EXTRAS_DIRS = ("Extras", "extras", "EXTRAS")
_EXTRAS_WORDS = ("promo", "trailer")


# ------------------------------------------------------------------ paths
def _sep(path):
    return "\\" if ("\\" in path and "/" not in path) else "/"


def _parent(path):
    """Folder of a file or folder path, with its trailing separator."""
    p = path.rstrip("/\\")
    i = max(p.rfind("/"), p.rfind("\\"))
    return p[:i + 1] if i >= 0 else ""


def _join(folder, name):
    if not folder:
        return ""
    if not folder.endswith(("/", "\\")):
        folder += _sep(folder)
    return folder + name


def _stem(path):
    return re.sub(r"\.[^./\\]+$", "", path)


def _exists(path):
    try:
        return bool(path) and xbmcvfs.exists(path)
    except Exception:
        return False


def _first(*paths):
    for p in paths:
        if _exists(p):
            return p
    return ""


def show_root(path, tv_file=""):
    """The show's own folder: Kodi's tvshow path, else the episode's folder
    (one up from a 'Season 2' / 'Specials' folder)."""
    if tv_file and not tv_file.startswith(("videodb://", "multipath://")):
        return tv_file if tv_file.endswith(("/", "\\")) else tv_file + _sep(tv_file)
    folder = _parent(path)
    name = folder.rstrip("/\\").replace("\\", "/").split("/")[-1]
    if _SEASON_DIR.match(name or ""):
        folder = _parent(folder)
    return folder


def _read_text(path, limit=65536):
    f = None
    try:
        f = xbmcvfs.File(path)            # read-only
        data = f.read(limit) if hasattr(f, "read") else ""
    except Exception:
        return ""
    finally:
        try:
            if f is not None:
                f.close()
        except Exception:
            pass
    if isinstance(data, bytes):
        data = data.decode("utf-8", "replace")
    return data or ""


def _nfo(path):
    """{title, plot, outline} from the episode's .nfo next to it (read-only)."""
    nfo = _stem(path) + ".nfo"
    if not _exists(nfo):
        return {}
    txt = _read_text(nfo)

    def tag(name):
        m = re.search(r"<%s>(.*?)</%s>" % (name, name), txt, re.S | re.I)
        if not m:
            return ""
        v = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", m.group(1), flags=re.S)
        v = v.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
        return v.strip()
    return {"title": tag("title"), "plot": tag("plot"), "outline": tag("outline")}


# ------------------------------------------------------------------ synopsis
# The synopsis line is never trimmed and never ends in "...": a text either fits
# the label's two lines whole, or the line is left out.  "Fits" is measured the
# way Kodi wraps it: Noto Sans (the font27 of Estuary and most skins) at 27 px
# in the label's 1080 px (1080p layout; 720p scales the same way).
SYNOPSIS_LINES = 2
SYNOPSIS_WIDTH = 1080 * 0.97           # a little room for the font's own rounding
_CHARS = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
_WIDTHS = (7.0, 7.2, 11.0, 17.4, 15.4, 22.4, 19.8, 6.1, 8.1, 8.1, 14.9, 15.4, 7.2, 8.7, 7.2, 10.0, 15.4, 15.4,
           15.4, 15.4, 15.4, 15.4, 15.4, 15.4, 15.4, 15.4, 7.2, 7.2, 15.4, 15.4, 15.4, 11.7, 24.3, 17.2, 17.5,
           17.1, 19.7, 15.0, 14.0, 19.6, 20.0, 9.2, 7.4, 16.7, 14.1, 24.5, 20.5, 21.1, 16.3, 21.1, 16.8, 14.8,
           15.0, 19.7, 16.2, 25.1, 15.8, 15.3, 15.4, 8.9, 10.0, 8.9, 15.4, 12.0, 7.6, 15.1, 16.6, 13.0, 16.6,
           15.2, 9.3, 16.6, 16.7, 7.0, 7.0, 14.4, 7.0, 25.2, 16.7, 16.3, 16.6, 16.6, 11.1, 12.9, 9.8, 16.7, 13.7,
           21.2, 14.3, 13.8, 12.7, 10.2, 14.9, 10.2, 15.4)
_W = dict(zip(_CHARS, _WIDTHS))
_W_OTHER = 20.0                        # accented letters, CJK, dashes...: on the wide side


def _px(text):
    return sum(_W.get(c, _W_OTHER) for c in text)


def fits(text, lines=SYNOPSIS_LINES, width=SYNOPSIS_WIDTH):
    """Does text wrap (word by word, like Kodi) into this many lines?"""
    n, cur = 1, 0.0
    space = _W[" "]
    for word in text.split(" "):
        w = _px(word)
        if w > width:
            return False                 # a word wider than the line: Kodi would break it
        if cur and cur + space + w > width:
            n += 1
            cur = w
            if n > lines:
                return False
        else:
            cur = cur + space + w if cur else w
    return True


# ------------------------------------------------------------------ names that must fit
# A channel's name is never cut off and never ends in "...": its label steps down
# through smaller skin fonts until it fits on one line, then wraps to two lines
# (the skin has a variant of the label for each font; the property names the
# one to show, "<font>2" for two lines).  Sizes as in Estuary (Noto Sans).
LADDER_27 = (("font27", 27), ("font12", 25), ("font10", 23))
LADDER_60 = (("font60", 60), ("font45", 45), ("font37", 37), ("font32", 32), ("font27", 27))
LADDER_45 = (("font45", 45), ("font37", 37), ("font32", 32), ("font27", 27))
TWO_23 = "font23_narrow"
TWO_27 = "font27_narrow"
FIT_SLACK = 0.96                       # the font's own rounding, and a bold-ish skin


def fit_font(text, width, ladder=LADDER_27, two=TWO_23, upper=False):
    """The skin font a label of `width` px shows `text` in without cutting it:
    the first of `ladder` it fits on one line, else `two` + '2' (two lines)."""
    t = (text or "").upper() if upper else (text or "")
    w = _px(t)
    for name, px in ladder:
        if w * px / 27.0 <= width * FIT_SLACK:
            return name
    return two + "2"


def two_lines(text, upper=False):
    """text split into two lines ('[CR]' between them) at the space that makes the
    wider line narrowest - before a ' · ' if that is about as good, never between
    'CH' and its number.  For the two-line variants of fit_font (Kodi's own wrap
    is greedy: 'NAME · CH' and a lone '3')."""
    t = (text or "").upper() if upper else (text or "")
    words = t.split(" ")
    best = None
    for i in range(1, len(words)):
        if words[i - 1] in ("CH", "Ch"):
            continue
        a, b = " ".join(words[:i]), " ".join(words[i:])
        cost = max(_px(a), _px(b))
        if b.startswith("· ") or a.endswith(" ·"):
            cost *= 0.9                  # break at the separator when it's nearly as good
        if a.endswith(" ·"):
            cost *= 1.2                  # ...with the dot starting the second line
        if best is None or cost < best[0]:
            best = (cost, a, b)
    return text if best is None else "%s[CR]%s" % (best[1], best[2])


def cross_kicker(name, number):
    """Another channel's promo heading: 'Name · Channel 6', or 'Name · CH 6' when
    the name is already long (or says Channel itself) - it must fit the early-90s
    card's channel strip on one line at the full size."""
    full = _("%s · Channel %d").replace("%d", str(number)).replace("%s", name)
    if "channel" not in name.lower() and fit_font(full, KICKER_90S, upper=True) == LADDER_27[0][0]:
        return full
    return _("%s · CH %d").replace("%d", str(number)).replace("%s", name)


KICKER_90S = 388                       # the early-90s card's channel strip (label width)
KICKER_MODERN = 1500


_ABBREV = re.compile(r"(\b(Mr|Mrs|Ms|Dr|St|Jr|Sr|Mt|Ft|Lt|Col|Gen|Capt|Cmdr|Sgt|Prof|Rev|No|vs|etc)|\b[A-Z])\.$")


def _clean(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def first_sentence(plot):
    """The plot's first sentence, whole (up to '. ', '! ' or '? ').
    'Mr. Bean' and initials like 'J. R.' don't end it."""
    p = _clean(plot)
    for m in re.finditer(r"[.!?][\"'\u201d\u2019)]? ", p):
        head = p[:m.end() - 1]
        if head.endswith(".") and _ABBREV.search(head):
            continue
        return head
    return p


def synopsis(outline, plot):
    """The episode's outline if it fits, else the plot's first sentence if the
    whole sentence fits, else '' (no synopsis line)."""
    for text in (_clean(outline), first_sentence(plot)):
        if text and fits(text):
            return text
    return ""


# ------------------------------------------------------------------ lookup
def usable_art(url):
    """Kodi art we can show right now.  Web artwork (TMDB, fanart.tv) only once
    Kodi has it in its thumbnail cache: otherwise it would download while the
    promo is on, leaving it black - or nameless, when it's the logo."""
    if not url:
        return False
    inner = unquote(url[8:].rstrip("/")) if url.startswith("image://") else url
    if not inner.lower().startswith(("http://", "https://")):
        return True
    res = rpc("Textures.GetTextures", {"properties": ["url"], "filter": {
        "field": "url", "operator": "contains", "value": inner.split("://", 1)[1]}})
    return bool(res.get("textures"))


def _texture_key(url):
    """The key Kodi's texture cache knows an image by (image://... unwrapped)."""
    return unquote(url[8:].rstrip("/")) if url.startswith("image://") else url


def texture_cached(url):
    """True when Kodi has this image in its texture cache, so a control shows
    it at once instead of loading it while the card is already on screen."""
    if not url:
        return False
    key = _texture_key(url)
    res = rpc("Textures.GetTextures", {"properties": ["url"], "filter": {
        "field": "url", "operator": "is", "value": key}})
    # Kodi answers with the url wrapped again (image://...)
    return any(_texture_key(t.get("url") or "") == key for t in res.get("textures") or [])


def logo_ready(url):
    """The card shows this logo only if it exists and is cached right now;
    otherwise it shows the show's title instead (never both)."""
    if not url:
        return False
    try:
        key = _texture_key(url)
        if not key.lower().startswith(("http://", "https://")) and not xbmcvfs.exists(key):
            return False
        return texture_cached(url)
    except Exception as exc:
        log("promo logo %s: %s" % (url, exc))
        return False


def _details(path):
    res = rpc("Files.GetFileDetails", {"file": path, "media": "video",
                                       "properties": ["title", "plot", "plotoutline", "art", "showtitle",
                                                      "tvshowid", "season", "episode"]})
    return res.get("filedetails") or {}


def _show_details(tvshowid):
    if not tvshowid or tvshowid < 0:
        return {}
    res = rpc("VideoLibrary.GetTVShowDetails", {"tvshowid": tvshowid,
                                                "properties": ["title", "file", "art"]})
    return res.get("tvshowdetails") or {}


def info(path, title=""):
    """What a promo for this programme shows and plays (cached for a while):
    {title, episode, plot, bg, letterbox, logo, theme, root}.  Never raises."""
    key = path or ("title:" + title)
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and time.time() - hit[0] < _CACHE_TTL:
            return hit[1]
    try:
        out = _info(path, title)
    except Exception as exc:
        log("promo info %s: %s" % (path, exc))
        out = {"title": title, "episode": "", "plot": "", "bg": "", "letterbox": False,
               "logo": "", "theme": "", "root": ""}
    with _LOCK:
        _CACHE[key] = (time.time(), out)
    return out


def _info(path, title):
    d = _details(path) if path else {}
    art = d.get("art") or {}
    try:
        is_ep = int(d.get("tvshowid", -1)) >= 0
    except (TypeError, ValueError):
        is_ep = False
    is_movie = d.get("type") == "movie"
    show = _show_details(d.get("tvshowid")) if is_ep else {}
    sart = show.get("art") or {}
    if not path:
        root = ""
    elif is_movie:
        root = _parent(path)                     # a movie: its own folder
    else:
        root = show_root(path, show.get("file", ""))

    if is_ep:
        name = d.get("showtitle") or show.get("title") or title
    elif is_movie:
        name = title or d.get("title")
    else:
        name = title or d.get("title")
    name = (name or "").strip()
    # the episode title always; the synopsis only from the episode itself (never the show's plot)
    episode = (d.get("title") or "").strip() if is_ep else ""
    plot = (d.get("plot") or "").strip() if (is_ep or is_movie) else ""
    outline = (d.get("plotoutline") or "").strip() if (is_ep or is_movie) else ""
    if path and not is_movie and not (episode and plot and outline):
        n = _nfo(path)                       # the files as a fallback
        episode = episode or n.get("title", "")
        plot = plot or n.get("plot", "")
        outline = outline or n.get("outline", "")

    def a(*keys, **kw):
        check = kw.get("check", True)
        for k in keys:
            for src in (art, sart):
                v = src.get(k)
                if v and (not check or usable_art(v)):
                    return v
        return ""

    # background: episode still > fanart > landscape > poster (letterboxed)
    bg, letterbox = "", False
    if path and not is_movie:
        thumb = art.get("thumb") if is_ep else ""
        bg = (thumb if usable_art(thumb) else "") or _first(_stem(path) + "-thumb.jpg", _stem(path) + "-thumb.png")
    if not bg:
        bg = a("tvshow.fanart", "fanart") or _first(_join(root, "fanart.jpg"))
    if not bg:
        bg = a("tvshow.landscape", "landscape") or _first(_join(root, "landscape.jpg"))
    if not bg:
        bg = a("tvshow.poster", "poster") or _first(_join(root, "poster.jpg"))
        letterbox = bool(bg)
    # the logo even when it isn't cached yet: it's preloaded during the spot before
    # the card, and card() decides then whether it's ready (logo_ready)
    logo = a("tvshow.clearlogo", "clearlogo", check=False) or _first(_join(root, "clearlogo.png"))
    theme = _first(_join(root, "theme.mp3")) if root else ""
    return {"title": name, "episode": episode, "plot": synopsis(outline, plot), "bg": bg, "letterbox": letterbox,
            "logo": logo, "theme": theme, "root": root}


def extras_promos(path, title=""):
    """[{path, dur, title}] of short 'Promo' / 'Trailer' videos in the show's
    Extras folder (read-only; longer clips are never used)."""
    key = "extras:" + (path or title)
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and time.time() - hit[0] < _CACHE_TTL:
            return hit[1]
    out = []
    try:
        root = info(path, title).get("root") if path else ""
        for name in _EXTRAS_DIRS:
            folder = (_join(root, name) + _sep(root)) if root else ""   # folders need the separator
            if not folder or not _exists(folder):
                continue
            for p in library.folder_files(folder):
                base = os.path.basename(p.replace("\\", "/")).lower()
                if not any(w in base for w in _EXTRAS_WORDS) or library.is_bad(p):
                    continue
                dur = library.durations().get(p)
                if 0 < dur <= EXTRAS_MAX:
                    out.append({"path": p, "dur": float(dur),
                                "title": os.path.splitext(os.path.basename(p.replace("\\", "/")))[0]})
            break
        library.durations().save()
    except Exception as exc:
        log("extras promos %s: %s" % (path, exc))
    with _LOCK:
        _CACHE[key] = (time.time(), out)
    return out


def clear_cache():
    with _LOCK:
        _CACHE.clear()


# ------------------------------------------------------------------ on screen
# Shared by the TV window (a promo in a break), Settings > Breaks > Preview
# promo and the development contact sheet, so all three show the same card.
# One time phrase per card, in the time label only (the heading is just the
# channel).  Every phrase is a whole sentence in strings.po, so it translates
# with its own grammar; the clock follows Kodi's regional format (12/24 hour).
def _day_at(wday):
    return (_("Monday at %s"), _("Tuesday at %s"), _("Wednesday at %s"), _("Thursday at %s"),
            _("Friday at %s"), _("Saturday at %s"), _("Sunday at %s"))[wday % 7]


def _days_at(wday):
    return (_("Mondays at %s"), _("Tuesdays at %s"), _("Wednesdays at %s"), _("Thursdays at %s"),
            _("Fridays at %s"), _("Saturdays at %s"), _("Sundays at %s"))[wday % 7]


def clock(ts):
    """'8:00 PM' or '20:00', as Kodi's region setting says."""
    try:
        f = xbmc.getRegion("time") or "%H:%M:%S"
    except Exception:
        f = "%H:%M:%S"
    f = re.sub(r"[:.]%S", "", f)
    lt = time.localtime(ts)
    if "%p" in f:
        try:
            am, pm = (xbmc.getRegion("meridiem") or "AM/PM").split("/", 1)
        except Exception:
            am, pm = "AM", "PM"
        f = f.replace("%p", (pm if lt.tm_hour >= 12 else am).replace("%", "%%"))
    s = time.strftime(f, lt)
    return s[1:] if "%I" in f and s.startswith("0") else s


def day_phrase(pt, now):
    """Today at 2:30 / Tonight at 8:00 / Tomorrow at 7:00 / Saturday at 9:00."""
    days = (datetime.date.fromtimestamp(pt) - datetime.date.fromtimestamp(now)).days
    lt = time.localtime(pt)
    if days <= 0:
        text = _("Tonight at %s") if lt.tm_hour >= 17 else _("Today at %s")
    elif days == 1:
        text = _("Tomorrow at %s")
    else:                                    # within the week (promos look at most a day ahead)
        text = _day_at(lt.tm_wday)
    return text % clock(pt)


def _day_all(wday):
    return (_("Monday, all day"), _("Tuesday, all day"), _("Wednesday, all day"), _("Thursday, all day"),
            _("Friday, all day"), _("Saturday, all day"), _("Sunday, all day"))[wday % 7]


def special_phrase(pt, end, now):
    """When a special is on: 'Thursday, all day' (23 hours or more), otherwise like
    any programme: 'Tonight at 6:00 PM' / 'Thursday at 6:00 PM'."""
    if end - pt < 23 * 3600:
        return day_phrase(pt, now)
    days = (datetime.date.fromtimestamp(pt) - datetime.date.fromtimestamp(now)).days
    if days <= 0:
        return _("Today, all day")
    if days == 1:
        return _("Tomorrow, all day")
    return _day_all(time.localtime(pt).tm_wday)


def slot_phrase(ch, pt):
    """A pinned weekly slot starting at pt, said the way a promo says it
    ('Weeknights at 8:00 PM'), or '' if pt isn't one."""
    from .scheduler import rule_occurrences
    for r in (ch or {}).get("slots") or []:
        for st, _en in rule_occurrences(r, pt, pt + 1):
            if abs(st - pt) > 60:
                continue
            days, at = r.get("days"), clock(st)
            if isinstance(days, list) and len(days) == 7:
                days = "all"
            if days == "weekdays" or (isinstance(days, list) and sorted(days) == [0, 1, 2, 3, 4]):
                return (_("Weeknights at %s") if time.localtime(st).tm_hour >= 17 else _("Weekdays at %s")) % at
            if days == "weekends" or (isinstance(days, list) and sorted(days) == [5, 6]):
                return _("Weekends at %s") % at
            if days in (None, "all"):
                return _("Every day at %s") % at
            if isinstance(days, list) and len(days) == 1:
                return _days_at(int(days[0])) % at
    return ""


def time_phrase(pt, now, ch=None, has_episode=True, next_up=False):
    """The card's one time phrase: 'Up next' for the very next programme on this
    channel; a pinned slot's 'Weeknights at 8:00' when there are no episode
    details; otherwise the day and time."""
    if next_up:
        return _("Up next")
    return (not has_episode and slot_phrase(ch, pt)) or day_phrase(pt, now)


def card(inf, title, pt, now, ch=None, channel_name="", later=False, special=None):
    """Window properties of a promo card: {property: value}.  later: not the
    very next programme on the channel.  special: {'end', 'sub'} when the card is
    for a special (Holidays and specials): its name is the title - never a show's
    logo - with what it airs under it and 'Thursday, all day' as the time."""
    if special:
        return {
            "promo_style": style(),
            "promo_kicker": channel_name or "",
            "promo_title": title or "",
            "promo_ep": special.get("sub") or "",
            "promo_plot": (inf.get("plot") or "") if "," not in (special.get("sub") or "") else "",
            "promo_when": special_phrase(pt, special.get("end") or pt, now),
            "promo_bg": inf.get("bg") or "",
            "promo_letterbox": "1" if inf.get("letterbox") else "",
            "promo_logo": "",
        }
    episode = inf.get("episode") or ""
    # the logo or the title, never both: the title is never a stand-in behind a
    # logo that is still loading.  A logo not yet in the texture cache -> title.
    logo = inf.get("logo") or ""
    if logo and not logo_ready(logo):
        log("promo: %s's logo isn't cached yet - showing the title" % (inf.get("title") or title))
        logo = ""
    return {
        "promo_style": style(),
        "promo_kicker": channel_name or "",     # the heading: the channel, no time words
        "promo_title": "" if logo else library.on_air(inf.get("title") or title or ""),   # no year on air
        "promo_ep": (u"\u201c%s\u201d" % episode) if episode else "",
        "promo_plot": inf.get("plot") or "",
        "promo_when": time_phrase(pt, now, ch, bool(episode), not later),
        "promo_bg": inf.get("bg") or "",
        "promo_letterbox": "1" if inf.get("letterbox") else "",
        "promo_logo": logo,
    }


# ------------------------------------------------------------------ 90s style
# Settings > Breaks > Look of promos and retro ads: early-90s cable (default) or Modern.
# The 90s card's title and time tab are lettered with pictures of Bebas Neue
# letters (media/promo90s/glyphs): Kodi 21 can't load a font from a script
# add-on.  Anything the letters can't spell falls back to the skin's font.
STYLE_90S, STYLE_MODERN = "90s", "modern"
_GLYPHS = None
_GLYPH_DIR = os.path.join(K.ADDON_PATH, "resources", "skins", "Default", "media", "promo90s")
TRACKING = 4                    # extra space between letters (px at full size)
SHADOW = "FF24145F"             # the title's hard drop shadow: deep purple


def style():
    return STYLE_MODERN if K.setting_int("promo_style", 0) == 1 else STYLE_90S


def _glyphs():
    global _GLYPHS
    if _GLYPHS is None:
        import json
        try:
            with open(os.path.join(_GLYPH_DIR, "glyphs.json"), encoding="utf-8") as f:
                _GLYPHS = json.load(f)
        except (IOError, OSError, ValueError) as exc:
            log("promo glyphs: %s" % exc)
            _GLYPHS = {"glyphs": {}, "height": 1, "space": 0, "pad": 0}
    return _GLYPHS


def glyph_width(text, scale=1.0):
    """Width of text in the letter pictures, or None if one can't be spelled."""
    g = _glyphs()
    w = 0.0
    for c in text.upper():
        if c == " ":
            w += g["space"]
        elif c in g["glyphs"]:
            w += g["glyphs"][c][2] + TRACKING
        else:
            return None
    return w * scale


TITLE_SLOTS, SHADOW_SLOTS, TAB_SLOTS = (1300, 40), (1400, 40), (1500, 28)   # image ids in the skin


def glyph_layout(text, x, y, height, max_width):
    """[(picture, x, y, w, h)] for text in the letter pictures, or None when it
    can't be spelled or won't fit (letters shrink to 55% at most)."""
    g = _glyphs()
    scale = float(height) / g["height"]
    width = glyph_width(text, scale)
    if not width:
        return None
    if width > max_width:
        f = max_width / width
        if f < 0.55:
            return None
        y += int(height * (1 - f) / 2)
        scale *= f
    h = int(g["height"] * scale)
    pad = g["pad"] * scale
    out = []
    cx = float(x)
    for c in text.upper():
        if c == " ":
            cx += g["space"] * scale
            continue
        name, w, adv = g["glyphs"][c]
        out.append((os.path.join(_GLYPH_DIR, "glyphs", name), int(cx - pad), int(y), int(w * scale), h))
        cx += (adv + TRACKING) * scale
    return out


def _fill(win, slots, layout, offset=0):
    """Put a layout into a row of the skin's letter slots; empty the rest."""
    first, count = slots
    layout = layout or []
    if len(layout) > count:
        return False
    for i in range(count):
        try:
            c = win.getControl(first + i)
        except Exception:
            return False
        if i < len(layout):
            path, x, y, w, h = layout[i]
            c.setVisible(True)
            c.setImage(path)
            c.setPosition(x + offset, y + offset)
            c.setWidth(w)
            c.setHeight(h)
        else:
            # hidden as well as emptied: lettered while the promo group is hidden (a
            # card after a programme), an emptied slot kept its old letter in Kodi 21
            c.setImage("")
            c.setVisible(False)
    return True


TITLE_BOX = (310, 568, 1250, 140)          # x, y, max width, letter height (on the band)
TAB_BOX = (314, 452, 64)                   # x, y, letter height (in the time tab)
TAB_LEFT, TAB_RIGHT = 24, 70               # tab.png's ends around its text


def apply_card(win, props):
    """Show a card's properties on a window (TV, Preview promo, contact sheet)
    and, in the 90s style, letter its title and time tab.  Call it before the
    window's mode becomes "promo", so the entrances play."""
    props = dict(props)
    props.update(promo_title_glyphs="", promo_tab_glyphs="")
    kicker = props.get("promo_kicker") or ""
    props.update(promo_kicker_f90=fit_font(kicker, KICKER_90S, upper=True),
                 promo_kicker_fm=fit_font(kicker, KICKER_MODERN, upper=True),
                 promo_kicker2=two_lines(kicker, upper=True))
    try:
        _letter(win, props)
    except Exception as exc:
        K.log_err("promo lettering: %s" % exc)
    for k, v in props.items():
        if k != "mode":
            win.setProperty(k, v)


def _letter(win, props):
    nineties = props.get("promo_style") == STYLE_90S
    # the time tab: black letters dropping in with the tab
    when = props.get("promo_when") or ""
    x, y, h = TAB_BOX
    lay = glyph_layout(when, x, y, h, 900) if nineties else None
    if lay and _fill(win, TAB_SLOTS, lay):
        props["promo_tab_glyphs"] = "1"
        w = lay[-1][1] + lay[-1][3] - x
    else:
        _fill(win, TAB_SLOTS, None)
        w = int(_px(when) * 45 / 27.0)          # the skin-font fallback label (font45)
    if nineties:
        try:
            win.getControl(1201).setWidth(int(w) + TAB_LEFT + TAB_RIGHT)
        except Exception:
            pass
    # the show's name on the band (card() sets it only when there's no logo)
    lay = None
    if nineties and props.get("promo_title"):
        x, y, maxw, h = TITLE_BOX
        lay = glyph_layout(props.get("promo_title") or "", x, y, h, maxw)
    if lay and len(lay) <= TITLE_SLOTS[1]:
        _fill(win, SHADOW_SLOTS, lay, offset=max(3, int(8 * lay[0][4] / _glyphs()["height"])))
        _fill(win, TITLE_SLOTS, lay)
        props["promo_title_glyphs"] = "1"
    else:
        _fill(win, SHADOW_SLOTS, None)
        _fill(win, TITLE_SLOTS, None)


def music(inf):
    """The theme (or the built-in tune) to play under a card, or '' for none."""
    if K.setting_int("promo_music", 0) != 0:
        return ""
    return inf.get("theme") or (BED if os.path.exists(BED) else "")


def air(win, ch, pt, path, title, later, now, kicker=None, special=None):
    """Put one promo card on `win` (a window with the TV's layout,
    script-cablebox42-tv.xml) and return its music ('' for a silent card).
    The one way a promo goes on screen: in a break (tv.start_promo), in
    Settings > Breaks > Preview a promo and with the Developer tools cheat code.
    The caller starts the music with ThemeAudio.start(music, end)."""
    try:
        inf = info(path, title or "")
    except Exception as exc:
        K.log_err("promo: %s" % exc)
        inf = {}
    from . import stations
    name = stations.brand(ch, pt)["name"] if ch else ""      # its branding at that hour
    if kicker:
        name = kicker(name) if callable(kicker) else kicker % name    # another channel's: cross_kicker
    apply_card(win, card(inf, title, pt, now, ch, name, later, special))
    win.setProperty("mode", "promo")
    return music(inf)


# ------------------------------------------------------------------ house ads
# System ads in house breaks: the cable system advertising its own channels.
# Original lines only (no real network slogans); three per kind, rotated.
HOUSE_LINES = {
    "guide": (("What's on tonight?", "Every channel, now and later, scrolling around the clock."),
              ("Never miss a show", "What's on now and next on every channel, in one place."),
              ("Plan your evening", "Two hours of listings, always up to date.")),
    "weather": (("Your local forecast", "Today's conditions and the days ahead, day and night."),
                ("Before you head out", "Check the sky first, any time you like."),
                ("Weather, around the clock", "Current conditions and the extended outlook, whenever you tune in.")),
}


def house_card(kind, line, target, now, rows=None):
    """Window properties of a system ad: 'guide' or 'weather' (target: that
    channel) or 'lineup' (rows: [(time, title, channel number)] of what's coming
    up on the lineup).  Same window and style as a promo card."""
    from . import stations
    if kind == "lineup":
        evening = time.localtime(now).tm_hour >= 17
        title = _("Tonight's lineup") if evening else _("Coming up")
        plot = "[CR]".join(_("%s  %s  ·  Channel %d") % (clock(t), name, num) for t, name, num in rows or [])
        kicker, when, logo = "CableBox 42", _("All channels"), ""
    else:
        lines = HOUSE_LINES[kind]
        t, plot = lines[line % len(lines)]
        title, plot = _(t), _(plot)
        kicker = stations.brand(target, now)["name"]
        when = _("Channel %d") % target["number"]
        logo = stations.brand(target, now)["logo"]      # its station logo too, as on its banner
        if logo and not logo_ready(logo):
            logo = ""
    return {
        "promo_style": style(),
        "promo_kicker": kicker,
        "promo_title": "" if logo else title,
        "promo_ep": title if logo else "",
        "promo_plot": plot,
        "promo_when": when,
        "promo_bg": "",
        "promo_letterbox": "",
        "promo_logo": logo,
    }


def air_house(win, props):
    """Put a system ad on `win`; returns its music (the built-in bed, by the
    Promo music setting)."""
    apply_card(win, props)
    win.setProperty("mode", "promo")
    return music({})


def close_busy_wheel():
    """A TV never shows a loading spinner: close Kodi's busy wheel if it pops up
    while something of ours starts (a theme, a channel coming in)."""
    try:
        for dlg in ("busydialog", "busydialognocancel"):
            if xbmc.getCondVisibility("Window.IsActive(%s)" % dlg):
                xbmc.executebuiltin("Dialog.Close(%s,true)" % dlg)
    except Exception:
        pass


def wait_stopped(player, secs=5.0):
    """Wait until Kodi's player has really stopped (not on a timer); True if it has."""
    mon = xbmc.Monitor()
    end = time.time() + secs
    while time.time() < end:
        try:
            if not player.isPlaying():
                return True
        except Exception:
            return True
        if mon.waitForAbort(0.05):
            break
    return False


class ThemeAudio(object):
    """A promo's theme music.  Played like the guide's music, at the file's own
    level: CableBox never changes Kodi's volume.  It is cut off cleanly when the
    card cuts to black (the built-in tune has its own fade baked in)."""

    def __init__(self, player):
        self.player = player
        self.pa = None

    @property
    def active(self):
        return self.pa is not None

    def start(self, path, end):
        pl = xbmc.PlayList(getattr(xbmc, "PLAYLIST_MUSIC", 0))
        pl.clear()
        pl.add(path)
        self.pa = {"end": end, "path": path}
        self.player.play(pl, windowed=True)

    def tick(self, now):
        """True once the card's time is up and the theme has been cut."""
        if self.pa and now >= self.pa["end"] - 0.05:
            self.stop()
            return True
        return False

    def _playing_theme(self):
        try:
            return self.player.isPlayingAudio() and self.player.getPlayingFile() == self.pa["path"]
        except Exception:
            return False

    def stop(self, stop_music=True):
        pa = self.pa
        if not pa:
            return
        if stop_music:
            try:
                if self._playing_theme():
                    self.player.stop()
                    for _i in range(25):          # fully stopped before whatever plays next
                        if not self.player.isPlaying():
                            break
                        xbmc.sleep(20)
            except Exception:
                pass
            try:
                xbmc.PlayList(getattr(xbmc, "PLAYLIST_MUSIC", 0)).clear()
            except Exception:
                pass
        self.pa = None
