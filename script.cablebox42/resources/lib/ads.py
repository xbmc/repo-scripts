"""Retro ads: made-up commercials as cards with a short jingle, for house breaks.

Settings > Programming > House breaks > Retro ads (on by default).  They are
house-break content only: the viewer's own commercials always win, and they
follow the House breaks modes (scheduler._house_block / _house_mix place them).

The ads are data (resources/ads/ads.json, English texts looked up in strings.po).
Picking: time of day, the channel's ad flavour and the season are filters, not
quotas, so there is always something to show; no ad twice in a break, the same
ad not again on a channel within about two hours, a running gag at most once a
break.  "Now on videocassette" cards name movies that are really in the library.

On screen: the blank backgrounds in resources/media/ads, lettered by Kodi with
pictures of letters (media/retroads, tools/retro-ads/make_glyphs.py: Kodi 21
can't load an add-on's fonts) placed into the image slots of the TV window's
retro group (ids SLOT_FILL / SLOT_LINE).  Zones as in retro-ads LAYOUTS.md.
"""
import json
import math
import os
import random
import re
import threading
import time
import unicodedata

from . import kodiutil as K
from . import library
from .kodiutil import _, log

DATA = os.path.join(K.ADDON_PATH, "resources", "ads", "ads.json")
BG_DIR = os.path.join(K.ADDON_PATH, "resources", "media", "ads")
JINGLE_DIR = os.path.join(K.ADDON_PATH, "resources", "media", "jingles")
GLYPH_DIR = os.path.join(K.ADDON_PATH, "resources", "skins", "Default", "media", "retroads")

RECENT = 2 * 3600            # the same ad not again on a channel within this
FORMATS = ("pitch", "kids", "local", "psa", "video")      # stage 1
BACKGROUND = {"pitch": "bg_1_pitch_card.jpg", "local": "bg_2_local_business.jpg", "psa": "bg_3_psa.jpg",
              "video": "bg_6_video.jpg", "kids": "bg_7_kids_pitch.jpg"}
JINGLE = {"pitch": "jingle_pitch.wav", "kids": "jingle_kids.wav", "local": "jingle_local.wav",
          "psa": "jingle_psa.wav", "video": "jingle_video.wav"}
# A card stays up for its whole jingle (each ends in its own 0.4 s fade): the
# jingle's length plus START for Kodi to start the sound, rounded up to whole
# seconds.  A jingle is never cut short and Kodi's volume is never touched: a slot
# too short for a card gets a promo or the station ID (scheduler._retro_block).
START = 0.45
JINGLE_LEN = {"pitch": 7.75, "kids": 7.2, "local": 8.51, "psa": 9.12, "video": 7.1}   # if a file can't be read
_JLEN = {}

FLAVOURS = ("auto", "G", "K", "S", "M", "L")
KIDS_GENRES = ("Children", "Kids")
KIDS_OK = KIDS_GENRES + ("Animation", "Family")
SPORTS_GENRES = ("Sport", "Sports")

_DATA = None
_LOCK = threading.Lock()


def flavour_label(code):
    return {"auto": _("Auto"), "G": _("General"), "K": _("Kids"), "S": _("Sports"), "M": _("Movies"),
            "L": _("Late night")}.get(code, code)


def load():
    """The ad data (cached; a broken file means no retro ads, never a crash)."""
    global _DATA
    with _LOCK:
        if _DATA is None:
            try:
                with open(DATA, encoding="utf-8") as f:
                    d = json.load(f)
                ads = [a for a in d.get("ads", []) if a.get("fmt") in FORMATS and a.get("id")]
                _DATA = {"ads": ads, "by_id": dict((a["id"], a) for a in ads), "video": d.get("video") or {}}
            except (IOError, OSError, ValueError) as exc:
                K.log_err("retro ads: %s" % exc)
                _DATA = {"ads": [], "by_id": {}, "video": {}}
        return _DATA


# ------------------------------------------------------------------ what fits now
def flavour(ch):
    """The channel's ad flavour: its Ad flavour setting, or Auto from its type
    and genres (movie channel -> Movies, children's genres -> Kids, sports -> Sports)."""
    f = ch.get("ad_flavour") or "auto"
    if f in FLAVOURS[1:]:
        return f
    return auto_flavour(ch)


def auto_flavour(ch):
    if ch.get("type") == "movies":
        return "M"
    genres = [s.get("value") for s in ch.get("sources", []) if s.get("type") == "tvgenre"]
    if genres and any(g in KIDS_GENRES for g in genres) and all(g in KIDS_OK for g in genres):
        return "K"
    if genres and any(g in SPORTS_GENRES for g in genres):
        return "S"
    return "G"


def daypart(ts):
    h = time.localtime(ts).tm_hour
    if 6 <= h < 11:
        return "morn"
    if 11 <= h < 17:
        return "day"
    if 17 <= h < 23:
        return "prime"
    return "late"


def seasons(ts):
    lt = time.localtime(ts)
    m, d = lt.tm_mon, lt.tm_mday
    out = set()
    if (m == 11 and d >= 15) or (m == 12 and d <= 24):
        out.add("holiday")
    if m in (12, 1, 2):
        out.add("winter")
    if m == 1:
        out.add("newyear")
    if m in (3, 4, 5):
        out.add("spring")
    if m in (6, 7, 8):
        out.add("summer")
    if m == 8:
        out.add("school")
    if m in (9, 10, 11):
        out.add("fall")
    if m == 10:
        out.add("halloween")
    return out


def fits(ad, flav, ts, style, strict_time=True):
    """Can this ad run on a channel of this flavour at ts?  The season, the
    era and kids' rules always hold; the time of day only when strict_time."""
    af = ad.get("flav") or []
    if flav == "K":
        if "K" not in af:
            return False                     # kids' channels: only ads marked K
    elif "G" not in af and flav not in af:
        return False
    if ad.get("claims"):
        return False                         # says what the weather is: needs a real reading (stage 2)
    if ad.get("season") and not seasons(ts).intersection(ad["season"]):
        return False
    era = ad.get("era")
    if era and era != ("2000s" if style == "modern" else "90s"):
        return False
    if strict_time:
        if ad.get("time") and daypart(ts) not in ad["time"]:
            return False
        hours = ad.get("hours")
        if hours and not (hours[0] <= time.localtime(ts).tm_hour <= hours[1]):
            return False
    return True


