"""One-step setups that make a lineup feel like real TV:

* overnight sign-off (default 12 AM - 5 AM) on every program channel
* prime-time lineups (default 8 - 11 PM): network channels get a weekly
  schedule of their best shows as pinned slots (half-hour comedies first,
  hour dramas later, a different lineup each night, in order week to week);
  movie channels get a nightly "Movie at 8".

Everything is written as ordinary off-air windows and pinned slots marked
"auto", so the weekly planner shows them and the user can edit them.
Hand-made pins are never touched.
"""
import uuid

from . import library
from . import assign
from .kodiutil import _

PRIME_START, PRIME_END = "20:00", "23:00"
OFF_START, OFF_END = "00:00", "05:00"
TV_TYPES = ("network",)
ALL_PROGRAM = ("network", "movies", "loop")


def _m(hhmm):
    h, m = str(hhmm).split(":")[:2]
    return int(h) % 24 * 60 + int(m)


def _hhmm(m):
    m %= 1440
    return "%02d:%02d" % (m // 60, m % 60)


# ------------------------------------------------------------------ overnight
def set_overnight(chans, start=OFF_START, end=OFF_END):
    for c in chans:
        if c.get("type") in ALL_PROGRAM:
            c["offair"] = [{"start": start, "end": end, "days": "all"}]
            c.setdefault("offair_style", "standby")


def clear_overnight(chans):
    for c in chans:
        if c.get("type") in ALL_PROGRAM:
            c["offair"] = []


# ------------------------------------------------------------------ prime time
def clear_prime(chans):
    for c in chans:
        c["slots"] = [r for r in c.get("slots", []) if not r.get("auto")]


def _slot_minutes(eps, step=30):
    durs = sorted(e["dur"] for e in eps[:30])
    med = durs[len(durs) // 2] / 60.0
    return int(-(-(med + 2) // step) * step)       # room for the breaks


def _manual_busy(c):
    """Minutes-of-week covered by hand-made pins: never overwritten."""
    busy = set()
    for r in c.get("slots", []):
        if r.get("auto"):
            continue
        days = r.get("days")
        days = list(range(7)) if days in (None, "all") else [0, 1, 2, 3, 4] if days == "weekdays" \
            else [5, 6] if days == "weekends" else list(days)
        for d in days:
            st = d * 1440 + _m(r["start"])
            for k in range(0, int(r.get("minutes", 30)), 30):
                busy.add((st + k) % (7 * 1440))
    return busy


def _ranked_shows(c, assignment):
    ok = assign.allowed_fn(assignment, c["id"])
    hidden = set(x.lower() for x in c.get("exclude", []))
    pool = library.resolve(c.get("sources", []))
    meta = dict((s["title"].lower(), s) for s in library.all_tvshows())
    shows = []
    for ser in pool["series"]:
        tl = ser["title"].lower()
        if tl in hidden or not ok(tl, False) or len(ser["episodes"]) < 2:
            continue
        mins = _slot_minutes(ser["episodes"])
        if mins > 90:
            continue
        info = meta.get(tl, {})
        shows.append((float(info.get("rating") or 0), len(ser["episodes"]), ser["title"], mins))
    shows.sort(key=lambda x: (-x[0], -x[1], x[2]))
    return [(title, mins) for _r, _n, title, mins in shows]


def prime_time(chans, assignment, start=PRIME_START, end=PRIME_END):
    """Replace the automatic prime-time pins on every channel."""
    clear_prime(chans)
    p0, p1 = _m(start), _m(end)
    length = (p1 - p0) % 1440 or 180
    made = {}
    for c in chans:
        if c.get("type") == "movies" and c.get("sources"):
            busy = _manual_busy(c)
            days = [d for d in range(7) if (d * 1440 + p0) not in busy]
            if days:
                c.setdefault("slots", []).append({
                    "id": uuid.uuid4().hex[:6], "label": _("Movie at %s") % _clock_label(p0),
                    "start": _hhmm(p0), "minutes": length, "days": "all" if len(days) == 7 else days,
                    "order": "random", "sources": list(c["sources"]), "auto": True})
                made[c["id"]] = 1
            continue
        if c.get("type") not in TV_TYPES:
            continue
        shows = _ranked_shows(c, assignment)
        if len(shows) < 2:
            continue
        busy = _manual_busy(c)
        nightly = {}
        cursor = 0
        for d in range(7):
            picks, used, t = [], 0, 0
            tries = 0
            while used < length and tries < len(shows) * 2:
                title, mins = shows[cursor % len(shows)]
                cursor += 1
                tries += 1
                if any(p[0] == title for p in picks) and len(shows) > 3:
                    continue
                if used + mins > length:
                    continue
                picks.append((title, mins))
                used += mins
            picks.sort(key=lambda p: p[1])                 # comedies first, dramas later
            for title, mins in picks:
                st = d * 1440 + p0 + t
                if not any(((st + k) % (7 * 1440)) in busy for k in range(0, mins, 30)):
                    nightly.setdefault((title, _hhmm(p0 + t), mins), []).append(d)
                t += mins
        for (title, hhmm, mins), days in sorted(nightly.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            c.setdefault("slots", []).append({
                "id": uuid.uuid4().hex[:6], "label": title, "start": hhmm, "minutes": mins,
                "days": "all" if len(days) == 7 else ("weekdays" if days == [0, 1, 2, 3, 4] else days),
                "order": "inorder", "sources": [{"type": "tvshow", "value": [title]}], "auto": True})
        made[c["id"]] = len(nightly)
    return made


def _clock_label(m):
    h12 = (m // 60) % 24 % 12 or 12
    return ("%d" % h12) if m % 60 == 0 else ("%d:%02d" % (h12, m % 60))
