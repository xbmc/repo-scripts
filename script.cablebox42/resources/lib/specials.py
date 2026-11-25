"""Holidays and specials: programming for dates, kept in calendar.json.

    {"specials": [{"id", "name", "when", "repeat", "blocks": [
        {"channel", "start", "end", "sources", "order"}]}]}

`when` is a rule, worked out fresh for each year and never stored as a date:
    {"type": "date", "month": 12, "day": 31}
    {"type": "nth", "n": 4, "weekday": 3, "month": 11}      n 1-4, or -1 for the last;
                                                            weekday 0 = Monday
    {"type": "easter", "offset": -2}                        days from Easter Sunday
    {"type": "years", "dates": {"2026": [11, 8], "2027": [10, 29]}}
                                                            typed per year (Diwali, Hanukkah,
                                                            Lunar New Year): no date that year,
                                                            no special; CableBox never works
                                                            out those calendars itself
each with an optional "shift" in days (the day after Thanksgiving: shift 1).
`repeat` is "yearly", or "once" with a "year".  A block's `start` and `end` are
"HH:MM" on the special's date; an end at or before the start is the next morning
(all day: 00:00-00:00, broadcast day: 06:00-06:00).  `order` is "continue" (where
last year's marathon stopped), "first" or "random".

Nothing is planned ahead: the scheduler asks at(specials, channel, t) while it plans
its usual hours, the way it asks for pinned slots.  No file = no specials.

No Kodi imports at module level (the date rules are checked outside Kodi:
.claude/tools/specials_check.py); only load() / save() without a path reach for
kodiutil.
"""
import datetime
import json
import os
import time
import uuid

DAY = 86400
ORDERS = ("continue", "first", "random")
LOOKAHEAD = 8                   # years to look for a rule's next date (29 Feb: up to 8)

# the ready-made holidays: shortcuts that fill in a rule, nothing more
PRESETS = [
    ("newyear", {"type": "date", "month": 1, "day": 1}),
    ("valentine", {"type": "date", "month": 2, "day": 14}),
    ("easter", {"type": "easter", "offset": 0}),
    ("halloween", {"type": "date", "month": 10, "day": 31}),
    ("thanksgiving", {"type": "nth", "n": 4, "weekday": 3, "month": 11}),
    ("christmaseve", {"type": "date", "month": 12, "day": 24}),
    ("christmas", {"type": "date", "month": 12, "day": 25}),
    ("newyearseve", {"type": "date", "month": 12, "day": 31}),
]


# ---------------------------------------------------------------- date rules

def easter(year):
    """Easter Sunday (Western), by the anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return datetime.date(year, month, day + 1)


def nth_weekday(year, month, weekday, n):
    """The n-th (1-5) or last (n = -1) weekday (0 = Monday) of a month; None when the
    month has no such day (a 5th Thursday)."""
    if n == -1:
        nxt = datetime.date(year + month // 12, month % 12 + 1, 1)
        last = nxt - datetime.timedelta(days=1)
        return last - datetime.timedelta(days=(last.weekday() - weekday) % 7)
    first = datetime.date(year, month, 1)
    day = first + datetime.timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))
    return day if day.month == month else None


def valid(when):
    """Is this a rule date_for() understands?"""
    try:
        kind = when.get("type")
        if not isinstance(when.get("shift", 0), int):
            return False
        if kind == "date":
            datetime.date(2000, when["month"], when["day"])         # 2000: a leap year
            return True
        if kind == "nth":
            return (when["n"] in (1, 2, 3, 4, 5, -1) and when["weekday"] in range(7)
                    and when["month"] in range(1, 13))
        if kind == "easter":
            return isinstance(when.get("offset", 0), int)
        if kind == "years":
            dates = when["dates"]
            if not isinstance(dates, dict) or not dates:
                return False
            for y, md in dates.items():
                datetime.date(int(y), md[0], md[1])
                if len(md) != 2 or len(y) != 4:
                    return False
            return True
    except (AttributeError, KeyError, TypeError, ValueError, IndexError):
        pass
    return False


def date_for(when, year):
    """The rule's date in a year; None when that year has none (29 February in a
    non-leap year, a 5th weekday the month doesn't have) or the rule is broken.
    The shift can carry the date into a neighbouring year (31 December + 1)."""
    if not valid(when):
        return None
    kind = when["type"]
    if kind == "date":
        try:
            day = datetime.date(year, when["month"], when["day"])
        except ValueError:
            return None
    elif kind == "nth":
        day = nth_weekday(year, when["month"], when["weekday"], when["n"])
    elif kind == "years":
        md = when["dates"].get(str(year))
        day = datetime.date(year, md[0], md[1]) if md else None
    else:
        day = easter(year) + datetime.timedelta(days=when.get("offset", 0))
    if day is None:
        return None
    return day + datetime.timedelta(days=when.get("shift", 0))


def season_of(when):
    """The holiday season (seasons.py) a rule is the big day of, for 'Holiday episodes
    of this channel's shows': halloween, thanksgiving, christmas; or None."""
    if not valid(when) or when.get("shift"):
        return None
    if when["type"] == "date":
        return {(10, 31): "halloween", (12, 24): "christmas", (12, 25): "christmas"}.get((when["month"], when["day"]))
    if when["type"] == "nth" and (when["n"], when["weekday"], when["month"]) == (4, 3, 11):
        return "thanksgiving"
    return None


def _years(sp, around):
    """The rule years worth trying for dates near the year `around`."""
    if sp.get("repeat") == "once":
        return [sp["year"]] if isinstance(sp.get("year"), int) else []
    return [around - 1, around, around + 1]         # a shift can cross New Year


def dates_near(sp, day):
    """The special's dates within a year either side of `day`, sorted."""
    out = set()
    for y in _years(sp, day.year):
        d = date_for(sp.get("when"), y)
        if d:
            out.add(d)
    return sorted(out)