def weight(ad, flav, ts):
    w = 1.0
    if flav not in ("G", "K") and flav in (ad.get("flav") or []):
        w *= 3.0                             # the channel's own kind of ad
    if ad.get("season"):
        w *= 3.0                             # in season (out of season it doesn't fit at all)
    if ad.get("time") or ad.get("hours"):
        w *= 1.5
    return w


def _weighted(rng, pool):
    total = sum(w for w, _a in pool)
    x = rng.random() * total
    for w, a in pool:
        x -= w
        if x <= 0:
            return a
    return pool[-1][1]


# Video-themed ads ('Now on videocassette', Video Village, VideoVault: "theme":
# "video" in ads.json): at most one a break, never in two breaks in a row on a
# channel (scheduler._prev_break_video), and at most this share of a channel's
# retro ads (VIDEO_WINDOW back): a sixth on General channels, a third on Movies.
VIDEO_SHARE = {"M": (1, 3), "G": (1, 6)}
# Retro ads in one break: two (four on movie channels, whose breaks between films
# are long); the back-to-back breaks at a programme's end are one break to the
# viewer, three in all of them (four on movie channels).  The
# rest of a break is promos, system ads and the station ID card.
PER_BREAK = {"M": 4}
PER_BREAK_OTHER = 2
PER_RUN = {"M": 4}
PER_RUN_OTHER = 3
# One of a long end gap's ~150 s breaks (scheduler.GAP_SPLIT): retro ads fill what
# fresh promos can't (each promo target once in 10 minutes), so up to this many.
PER_GAP_BREAK = 10


def per_break(flav):
    return PER_BREAK.get(flav, PER_BREAK_OTHER)


def per_run(flav):
    return PER_RUN.get(flav, PER_RUN_OTHER)


def per_gap_break(flav):
    return max(PER_GAP_BREAK, per_break(flav))
VIDEO_SHARE_OTHER = (1, 4)
VIDEO_WINDOW = 6 * 3600


def video_share(flav):
    """(at most, out of) video-themed retro ads on a channel of this flavour."""
    return VIDEO_SHARE.get(flav, VIDEO_SHARE_OTHER)


def is_video(it):
    """A video-themed plan item (a videocassette card or an ad marked theme video)."""
    if it.get("ad") == "video":
        return True
    return (load()["by_id"].get(it.get("ad")) or {}).get("theme") == "video"


def video_ok(flav, videos, total):
    """May the next retro ad be video-themed, with `videos` of the channel's last
    `total` retro ads (VIDEO_WINDOW back) video-themed?  The share counts the new one."""
    num, den = video_share(flav)
    return (videos + 1) * den <= (total + 1) * num


def pick(rng, flav, ts, style, recent=(), used=(), gags=(), movies=None, want_video=True):
    """One ad for a break at ts: a plan item {"k": "retro", "ad": id, ...} or None
    (every ad that fits has run on this channel within RECENT).
    recent: ad keys aired on this channel within RECENT; used: keys in this
    break; gags: running-gag groups in this break; movies: () -> [movie] for
    'Now on videocassette' (None: no video cards); want_video False: nothing
    video-themed (the break has one, or the channel's share is used up) - another
    ad that fits takes the slot."""
    data = load()
    skip = set(recent) | set(used)
    # the time of day is a filter, not a rule: a general ad at another hour beats
    # no ad.  The two-hour rule always holds: when every ad that fits has run,
    # the slot goes to a promo or the station ID instead (scheduler._retro_block).
    for strict in (True, False):
        pool = []
        for ad in data["ads"]:
            if ad["id"] in skip:
                continue
            if ad.get("gag") and ad["gag"] in gags:
                continue
            if not want_video and ad.get("theme") == "video":
                continue
            if fits(ad, flav, ts, style, strict):
                pool.append((weight(ad, flav, ts), ad))
        vid = None
        if want_video and movies is not None and flav in ("G", "M", "S", "L"):
            vid = _video_item(rng, movies, skip)
            if vid:
                # movie channels: about half their retro ads; elsewhere now and then
                pool.append((sum(w for w, _a in pool) if flav == "M" else 2.0, vid))
        if pool:
            a = _weighted(rng, pool)
            if a is vid:
                return dict(vid)
            return {"k": "retro", "ad": a["id"], "ln": rng.randrange(3)}
    return None


def _video_item(rng, movies, skip):
    try:
        cands = [m for m in movies() if "V%s" % m["movieid"] not in skip]
    except Exception as exc:
        log("retro ads: movies %s" % exc)
        return None
    if not cands:
        return None
    m = rng.choice(cands)
    return {"k": "retro", "ad": "video", "mv": m["movieid"], "t": m.get("label") or m.get("title", ""),
            "ln": rng.randrange(3)}


def key(it):
    """What makes two retro ads the same ad (variety rules)."""
    return "V%s" % it.get("mv") if it.get("ad") == "video" else it.get("ad")


def gag(it):
    ad = load()["by_id"].get(it.get("ad"))
    return ad.get("gag") if ad else None


def jingle_len(fmt):
    """Seconds of the format's jingle (from the WAV header; cached)."""
    if fmt not in _JLEN:
        import wave
        try:
            w = wave.open(os.path.join(JINGLE_DIR, JINGLE[fmt]), "rb")
            try:
                _JLEN[fmt] = w.getnframes() / float(w.getframerate())
            finally:
                w.close()
        except Exception as exc:
            log("retro ads: jingle %s %s" % (fmt, exc))
            _JLEN[fmt] = JINGLE_LEN[fmt]
    return _JLEN[fmt]


def fmt_of(it):
    if it.get("ad") == "video":
        return "video"
    return (load()["by_id"].get(it.get("ad")) or {}).get("fmt", "pitch")


def length(it):
    """How long a retro ad's card stays up: its whole jingle and then some."""
    return float(math.ceil(jingle_len(fmt_of(it)) + START))


# ------------------------------------------------------------------ movies
_MOVIES = {"t": 0, "list": []}


def library_movies():
    """Movies in Kodi's library with a title (30 min cache)."""
    if time.time() - _MOVIES["t"] < 1800:
        return _MOVIES["list"]
    res = K.rpc("VideoLibrary.GetMovies", {"properties": ["title", "year", "file"]})
    out = []
    for m in res.get("movies", []) or []:
        if m.get("title") and m.get("file"):
            label = m["title"] + (" (%s)" % m["year"] if m.get("year") else "")
            out.append({"movieid": m["movieid"], "title": m["title"], "label": label, "file": m["file"]})
    _MOVIES.update(t=time.time(), list=out)
    return out


