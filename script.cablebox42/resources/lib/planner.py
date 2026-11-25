"""Weekly planner: a 7-day x half-hour grid per channel.

Pin shows to fixed times ("Seinfeld, Fridays 8:00 PM, in order"), paint
off-air hours, copy or clear days.  Anything not pinned is filled by the
automatic scheduler, which never runs into a pinned slot.

Pins and off-air hours are the same in every week.  Holidays and specials are looked
up for the week on screen (a star in the day's header, their hours as a block;
load_marks).  The pins underneath are not changed and the planner's own overlap check
ignores them.  Right past Sunday is the next week, Left past Monday the week before;
it always opens on this week, and a past week is read-only.
"""
import datetime
import json
import time
import uuid

import xbmc
import xbmcgui

from . import kodiutil as K
from . import channels as C
from . import library
from . import manager as M
from .kodiutil import _

ROWS = 14
DAYS = 7
STEP = 30          # minutes per row
WEEK = 7 * 1440
PIN_COLORS = 6
WEEKS = 520        # how far Left / Right go from this week

A_LEFT, A_RIGHT, A_UP, A_DOWN = 1, 2, 3, 4
A_PGUP, A_PGDN, A_SELECT, A_INFO = 5, 6, 7, 11
A_CHUP, A_CHDN = 184, 185
A_CONTEXT = (117, 163)
A_BACK = (9, 10, 92, 13)