# ---------------------------------------------------------------- hours

def mins(hhmm):
    """'18:30' -> 1110 (0 for anything unreadable)."""
    try:
        h, m = str(hhmm).split(":")
        return max(0, min(1439, int(h) * 60 + int(m)))
    except (TypeError, ValueError):
        return 0


def span(block):
    """(start, end) in minutes from midnight of the special's date; an end at or
    before the start is the next morning, so the end can pass 1440."""
    a, b = mins(block.get("start")), mins(block.get("end"))
    return a, (b if b > a else b + 1440)


def _ts(day, minutes):
    """Local wall-clock time `minutes` after midnight of `day`, as a timestamp
    (right across a daylight-saving change: 06:00 is 06:00)."""
    dt = datetime.datetime.combine(day, datetime.time()) + datetime.timedelta(minutes=minutes)
    return time.mktime(dt.timetuple())


def window(block, day):
    """(start, end) timestamps of a block for the special's date `day`."""
    a, b = span(block)
    return _ts(day, a), _ts(day, b)


# ---------------------------------------------------------------- what's on

def _windows(specials, channel, t0, t1):
    """[(start, end, special, block)] on a channel touching [t0, t1), by start."""
    out = []
    d0 = datetime.date.fromtimestamp(t0) - datetime.timedelta(days=1)   # a block can run into the next day
    d1 = datetime.date.fromtimestamp(max(t0, t1))
    for sp in specials or ():
        blocks = [b for b in sp.get("blocks") or () if b.get("channel") == channel]
        if not blocks:
            continue
        for y in _years(sp, d0.year) if d0.year == d1.year else sorted(set(_years(sp, d0.year) + _years(sp, d1.year))):
            day = date_for(sp.get("when"), y)
            if not day or not d0 <= day <= d1:
                continue
            for b in blocks:
                st, en = window(b, day)
                if st < t1 and en > t0:
                    out.append((st, en, sp, b))
    out.sort(key=lambda w: (w[0], w[1]))
    return out


def at(specials, channel, t):
    """The special on this channel at time t: (special, block, start, end), or
    (None, None, None, None).  When two cover t, the one that started last."""
    hit = None
    for st, en, sp, b in _windows(specials, channel, t, t + 1):
        if st <= t < en:
            hit = (sp, b, st, en)
    return hit or (None, None, None, None)


def next_change(specials, channel, t, horizon=8 * DAY):
    """The next time strictly after t that a special starts or ends on this channel
    (within the horizon), or None: where the planner has to stop a programme."""
    best = None
    for st, en, _sp, _b in _windows(specials, channel, t, t + horizon):
        for x in (st, en):
            if t + 0.5 < x <= t + horizon and (best is None or x < best):
                best = x
    return best


def between(specials, t0, t1, channel=None):
    """[(start, end, special, block)] in [t0, t1), by start; every channel, or one.
    For the weekly planner's marks and the guide."""
    chans = [channel] if channel is not None else sorted(
        {b.get("channel") for sp in specials or () for b in sp.get("blocks") or ()}, key=str)
    out = []
    for c in chans:
        out.extend(_windows(specials, c, t0, t1))
    out.sort(key=lambda w: (w[0], w[1]))
    return out