def movie_details(movieid):
    """The movie as the library has it now, or None (removed since planning)."""
    res = K.rpc("VideoLibrary.GetMovieDetails", {"movieid": int(movieid),
                                                 "properties": ["title", "year", "art", "mpaa", "file"]})
    return res.get("moviedetails") or None


# ------------------------------------------------------------------ letters
SLOT_FILL = (3000, 400)      # first id, count: letters
SLOT_LINE = (3400, 140)      # outlines, drawn behind the letters
SLOT_CLOCK = (3600, 16)      # the Up next card's live countdown (relettered every second)
_GLYPHS = None


def glyphs():
    global _GLYPHS
    if _GLYPHS is None:
        try:
            with open(os.path.join(GLYPH_DIR, "glyphs.json"), encoding="utf-8") as f:
                _GLYPHS = json.load(f)
        except (IOError, OSError, ValueError) as exc:
            K.log_err("retro ads: letters %s" % exc)
            _GLYPHS = {}
    return _GLYPHS


def _spellable(text, font):
    g = glyphs().get(font, {}).get("glyphs", {})
    out = []
    for c in text:
        if c == " " or c in g:
            out.append(c)
            continue
        base = unicodedata.normalize("NFKD", c)
        base = "".join(b for b in base if not unicodedata.combining(b))
        if base and all(b in g for b in base):
            out.append(base)
        elif c in u"’‘":
            out.append("'")
        elif c in u"“”":
            out.append('"')
    return "".join(out)


def can_spell(text, font):
    g = glyphs().get(font, {}).get("glyphs", {})
    return all(c == " " or c in g for c in text)


def width(text, font, size):
    f = glyphs().get(font)
    if not f:
        return 0.0
    k = float(size) / f["size"]
    return sum((f["space"] if c == " " else f["glyphs"].get(c, [0, 0, 0])[1]) for c in text) * k


class Zone(object):
    """One line of text: font set, baseline (x, y), size, max width, colour,
    outline colour, align 'l' or 'c' (x is then the centre)."""

    def __init__(self, text, font, x, y, size, maxw, color, line=None, align="l", upper=False, minf=0.5):
        text = text or ""
        if upper:
            text = text.upper()
        self.text = _spellable(text, font)
        self.font, self.x, self.y, self.size, self.maxw = font, x, y, float(size), maxw
        self.color, self.line, self.align, self.minf = color, line, align, minf

    def fitted(self):
        """The size it is drawn at: shrunk to the width (not below minf of its size)."""
        w = width(self.text, self.font, self.size)
        if w > self.maxw and w:
            return max(self.size * self.minf, self.size * self.maxw / w)
        return self.size

    def overflows(self):
        return width(self.text, self.font, self.size * self.minf) > self.maxw

    def place(self):
        """[(picture, x, y, w, h, colour, outline?)] - outlines first."""
        f = glyphs().get(self.font)
        if not f or not self.text.strip():
            return []
        size = self.fitted()
        k = size / f["size"]
        total = width(self.text, self.font, size)
        x = self.x - total / 2.0 if self.align == "c" else float(self.x)
        top = self.y - (f["ascent"] + f["pad"]) * k
        h = (f["ascent"] + f["descent"] + 2 * f["pad"]) * k
        out = []
        folder = os.path.join(GLYPH_DIR, self.font)
        for c in self.text:
            if c == " ":
                x += f["space"] * k
                continue
            g = f["glyphs"].get(c)
            if not g:
                continue
            w_img, adv, left = g
            name = "%04x" % ord(c)
            gx, gw = x + left * k, w_img * k
            if self.line and f.get("outline"):
                out.append((os.path.join(folder, name + "o.png"), gx, top, gw, h, self.line, True))
            out.append((os.path.join(folder, name + ".png"), gx, top, gw, h, self.color, False))
            x += adv * k
        return out


def wrap(text, font, size, maxw, lines=2, minf=0.6):
    """Split text into at most `lines` lines at word breaks so the widest is as
    narrow as possible; returns (lines, size) with size shrunk to fit."""
    words = text.split()
    if lines < 2 or len(words) < 2 or width(text, font, size) <= maxw:
        w = width(text, font, size)
        return [text], (size if w <= maxw else max(size * minf, size * maxw / w))
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        wid = max(width(a, font, size), width(b, font, size))
        if best is None or wid < best[0]:
            best = (wid, [a, b])
    wid, parts = best
    return parts, (size if wid <= maxw else max(size * minf, size * maxw / wid))


# ------------------------------------------------------------------ cards
def tr(text):
    return _(text) if text else ""


def _pitch(ad):
    z = [Zone(tr(ad.get("head")), "sbi", 110, 300, 150, 1150, "ffd23a", "1a0840", upper=True, minf=0.45)]
    if ad.get("sub"):
        z.append(Zone(tr(ad["sub"]), "sb", 110, 420, 92, 1150, "ffffff", "1a0840", minf=0.5))
    claim = tr(ad.get("claim"))
    parts, size = wrap(_spellable(claim, "sbi"), "sbi", 70, 1100)
    for i, part in enumerate(parts):
        z.append(Zone(part, "sbi", 110, 560 + 90 * i, size, 1100, "3ee6d0", "1a0840"))
    z += _burst(ad, 1500, 590, 700, 360, 380, "c4171f", None, 60, 110)
    cta = tr(ad.get("cta"))
    if "%s" in cta:
        cta = cta % ad.get("phone", "")
    z.append(Zone(cta, "sb", 960, 1000, 84, 1800, "ffffff", align="c", upper=True))
    return z


def _burst(ad, cx, ly, py, lw, pw, color, line, lsize, psize):
    """The starburst: a small label over the price; a price line that isn't a
    price ('At grocers everywhere') goes in at 50-60, in up to two lines."""
    label, price = tr(ad.get("label")), tr(ad.get("price"))
    z = []
    if label:
        z.append(Zone(label, "sb", cx, ly, lsize, lw, color, align="c", upper=True, minf=0.4))
    if not price:
        return z
    if label or width(_spellable(price, "sb"), "sb", psize) <= pw:
        z.append(Zone(price, "sb", cx, py, psize, pw, color, line, align="c"))
        return z
    parts, size = wrap(_spellable(price, "sb"), "sb", 56, pw, minf=0.75)
    mid = (ly + py) / 2.0 + 20
    for i, part in enumerate(parts):
        y = mid + (i - (len(parts) - 1) / 2.0) * size * 1.15
        z.append(Zone(part, "sb", cx, y, size, pw, color, line, align="c"))
    return z


