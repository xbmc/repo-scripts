"""Holidays and specials: the editor (main menu > Holidays & events, and a channel's Schedule group).

It opens on a month calendar (Calendar: a 6 x 7 grid of days, a star on the days with
a special; OK on a day: its specials and 'Add a special on this day') or on the
soonest-first list, whichever was used last (open_specials).
The list is a menu (changes save as you go, Done at the bottom).  Adding a special is
step-by-step: Back on any step cancels it and nothing is saved; it ends on a
Cancel / Add special question.  The rules, hours and calendar.json are specials.py;
what airs on the day is scheduler.py.

Saving replans the channels a special is on and the channels whose shows it now
keeps off, each from the end of what is on air (replan); no other channel is touched.

A block whose channel is no longer in the lineup (Build my lineup > Replace gives every
channel a new id) is kept: it reads 'channel removed', airs nowhere, and selecting it
offers Choose a channel / Remove.  Only deleting a channel by hand takes its blocks.
"""
import datetime
import json
import os
import threading
import time

import xbmc
import xbmcgui

from . import kodiutil as K
from . import channels as C
from . import scheduler
from . import specials
from . import manager as M
from . import planner as P
from .kodiutil import _

D = M.D
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December")
SEASON = {"halloween": _("Halloween"), "thanksgiving": _("Thanksgiving"), "christmas": _("Christmas")}
PRESET = {"newyear": _("New Year's Day"), "valentine": _("Valentine's Day"), "easter": _("Easter"),
          "halloween": _("Halloween"), "thanksgiving": _("Thanksgiving (US)"), "christmaseve": _("Christmas Eve"),
          "christmas": _("Christmas Day"), "newyearseve": _("New Year's Eve")}
ORDERS = (("continue", _("Continue where last year's marathon stopped"), _("in order, continuing each year")),
          ("first", _("From the first episode"), _("from the first episode")),
          ("random", _("Random"), _("random")))
DOT = u"  ·  "


# ------------------------------------------------------------------ words
def now():
    """The clock specials go by (the real one, unless the test setting moves today)."""
    return time.time() + scheduler.specials_shift(K.schedule_cfg())


def today():
    return datetime.date.fromtimestamp(now())


def month(m, short=False):
    """Kodi's own month names (January = 21, Jan = 51)."""
    try:
        s = xbmc.getLocalizedString((50 if short else 20) + m)
    except Exception:
        s = ""
    return s or (MONTHS[m - 1][:3] if short else MONTHS[m - 1])


def date_text(day):
    """'Thu 26 Nov', with the year when it isn't this one."""
    txt = "%s %d %s" % (P.day_names()[day.weekday()], day.day, month(day.month, True))
    return txt if day.year == today().year else "%s %d" % (txt, day.year)


def nth_names():
    return [_("1st"), _("2nd"), _("3rd"), _("4th"), _("Last")]


def when_text(when):
    """A rule in words: '31 December', '4th Thursday of November', 'Good Friday'."""
    kind = when.get("type")
    if kind == "date":
        txt = "%d %s" % (when["day"], month(when["month"]))
    elif kind == "nth":
        n = when["n"]
        txt = _("%s %s of %s") % (nth_names()[4 if n == -1 else n - 1] if n in (1, 2, 3, 4, -1) else _("5th"),
                                  P.day_names(False)[when["weekday"]], month(when["month"]))
    elif kind == "years":
        txt = years_text(when)
    else:
        off = when.get("offset", 0)
        txt = {0: _("Easter Sunday"), -2: _("Good Friday"), 1: _("Easter Monday")}.get(off) or (
            (_("%d days after Easter") % off) if off > 0 else (_("%d days before Easter") % -off))
    shift = when.get("shift", 0)
    if shift == 1:
        return _("The day after %s") % txt
    if shift == -1:
        return _("The day before %s") % txt
    if shift:
        return (_("%d days after %s") if shift > 0 else _("%d days before %s")) % (abs(shift), txt)
    return txt


def years_text(when):
    """A rule typed per year in words: the next date and how many years have one,
    or that this year has none ('no date for 2031')."""
    t = today()
    have = sorted(int(y) for y in when.get("dates") or {})
    nxt = None
    for y in have:
        d = specials.date_for(dict(when, shift=0), y)
        if d and d >= t:
            nxt = d
            break
    if nxt is None:
        return _("Dates for each year: none from today on")
    txt = _("Dates for each year: next %s (%d years typed)") % (date_text(nxt), len(have))
    if t.year not in have and nxt.year != t.year:
        txt += "  " + _("no date for %d") % t.year
    return txt


