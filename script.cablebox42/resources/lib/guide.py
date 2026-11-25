"""The guide channel's grid, Prevue style: short channel labels, listing details
fitted to a cell, and the scroll-ad rows between the last channel and the first.

No skin or player code here (tv.fill_guide lays the rows out); reads only the
viewer's optional guide.txt (never writes to the station folder).
"""
import re
import time

from . import promos
from . import stations
from .kodiutil import _

CELL_W = (460, 460, 440)            # the three listing cells' label widths (skin list 50)
CALL_W = 270
LADDER_CALL = (("font37", 37), ("font27", 27), ("font12", 25), ("font10", 23))
LADDER_CELL = (("font27", 27), ("font12", 25))
SPEEDS = (3.0, 2.5, 1.7)            # seconds per row: Slow / Normal / Fast
_SKIP_WORDS = ("the", "and", "of", "&", "a", "channel", "network")
_OWN_ADS = {}                       # folder -> (read at, lines)
_OWN_TTL = 600


def speed(index):
    try:
        return SPEEDS[int(index)]
    except (ValueError, IndexError, TypeError):
        return SPEEDS[1]


def short_call(name, call):
    """The channel cell's label: the station's call letters, else a short
    uppercase abbreviation of the name (at most 5 letters): 'Shorties TV' -> 'STV',
    'Chameleon' -> 'CHAM', 'Red Thread TV' -> 'RTTV', 'The Exploration Channel' -> 'EXPL'."""
    call = (call or "").strip()
    if call:
        return call.upper()
    words = [w for w in re.split(r"[^0-9A-Za-z]+", name or "") if w]
    keep = [w for w in words if w.lower() not in _SKIP_WORDS] or words
    if not keep:
        return ""
    if len(keep) == 1:
        w = keep[0].upper()
        return w if len(w) <= 5 else w[:4]
    out = ""
    for w in keep:
        # short all-capitals words stay whole (TV, HBO, 42)
        out += w if (w.isupper() or w.isdigit()) and len(w) <= 3 else w[0].upper()
    return out[:5]


def details(info, rerun=False, special=""):
    """The listing's details in the order they're dropped last to first: the name of
    the special it airs in ('Taxi \u00b7 Turkey Day Marathon'), '(R)' for a summer rerun, movies
    '(1990)' and 'PG-13'; then '(CC)' and '(Stereo)'."""
    from . import library
    out = ([u"\u00b7 " + special] if special else []) + ([_("(R)")] if rerun else [])
    if info:
        if info.get("kind") == "movie":
            if info.get("year"):
                out.append("(%s)" % info["year"])
            code = library.mpaa_code(info.get("mpaa"))
            if code:
                out.append(code)
        if info.get("cc"):
            out.append(_("(CC)"))
        if info.get("stereo"):
            out.append(_("(Stereo)"))
    return out


def fit_cell(title, extra, width):
    """(text, font, two-line text) for a listing cell: the details go before the
    title is shrunk, and the title is never cut (smaller font, then two lines:
    font 'two', a value no font name ends like - font12 ends in 2)."""
    for k in range(len(extra), -1, -1):
        txt = " ".join([title] + list(extra[:k]))
        f = promos.fit_font(txt, width, LADDER_CELL, promos.TWO_23)
        if not f.endswith("2"):
            return txt, f, ""
    f = promos.fit_font(title, width, promos.LADDER_27, promos.TWO_23)
    return (title, f, "") if not f.endswith("2") else (title, "two", promos.two_lines(title))


def call_fit(text):
    f = promos.fit_font(text, CALL_W, LADDER_CALL, promos.TWO_23)
    return (f, "") if not f.endswith("2") else ("two", promos.two_lines(text))


def builtin_ads():
    """Fictional cable-company lines (no real brands)."""
    return [_("Add a premium channel today!  Call your cable company."),
            _("Pay-Per-View: call 555-0142 to order."),
            _("Ask about our Movie Lovers package."),
            _("Two months of premium channels, half price."),
            _("Moving?  Take your cable with you.  Call 555-0199."),
            _("Remote not working?  Free replacement at the cable office."),
            _("New this month: more channels on the basic tier."),
            _("Watch the big fight live on Pay-Per-View."),
            _("Cable installation: just $9.95 this month."),
            _("Thank you for choosing cable.")]


def own_ads(folder):
    """The guide channel's guide.txt (one ad per line; '#' lines are notes), read-only."""
    if not folder:
        return []
    hit = _OWN_ADS.get(folder)
    if hit and time.time() - hit[0] < _OWN_TTL:
        return hit[1]
    lines = []
    for f in ("guide.txt", "Guide.txt", "GUIDE.TXT"):
        text = promos._read_text(stations._join(folder, f))
        if text:
            lines = [ln.strip() for ln in text.lstrip(u"﻿").splitlines()
                     if ln.strip() and not ln.strip().startswith("#")]
            break
    _OWN_ADS[folder] = (time.time(), lines)
    return lines


KIDS_GENRES = ("animation", "family", "children", "children's", "kids")
SPORTS_GENRES = ("sport", "sports", "football", "soccer", "basketball", "baseball", "hockey", "boxing",
                 "wrestling", "motorsport", "golf", "tennis")
KIDS_STATIONS = ("chameleon", "animation_station")


def kids_channel(ch):
    """A kids' channel for the guide's colours: Ad flavour Kids (set or automatic),
    or a built-in kids' station (Chameleon with its CAM Jr. block, Animation Station)."""
    from . import ads
    return ch.get("station") in KIDS_STATIONS or ads.flavour(ch) == "K"


def category(info, kids_ch=False):
    """The listing cell's colour: 'movie' (any movie), 'sports', 'kids' or '' (the row's blue).
    From the library's genres; on a kids' channel every programme counts as kids."""
    if info and info.get("kind") == "movie":
        return "movie"
    genres = [g.lower() for g in (info or {}).get("genre") or []]
    if any(g in SPORTS_GENRES for g in genres):
        return "sports"
    if kids_ch or any(g in KIDS_GENRES for g in genres):
        return "kids"
    return ""


def ad_count(channels):
    """Scroll ads a cycle: 1 for a small lineup, up to 3 for a big one."""
    return max(1, min(3, int(round(channels / 8.0))))