def _kids(ad):
    z = [Zone(tr(ad.get("head")), "sbi", 120, 310, 190, 1100, "ffd23a", "7a2fd0", upper=True, minf=0.4)]
    parts, size = wrap(_spellable(tr(ad.get("claim")), "sb"), "sb", 76, 1100)
    for i, part in enumerate(parts):
        z.append(Zone(part, "sb", 120, 430 + 90 * i, size, 1100, "ffffff", "0d5f80"))
    z += _burst(ad, 1460, 445, 545, 340, 360, "ffffff", "7a2fd0", 56, 110)
    z.append(Zone(tr(ad.get("small")), "sr", 960, 1035, 48, 1800, "ffffff", align="c"))
    return z


def _local(ad, kids=False):
    z = [Zone(tr(ad.get("banner")), "sb", 960, 162, 56, 760, "ffffff", align="c", upper=True, minf=0.45)]
    name = [tr(n) for n in ad.get("name") or [] if n]
    if len(name) >= 2:
        z.append(Zone(name[0], "fb", 960, 380, 170, 1360, "1f5a3a", "c99a2e", align="c", upper=True))
        z.append(Zone(name[1], "fb", 960, 500, 110, 1360, "c4171f", align="c", upper=True))
    elif name:
        z.append(Zone(name[0], "fb", 960, 430, 170, 1360, "1f5a3a", "c99a2e", align="c", upper=True))
    if ad.get("tagline"):
        z.append(Zone(u"“%s”" % tr(ad["tagline"]), "fi", 960, 640, 64, 1360, "3a200e", align="c"))
    # nothing a kids' channel shows asks anyone to call: the number stays off there
    chy = u"  •  ".join(x for x in (tr(ad.get("where")), "" if kids else ad.get("phone", "")) if x)
    z.append(Zone(chy, "sb", 960, 975, 64, 1800, "fbf1d6", align="c"))
    return z


def _psa(ad):
    z = []
    seal = list(ad.get("seal") or []) + ["", "", ""]
    for word, y, size, font in ((seal[0], 450, 34, "sb"), (seal[1], 488, 26, "sr"), (seal[2], 528, 34, "sb")):
        if word:
            z.append(Zone(tr(word), font, 330, y, size, 200, "0f3d7a", align="c", upper=True, minf=0.4))
    msg = _spellable(tr(ad.get("message")), "sb")
    second_y, from_y = 490, 620
    if width(msg, "sb", 110) * 0.6 > 1100:
        parts, size = wrap(msg, "sb", 84, 1100, minf=0.7)
        for i, part in enumerate(parts):
            z.append(Zone(part, "sb", 640, 350 + 90 * i, size, 1100, "0f3d7a"))
        second_y = 350 + 90 * len(parts) + 40
        from_y = max(from_y, second_y + 64)
    else:
        z.append(Zone(msg, "sb", 640, 380, 110, 1100, "0f3d7a"))
    z.append(Zone(tr(ad.get("second")), "si", 640, second_y, 64, 1100, "2f4f6f"))
    z.append(Zone(_("A message from %s") % tr(ad.get("from")), "sr", 640, from_y, 38, 1100, "2f4f6f"))
    z.append(Zone(_("and this station."), "sbi", 960, 790, 52, 1200, "ffffff", "0f3d7a", align="c"))
    return z


def _video(e, mv, lines):
    """'Now on videocassette' for a movie in the library: (zones, poster, title in the slot)."""
    n = int(e.get("ln", 0))
    top = (lines.get("top") or [["NOW ON", "VIDEOCASSETTE!"]])
    top = top[n % len(top)]
    pitch = lines.get("pitch") or []
    bottom = lines.get("bottom") or []
    z = [Zone(tr(top[0]), "sbi", 820, 255, 84, 1000, "dfe6ee", "0b0b12", upper=True),
         Zone(tr(top[1]), "sbi", 820, 370, 104, 1020, "dfe6ee", "0b0b12", upper=True)]
    title = mv.get("title") or e.get("t") or ""
    if mv.get("year"):
        title = "%s (%s)" % (title, mv["year"])
    spelled = _spellable(title, "sb")
    fallback = ""
    if len(spelled.replace(" ", "")) < 0.8 * len(title.replace(" ", "")):
        fallback = title                     # a script the letters can't spell: the skin's font
    else:
        one = Zone(spelled, "sb", 820, 520, 72, 1000, "ffffff", minf=48 / 72.0)
        if not one.overflows():
            z.append(one)
        else:
            parts, size = wrap(spelled, "sb", 48, 1000, minf=0.8)
            for i, part in enumerate(parts):
                z.append(Zone(part, "sb", 820, 495 + 58 * i, size, 1000, "ffffff"))
    if pitch:
        z.append(Zone(tr(pitch[n % len(pitch)]), "si", 820, 600, 50, 1000, "ffd23a"))
    rating = _rating(mv.get("mpaa"))
    if rating:
        z.append(Zone(rating, "sr", 820, 680, 40, 600, "c9d3e0"))
    if bottom:
        z.append(Zone(tr(bottom[n % len(bottom)]), "sb", 1310, 1000, 44, 1000, "ffffff", align="c"))
    art = mv.get("art") or {}
    poster = art.get("poster") or art.get("fanart") or ""
    if not poster and not fallback:
        # no picture: the slot stays dark and shows the title, larger
        parts, size = wrap(spelled, "sb", 64, 460, lines=2, minf=0.6)
        for i, part in enumerate(parts):
            z.append(Zone(part, "sb", 430, 560 + (i - (len(parts) - 1) / 2.0) * size * 1.2, size, 460,
                          "c9d3e0", align="c"))
    return z, poster, fallback


def _rating(mpaa):
    """'Rated PG' from the library's MPAA field ('Rated PG', 'PG', 'US:PG')."""
    r = (mpaa or "").strip()
    if not r:
        return ""
    if ":" in r:
        r = r.split(":", 1)[1].strip()
    if r.lower().startswith("rated "):
        r = r[6:].strip()
    return _("Rated %s") % r if r and len(r) <= 12 else ""