def overlapping(specials, sp):
    """Other specials whose hours on a channel overlap this one's on its next date
    (the editor's Cancel / Replace question): [(other special, channel)]."""
    out = []
    day, _skipped = next_date(sp, time.time())
    if not day:
        return out
    for b in sp.get("blocks") or ():
        st, en = window(b, day)
        others = [o for o in specials or () if o.get("id") != sp.get("id")]
        for _s, _e, o, _b in _windows(others, b.get("channel"), st, en):
            if (o, b.get("channel")) not in out:
                out.append((o, b.get("channel")))
    return out


# ---------------------------------------------------------------- the list

def _last_end(sp, day):
    """When the special's last block ends for the date `day` (end of that day when
    it has no blocks yet)."""
    ends = [window(b, day)[1] for b in sp.get("blocks") or ()]
    return max(ends) if ends else _ts(day, 1440)


def next_date(sp, now):
    """(date, skipped years): the special's next date, counting one that is still
    on the air; skipped lists the years before it that have no such date (29 Feb).
    (None, skipped) when there is none: a 'this year only' special that has passed,
    a broken rule."""
    today = datetime.date.fromtimestamp(now)
    skipped = []
    if sp.get("repeat") == "once":
        years = _years(sp, today.year)
    else:
        years = range(today.year - 1, today.year + LOOKAHEAD + 1)
    for y in years:
        day = date_for(sp.get("when"), y)
        if day is None:
            if y >= today.year:
                skipped.append(y)
            continue
        if _last_end(sp, day) > now:
            return day, skipped
    return None, skipped


def upcoming(specials, now):
    """[(date, special, skipped years)], soonest first; specials with no next date
    are left out."""
    rows = []
    for sp in specials or ():
        day, skipped = next_date(sp, now)
        if day:
            rows.append((day, sp, skipped))
    rows.sort(key=lambda r: (r[0], (r[1].get("name") or "").lower()))
    return rows


def expired(sp, now):
    """A 'this year only' special whose date has passed."""
    return sp.get("repeat") == "once" and valid(sp.get("when")) and next_date(sp, now)[0] is None


# ---------------------------------------------------------------- storage

_cache = {}                     # path -> (mtime, specials)


def path():
    from .kodiutil import PROFILE
    return os.path.join(PROFILE, "calendar.json")


def new_id():
    return uuid.uuid4().hex[:6]


def clean(data):
    """The specials of a loaded file that can be used; anything broken is left out
    (never an exception: a bad calendar.json means no specials, not no TV)."""
    out = []
    items = data.get("specials") if isinstance(data, dict) else None
    for sp in items if isinstance(items, list) else ():
        if not isinstance(sp, dict) or not sp.get("id") or not valid(sp.get("when")):
            continue
        if sp.get("repeat") == "once":
            if not isinstance(sp.get("year"), int):
                continue
        else:
            sp["repeat"] = "yearly"
        sp["name"] = sp["name"] if isinstance(sp.get("name"), str) else ""
        blocks = []
        for b in sp["blocks"] if isinstance(sp.get("blocks"), list) else ():
            if isinstance(b, dict) and b.get("channel") is not None and isinstance(b.get("sources"), list):
                if b.get("order") not in ORDERS:
                    b["order"] = "continue"
                blocks.append(b)
        sp["blocks"] = blocks
        out.append(sp)
    return out


def load(file=None):
    """The specials ([] when there is no calendar.json).  Read again only when the
    file has changed: the scheduler asks often."""
    file = file or path()
    try:
        mt = os.path.getmtime(file)
    except OSError:
        _cache.pop(file, None)
        return []
    hit = _cache.get(file)
    if hit and hit[0] == mt:
        return hit[1]
    try:
        with open(file, "r", encoding="utf-8") as f:
            specials = clean(json.load(f))
    except (IOError, OSError, ValueError):
        specials = []
    _cache[file] = (mt, specials)
    return specials


def save(specials, file=None, now=None):
    """Write the specials; 'this year only' ones that have passed are dropped."""
    file = file or path()
    now = time.time() if now is None else now
    keep = [sp for sp in specials if not expired(sp, now)]
    folder = os.path.dirname(file)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    tmp = file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"specials": keep}, f, separators=(",", ":"))
    os.replace(tmp, file)
    _cache.pop(file, None)
    return keep


def find(specials, sid):
    for sp in specials or ():
        if sp.get("id") == sid:
            return sp
    return None


def bookmark_key(sp, title):
    """A marathon's own bookmark, so the show's regular run doesn't jump ahead and
    next year continues where this year stopped."""
    return "event:%s|tv:%s" % (sp.get("id"), title)