def day_names(short=True):
    if short:
        return [_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun")]
    return [_("Monday"), _("Tuesday"), _("Wednesday"), _("Thursday"), _("Friday"), _("Saturday"), _("Sunday")]


def norm_days(days):
    if days in (None, "all"):
        return list(range(7))
    if days == "weekdays":
        return [0, 1, 2, 3, 4]
    if days == "weekends":
        return [5, 6]
    if isinstance(days, list):
        return sorted(set(int(d) for d in days))
    return list(range(7))


def compact_days(days):
    """Store the friendliest form of a day list."""
    days = sorted(set(days))
    if days == list(range(7)):
        return "all"
    if days == [0, 1, 2, 3, 4]:
        return "weekdays"
    if days == [5, 6]:
        return "weekends"
    return days


def days_text(days):
    days = norm_days(days)
    if days == list(range(7)):
        return _("every day")
    if days == [0, 1, 2, 3, 4]:
        return _("weekdays")
    if days == [5, 6]:
        return _("weekends")
    long_ = day_names(False)
    if len(days) == 1:
        return _("%ss") % long_[days[0]]
    return ", ".join(day_names()[d] for d in days)


def mins(hhmm):
    try:
        h, m = str(hhmm).split(":")[:2]
        return (int(h) % 24) * 60 + int(m) % 60
    except ValueError:
        return 0


def hhmm(m):
    m %= 1440
    return "%02d:%02d" % (m // 60, m % 60)


def clock(m):
    m %= 1440
    try:
        fmt = xbmc.getRegion("time").replace(":%S", "")
    except Exception:
        fmt = "%I:%M %p"
    s = time.strftime(fmt, time.struct_time((2000, 1, 1, m // 60, m % 60, 0, 5, 1, -1)))
    return s[1:] if s.startswith("0") else s


def length_text(n):
    if n % 60 == 0:
        return _("%d hr") % (n // 60) if n > 60 else _("1 hr")
    if n > 60:
        return _("%d hr %d min") % (n // 60, n % 60)
    return _("%d min") % n


def covers(start_w, length, w):
    return (w - start_w) % WEEK < length


def rule_spans(r):
    L = max(1, int(r.get("minutes", 30)))
    return [(d * 1440 + mins(r.get("start")), L) for d in norm_days(r.get("days"))]


def window_spans(w):
    a, b = mins(w.get("start")), mins(w.get("end"))
    L = (b - a) % 1440 or 1440
    return [(d * 1440 + a, L) for d in norm_days(w.get("days"))]


def spans_overlap(a, b):
    (s1, l1), (s2, l2) = a, b
    return (s2 - s1) % WEEK < l1 or (s1 - s2) % WEEK < l2


def typical_minutes(sources, slot):
    """Length a show naturally needs: median running time rounded up to the channel slot."""
    pool = library.resolve(sources)
    durs = sorted([e["dur"] for s in pool["series"] for e in s["episodes"][:20]] +
                  [i["dur"] for i in pool["singles"][:40]])
    if not durs:
        return slot or 30
    med = durs[len(durs) // 2] / 60.0
    step = slot or 30
    return int(-(-(med + 0.5) // step) * step)


def source_label(src):
    v = src.get("value")
    if isinstance(v, list) and len(v) == 1:
        return v[0]
    if isinstance(v, list) and v:
        return "%s +%d" % (v[0], len(v) - 1)
    if isinstance(v, str) and v:
        return v
    return M.describe_source(src)


class Planner(xbmcgui.WindowXMLDialog):
    cid = None

    def onInit(self):
        chans = C.load()
        self.ch = next((c for c in chans if c["id"] == self.cid), None)
        if not self.ch:
            self.close()
            return
        from . import scheduler
        self.shift = scheduler.specials_shift(K.schedule_cfg())    # 0, but for the rig's test date
        lt = time.localtime()
        self.week = 0                                   # weeks from this one
        self.col = self.today().weekday()
        self.row = (lt.tm_hour * 60 + lt.tm_min) // STEP
        self.top = max(0, min(self.row - 3, 1440 // STEP - ROWS))
        for c, n in enumerate(day_names()):
            self.setProperty("D%d" % c, n)
        self.show_week()
        self.refresh()

    # ---------------------------------------------------------------- weeks
    def today(self):
        return datetime.date.fromtimestamp(time.time() + self.shift)

    def monday(self):
        """The Monday of the week on screen."""
        t = self.today()
        return t - datetime.timedelta(days=t.weekday()) + datetime.timedelta(weeks=self.week)

    def show_week(self):
        """The title, hint and specials of the week on screen (nothing else changes
        from week to week)."""
        if self.week == 0:
            week = _("This week")
        else:
            mon = self.monday()
            try:
                month = xbmc.getLocalizedString(50 + mon.month)      # Kodi's 'Jan' ... 'Dec'
            except Exception:
                month = ""
            day = "%d %s" % (mon.day, month or mon.strftime("%b"))
            week = _("Week of %s") % (day if mon.year == self.today().year else "%s %d" % (day, mon.year))
        self.setProperty("title", "%s  -  %s" % (
            _("Weekly planner  -  %d  %s") % (self.ch["number"], self.ch["name"]), week))
        self.setProperty("hint", _("OK: pin / edit    Menu: copy / clear day    Back: done") if self.week >= 0
                         else _("A past week: view only    Back: done"))
        self.load_marks()

    def step_week(self, by):
        week = max(-WEEKS, min(WEEKS, self.week + by))
        if week == self.week:
            return False
        self.week = week
        self.show_week()
        return True

    def past(self):
        """A past week is for looking at: OK and Menu only say so."""
        if self.week >= 0:
            return False
        M.D.notification(K.ADDON_NAME, _("A past week can't be changed"), time=2500)
        return True

    # ---------------------------------------------------------------- model
    def save(self):
        chans = C.load()
        before = json.dumps(chans, sort_keys=True)
        for i, c in enumerate(chans):
            if c["id"] == self.ch["id"]:
                chans[i] = self.ch
        if json.dumps(chans, sort_keys=True) != before:
            self.saved = True                # open_planner tells the caller to check for a refresh
        C.save(chans)

    def load_marks(self):
        """The specials on the channel in the week on screen (most weeks: none):
        marks = [(first minute of the week, end, special, block, date)], cut to the
        week, so a block that began on Sunday night shows on Monday morning too;
        stars = {day column: name, or '2 specials'} for the header, on the special's
        own date only.  calendar.json is read once (specials.load keeps it)."""
        from . import specials
        self.marks, stars = [], {}
        try:
            cal = specials.load()
            if cal:
                mon = self.monday()
                t0 = time.mktime(mon.timetuple())
                t1 = time.mktime((mon + datetime.timedelta(days=7)).timetuple())
                for st, en, sp, blk in specials.between(cal, t0, t1, self.ch["id"]):
                    a, b = [(d.date() - mon).days * 1440 + d.hour * 60 + d.minute
                            for d in (datetime.datetime.fromtimestamp(st), datetime.datetime.fromtimestamp(en))]
                    day = mon + datetime.timedelta(days=a // 1440)      # the special's date
                    if 0 <= a < WEEK:
                        names = stars.setdefault(a // 1440, [])
                        if sp["name"] not in names:
                            names.append(sp["name"])
                    a, b = max(0, a), min(WEEK, b)
                    if a < b:
                        self.marks.append((a, b, sp, blk, day))
        except Exception as exc:                    # the planner opens without its marks
            K.log("Weekly planner, specials: %s" % exc)
        self.stars = dict((c, n[0] if len(n) == 1 else _("%d specials") % len(n)) for c, n in stars.items())

    def mark_at(self, day, minute):
        w = day * 1440 + minute
        for mk in self.marks:
            if mk[0] - mk[0] % STEP <= w < mk[1]:
                return mk
        return None

    def cell(self, day, minute, marks=True):
        """(kind, index, text, first) for one grid cell."""
        w = day * 1440 + minute
        mk = self.mark_at(day, minute) if marks and self.marks else None
        if mk:
            first = w - mk[0] < STEP or minute == 0
            return "sp", self.marks.index(mk), mk[2]["name"] if first else "", first
        for i, r in enumerate(self.ch.get("slots", [])):
            for st, L in rule_spans(r):
                if covers(st, L, w):
                    first = (w - st) % WEEK < STEP
                    return "pin", i, (r.get("label") or "?") if first else "", first
        for i, win in enumerate(self.ch.get("offair", [])):
            for st, L in window_spans(win):
                if covers(st, L, w):
                    first = (w - st) % WEEK < STEP or minute == 0
                    return "off", i, _("OFF AIR") if first else "", first
        for i, dp in enumerate(self.ch.get("dayparts", [])):
            for st, L in window_spans(dp):
                if covers(st, L, w):
                    first = (w - st) % WEEK < STEP or minute == 0
                    return "dp", i, ("[I]%s[/I]" % dp.get("label", _("Block"))) if first else "", first
        return "auto", None, "", False

    # ---------------------------------------------------------------- view
    def refresh(self):
        for r in range(ROWS):
            m = (self.top + r) * STEP
            self.setProperty("T%d" % r, clock(m))
            for c in range(DAYS):
                kind, idx, text, _first = self.cell(c, m)
                if kind == "pin":
                    tex = "planner_pin%d.png" % (idx % PIN_COLORS)
                elif kind == "sp":
                    tex = "planner_special.png"
                    if r == 0:                      # a long block: its name at the top of the screen too
                        text = self.marks[idx][2]["name"]
                elif kind == "off":
                    tex = "planner_offair.png"
                elif kind == "dp":
                    tex = "planner_daypart.png"
                else:
                    tex = "planner_auto.png" if (m // 60) % 2 == 0 else "planner_auto_alt.png"
                self.setProperty("B%d_%d" % (r, c), tex)
                self.setProperty("L%d_%d" % (r, c), text)
        for c in range(DAYS):                       # "Thu \u2605" over the special's name
            name = self.stars.get(c)
            color = "FFFFD24A" if c == self.col else "FFB8C4E0"
            self.setProperty("S%d" % c, (u"[COLOR %s][B]%s  \u2605[/B][/COLOR]" % (color, day_names()[c])) if name else "")
            self.setProperty("N%d" % c, ("[COLOR %s]%s[/COLOR]" % (color, name)) if name else "")
        self.setProperty("col", str(self.col))
        self.setProperty("cur", "%d_%d" % (self.row - self.top, self.col))
        self.setProperty("detail", self.detail())

    def detail(self):
        m = self.row * STEP
        day = day_names(False)[self.col]
        kind, idx, _t, _f = self.cell(self.col, m)
        where = "%s %s" % (day, clock(m))
        if kind == "sp":
            from . import specials_editor as E
            _a, _b, sp, blk, date = self.marks[idx]
            under = self.cell(self.col, m, marks=False)
            return u"%s:  [B]\u2605 %s[/B]  -  %s, %s: %s" % (
                where, sp["name"], E.date_text(date), E.hours_text(blk), E.source_text(blk)) + (
                    _("  (instead of %s)") % self.ch["slots"][under[1]].get("label", "?") if under[0] == "pin" else "")
        if kind == "pin":
            r = self.ch["slots"][idx]
            order = _("in order") if r.get("order", "inorder") == "inorder" else _("random episodes")
            return _("%s:  [B]%s[/B]  -  %s at %s, %s, %s") % (
                where, r.get("label", ""), days_text(r.get("days")), clock(mins(r["start"])),
                length_text(int(r.get("minutes", 30))), order) + (_("  (automatic prime time)") if r.get("auto") else "")
        if kind == "off":
            w = self.ch["offair"][idx]
            return _("%s:  [B]Off the air[/B] %s - %s, %s") % (
                where, clock(mins(w["start"])), clock(mins(w["end"])), days_text(w.get("days")))
        if kind == "dp":
            dp = self.ch["dayparts"][idx]
            return _("%s:  time block '%s' - picked automatically from its own programming") % (
                where, dp.get("label", ""))
        if self.week < 0:
            return _("%s:  automatic programming") % where
        return _("%s:  automatic programming  -  press OK to pin a show here") % where

    # ---------------------------------------------------------------- input
    def onAction(self, action):
        a = action.getId()
        total = 1440 // STEP
        if a in A_BACK:
            self.close()
            return
        if a == A_LEFT:                 # past Monday: the week before
            if self.col > 0:
                self.col -= 1
            elif self.step_week(-1):
                self.col = DAYS - 1
        elif a == A_RIGHT:              # past Sunday: the next week
            if self.col < DAYS - 1:
                self.col += 1
            elif self.step_week(1):
                self.col = 0
        elif a == A_UP:
            self.row = (self.row - 1) % total
        elif a == A_DOWN:
            self.row = (self.row + 1) % total
        elif a in (A_PGUP, A_CHUP):
            self.row = max(0, self.row - ROWS)
        elif a in (A_PGDN, A_CHDN):
            self.row = min(total - 1, self.row + ROWS)
        elif a == A_SELECT:
            self.on_select()
        elif a in A_CONTEXT or a == A_INFO:
            self.on_menu()
        else:
            return
        if self.row < self.top:
            self.top = self.row
        elif self.row >= self.top + ROWS:
            self.top = self.row - ROWS + 1
        self.refresh()

    # ---------------------------------------------------------------- actions
    def on_select(self):
        if self.past():
            return
        m = self.row * STEP
        kind, idx, _t, _f = self.cell(self.col, m)
        if kind == "sp":
            sp = self.marks[idx][2]
            if M.D.select(sp["name"], [_("Edit this special"), _("Cancel")]) == 0:
                from . import specials_editor
                specials_editor.special_page(sp["id"])
                self.load_marks()
            return
        if kind == "pin":
            self.edit_rule(idx)
            return
        opts = [_("Pin a show here"), _("Make off-air from here")]
        if kind == "off":
            opts = [_("Pin a show here"), _("Change these off-air hours"), _("Remove these off-air hours")]
        j = M.D.select("%s %s" % (day_names(False)[self.col], clock(m)), opts)
        if j == 0:
            self.add_rule(m)
        elif j == 1 and kind == "off":
            self.edit_offair(idx)
        elif j == 1:
            self.add_offair(m)
        elif j == 2:
            w = self.ch["offair"][idx]
            if M.confirm_remove(_("Remove the off-air hours %s - %s?") % (clock(mins(w["start"])), clock(mins(w["end"])))):
                del self.ch["offair"][idx]
                self.save()

    def ask_length(self, sources, current=None):
        natural = typical_minutes(sources, int(self.ch.get("slot", 30)) or 30)
        choices = [natural, 30, 60, 90, 120, 180]
        labels = [_("Match the show (%s)") % length_text(natural)] + [length_text(n) for n in choices[1:]] + \
            [_("Other...")]
        j = M.D.select(_("How long is this slot?"), labels,
                       preselect=choices.index(current) if current in choices else 0)
        if j < 0:
            return None
        if j < len(choices):
            return choices[j]
        v = M.D.numeric(0, _("Length in minutes"), str(current or natural))
        return max(5, int(v)) if v else None

    def ask_days(self, default_day, current=None):
        long_ = day_names(False)
        opts = [_("%ss only") % long_[default_day], _("Weekdays"), _("Every day"), _("Weekends"), _("Pick days...")]
        j = M.D.select(_("Which days?"), opts)
        if j < 0:
            return None
        if j == 0:
            return [default_day]
        if j == 4:
            pre = norm_days(current) if current is not None else [default_day]
            sel = M.D.multiselect(_("Which days?"), long_, preselect=pre)
            return compact_days(sel) if sel else None
        return ["weekdays", "all", "weekends"][j - 1]

    def ask_order(self):
        j = M.D.select(_("Episode order"), [_("In order - continues where it left off each week"),
                                           _("Random episodes")])
        return None if j < 0 else ("inorder", "random")[j]

    def resolve_conflicts(self, rule, skip=None):
        """Remove the overlapping days from other pinned shows (after asking)."""
        mine = rule_spans(rule)
        clashes = []
        for i, r in enumerate(self.ch["slots"]):
            if i == skip:
                continue
            bad = [d for d, sp in zip(norm_days(r.get("days")), rule_spans(r))
                   if any(spans_overlap(sp, x) for x in mine)]
            if bad:
                clashes.append((i, bad))
        if not clashes:
            return True
        names = ", ".join(self.ch["slots"][i].get("label", "?") for i, _b in clashes)
        if not M.confirm_remove(_("This overlaps %s.[CR]Replace it on the overlapping days?") % names, _("Replace")):
            return False
        for i, bad in clashes:
            r = self.ch["slots"][i]
            left = [d for d in norm_days(r.get("days")) if d not in bad]
            r["days"] = compact_days(left) if left else []
        self.ch["slots"] = [r for r in self.ch["slots"] if norm_days(r.get("days")) and r.get("days") != []]
        return True

    def add_rule(self, m):
        src = M.pick_source()
        if not src:
            return
        length = self.ask_length([src])
        if not length:
            return
        days = self.ask_days(self.col)
        if days is None:
            return
        order = self.ask_order()
        if not order:
            return
        rule = {"id": uuid.uuid4().hex[:6], "label": source_label(src), "start": hhmm(m), "minutes": length,
                "days": days, "order": order, "sources": [src]}
        if not self.resolve_conflicts(rule):
            return
        self.ch.setdefault("slots", []).append(rule)
        self.save()
        M.D.notification(_("Pinned: %s") % rule["label"], _("%s at %s") % (days_text(days), clock(m)),
                         time=3000)

    def edit_rule(self, idx):
        r = self.ch["slots"][idx]
        order = r.get("order", "inorder")
        opts = [_("Change the show"), _("Change start time"), _("Change length (%s)") % length_text(int(r.get("minutes", 30))),
                _("Change days (%s)") % days_text(r.get("days")),
                _("Order: %s") % (_("in order") if order == "inorder" else _("random")),
                _("Start the series over from the first episode"), _("Rename"), _("Remove")]
        j = M.D.select(r.get("label", ""), opts)
        new = json.loads(json.dumps(r))
        if j == 0:
            src = M.pick_source()
            if not src:
                return
            new["sources"] = [src]
            new["label"] = source_label(src)
        elif j == 1:
            t = M.ask_time(_("Starts at"), r["start"])
            if not t:
                return
            new["start"] = hhmm(mins(t))
        elif j == 2:
            n = self.ask_length(r["sources"], int(r.get("minutes", 30)))
            if not n:
                return
            new["minutes"] = n
        elif j == 3:
            d = self.ask_days(self.col, r.get("days"))
            if d is None:
                return
            new["days"] = d
        elif j == 4:
            new["order"] = "random" if order == "inorder" else "inorder"
        elif j == 5:
            self.restart_series(r)
            M.D.notification(K.ADDON_NAME, _("%s starts from episode 1 next time") % r.get("label", ""), time=3000)
            return
        elif j == 6:
            v = M.D.input(_("Name"), r.get("label", ""))
            if not v:
                return
            new["label"] = v
        elif j == 7:
            days = norm_days(r.get("days"))
            start_day = self.start_day(r)
            if len(days) > 1:
                k = M.D.select(_("Remove %s") % r.get("label", ""),
                               [_("Only on %ss") % day_names(False)[start_day], _("Every day it airs (%s)") % days_text(days),
                                _("Cancel")])
                if k not in (0, 1):
                    return
                if k == 0:
                    left = [d for d in days if d != start_day]
                    r["days"] = compact_days(left)
                    self.save()
                    return
            elif not M.confirm_remove(_("Remove %s?") % r.get("label", "")):
                return
            del self.ch["slots"][idx]
            self.save()
            return
        else:
            return
        if j in (1, 2, 3) and not self.resolve_conflicts(new, skip=idx):
            return
        new.pop("auto", None)        # edited by hand: Quick setup will leave it alone from now on
        r.clear()
        r.update(new)
        self.save()

    def start_day(self, rule):
        """Day the airing under the cursor started (it may have begun the night before)."""
        w = self.col * 1440 + self.row * STEP
        for (st, L), d in zip(rule_spans(rule), norm_days(rule.get("days"))):
            if covers(st, L, w):
                return d
        return self.col

    def restart_series(self, rule):
        """This pinned slot's series from the first episode again, from the end of
        what's on air (the slot keeps its own bookmark; other airings of the show
        are not affected)."""
        from . import scheduler
        lineup = scheduler.Lineup(K.schedule_cfg())
        ch = next((c for c in lineup.channels if c["id"] == self.ch["id"]), None)
        if ch is None:
            return
        s = lineup.schedule(ch, ensure=False)
        with lineup.lock:
            s.cut()                          # first: the cut puts back what the plan moved
            rid = "rule:%s" % rule.get("id", "")
            st = s.data["state"]
            st["last"] = dict((k, v) for k, v in st.get("last", {}).items() if not k.startswith(rid))
            st.get("rr", {}).pop(rid, None)
            s.save()                         # planned again from here when next needed

    def add_offair(self, m):
        end = M.ask_time(_("Back on the air at"), "07:00")
        if not end:
            return
        days = self.ask_days(self.col)
        if days is None:
            return
        self.ch.setdefault("offair", []).append({"start": hhmm(m), "end": hhmm(mins(end)), "days": days})
        self.save()
        M.D.notification(K.ADDON_NAME, _("Off the air %s - %s, %s") % (clock(m), clock(mins(end)), days_text(days)),
                         time=3000)

    def edit_offair(self, idx):
        w = self.ch["offair"][idx]
        a = M.ask_time(_("Sign off at"), w["start"])
        b = M.ask_time(_("Sign on at"), w["end"])
        if a and b:
            w["start"], w["end"] = hhmm(mins(a)), hhmm(mins(b))
            self.save()

    def on_menu(self):
        if self.past():
            return
        day = day_names(False)[self.col]
        opts = [_("Copy %s's pinned shows to other days") % day, _("Clear %s's pinned shows") % day,
                _("Off-air screen and sign-off clips..."), _("Preview what airs next")]
        j = M.D.contextmenu(opts)
        if j == 0:
            others = [d for d in range(7) if d != self.col]
            sel = M.D.multiselect(_("Copy to"), [day_names(False)[d] for d in others])
            if sel:
                targets = [others[i] for i in sel]
                for r in [x for x in self.ch["slots"] if self.col in norm_days(x.get("days"))]:
                    copy = json.loads(json.dumps(r))
                    copy["id"] = uuid.uuid4().hex[:6]
                    copy["days"] = targets
                    if self.resolve_conflicts(copy):
                        self.ch["slots"].append(copy)
                self.save()
        elif j == 1:
            if M.confirm_remove(_("Clear every pinned show on %ss?") % day, _("Clear")):
                for r in self.ch["slots"]:
                    left = [d for d in norm_days(r.get("days")) if d != self.col]
                    r["days"] = compact_days(left) if left else []
                self.ch["slots"] = [r for r in self.ch["slots"] if r.get("days") != []]
                self.save()
        elif j == 2:
            M.edit_offair(self.ch)
            self.save()
        elif j == 3:
            self.save()
            M.preview(self.ch)


def open_planner(cid):
    """The weekly planner for one channel.  True if it saved a change (like the
    channel editor's _edit_group): only then does the caller check for a refresh."""
    win = Planner("script-cablebox42-planner.xml", K.ADDON_PATH, "Default", "1080i")
    win.cid = cid
    win.saved = False
    win.doModal()
    saved = win.saved
    del win
    return saved