def card(e, kids=False):
    """Everything a retro ad needs on screen: {"bg", "poster", "zones", "fmt",
    "jingle", "title"} or None when it can't run truthfully any more (the movie
    left the library, the ad isn't in the data)."""
    data = load()
    if e.get("ad") == "video":
        try:
            mv = movie_details(e.get("mv"))
        except Exception as exc:
            log("retro ads: movie %s" % exc)
            mv = None
        if not mv or not mv.get("file"):
            return None
        zones, poster, fallback = _video(e, mv, data["video"])
        fmt = "video"
    else:
        ad = data["by_id"].get(e.get("ad"))
        if not ad or ad.get("claims"):
            return None
        fmt = ad["fmt"]
        zones = _local(ad, kids) if fmt == "local" else {"pitch": _pitch, "kids": _kids, "psa": _psa}[fmt](ad)
        poster, fallback = "", ""
    jingle = os.path.join(JINGLE_DIR, JINGLE[fmt])
    return {"fmt": fmt, "bg": os.path.join(BG_DIR, BACKGROUND[fmt]), "poster": poster, "zones": zones,
            "jingle": jingle if os.path.exists(jingle) else "", "title": fallback}


# ------------------------------------------------------------------ station ID
# The station ID card ("You're watching ...", LAYOUTS.md section 9): it fills the
# last seconds of a break, so it has no jingle and its motion loops (the skin's
# station layers, media/station, tools/retro-ads/make_station_layers.py).
def _spelled(text, font):
    """text in the letters' spelling, or None when they can't spell most of it
    (another script: the skin's font shows it instead)."""
    sp = _spellable(text, font)
    if len(sp.replace(" ", "")) < 0.8 * len(text.replace(" ", "")):
        return None
    return sp


def _lines(text, font, size, maxw, cx, mid, color, line=None, minsize=52, upper=True):
    """One line shrunk to fit (down to minsize), else two lines at minsize (shrunk
    further only if a word is still too wide), centred on cx with their middle at mid."""
    t = text.upper() if upper else text
    one = Zone(t, font, cx, 0, size, maxw, color, line, align="c", minf=float(minsize) / size)
    if not one.overflows():
        s = one.fitted()
        one.y = mid + 0.365 * s
        return [one]
    parts, s = wrap(t, font, minsize, maxw, lines=2, minf=0.3)
    return [Zone(p, font, cx, mid + 0.365 * s + (i - (len(parts) - 1) / 2.0) * 1.15 * s, s, maxw, color, line,
                 align="c", minf=0.3) for i, p in enumerate(parts)]


def station_card(name, number, logo="", tagline="", genre="", headline=None, resume=""):
    """{"fmt": "station", "zones", "logo", "label"...}: the channel's logo fitted in
    the box, its number on the badge, its name on the gold band, the tagline in
    the bottom strip.  No logo: the name in the logo box, the tagline (or the
    genre; neither: the sign-off's return time, else "Channel N") on the band,
    the strip empty.  Never cut off: shrink, then two lines.
    headline: instead of "You're watching" (signoff_card); resume: a line between
    the logo box and the band."""
    head = _("You're watching") if headline is None else headline
    # a longer headline stays clear of the CH badge (its left edge is at ~1540)
    z = [Zone(head, "sbi", 960, 160, 64, 1200 if headline is None else 1100, "ffffff", "070d33", align="c",
              upper=True, minf=0.3),
         Zone("CH", "sb", 1660, 160, 36, 190, "ffffff", align="c"),
         Zone(str(number), "sb", 1660, 250, 96, 190, "ffffff", align="c", minf=0.3)]
    sname = _spelled((name or "").upper(), "sb")
    tag = _spelled(tagline, "si") if tagline else ""
    label = ""
    if logo:
        if sname is None:
            label = name                       # the skin's font on the band (sid_label)
        else:
            z += _lines(sname, "sb", 92, 1400, 960, 798, "14257a")
        if tag:
            z.append(Zone(tag, "si", 960, 1035, 48, 1800, "ffffff", align="c"))
    else:
        if sname is None:
            label = name
        else:
            big = Zone(sname, "sb", 960, 0, 150, 900, "ffffff", "070d33", align="c")
            if big.fitted() >= 90:
                z += _lines(sname, "sb", 150, 900, 960, 440, "ffffff", "070d33", minsize=90)
            else:
                z += _lines(sname, "sb", 120, 900, 960, 440, "ffffff", "070d33", minsize=120)
        band = _spelled(tagline, "sb") if tagline else None
        band = band or (_spelled(genre, "sb") if genre else None)
        if not band:
            # nothing of the channel's own for the band: never leave it empty -
            # the sign-off's "We return at ..." moves onto it, an ID card says "Channel N"
            if resume:
                band = _spelled(resume, "sb")
                if band:
                    resume = ""
            else:
                try:
                    band = _spelled(_("Channel %d") % int(number), "sb")
                except (TypeError, ValueError):
                    band = None
        if band:
            z += _lines(band, "sb", 92, 1400, 960, 798, "14257a", upper=False)
    if resume:
        z.append(Zone(resume, "sbi", 960, 692, 56, 1300, "ffd23a", "070d33", align="c", minf=0.4))
    return {"fmt": "station", "bg": "", "poster": "", "zones": z, "jingle": "", "title": "",
            "logo": logo, "label": label, "label_box": "" if logo else "1"}


def signoff_card(name, number, logo="", tagline="", genre="", resume=""):
    """The sign-off card at the start of a channel's off-air hours: the station ID
    card with "This concludes our broadcast day" on top and "We return at 6:00 AM"
    (resume: the time, as the off-air screen writes it).  Silent, like the ID card."""
    return station_card(name, number, logo, tagline, genre, headline=_("This concludes our broadcast day"),
                        resume=(_("We return at %s") % resume) if resume else "")


def logo_usable(path):
    """A station logo the card can show at once: a file on this box or the
    network that exists (Kodi loads it as the card comes up), or web art Kodi
    already has cached.  Otherwise the card's no-logo layout, never an empty box."""
    if not path:
        return False
    from . import promos
    if path.lower().startswith(("http://", "https://", "image://")):
        return promos.logo_ready(path)
    try:
        import xbmcvfs
        return bool(xbmcvfs.exists(path))
    except Exception:
        return False


# ------------------------------------------------------------------ up next
# The end-of-show "Up next" card (LAYOUTS.md section 10): what comes next on this
# channel, with a live countdown.  It can stay up for about 90 s between films, so
# its motion loops (the skin's upnext layers, tools/retro-ads/make_upnext_layers.py).
# Nothing that names the programme or the channel is ever cut off: shrink, then two
# lines; only the synopsis may end in "..." after its third line.
UN_X, UN_W = 1150, 650