def ask_years(current=None):
    """A 'years' rule: the date typed for each year, this year and the nine after
    (CableBox never works out lunar or other calendars: you type what yours says).
    None on Back; a year left without a date has no season or special that year."""
    dates = dict((current or {}).get("dates") or {})
    first = today().year
    months = [month(m) for m in range(1, 13)]
    pos = 0
    while True:
        years = list(range(first, first + 10))
        rows = []
        for y in years:
            md = dates.get(str(y))
            rows.append("%d:  %s" % (y, ("%d %s" % (md[1], months[md[0] - 1])) if md else _("no date")))
        rows.append(_("[B]Done[/B]"))
        i = D.select(_("Dates for each year"), rows, preselect=pos)
        if i < 0:
            return None
        if i == len(years):
            if not dates:
                D.ok(M.TITLE, _("Type the date of at least one year."))
                continue
            return {"type": "years", "dates": dates}
        pos = i
        y = years[i]
        md = dates.get(str(y))
        m = D.select(str(y), months + [_("No date this year")], preselect=(md[0] - 1) if md else 0)
        if m < 0:
            continue
        if m == 12:
            dates.pop(str(y), None)
            continue
        last = (datetime.date(y + (m + 1) // 12, (m + 1) % 12 + 1, 1) - datetime.timedelta(days=1)).day
        d = D.select("%s %d" % (months[m], y), [str(k) for k in range(1, last + 1)],
                     preselect=(md[1] - 1) if md and md[0] == m + 1 else 0)
        if d >= 0:
            dates[str(y)] = [m + 1, d + 1]
            pos = min(i + 1, len(years))


# ------------------------------------------------------------------ the holiday list (seasons.py)
def seasons_cfg():
    """The holiday seasons as planning sees them, without the rig's test date."""
    sc = dict(K.seasons_cfg())
    sc.pop("shift", None)
    return sc


def season_name(sid, sc=None):
    """A holiday's name: its own (seasons.json), the built-in's, or its id."""
    d = (sc if sc is not None else seasons_cfg()).get(sid) or {}
    return d.get("name") or SEASON.get(sid) or sid


def holidays(sc=None):
    """[(id, name, its first big day as a rule, has material)] in list order: the
    built-ins and every holiday the viewer added (Holidays & events > Holiday seasons)."""
    from . import seasons
    sc = sc if sc is not None else seasons_cfg()
    out = []
    for sid in seasons.order(sc):
        d = sc.get(sid) or {}
        tags, genres = seasons._season_words(sid, {"seasons": sc})
        stuff = bool(tags or genres or seasons.title_words(sid, sc))
        out.append((sid, season_name(sid, sc), seasons.rules(sid, d)[1], stuff))
    return out


def holiday_of_rule(when, sc=None):
    """The holidays a special's date is the big day of: the season whose first big
    day is this rule, and for the built-ins any of their big days (25 December is
    Christmas too)."""
    key = json.dumps(when, sort_keys=True)
    out = [sid for sid, _n, rule, _s in holidays(sc) if json.dumps(rule, sort_keys=True) == key]
    builtin = specials.season_of(when)
    if builtin and builtin not in out:
        out.append(builtin)
    return out


def repeat_text(sp):
    return _("Every year") if sp.get("repeat") != "once" else _("Only in %d") % sp.get("year", 0)


def hours_text(blk):
    a, b = specials.span(blk)
    if (a, b) == (0, 1440):
        return _("all day")
    if (a, b) == (360, 1800):
        return _("broadcast day")
    return "%s - %s" % (P.clock(a), P.clock(b))


def source_text(blk):
    season = scheduler.ChannelSchedule._holiday_source(blk)
    if season is not None:
        return _("%s episodes") % season_name(season)
    srcs = blk.get("sources") or [{}]
    return P.source_label(srcs[0]) + ((" +%d" % (len(srcs) - 1)) if len(srcs) > 1 else "")


def order_text(blk, row=True):
    if single_movie(blk):
        return ""                    # one movie: no order to speak of
    for key, label, short in ORDERS:
        if key == blk.get("order"):
            return short if row else label
    return ""


def chan(chans, cid):
    for c in chans:
        if c["id"] == cid:
            return c
    return None


def chan_name(ch):
    return "%d %s" % (ch["number"], ch["name"])


def what_text(blk):
    return "%s, %s" % (source_text(blk), hours_text(blk))


def block_text(chans, blk):
    ch = chan(chans, blk.get("channel"))
    return "%s: %s" % (chan_name(ch) if ch else _("Channel removed"), what_text(blk))


def lost(chans, sp):
    """The special's blocks whose channel is no longer in the lineup."""
    ids = set(c["id"] for c in chans)
    return [b for b in sp["blocks"] if b.get("channel") not in ids]


# ------------------------------------------------------------------ calendar.json
def load(chans=None):
    """A copy of the specials to change freely.  Blocks of channels that are gone
    stay (see lost); 'this year only' specials that have passed go when it is saved."""
    cal = json.loads(json.dumps(specials.load()))
    return [sp for sp in cal if not specials.expired(sp, now())]


REPLAN_FILE = os.path.join(K.PROFILE, "specials_replan.json")
REPLAN_BELL = "cablebox42.specials_replan"      # home property: the service looks at once


def save(cal, cids=(), sp=None):
    """Write calendar.json and ask the service to plan again - from the end of what
    is on air - the channels in `cids` and the channels whose shows `sp` now keeps
    off (run_pending).  Returns at once: the editor never waits for planning."""
    specials.save(cal, now=now())
    scheduler.forget_specials()
    try:
        want = K.load_json(REPLAN_FILE, None) or {}
        want["cids"] = sorted(set(want.get("cids") or []) | set(c for c in cids if c))
        want["sps"] = sorted(set(want.get("sps") or []) | ({sp["id"]} if sp is not None else set()))
        K.save_json(REPLAN_FILE, want)
        xbmcgui.Window(10000).setProperty(REPLAN_BELL, str(time.time()))
    except Exception as exc:
        K.log_err("Holidays and specials, asking to plan again: %s" % exc)


def run_pending(busy=""):
    """In the service: the replanning the editor asked for (save).  Not while another
    tool refreshes (busy: its TOOL_BUSY), which would plan the same channels.  True
    if it planned."""
    if busy and busy != "specials" or not os.path.exists(REPLAN_FILE):
        return False
    want = K.load_json(REPLAN_FILE, None) or {}
    try:
        os.remove(REPLAN_FILE)
    except OSError:
        pass
    xbmcgui.Window(10000).clearProperty(REPLAN_BELL)
    scheduler.forget_specials()
    todo = set(want.get("cids") or [])
    try:
        lineup = scheduler.Lineup(K.schedule_cfg())
        for sid in want.get("sps") or []:
            sp = specials.find(specials.load(), sid)
            if sp is not None:
                todo |= kept_off(lineup, sp)
        replan(lineup, todo)
    except Exception as exc:
        K.log_err("Holidays and specials, planning again: %s" % exc)
    return True


def kept_off(lineup, sp):
    """Channels that have one of the special's shows planned during its hours."""
    off = scheduler.specials_shift(lineup.cfg)
    day, _skipped = specials.next_date(sp, time.time() + off)
    out = set()
    if not day:
        return out
    for blk in sp["blocks"]:
        ch = chan(lineup.channels, blk.get("channel"))
        if not ch:
            continue
        titles = set(t.lower() for t in lineup.schedule(ch, ensure=False)._special_titles(blk))
        if not titles:
            continue
        st, en = specials.window(blk, day)
        for c in lineup.channels:
            if c["id"] == ch["id"] or c["type"] in ("guide", "weather"):
                continue
            other = lineup.schedule(c, ensure=False)
            if any(b.get("k") == "show" and b["t"].lower() in titles for b in other.blocks_between(st - off, en - off)):
                out.add(c["id"])
    return out


def replan(lineup, cids):
    """Cut these channels after what is on air (all of them first: bookmarks go back
    before anything is planned again), then plan them.  Holds TOOL_BUSY like a tool."""
    cids = [c for c in lineup.channels if c["id"] in cids]
    if not cids:
        return
    home = xbmcgui.Window(10000)
    mine = not home.getProperty(M.TOOL_BUSY)
    if mine:
        home.setProperty(M.TOOL_BUSY, "specials")
    try:
        t = time.time()
        with lineup.lock:
            for c in cids:
                s = lineup.schedule(c, ensure=False)
                s.reload()
                if s.data["entries"] and s.data["until"] >= t:
                    s.cut(t)
                s.data["hash"] = s.full_hash()
                s.save()
            for c in cids:
                try:
                    lineup.schedule(c, ensure=False).ensure(t)
                except Exception as exc:
                    K.log("Schedule build failed for %s: %s" % (c.get("name"), exc))
        K.log("Holidays and specials: planned again: %s" % ", ".join(c["name"] for c in cids), xbmc.LOGINFO)
    finally:
        if mine:
            home.clearProperty(M.TOOL_BUSY)


# ------------------------------------------------------------------ deleting a channel
def on_channel(cid):
    """Names of the specials with programming on this channel."""
    t = now()
    return [sp["name"] for sp in specials.load()
            if any(b.get("channel") == cid for b in sp["blocks"]) and not specials.expired(sp, t)]


def drop_channel(cid):
    """The channel is deleted: its blocks go, and specials left with none."""
    cal = json.loads(json.dumps(specials.load()))
    if not any(b.get("channel") == cid for sp in cal for b in sp["blocks"]):
        return
    for sp in cal:
        sp["blocks"] = [b for b in sp["blocks"] if b.get("channel") != cid]
    specials.save([sp for sp in cal if sp["blocks"]], now=now())
    scheduler.forget_specials()


# ------------------------------------------------------------------ the list
def view():
    """'calendar' (to start with) or 'list': the one used last."""
    return "list" if K.load_state().get("specials_view") == "list" else "calendar"


def set_view(name):
    if K.load_state().get("specials_view") != name:
        K.update_state({"specials_view": name})


def open_specials(cid=None):
    """Tools > Holidays and specials; with cid, the same for one channel.  The month
    calendar or the list, as last time; each has a way to the other."""
    if not [c for c in C.load() if c["type"] in M.AIR_TYPES]:
        D.ok(M.TITLE, _("Add a channel first."))
        return
    which = view()
    while which:
        which = open_calendar(cid) if which == "calendar" else open_list(cid)
        if which:
            set_view(which)


def open_special(cal, sp, chans):
    """A special picked in the list or on the calendar: its page (first Choose a
    channel / Remove when none of its channels is left)."""
    if len(lost(chans, sp)) < len(sp["blocks"]) or lost_special(cal, sp, chans):
        special_page(sp["id"])


def open_list(cid=None):
    """The soonest-first list.  Returns 'calendar' to switch to the month calendar."""
    while True:
        chans = C.load()
        air = [c for c in chans if c["type"] in M.AIR_TYPES]
        if not air:
            D.ok(M.TITLE, _("Add a channel first."))
            return
        only = chan(chans, cid) if cid else None
        cal = load(chans)
        ups = [u for u in specials.upcoming(cal, now())
               if not cid or any(b["channel"] == cid for b in u[1]["blocks"])]
        rows = [M._menu_row(_("[B]+ Add a special[/B]"),
                            _("A marathon or a holiday lineup on a date, back every year"))]
        for day, sp, skipped in ups:
            blocks = sp["blocks"]
            gone = lost(chans, sp)
            detail = block_text(chans, blocks[0]) if len(blocks) == 1 else _("%d channels") % len(
                set(b["channel"] for b in blocks))
            if today().year in skipped:
                detail += DOT + _("skips this year")
            if gone and len(gone) == len(blocks):       # airs nowhere until a channel is chosen
                if len(blocks) == 1:
                    detail = what_text(blocks[0])
                rows.append(M._menu_row("%s%s%s" % (sp["name"], DOT, _("channel removed")),
                                        "%s%s%s" % (date_text(day), DOT, detail)))
                continue
            if gone:
                detail += DOT + _("channel removed")
            rows.append(M._menu_row("%s%s%s" % (sp["name"], DOT, date_text(day)), detail))
        rows.append(M._menu_row(_("[B]Month calendar[/B]"), _("The same specials on a calendar, month by month")))
        head = (_("Holidays and specials - %s") % only["name"]) if only else _("Holidays and specials")
        i = M.done_select(head, rows, useDetails=True)
        if i < 0:
            return
        if i == len(rows) - 1:
            return "calendar"
        if i == 0:
            sid = add_special(cal, chans, cid)
            if sid:
                special_page(sid)
        else:
            open_special(cal, ups[i - 1][1], chans)


# ------------------------------------------------------------------ the month calendar
A_LEFT, A_RIGHT, A_UP, A_DOWN = 1, 2, 3, 4
A_PGUP, A_PGDN, A_SELECT, A_INFO = 5, 6, 7, 11
A_CHUP, A_CHDN = 184, 185
A_CONTEXT = (117, 163)
A_BACK = (9, 10, 92, 13)
FIRST_YEAR, LAST_YEAR = 1990, 2099


def on_days(cal, first, last, cid=None):
    """{date: [special]} for the days first..last: each special on its own date
    (a block that runs past midnight marks the day it starts)."""
    out = {}
    for sp in cal:
        if cid and not any(b.get("channel") == cid for b in sp["blocks"]):
            continue
        for y in range(first.year - 1, last.year + 2):      # a rule moved by days can cross New Year
            if sp.get("repeat") == "once" and sp.get("year") != y:
                continue
            d = specials.date_for(sp["when"], y)
            if d and first <= d <= last and sp not in out.setdefault(d, []):
                out[d].append(sp)
    return out


INTENSITY_WORDS = (_("A little"), _("Some"), _("Lots"))


def season_days(first, last, sc=None):
    """{date: (season id, True on a big day / False in the run-up)} for first..last:
    what the automatic holiday seasons do on each day (seasons.phase at noon, the
    real calendar, not the rig's test date)."""
    from . import seasons
    sc = sc if sc is not None else seasons_cfg()
    cfg = {"seasons": sc}
    out = {}
    d = first
    while d <= last:
        sid, level = seasons.phase(time.mktime((d.year, d.month, d.day, 12, 0, 0, 0, 0, -1)), cfg)
        if sid:
            out[d] = (sid, level >= seasons.FULL)
        d += datetime.timedelta(days=1)
    out[None] = sc
    return out


def season_text(sea, sc):
    """'Christmas run-up (Some)' / 'Thanksgiving: all day'."""
    sid, big = sea
    name = season_name(sid, sc)
    if big:
        return _("%s: all day") % name
    n = (sc.get(sid) or {}).get("intensity")
    return _("%s run-up (%s)") % (name, INTENSITY_WORDS[sc.get("intensity", 1) if n is None else n])


def rules_for(day):
    """The every-year rules a date picked on the calendar can mean, weekday rules
    first where they fit: [(rule, its words)]."""
    out = []
    n = (day.day - 1) // 7 + 1
    if n <= 4:
        out.append({"type": "nth", "n": n, "weekday": day.weekday(), "month": day.month})
    if (day + datetime.timedelta(days=7)).month != day.month:
        out.append({"type": "nth", "n": -1, "weekday": day.weekday(), "month": day.month})
    off = (day - specials.easter(day.year)).days
    if off in (-2, 0, 1):
        out.append({"type": "easter", "offset": off})
    out.append({"type": "date", "month": day.month, "day": day.day})
    return [(w, when_text(w)) for w in out]


def ask_day_rule(day):
    """Add a special on this day: the date is chosen, so only how it repeats is
    asked.  (rule, name, (repeat, year)) or None."""
    rules = rules_for(day)
    rows = []
    for w, words in rules:
        rows.append((_("On %s every year") if w["type"] != "nth" else _("On the %s every year")) % words)
    rows.append(_("This year only") if day.year == today().year else _("Only in %d") % day.year)
    j = D.select(date_text(day), rows)
    if j < 0:
        return None
    once = j == len(rules)
    when = {"type": "date", "month": day.month, "day": day.day} if once else rules[j][0]
    mine = [n for _sid, n, rule, _s in holidays() if rule == when]
    name = mine[0] if mine else next((_("Thanksgiving") if key == "thanksgiving" else PRESET[key]
                                     for key, rule in specials.PRESETS if rule == when), when_text(when))
    return when, name, (("once", day.year) if once else ("yearly", None))


class Calendar(xbmcgui.WindowXMLDialog):
    """The month on screen: 42 cells from the Monday on or before the 1st.  The
    cursor is a date; a month's specials are worked out once (on_days).

    Keys never queue up: onAction only moves the cursor's target (want) and returns;
    a drawing thread draws whatever the target is when it's ready, so presses that
    come while a month draws collapse into one step, and when the key is let go the
    screen stops on its target at once (no backlog of months still to draw)."""
    cid = None
    result = None
    closing = False
    drawer = None

    def onInit(self):
        self.chans = C.load()
        self.only = chan(self.chans, self.cid) if self.cid else None
        self.day = getattr(self, "day", None) or today()
        self.want = getattr(self, "want", None) or self.day
        self.setProperty("hint", _("OK: open / add    Menu: list    CH+ / CH-: month    Back: done"))
        for c, n in enumerate(P.day_names()):
            self.setProperty("D%d" % c, n)
        self.shown = None
        if self.drawer is None:
            self.lock = threading.RLock()
            self.wake = threading.Event()
            self.reload()
            self.drawer = threading.Thread(target=self._draw_loop, name="cablebox42-calendar")
            self.drawer.start()
        else:
            self.reload()

    def _draw_loop(self):
        while not self.closing and not xbmc.Monitor().abortRequested():
            self.wake.wait(0.5)
            self.wake.clear()
            self.settle()

    def settle(self):
        """Draw the target day if the screen isn't there yet (before OK opens it)."""
        with self.lock:
            while not self.closing and self.want != self.day:
                self.day = self.want
                self.refresh()

    def close(self):
        self.closing = True
        if self.drawer is not None:
            self.wake.set()
        xbmcgui.WindowXMLDialog.close(self)

    def reload(self):
        """calendar.json again (something may have been added or changed)."""
        with self.lock:
            self.chans = C.load()
            self.cal = load(self.chans)
            self.sc = seasons_cfg()             # read once: holding CH+ draws months without asking Kodi again
            self.shown = None
            self.day = self.want
            self.refresh()

    def first(self):
        one = self.day.replace(day=1)
        return one - datetime.timedelta(days=one.weekday())

    def refresh(self):
        first = self.first()
        t = today()
        if self.shown != (self.day.year, self.day.month):       # another month: its 42 days
            self.shown = (self.day.year, self.day.month)
            self.days = on_days(self.cal, first, first + datetime.timedelta(days=41), self.cid)
            self.seas = season_days(first, first + datetime.timedelta(days=41), self.sc)
            head = (_("Holidays and specials - %s") % self.only["name"]) if self.only else _("Holidays and specials")
            title = "%s  -  %s %d" % (head, month(self.day.month), self.day.year)
            self.setProperty("title", title)
            from . import promos            # a long channel name: the title is never cut, the hint makes room
            self.setProperty("hint", _("OK: open / add    Menu: list    CH+ / CH-: month    Back: done")
                             if promos._px(title) * 45 / 27.0 < 1000 else "")
            for i in range(42):
                d = first + datetime.timedelta(days=i)
                sps = self.days.get(d) or []
                here = d.month == self.day.month
                sea = self.seas.get(d)
                # a special on a season's day: the season's shade with a gold border (both show)
                self.setProperty("B%d" % i, ("calendar_special_big.png" if sea[1] else "calendar_special_run.png")
                                 if sps and sea else "planner_special.png" if sps else
                                 ("calendar_season_big.png" if sea[1] else "calendar_season_run.png") if sea else
                                 ("planner_auto.png" if here else "planner_auto_alt.png"))
                self.setProperty("N%d" % i, ("[B]%d[/B]" if here else "[COLOR 66FFFFFF]%d[/COLOR]") % d.day)
                self.setProperty("L%d" % i, (u"\u2605 " + (sps[0]["name"] if len(sps) == 1 else _("%d specials") % len(sps)))
                                 if sps else "")
            self.setProperty("today", str((t - first).days) if 0 <= (t - first).days < 42 else "")
        self.setProperty("cur", str((self.day - first).days))
        self.setProperty("col", str(self.day.weekday()))
        self.setProperty("detail", self.detail())

    def detail(self):
        d = self.day
        where = "%s %d %s" % (P.day_names(False)[d.weekday()], d.day, month(d.month))
        sps = self.days.get(d) or []
        sea = self.seas.get(d)
        season = season_text(sea, self.seas[None]) if sea else ""
        if sps:
            if len(sps) == 1:
                blocks = sps[0]["blocks"]
                what = block_text(self.chans, blocks[0]) if len(blocks) == 1 else _("%d channels") % len(
                    set(b["channel"] for b in blocks))
                text = u"%s:  [B]\u2605 %s[/B]  -  %s" % (where, sps[0]["name"], what)
            else:
                text = u"%s:  [B]\u2605 %s[/B]" % (where, ", ".join(sp["name"] for sp in sps))
            if sea:     # the special beats the season on its channels; the others keep it
                text += DOT + _("other channels: %s") % season
            return text
        if sea:
            return u"%s:  %s" % (where, season)
        if d < today():
            return where
        return _("%s:  no special  -  press OK to add one") % where

    @staticmethod
    def moved(d, months):
        """The same day in another month (the 31st becomes the month's last day);
        d itself outside FIRST_YEAR..LAST_YEAR."""
        m = d.year * 12 + d.month - 1 + months
        y, mo = divmod(m, 12)
        if not FIRST_YEAR <= y <= LAST_YEAR:
            return d
        day = d.day
        while True:
            try:
                return datetime.date(y, mo + 1, day)
            except ValueError:
                day -= 1

    def onAction(self, action):
        a = action.getId()
        if a in A_BACK:
            self.close()
            return
        step = {A_LEFT: -1, A_RIGHT: 1, A_UP: -7, A_DOWN: 7}.get(a)
        want = self.want
        if step:
            d = want + datetime.timedelta(days=step)
            if FIRST_YEAR <= d.year <= LAST_YEAR:
                want = d
        elif a in (A_PGUP, A_CHUP):
            want = self.moved(want, 1)
        elif a in (A_PGDN, A_CHDN):
            want = self.moved(want, -1)
        elif a == A_SELECT:
            self.settle()
            self.on_select()
            return
        elif a in A_CONTEXT or a == A_INFO:
            if D.contextmenu([_("Show as a list")]) == 0:
                self.result = "list"
                self.close()
            return
        else:
            return
        self.want = want            # the drawing thread takes it from here
        self.wake.set()

    def on_select(self):
        """That day's specials (open one) and Add a special on this day."""
        d = self.day
        sps = self.days.get(d) or []
        past = d < today()
        if past and not sps:
            D.notification(M.TITLE, _("A past day can't be changed"), time=2500)
            return
        rows = [u"\u2605 " + sp["name"] for sp in sps]
        sea = self.seas.get(d)
        if sea:
            rows.append(season_text(sea, self.seas[None]))
        if not past:
            rows.append(_("+ Add a special on this day"))
        rows.append(_("Cancel"))
        j = D.select(date_text(d), rows)
        if j < 0 or j == len(rows) - 1:
            return
        if j < len(sps):
            open_special(self.cal, sps[j], self.chans)
        elif sea and j == len(sps):
            from . import seasons_editor           # the season's own page
            seasons_editor.season_page(sea[0])
            M.refresh_if_changed()
        else:
            r = ask_day_rule(d)
            sid = add_special(self.cal, self.chans, self.cid, picked=r) if r else None
            if sid:
                special_page(sid)
        self.reload()


def open_calendar(cid=None, day=None):
    """The month calendar.  Returns 'list' to switch to the list."""
    win = Calendar("script-cablebox42-calendar.xml", K.ADDON_PATH, "Default", "1080i")
    win.cid = cid
    win.day = day
    win.doModal()
    result = win.result
    win.closing = True
    if win.drawer is not None:
        win.wake.set()
        win.drawer.join(2)
    del win
    return result


# ------------------------------------------------------------------ adding: step by step
def ask_when():
    """(rule, a name for it) or None."""
    i = D.select(_("When?"), [_("A date..."), _("A weekday of a month..."), _("Easter..."),
                              _("A holiday from my list..."), _("Dates for each year...")])
    if i < 0:
        return None
    if i == 4:
        # Diwali, Hanukkah, Lunar New Year...: typed per year, no 'move by days'
        when = ask_years()
        return (when, when_text(when)) if when else None
    months = [month(m) for m in range(1, 13)]
    name = None
    if i == 0:
        m = D.select(_("Month"), months)
        if m < 0:
            return None
        last = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)[m]
        d = D.select(months[m], [str(k) for k in range(1, last + 1)])
        if d < 0:
            return None
        when = {"type": "date", "month": m + 1, "day": d + 1}
    elif i == 1:
        n = D.select(_("Which one in the month?"), nth_names())
        if n < 0:
            return None
        wd = D.select(_("Weekday"), P.day_names(False))
        if wd < 0:
            return None
        m = D.select(_("Month"), months)
        if m < 0:
            return None
        when = {"type": "nth", "n": -1 if n == 4 else n + 1, "weekday": wd, "month": m + 1}
    elif i == 2:
        j = D.select(_("Easter"), [_("Easter Sunday"), _("Good Friday (2 days before)"),
                                   _("Easter Monday (1 day after)"), _("Days before Easter..."),
                                   _("Days after Easter...")])
        if j < 0:
            return None
        off = (0, -2, 1)[j] if j < 3 else None
        if off is None:
            v = D.numeric(0, _("How many days?"), "1")
            if not v or int(v) < 1:
                return None
            off = min(int(v), 300) * (-1 if j == 3 else 1)
        when = {"type": "easter", "offset": off}
    else:
        # the holiday seasons (built-ins and the viewer's own: one list of holidays),
        # then the ready-made dates that aren't one of them
        mine = [(n, rule) for _sid, n, rule, _s in holidays()]
        have = set(json.dumps(r, sort_keys=True) for _n, r in mine)
        ready = [(_("Thanksgiving") if k == "thanksgiving" else PRESET[k], r) for k, r in specials.PRESETS
                 if json.dumps(r, sort_keys=True) not in have]
        rows = [M._menu_row(n, when_text(r)) for n, r in mine] + \
            [M._menu_row(n, when_text(r) + DOT + _("ready-made")) for n, r in ready]
        j = D.select(_("A holiday from my list"), rows, useDetails=True)
        if j < 0:
            return None
        name, rule = (mine + ready)[j]
        when = json.loads(json.dumps(rule))
        if when.get("type") == "years":
            return when, name           # dates typed per year: nothing to move
    j = D.select(when_text(when), [_("On the day itself"), _("The day after"), _("The day before"),
                                   _("Move by days...")])
    if j < 0:
        return None
    if j in (1, 2):
        when["shift"] = 1 if j == 1 else -1
    elif j == 3:
        v = D.numeric(0, _("How many days?"), "1")
        if not v or int(v) < 1:
            return None
        n = min(int(v), 300)
        k = D.select(when_text(when), [_("%d days later") % n, _("%d days earlier") % n])
        if k < 0:
            return None
        when["shift"] = n if k == 0 else -n
    return when, (name if name and not when.get("shift") else when_text(when))


def next_year(when):
    """(year, date) of the rule's next date from today on, or (None, None)."""
    t = today()
    for y in range(t.year - 1, t.year + specials.LOOKAHEAD + 1):
        d = specials.date_for(when, y)
        if d and d >= t:
            return y, d
    return None, None


def ask_repeat(when):
    """('yearly', None) / ('once', year) or None."""
    year, day = next_year(when)
    if year is None:
        return None
    once = (_("This year only (%s)") if day.year == today().year else _("Next time only (%s)")) % date_text(day)
    j = D.select(_("How often?"), [_("Every year"), once])
    if j < 0:
        return None
    return ("yearly", None) if j == 0 else ("once", year)


def ask_hours(blk=None):
    """(start, end) as 'HH:MM', or None."""
    j = D.select(_("Which hours?"), [_("All day (midnight to midnight)"),
                                     _("Broadcast day (%s to %s next morning)") % (P.clock(360), P.clock(360)),
                                     _("Choose hours...")])
    if j < 0:
        return None
    if j == 0:
        return "00:00", "00:00"
    if j == 1:
        return "06:00", "06:00"
    a = M.ask_time(_("Starts at"), (blk or {}).get("start", "18:00"))
    if not a:
        return None
    b = M.ask_time(_("Ends at (earlier than the start: the next morning)"), (blk or {}).get("end", "06:00"))
    if not b:
        return None
    return P.hhmm(P.mins(a)), P.hhmm(P.mins(b))


def ask_source(sp):
    """One source for a block, or None: the holiday episodes of the channel's own
    shows for the holiday on this date (any holiday in the list, with its own tags,
    genres and words), those of another holiday, or programming chosen as usual."""
    sc = seasons_cfg()
    own = holiday_of_rule(sp["when"], sc)
    others = [(sid, n) for sid, n, _r, stuff in holidays(sc) if stuff and sid not in own]
    rows = [_("%s episodes of this channel's shows") % season_name(sid, sc) for sid in own]
    if others:
        rows.append(_("Holiday episodes of another holiday..."))
    rows.append(_("Choose programming..."))
    if len(rows) > 1:
        j = D.select(_("What to air?"), rows)
        if j < 0:
            return None
        if j < len(own):
            return {"type": "holiday", "season": own[j]}
        if others and j == len(own):
            k = D.select(_("Holiday episodes of"), [n for _sid, n in others])
            if k < 0:
                return None
            return {"type": "holiday", "season": others[k][0]}
    return M.pick_source()


def single_movie(blk_or_src):
    """One movie picked by name: nothing to put in order (no order question, no order text)."""
    srcs = blk_or_src.get("sources") if "sources" in blk_or_src else [blk_or_src]
    return len(srcs or ()) == 1 and isinstance(srcs[0], dict) and srcs[0].get("type") == "movie" and \
        len(srcs[0].get("value") or ()) == 1


def ask_order(current=None, once=False):
    """The order of a block's programmes.  once: a This year only special has no
    'last year' to continue from: From the first episode / Random only."""
    orders = [o for o in ORDERS if not (once and o[0] == "continue")]
    keys = [o[0] for o in orders]
    j = D.select(_("Episode order"), [o[1] for o in orders], preselect=keys.index(current) if current in keys else 0)
    return keys[j] if j >= 0 else None


def ask_block(chans, sp, cid=None):
    """A new block for the special: channel, hours, what to air, order.  None on Back."""
    air = [c for c in chans if c["type"] in M.AIR_TYPES]
    ch = chan(air, cid) if cid else None
    if ch is None:
        ch = ask_channel(chans)
        if not ch:
            return None
    hours = ask_hours()
    if not hours:
        return None
    src = ask_source(sp)
    if not src:
        return None
    order = "first" if single_movie(src) else ask_order(once=sp.get("repeat") == "once")
    if not order:
        return None
    return {"channel": ch["id"], "start": hours[0], "end": hours[1], "sources": [src], "order": order}


def length_text(secs, about=False):
    """'2 hours', '1½ hours', '45 minutes' (to the half hour from an hour up)."""
    if secs < 3600 - 900:
        n = max(1, int(round(secs / 60.0)))
        txt = _("1 minute") if n == 1 else _("%d minutes") % n
    else:
        halves = int(round(secs / 1800.0))
        h, half = divmod(halves, 2)
        if half:
            txt = _("%s½ hours") % h if h else _("½ hour")
        else:
            txt = _("1 hour") if h == 1 else _("%d hours") % h
    return (_("about %s") % txt) if about else txt


def checks(cal, sp, blk, chans, kept=None, clashes=None):
    """The questions before a block is saved.  False: cancelled.  'Replace' takes the
    blocks it replaces out of `cal` (and out of `sp`) here.  `kept`: a set shared by
    the checks of several blocks, so Keep both is asked once for a pair of channels.
    clashes: a list to collect pinned-show clashes in instead of asking (checks_all
    asks once for all the blocks of a save)."""
    ch = chan(chans, blk["channel"])
    if not ch:
        return True                 # channel removed: it airs nowhere, nothing to ask
    lineup = scheduler.Lineup(K.schedule_cfg())
    sched = lineup.schedule(ch, ensure=False)
    day, _skipped = specials.next_date(dict(sp, blocks=[blk]), now())
    season = sched._holiday_source(blk)
    if season is not None:
        pool = sched._special_pool(blk)
        items = [e for ser in pool["series"] for e in ser["episodes"]] + pool["singles"]
        if not items:
            D.ok(_("Holidays and specials"), _("%s has no %s episodes.[CR]It will air its normal programming "
                                                "on the day.") % (ch["name"], season_name(season)))
        elif day:
            # none of them twice in the day: when they run out, the channel's normal programming
            st, en = specials.window(blk, day)
            have = sum(float(e.get("dur") or 0) for e in items)
            if have < en - st:
                name, what = ch["name"], season_name(season)
                if len(items) == 1:
                    text = _("%s has 1 %s episode (%s) for %s.") % (
                        name, what, length_text(have, about=True), length_text(en - st))
                else:
                    text = _("%s has %d %s episodes (%s) for %s.") % (
                        name, len(items), what, length_text(have, about=True), length_text(en - st))
                if not M.confirm(text + "[CR]" + _("The rest of the day will be its normal programming."), _("OK")):
                    return False
    if not day:
        return True
    st, en = specials.window(blk, day)
    others = [o for o in cal if o["id"] != sp["id"]]
    same = specials.between(others, st, en, blk["channel"])
    own = [b for b in sp["blocks"] if b is not blk and b["channel"] == blk["channel"]
           and specials.window(b, day)[0] < en and specials.window(b, day)[1] > st]
    if same or own:
        names = []
        for name in [w[2]["name"] for w in same] + ([sp["name"]] if own else []):
            if name not in names:
                names.append(name)
        if not M.confirm_remove(_("%s already has %s in those hours.[CR]Replace it?") % (ch["name"], ", ".join(names)),
                                _("Replace")):
            return False
        for _a, _b, o, ob in same:
            if ob in o["blocks"]:
                o["blocks"].remove(ob)
        for b in own:
            sp["blocks"].remove(b)
        cal[:] = [o for o in cal if o["blocks"] or o["id"] == sp["id"]]
        others = [o for o in cal if o["id"] != sp["id"]]
    titles = dict((t.lower(), t) for t in sched._special_titles(blk))
    if titles:
        rest = dict(sp, blocks=[b for b in sp["blocks"] if b is not blk])     # its own other channels too
        for _a, _b, o, ob in specials.between(others + [rest], st, en):
            och = chan(chans, ob["channel"])
            if not och or och["id"] == ch["id"]:
                continue
            both = [titles[t.lower()] for t in lineup.schedule(och, ensure=False)._special_titles(ob)
                    if t.lower() in titles]
            pair = frozenset((ch["id"], och["id"]))
            if both and (kept is None or pair not in kept):
                if not M.confirm(_("%s is also in %s on %s at the same time.") % (both[0], o["name"], och["name"]),
                                 _("Keep both")):
                    return False
                if kept is not None:
                    kept.add(pair)
                break
        found = pinned_elsewhere(titles, ch, chans, st, en, kept)
        if clashes is not None:
            clashes.extend(found)
        elif not ask_pinned(found):
            return False
    return True


def checks_all(cal, sp, blocks, chans):
    """checks() for several blocks saved at once: one pinned-show question for all."""
    kept, clashes = set(), []
    for b in blocks:
        if b in sp["blocks"] and not checks(cal, sp, b, chans, kept, clashes):
            return False
    return ask_pinned(clashes)


def pinned_elsewhere(titles, ch, chans, st, en, kept=None):
    """A special's shows that are pinned on another channel during its hours (they
    air there too: pins win on their own channel): [(text, key)], one per pinned
    airing, 'Friends on Keystone, Thu 8:00 PM', in time order."""
    from . import library
    off = scheduler.specials_shift(K.schedule_cfg())
    out = []
    for c in chans:
        if c["id"] == ch["id"] or c["type"] not in M.AIR_TYPES:
            continue
        for r in c.get("slots") or []:
            occ = scheduler.rule_occurrences(r, st - off, en - off)
            if not occ:
                continue
            try:
                both = [titles[t.lower()] for t in library.titles(library.resolve(r["sources"])) if t.lower() in titles]
            except Exception as exc:
                K.log("Holidays and specials, pinned shows: %s" % exc)
                continue
            key = ("pin", c["id"], r.get("id"), r.get("start"))
            if not both or (kept is not None and key in kept):
                continue
            if kept is not None:
                kept.add(key)
            a = occ[0][0] + off
            lt = time.localtime(a)
            at = "%s %s" % (P.day_names()[lt.tm_wday], P.clock(lt.tm_hour * 60 + lt.tm_min))
            out.append((a, _("%s on %s, %s") % (both[0], c["name"], at)))
    out.sort(key=lambda x: x[0])
    seen, texts = set(), []
    for _a, txt in out:
        if txt not in seen:
            seen.add(txt)
            texts.append(txt)
    return texts


def ask_pinned(texts):
    """One question for every pinned-show clash of a save: Cancel / Keep all.
    True: keep them (or there were none)."""
    if not texts:
        return True
    lead = (_("This show is pinned on another channel during this special:") if len(texts) == 1 else
            _("These shows are pinned on other channels during this special:"))
    return M.confirm("%s %s" % (lead, "; ".join(texts)), _("Keep all"))


def add_special(cal, chans, cid=None, picked=None):
    """The steps of a new special; its id when it was added, None when cancelled.
    picked: (rule, name, (repeat, year)) from the calendar - When? and How often?
    are answered already."""
    if picked:
        when, name, rep = picked
    else:
        r = ask_when()
        if not r:
            return None
        when, name = r
        rep = ask_repeat(when)
        if not rep:
            return None
    name = (D.input(_("Name"), name) or "").strip()
    if not name:
        return None
    sp = {"id": specials.new_id(), "name": name, "when": when, "repeat": rep[0], "blocks": []}
    if rep[0] == "once":
        sp["year"] = rep[1]
    blk = ask_block(chans, sp, cid)
    if not blk or not checks(cal, sp, blk, chans):
        return None
    sp["blocks"].append(blk)
    day, _skipped = specials.next_date(sp, now())
    text = "%s%s%s[CR]%s[CR]%s" % (date_text(day) if day else when_text(when), DOT, repeat_text(sp),
                                   block_text(chans, blk), order_text(blk, row=False))
    if not M.confirm(text, _("Add special"), heading=name):
        return None
    cal.append(sp)
    save(cal, [blk["channel"]], sp)
    D.notification(M.TITLE, _("%s added") % name, time=2500)
    return sp["id"]


# ------------------------------------------------------------------ a special's page
def special_page(sid):
    """One special: its name, date, channels; changes save as you go."""
    while True:
        chans = C.load()
        cal = load(chans)
        sp = specials.find(cal, sid)
        if not sp:
            return
        day, skipped = specials.next_date(sp, now())
        rows = [("name", _("Name: %s") % sp["name"], ""),
                ("when", _("When: %s") % when_text(sp["when"]),
                 (_("Next: %s") % date_text(day)) + ((DOT + _("skips this year")) if today().year in skipped else "")
                 if day else ""),
                ("repeat", _("Repeats: %s") % repeat_text(sp), "")]
        for k, b in enumerate(sp["blocks"]):
            rows.append(("block:%d" % k, block_text(chans, b), order_text(b)))
        rows += [("add", _("[B]+ Add another channel[/B]"), _("More programming for this special, on any channel")),
                 ("preview", _("[B]Preview the day[/B]"), _("What will air, channel by channel")),
                 ("remove", _("[COLOR red]Remove this special[/COLOR]"), "")]
        head = "%s%s%s" % (sp["name"], DOT, date_text(day)) if day else sp["name"]
        i = M.done_select(head, [M._menu_row(r[1], r[2]) for r in rows], useDetails=True)
        if i < 0:
            return
        key = rows[i][0]
        mine = [b["channel"] for b in sp["blocks"]]
        if key == "name":
            v = (D.input(_("Name"), sp["name"]) or "").strip()
            if v and v != sp["name"]:
                sp["name"] = v
                save(cal, mine)
        elif key == "when":
            r = ask_when()
            if r and r[0] != sp["when"]:
                sp["when"] = r[0]
                if sp.get("repeat") == "once":
                    sp["year"] = next_year(r[0])[0] or sp["year"]
                if checks_all(cal, sp, list(sp["blocks"]), chans):
                    save(cal, mine, sp)
        elif key == "repeat":
            rep = ask_repeat(sp["when"])
            if rep:
                sp["repeat"] = rep[0]
                sp.pop("year", None)
                if rep[0] == "once":
                    sp["year"] = rep[1]
                    for b in sp["blocks"]:           # no last year to continue from
                        if b.get("order") == "continue":
                            b["order"] = "first"
                save(cal, mine)
        elif key.startswith("block:"):
            blk = sp["blocks"][int(key[6:])]
            if chan(chans, blk.get("channel")):
                edit_block(cal, sp, blk, chans)
            else:
                lost_block(cal, sp, blk, chans)
        elif key == "add":
            blk = ask_block(chans, sp)
            if blk and checks(cal, sp, blk, chans):
                sp["blocks"].append(blk)
                save(cal, mine + [blk["channel"]], sp)
                D.notification(M.TITLE, _("%s added") % block_text(chans, blk), time=2500)
        elif key == "preview":
            preview(sp, chans)
        elif key == "remove":
            if M.confirm_remove(_("Remove %s?[CR]Its channels air their normal programming on the day.") % sp["name"]):
                cal.remove(sp)
                save(cal, mine)
                return


def edit_block(cal, sp, blk, chans):
    """One channel's programming in a special: hours, what airs, order, remove."""
    acts = [("hours", _("Change the hours (%s)") % hours_text(blk)),
            ("what", _("Change what airs (%s)") % source_text(blk))]
    if not single_movie(blk):                    # one movie: nothing to put in order
        acts.append(("order", _("Change the order (%s)") % order_text(blk)))
    acts += [("remove", _("Remove this channel from the special")), ("cancel", _("Cancel"))]
    i = D.select(block_text(chans, blk), [a[1] for a in acts])
    act = acts[i][0] if i >= 0 else "cancel"
    if act == "cancel":
        return
    new = dict(blk)
    if act == "hours":
        hours = ask_hours(blk)
        if not hours:
            return
        new["start"], new["end"] = hours
    elif act == "what":
        src = ask_source(sp)
        if not src:
            return
        new["sources"] = [src]
        if single_movie(src):
            new["order"] = "first"
        elif single_movie(blk):                  # was one movie: now there's an order to choose
            order = ask_order(once=sp.get("repeat") == "once")
            if not order:
                return
            new["order"] = order
    elif act == "order":
        order = ask_order(blk.get("order"), once=sp.get("repeat") == "once")
        if not order:
            return
        new["order"] = order
    elif act == "remove":
        remove_block(cal, sp, blk, chans)
        return
    if new == blk:
        return
    k = sp["blocks"].index(blk)
    sp["blocks"][k] = new
    if checks(cal, sp, new, chans):
        save(cal, [new["channel"]], sp)


def remove_block(cal, sp, blk, chans):
    """Cancel / Remove for one channel's programming; the special goes with its last."""
    last = len(sp["blocks"]) == 1
    what = block_text(chans, blk) if chan(chans, blk.get("channel")) else what_text(blk)
    text = (_("Remove %s?[CR]It is the special's only channel: %s is removed too.") % (what, sp["name"])
            if last else _("Remove %s from %s?") % (what, sp["name"]))
    if not M.confirm_remove(text):
        return False
    sp["blocks"].remove(blk)
    if last:
        cal.remove(sp)
    save(cal, [blk["channel"]])
    return True


# ------------------------------------------------------------------ channel removed
def ask_channel(chans, heading=None):
    air = [c for c in chans if c["type"] in M.AIR_TYPES]
    j = D.select(heading or _("Which channel?"), ["%3d  %s" % (c["number"], c["name"]) for c in air])
    return air[j] if j >= 0 else None


def lost_block(cal, sp, blk, chans):
    """A block whose channel is gone, on the special's page: Choose a channel / Remove."""
    i = D.select(block_text(chans, blk), [_("Choose a channel"), _("Remove"), _("Cancel")])
    if i == 1:
        remove_block(cal, sp, blk, chans)
    if i != 0:
        return
    ch = ask_channel(chans)
    if not ch:
        return
    new = dict(blk, channel=ch["id"])
    sp["blocks"][sp["blocks"].index(blk)] = new
    if checks(cal, sp, new, chans):
        save(cal, [ch["id"]], sp)


def lost_special(cal, sp, chans):
    """A special none of whose channels is left, in the list: Choose a channel / Remove.
    True when it has a channel again (its page opens next)."""
    i = D.select("%s%s%s" % (sp["name"], DOT, _("channel removed")),
                 [_("Choose a channel"), _("Remove"), _("Cancel")])
    if i == 1:
        if M.confirm_remove(_("Remove %s?[CR]Its channels air their normal programming on the day.") % sp["name"]):
            cal.remove(sp)
            save(cal)
    if i != 0:
        return False
    several = len(sp["blocks"]) > 1
    picked = []
    for blk in list(sp["blocks"]):                  # Back on any of them: nothing is changed
        ch = ask_channel(chans, _("Which channel for %s?") % what_text(blk) if several else None)
        if not ch:
            return False
        picked.append((blk, dict(blk, channel=ch["id"])))
    for blk, new in picked:
        sp["blocks"][sp["blocks"].index(blk)] = new
    if not checks_all(cal, sp, [new for _blk, new in picked], chans):
        return False
    save(cal, [b["channel"] for b in sp["blocks"]], sp)
    return True


# ------------------------------------------------------------------ preview the day
def preview(sp, chans):
    """What will air on the special's next date, channel by channel (read-only)."""
    from .tv import fmt_time
    cfg = K.schedule_cfg()
    off = scheduler.specials_shift(cfg)
    day, _skipped = specials.next_date(sp, now())
    if not day:
        D.ok(_("Holidays and specials"), _("%s has no date coming up.") % sp["name"])
        return
    lineup = scheduler.Lineup(cfg)
    lines = []
    for blk in sp["blocks"]:
        ch = chan(chans, blk["channel"])
        if not ch:
            lines += ["[B]%s[/B]" % block_text(chans, blk),
                      "[COLOR grey]%s[/COLOR]" % _("It doesn't air until a channel is chosen."), ""]
            continue
        sched = lineup.schedule(ch, ensure=False)
        st, en = specials.window(blk, day)
        st, en = st - off, en - off
        lines.append("[B]%s[/B]   %s%s%s" % (chan_name(ch), hours_text(blk), DOT, order_text(blk)))
        planned = [b for b in sched.blocks_between(st, en) if b.get("sp")]
        if planned:
            for b in planned:
                extra = " ".join(x for x in (b.get("lb", ""), b.get("sub", "")) if x)
                lines.append(_("[B]%8s[/B]   %s   [COLOR grey]%s[/COLOR]") % (fmt_time(b["s"]), b["t"], extra))
            if sched.data["until"] < en - 60:
                lines.append("[COLOR grey]%s[/COLOR]" % _("The rest of the day isn't planned yet."))
        else:
            lines += _simulate(sched, sp, blk, st, en, fmt_time)
        lines.append("")
    D.textviewer("%s%s%s" % (sp["name"], DOT, date_text(day)), "[CR]".join(lines))


def _simulate(sched, sp, blk, st, en, fmt_time):
    """The day as the scheduler would plan it now, without planning it: in-order
    blocks from their bookmarks; a random block just says what it picks from."""
    pool = sched._special_pool(blk)
    series, singles = pool["series"], pool["singles"]
    if not series and not singles:
        return ["[COLOR grey]%s[/COLOR]" % _("Nothing to air: the channel's normal programming.")]
    if blk.get("order") == "random":
        names = [s["title"] for s in series] + ([_("%d movies") % len(singles)] if singles else [])
        return [_("Random picks from: %s") % (", ".join(names[:6]) + (" ..." if len(names) > 6 else ""))]
    rid = "event:%s" % sp["id"]
    state = sched.data.get("state", {})
    cont = blk.get("order") == "continue"
    last = state.get("last", {}) if cont else {}
    turn = (state.get("rr", {}).get(rid, 0) if cont else 0)
    shows = [(ser["key"], ser["episodes"]) for ser in series] + ([("movies", singles)] if singles else [])
    at = {}
    slot = sched.slot
    out, t = [], st
    while t < en - 60 and len(out) < 100:
        for k in range(len(shows)):
            key, eps = shows[(turn + k) % len(shows)]
            if key in at:
                idx = (at[key] + 1) % len(eps)
            else:
                prev = last.get("%s|%s" % (rid, key))
                idx = next(((j + 1) % len(eps) for j, e in enumerate(eps) if e["path"] == prev), 0)
            ep = eps[idx]
            dur = float(ep["dur"])
            if dur > en - t - 2:
                continue
            at[key] = idx
            turn += k + 1
            extra = " ".join(x for x in (ep.get("label") or "", ep.get("sub") or "") if x)
            out.append(_("[B]%8s[/B]   %s   [COLOR grey]%s[/COLOR]") % (fmt_time(t), ep["title"], extra))
            t = min(en, scheduler.ceil_slot(t + dur + 2, slot)) if slot else t + dur
            break
        else:
            break
    return out