def _wrap_n(text, font, size, maxw, n):
    """Greedy word wrap into at most n lines; (lines, cut) - cut: it didn't all fit."""
    words, lines, cur = text.split(), [], ""
    for i, w in enumerate(words):
        t = (cur + " " + w) if cur else w
        if width(t, font, size) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
            if len(lines) == n:
                return lines, True
    if cur:
        lines.append(cur)
    return lines[:n], len(lines) > n


def _synopsis(text, font, size, maxw, n=3):
    lines, cut = _wrap_n(text, font, size, maxw, n)
    if cut and lines:
        last = lines[-1]
        while last and width(last + u"\u2026", font, size) > maxw:
            last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]
        lines[-1] = last.rstrip(" ,;:") + u"\u2026"
    return lines


def _artists(names, font, size, maxw, n=3):
    """'Josh Groban · Savage Garden · 98° · ...' in up to n lines, wrapped between
    names (never inside one, unless a single name is wider than a line), ending in
    'and more' when not every name fits."""
    sep = u" · "
    more = _("and more")

    def lay(items):
        lines, cur = [], ""
        for k, it in enumerate(items):
            piece = it + (sep.rstrip() if k < len(items) - 1 else "")
            t = (cur + " " + piece) if cur else piece
            if cur and width(t, font, size) > maxw:
                lines.append(cur)
                cur = piece
            else:
                cur = t
        if cur:
            lines.append(cur)
        return lines

    for k in range(len(names), 0, -1):
        lines = lay(names[:k] + ([] if k == len(names) else [more]))
        if len(lines) <= n and all(width(l, font, size) <= maxw for l in lines):
            return lines
    return _synopsis(sep.join(names), font, size, maxw, n)


def _title_zones(title, font="sb"):
    """The title by 1150, 340 (and 440): one line shrunk to fit, or two lines,
    whichever draws it bigger (the preview's "The Long / Weekend" at 96).  A title
    that would go under 48 even on two lines takes three; smaller still rather than
    ever cut off."""
    one = width(title, font, 96)
    s1 = 96.0 if one <= UN_W else 96.0 * UN_W / one
    parts, s2 = wrap(title, font, 96, UN_W, lines=2, minf=0.2)
    if max(s1, s2) < 48:
        size = 60.0
        while size > 24:
            lines, cut = _wrap_n(title, font, size, UN_W, 3)
            if not cut and all(width(l, font, size) <= UN_W for l in lines):
                break
            size -= 2
        lines = _wrap_n(title, font, size, UN_W, 3)[0]
        top = 360 - (len(lines) - 1) * 0.55 * size * 1.08
        return [Zone(l, font, UN_X, top + 0.365 * size + i * 1.08 * size, size, UN_W, "ffffff", minf=0.1)
                for i, l in enumerate(lines)]
    if len(parts) == 2 and s2 > s1:
        return [Zone(p, font, UN_X, 340 + i * 100 * s2 / 96.0, s2, UN_W, "ffffff", minf=0.2)
                for i, p in enumerate(parts)]
    return [Zone(title, font, UN_X, 355 + 0.365 * s1, s1, UN_W, "ffffff", minf=0.1)]


def upnext_info(path, title):
    """What the card says about the next programme: promos.info (picture, logo,
    episode title, plot) plus season/episode, or a film's year, rating and running time."""
    from . import promos
    inf = dict(promos.info(path, title or "")) if path else {"title": title}
    extra = {}
    if path:
        try:
            res = K.rpc("Files.GetFileDetails", {"file": path, "media": "video", "properties": [
                "season", "episode", "year", "mpaa", "runtime", "tvshowid", "art"]})
            extra = res.get("filedetails") or {}
        except Exception as exc:
            log("up next: %s" % exc)
    inf["season"], inf["episode_no"] = extra.get("season", -1), extra.get("episode", -1)
    inf["year"], inf["mpaa"], inf["runtime"] = extra.get("year") or 0, extra.get("mpaa") or "", extra.get("runtime") or 0
    inf["is_movie"] = extra.get("type") == "movie"
    art = extra.get("art") or {}
    inf["poster"] = art.get("poster") or ""
    return inf


def upnext_card(ch, number, name, block, start, when, path, chlogo=""):
    """{"fmt": "upnext", "zones", pictures, labels}: the card for the programme
    `block` ({"t", "sub"} from the schedule) starting at `start` ('4:30 PM': when)."""
    from . import promos
    music = ch.get("type") == "musicvideos"
    title = block.get("t") or ""
    z = [Zone(_("UP NEXT"), "sbi", 140, 172, 80, 520, "14257a", upper=True, minf=0.5)]
    inf = {} if music else upnext_info(path, title)
    pic = poster = ""
    if not music:
        bg = inf.get("bg") or ""
        if bg and inf.get("letterbox"):
            poster = bg                                   # only a poster: centred on a dimmed copy
        elif bg:
            pic = bg
        elif inf.get("poster") and promos.usable_art(inf["poster"]):
            poster = inf["poster"]
    logo = inf.get("logo") or ""
    if logo and not promos.logo_ready(logo):
        logo = ""
    labels = {}
    show_title = library.on_air(inf.get("title") or title) if not music else title
    if not logo:
        sp = _spelled(show_title, "sb")
        if sp is None:
            labels["un_title"] = show_title
        else:
            z += _title_zones(sp)
    # the line under the gold rule
    line = ""
    if music:
        pass
    elif inf.get("is_movie"):
        bits = [str(inf["year"])] if inf.get("year") else []
        r = _rating(inf.get("mpaa"))
        if r:
            bits.append(r)
        rt = int(inf.get("runtime") or 0) // 60
        if rt:
            bits.append(_("%d h %02d min") % (rt // 60, rt % 60) if rt >= 60 else _("%d min") % rt)
        line = u" \u00b7 ".join(bits)
    elif (inf.get("season") or -1) >= 0 and (inf.get("episode_no") or -1) >= 0:
        line = _("Season %d · Episode %d").replace("%d", str(inf["season"]), 1).replace("%d", str(inf["episode_no"]), 1)
    if line:
        z.append(Zone(_spellable(line, "sb"), "sb", UN_X, 560, 46, UN_W, "ffd23a", minf=0.4))
    ep = inf.get("episode") or ""
    if ep:
        sp = _spelled(u"\u201c%s\u201d" % ep, "si")
        if sp is None:
            labels["un_ep"] = u"\u201c%s\u201d" % ep
        else:
            z.append(Zone(sp, "si", UN_X, 620, 46, UN_W, "ffffff", minf=0.5))
    # synopsis, or Boombox's artists
    if music:
        names = [n.strip() for n in (block.get("sub") or "").split(u"\u00b7") if n.strip()]
        names = [_spellable(n, "sr") or n for n in names]
        for i, l in enumerate(_artists(names, "sr", 38, UN_W)):
            z.append(Zone(l, "sr", UN_X, 700 + 50 * i, 38, UN_W, "c9d3e0"))
    else:
        plot = re.sub(r"\s+", " ", inf.get("plot") or "").strip()
        if plot:
            sp = _spelled(plot, "sr")
            if sp is None:
                labels["un_plot"] = plot
            else:
                for i, l in enumerate(_synopsis(sp, "sr", 38, UN_W)):
                    z.append(Zone(l, "sr", UN_X, 700 + 50 * i, 38, UN_W, "c9d3e0"))
    # bottom row: the start time, the channel
    z.append(Zone(_("AT"), "sb", 330, 910, 28, 380, "ffffff", align="c", upper=True))
    z.append(Zone(_spellable(when, "sb"), "sb", 330, 1000, 84, 380, "ffffff", align="c", minf=0.3))
    chan = _("CH %d · %s").replace("%d", str(number), 1).replace("%s", name or "", 1)
    sp = _spelled(chan, "sb")
    if sp is None:
        labels["un_chan"] = chan
    else:
        z += _lines(sp, "sb", 46, 720, 950, 945, "ffffff", minsize=34, upper=False)
    z.append(Zone(_("STARTS IN"), "sb", 1580, 935, 32, 400, "3ee6d0", align="c", upper=True))
    nopic = ""
    if not (pic or poster):
        if chlogo:
            pic = ""
        else:
            nopic = str(number)
            z.append(Zone(nopic, "sb", 600, 520 + 0.365 * 260, 260, 900, "3a3f66", align="c", minf=0.3))
    return {"fmt": "upnext", "zones": z, "pic": pic, "poster": poster, "logo": logo,
            "chlogo": chlogo if not (pic or poster) else "", "labels": labels, "start": start}


CLOCK_AT = {"upnext": (1580, 990, 60, 400), "squeeze": (1545, 762, 64, 560)}


def countdown(start, now, where="upnext"):
    """'2:14' to the programme's real start, 'STARTING NOW' at 0 (where: which card)."""
    x, y, size, maxw = CLOCK_AT[where]
    left = int(math.ceil(start - now))
    if left <= 0:
        return [Zone(_("STARTING NOW"), "sb", x, y, size * 0.8, maxw, "ffffff", align="c", upper=True, minf=0.4)]
    txt = "%d:%02d" % (left // 60, left % 60) if left < 3600 else "%d:%02d:%02d" % (
        left // 3600, left // 60 % 60, left % 60)
    return [Zone(txt, "sb", x, y, size, maxw, "ffffff", align="c")]


# ------------------------------------------------------------------ squeezed credits
# An episode's end credits (scheduler: "cr" from its chapters) keep playing in a
# window on the left with their own sound; the right side says what's next
# (LAYOUTS.md section 11, skin: media/squeeze).  Same facts as the Up next card.
SQ_X, SQ_W = 1270, 560


def squeeze_card(ch, number, name, block, start, when, path):
    """{"zones", "logo", "labels", "start"} for the squeeze's Up next panel."""
    from . import promos
    music = ch.get("type") == "musicvideos"
    title = block.get("t") or ""
    z = [Zone(_("UP NEXT"), "sbi", 1260, 215, 64, 560, "14257a", upper=True, minf=0.5)]
    inf = {} if music else upnext_info(path, title)
    logo = inf.get("logo") or ""
    if logo and not promos.logo_ready(logo):
        logo = ""
    labels = {}
    show_title = library.on_air(inf.get("title") or title) if not music else title
    ep_y, syn_y, syn_lines = 400, 470, 3       # section 11's places for a one-line title
    if not logo:
        sp = _spelled(show_title, "sb")
        if sp is None:
            labels["sq_title"] = show_title
        else:
            # one line shrunk to fit, down to 46; else two lines at up to 64 (not
            # below 46 unless a single word needs it): the episode title moves down
            # and the synopsis gives up its third line instead
            one = width(sp, "sb", 64)
            s1 = 64.0 if one <= 580 else 64.0 * 580 / one
            if s1 >= 46:
                z.append(Zone(sp, "sb", 1260, 325 + 0.365 * s1, s1, 580, "ffffff", minf=0.1))
            else:
                parts, s2 = wrap(sp, "sb", 64, 580, lines=2, minf=46 / 64.0)
                if any(width(p, "sb", s2) > 580 for p in parts):
                    # even two lines at 46 are too wide: three lines at 46 or more
                    s2 = 64.0
                    while s2 > 46 and _wrap_n(sp, "sb", s2, 580, 3)[1]:
                        s2 -= 2
                    parts = _wrap_n(sp, "sb", s2, 580, 3)[0]
                    if _wrap_n(sp, "sb", s2, 580, 3)[1] or any(width(p, "sb", s2) > 580 for p in parts):
                        parts, s2 = wrap(sp, "sb", 46, 580, lines=2, minf=0.2)    # a word wider than a line
                b1 = 285 + 0.8 * s2
                z += [Zone(p, "sb", 1260, b1 + i * 1.1 * s2, s2, 580, "ffffff", minf=0.1)
                      for i, p in enumerate(parts)]
                ep_y = b1 + (len(parts) - 1) * 1.1 * s2 + 48
                syn_y, syn_lines = ep_y + 58, 4 - len(parts)
    ep = inf.get("episode") or ""
    if ep:
        sp = _spelled(u"“%s”" % ep, "si")
        if sp is not None:
            z.append(Zone(sp, "si", SQ_X, ep_y, 40, SQ_W, "ffd23a", minf=0.5))
    elif syn_lines < 3:
        syn_y = ep_y + 10
    if music:
        names = [n.strip() for n in (block.get("sub") or "").split(u"·") if n.strip()]
        for i, l in enumerate(_artists([_spellable(n, "sr") or n for n in names], "sr", 34, SQ_W, syn_lines)):
            z.append(Zone(l, "sr", SQ_X, syn_y + 44 * i, 34, SQ_W, "c9d3e0"))
    else:
        plot = re.sub(r"\s+", " ", inf.get("plot") or "").strip()
        sp = _spelled(plot, "sr") if plot else None
        if sp:
            for i, l in enumerate(_synopsis(sp, "sr", 34, SQ_W, syn_lines)):
                z.append(Zone(l, "sr", SQ_X, syn_y + 44 * i, 34, SQ_W, "c9d3e0"))
    z.append(Zone(_("STARTS IN"), "sb", 1545, 688, 30, SQ_W, "ffffff", align="c", upper=True))
    strip = _("CH %d · %s").replace("%d", str(number), 1).replace("%s", name or "", 1) +         u"  •  " + _("Next at %s") % when
    sp = _spelled(strip, "sb")
    if sp is None:
        labels["sq_strip"] = strip
    else:
        z += _lines(sp, "sb", 50, 1800, 960, 915, "ffffff", minsize=36, upper=False)
    return {"zones": z, "logo": logo, "labels": labels, "start": start}


def apply_squeeze(win, c, slots, now):
    """Letter the squeeze's panel (before its property turns on)."""
    from . import promos
    slots.fill(win, c["zones"])
    slots.fill(win, countdown(c["start"], now, "squeeze"), (SLOT_CLOCK,))
    labels = c.get("labels") or {}
    props = {"sq_logo": c["logo"], "ad_style": promos.style()}
    for key, width_px, ladder in (("sq_title", 580, promos.LADDER_45), ("sq_strip", 1800, promos.LADDER_45)):
        t = labels.get(key, "")
        props[key] = t
        props[key + "2"] = promos.two_lines(t) if t else ""
        props[key + "_fit"] = promos.fit_font(t, width_px, ladder, promos.TWO_27) if t else ""
    for k, v in props.items():
        win.setProperty(k, v)


def apply_upnext(win, c, slots, now):
    """Put the Up next card on the window (before its mode becomes "upnext")."""
    from . import promos
    slots.fill(win, c["zones"])
    slots.fill(win, countdown(c["start"], now), (SLOT_CLOCK,))
    labels = c.get("labels") or {}
    props = {"un_pic": c["pic"], "un_poster": c["poster"], "un_logo": c["logo"], "un_chlogo": c["chlogo"],
             "ad_style": promos.style()}
    for key, width_px, ladder in (("un_title", UN_W, promos.LADDER_60), ("un_chan", 720, promos.LADDER_45)):
        t = labels.get(key, "")
        props[key] = t
        props[key + "2"] = promos.two_lines(t) if t else ""
        props[key + "_fit"] = promos.fit_font(t, width_px, ladder, promos.TWO_27) if t else ""
    props["un_ep"] = labels.get("un_ep", "")
    props["un_plot"] = labels.get("un_plot", "")
    for k, v in props.items():
        win.setProperty(k, v)


def genre_line(ch):
    """The channel's first genre, for a station card without a logo or tagline."""
    for s in ch.get("sources") or []:
        if s.get("type") in ("tvgenre", "moviegenre", "genre") and s.get("value"):
            return s["value"]
    return ""


def music(c, left=None):
    """The jingle, by the Promo music setting (silent cards stay silent).  left:
    seconds the card has left (tuned in part-way): a jingle that wouldn't finish
    isn't started at all - the card stays up silent rather than cut it off."""
    if K.setting_int("promo_music", 0) != 0 or not c.get("jingle"):
        return ""
    if left is not None and left < jingle_len(c["fmt"]) + START:
        return ""
    return c["jingle"]


class Slots(object):
    """The TV window's letter slots, filled from Python (controls declared in
    the skin XML: image controls added from Python are unreliable)."""

    def __init__(self):
        self.used = {SLOT_FILL[0]: 0, SLOT_LINE[0]: 0, SLOT_CLOCK[0]: 0}
        # a new window may hold whatever a card in an earlier one put there: clear all once
        self.stale = {SLOT_FILL[0]: SLOT_FILL[1], SLOT_LINE[0]: SLOT_LINE[1], SLOT_CLOCK[0]: SLOT_CLOCK[1]}

    def fill(self, win, zones, sets=(SLOT_FILL, SLOT_LINE)):
        """Letters into the first slot set, outlines into the second (the countdown:
        its own set, relettered alone)."""
        fills, lines = [], []
        for z in zones:
            for p in z.place():
                (lines if p[6] else fills).append(p)
        pairs = [(sets[0], fills)] + ([(sets[1], lines)] if len(sets) > 1 else [])
        for (first, count), items in pairs:
            if len(items) > count:
                log("retro ads: %d letters, %d slots" % (len(items), count))
                items = items[:count]
            for i, (path, x, y, w, h, color, _o) in enumerate(items):
                try:
                    c = win.getControl(first + i)
                    c.setVisible(True)
                    c.setImage(path, False)
                    c.setPosition(int(round(x)), int(round(y)))
                    c.setWidth(max(1, int(round(w))))
                    c.setHeight(max(1, int(round(h))))
                    c.setColorDiffuse("FF" + color.upper())
                except Exception as exc:
                    K.log_err("retro ads: slot %d %s" % (first + i, exc))
                    break
            # slots left over from the card before: hidden as well as emptied - lettered
            # while their group is hidden (the squeeze, a break's first card after a
            # programme), an emptied slot kept showing its old picture in Kodi 21
            for i in range(len(items), max(self.used.get(first, count), self.stale.get(first, 0))):
                try:
                    c = win.getControl(first + i)
                    c.setImage("", False)
                    c.setVisible(False)
                except Exception:
                    break
            self.used[first] = len(items)
            self.stale[first] = 0


def apply_card(win, c, slots):
    """Put a retro ad on the window (call before the mode becomes "retro")."""
    from . import promos
    slots.fill(win, c["zones"])
    label = c.get("label") or ""
    box = bool(c.get("label_box"))
    for k, v in (("ad_bg", c["bg"]), ("ad_poster", c["poster"]), ("ad_fmt", c["fmt"]),
                 ("ad_title", c["title"]), ("ad_style", promos.style()), ("ad_logo", c.get("logo") or ""),
                 ("sid_label", label), ("sid_label2", promos.two_lines(label)), ("sid_label_box", "1" if box else ""),
                 ("sid_label_fit", promos.fit_font(label, 900 if box else 1400, promos.LADDER_60, promos.TWO_27)
                  if label else "")):
        win.setProperty(k, v)


def demo_entry(ad_id, rng=None):
    """A plan item for one ad (Developer tools / contact sheet)."""
    rng = rng or random.Random()
    return {"k": "retro", "ad": ad_id, "ln": rng.randrange(3)}
