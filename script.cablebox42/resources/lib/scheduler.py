"""Real-time, self-building schedules.

There is no separate "build the station" step.  Each channel keeps a rolling
schedule file that is extended on demand (when you tune in, when the guide
needs it, or by the background service).  Programme picks are seeded from the
channel id and the wall-clock slot, so a 'strip' channel airs the same show at
the same time every weekday, while series always advance episode by episode.

Where a show is in its series is its bookmark (bookmarks.py): shared by the show's
home channel wherever that is, kept per channel elsewhere.  Every bookmark a plan
moves is written to the schedule's undo log with the start of the block that moved
it, so the plan can be cut after any block and the bookmarks put back (cut()).
"""
import bisect
import datetime
import hashlib
import json
import math
import os
import random
import re
import threading
import time

import xbmc

from .kodiutil import SCHEDULE_DIR, PROFILE, load_json, save_json, log, ensure_dirs, setting_bool
from . import library
from . import channels as chmod
from . import assign
from . import seasons
from . import stations
from . import promos
from . import musicvideos
from . import music
from . import bookmarks
from . import ads
from . import chapters
from . import specials
from .kodiutil import _

DAY = 86400
SHORTS_PACK, SHORTS_PINNED_ONLY, SHORTS_ONE_PER_SLOT = 0, 1, 2
# Settings > Programming > Skip episodes shorter than: Off / 2 / 5 / 10 min
SKIP_SHORT_MIN = (0, 2, 5, 10)
SKIPPED_FILE = os.path.join(PROFILE, "skipped.json")
_SKIPPED = {}            # path -> [series, label, seconds]: skipped since the last refresh
_SKIP_LOGGED = set()     # files the log has named since the last refresh
_SKIP_LOCK = threading.Lock()


def skip_short_secs(cfg):
    """The 'Skip episodes shorter than' limit in seconds (0: off)."""
    i = int(cfg.get("skip_short", 2) or 0)
    return SKIP_SHORT_MIN[i] * 60 if 0 <= i < len(SKIP_SHORT_MIN) else 0


def skip_short_begin():
    """A refresh starts: the log names each skipped file once again."""
    with _SKIP_LOCK:
        _SKIP_LOGGED.clear()
        _SKIPPED.clear()


def skip_short_save():
    """What this refresh skipped, for Settings > Tools > Check skipped episodes."""
    with _SKIP_LOCK:
        data = {"t": time.time(), "episodes": [[p] + v for p, v in sorted(_SKIPPED.items())]}
    try:
        save_json(SKIPPED_FILE, data)
    except Exception as exc:
        log("skipped episodes: %s" % exc)
PROMO_RATES = (1.0, 0.5, 0.25)      # every break, about half, now and then
PROMO_LOOKAHEAD = 6 * 3600          # 'later today' looks this far ahead
SPECIAL_PROMO_DAYS = 6              # a special is promoted from this many days before ('Thursday')
SPECIAL_PROMO_RATES = (0.5, 0.4, 0.25)   # of the promo slots: on the day, the day before, earlier
SPECIAL_CROSS_SHARE = 0.5   # a plain promo slot with no special of its own: that share of the rate for another channel's
PROMO_TYPES = assign.PROGRAM_TYPES + ("musicvideos",)    # channels whose breaks carry promos
# House breaks (Settings > Programming > House breaks): the channel's own promos,
# promos for other channels and ads for the guide / weather channels, in place of
# commercials.  HOUSE_NO_ADS: only where no commercials are available.
HOUSE_NO_ADS, HOUSE_MIX, HOUSE_OFF = 0, 1, 2
HOUSE_MAX = 60.0         # a house break lasts at most this long
HOUSE_FINAL_MIN = 20.0   # less time left at a programme's end: the 'Up next' card as before
HOUSE_ITEM = 15.0        # a house ad card, at most (stretched down to HOUSE_ITEM_MIN)
HOUSE_ITEM_MIN = 8.0
HOUSE_ID = 5.0           # the station ID card that rounds a house break off
HOUSE_KINDS = ("guide", "weather", "lineup")
UPNEXT_MAX = 90.0        # at a programme's end the 'Up next' card runs at most about this long
UPNEXT_MIN = 10.0
GAP_SPLIT = 240.0        # a programme's end gap longer than this is a series of normal breaks...
GAP_BREAK = 150.0        # ...of about this long (2-3 min), each ending on a station ID card ("sep")
# Variety in a gap (the run of back-to-back breaks between two programmes): the same
# promo target (show, own channel or another) at most once in GAP_PROMO_SPACING s and
# GAP_PROMO_MAX times in all; each system ad once.  A long gap's breaks plan at most
# GAP_PROMOS promos each; one with nothing fresh to name becomes a retro ad, a system
# ad, or the station ID card (_gap_filler).  Before off-air the channel's next
# programme ("tomorrow at 5:00") at most OFFAIR_PROMOS times: early on, and last.
GAP_PROMO_SPACING = 600.0
GAP_PROMO_MAX = 3
GAP_PROMOS = 3
OFFAIR_PROMOS = 2
SIGNOFF_CARD_SECS = 25.0    # the built-in "This concludes our broadcast day" card
BREAK_KINDS = ("retro", "promo", "house", "card", "bump", "ad")


_PLANNING_CODE = []


def planning_code():
    """A short fingerprint of the code that plans breaks (as manager.code_fingerprint,
    without the version): every block keeps the one that planned it ("cf"), so a
    schedule kept across an update shows which of its breaks an earlier build made
    (a refresh keeps what's on air; retro_check.py sets those aside)."""
    if not _PLANNING_CODE:
        import hashlib
        h = hashlib.md5()
        here = os.path.dirname(os.path.abspath(__file__))
        for name in ("scheduler.py", "promos.py", "ads.py", "chapters.py", os.path.join("..", "ads", "ads.json")):
            try:
                with open(os.path.join(here, name), "rb") as f:
                    h.update(f.read())
            except OSError:
                pass
        _PLANNING_CODE.append(h.hexdigest()[:8])
    return _PLANNING_CODE[0]


def _house_key(it):
    """What makes two house ads the same ad (this channel's promos name different shows)."""
    if it.get("k") == "retro":
        return ("retro", ads.key(it))
    return (it.get("k"), it.get("h"), it.get("xc")) if it.get("k") == "house" or it.get("xc") else None


def _episode_order(label):
    """'S01E04' -> a key in the library's episode order (specials, season 0, last)."""
    m = re.match(r"S(\d+)E(\d+)", label or "")
    if not m:
        return None
    season, episode = int(m.group(1)), int(m.group(2))
    return (season == 0, season, episode)


# ----------------------------------------------------------------- summer reruns
RERUN_OFF, RERUN_NETWORKS, RERUN_ALL = 0, 1, 2
RERUN_MONTHS = (6, 7, 8)        # 1 June - 31 August, local time
RERUN_SUFFIX = ":rerun"
RERUN_MIN = 3                   # aired episodes a season needs before it reruns


def rerun_season(ts, cfg):
    """Summer reruns at ts?  cfg 'reruns' is the setting; 'rerun_today' (a hidden test
    setting, YYYY-MM-DD) stands in for the date in the rig."""
    if not cfg or not cfg.get("reruns"):
        return False
    fake = cfg.get("rerun_today") or ""
    if fake:
        try:
            return int(fake.split("-")[1]) in RERUN_MONTHS
        except (IndexError, ValueError):
            pass
    return time.localtime(ts).tm_mon in RERUN_MONTHS


def rerun_channel(ch, cfg):
    """Does this channel rerun in the summer?  'Broadcast networks': the broadcast
    networks (Keystone, Beacon, Horizon and channels set up as one); 'All channels':
    every show channel.  Movie, loop, Boombox, extras, guide and weather: never."""
    mode = (cfg or {}).get("reruns", RERUN_OFF)
    if ch.get("type") != "network":
        return False
    if mode == RERUN_ALL:
        return True
    return mode == RERUN_NETWORKS and bool(ch.get("broadcast"))


def _season_of(ep):
    k = _episode_order(ep.get("label"))
    return k[:2] if k else None


def rerun_range(eps, last_i):
    """Indexes of the episodes a summer rerun picks from: the season the series is
    in (where its next new episode is), from its first episode up to the last one
    that aired (last_i); the season before when fewer than RERUN_MIN of this season
    have aired (an episode 1 next: none).  Series without season numbers: from the
    start.  Empty (the series airs new episodes) when there isn't enough to rerun:
    one episode again and again all summer would be no rerun season."""
    if last_i is None or last_i < 0:
        return []
    nxt = last_i + 1
    want = _season_of(eps[nxt]) if nxt < len(eps) else _season_of(eps[last_i])
    rng = [j for j in range(last_i + 1) if _season_of(eps[j]) == want]
    if len(rng) < RERUN_MIN:
        before = (rng[0] if rng else nxt) - 1
        if before >= 0:
            prev = _season_of(eps[before])
            rng = [j for j in range(before + 1) if _season_of(eps[j]) == prev]
    return rng if len(rng) >= RERUN_MIN else []


# ----------------------------------------------------------------- holidays and specials
_SPECIALS = [0.0, []]           # [looked at, specials]: calendar.json is checked every 2 s at most


def all_specials():
    """Every special in calendar.json ([] without the file: nothing changes)."""
    now = time.time()
    if abs(now - _SPECIALS[0]) > 2:
        try:
            _SPECIALS[1] = specials.load()
        except Exception as exc:         # a broken calendar never costs a channel its schedule
            log("Holidays and specials: %s" % exc)
            _SPECIALS[1] = []
        _SPECIALS[0] = now
    return _SPECIALS[1]


def forget_specials():
    """calendar.json was just written here: read it again at once."""
    _SPECIALS[0] = 0.0


def specials_shift(cfg):
    """Seconds from the real clock to the one specials go by: 0, or with the hidden
    test setting 'specials_today' (YYYY-MM-DD) today counts as that date, for the rig."""
    fake = (cfg or {}).get("specials_today") or ""
    if not fake:
        return 0
    try:
        y, m, d = [int(x) for x in fake.split("-")]
        return time.mktime((y, m, d, 0, 0, 0, 0, 0, -1)) - local_midnight(time.time())
    except (ValueError, OverflowError):
        return 0


# ----------------------------------------------------------------- time utils
def local_tod(ts):
    lt = time.localtime(ts)
    return lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec + (ts - int(ts)), lt.tm_wday


def floor_slot(ts, slot):
    tod, _wday = local_tod(ts)
    return ts - (tod % slot)


def ceil_slot(ts, slot):
    f = floor_slot(ts, slot)
    return f if abs(f - ts) < 0.001 else f + slot


def hm(s):
    """'HH:MM' -> seconds after midnight."""
    try:
        h, m = str(s).split(":")[:2]
        return (int(h) % 24) * 3600 + int(m) * 60
    except ValueError:
        return 0


def _day_ok(days, wday):
    if not days or days == "all":
        return True
    if days == "weekdays":
        return wday < 5
    if days == "weekends":
        return wday >= 5
    if isinstance(days, list):
        return wday in days
    return True


def in_window(ts, win):
    tod, wday = local_tod(ts)
    a, b = hm(win.get("start", "00:00")), hm(win.get("end", "00:00"))
    if a == b:
        inside = True
    elif a < b:
        inside = a <= tod < b
    else:
        inside = tod >= a or tod < b
        if tod < b:  # we are in the after-midnight tail: judge by yesterday
            wday = (wday - 1) % 7
    return inside and _day_ok(win.get("days"), wday)


def window_end(ts, win):
    tod, _wday = local_tod(ts)
    b = hm(win.get("end", "00:00"))
    delta = (b - tod) % DAY
    if delta < 1:
        delta = DAY
    return ts + delta


def local_midnight(ts):
    tod, _wday = local_tod(ts)
    return ts - tod


def rule_occurrences(rule, t0, t1):
    """(start, end) of every airing of a weekly slot rule overlapping [t0, t1)."""
    days = rule.get("days")
    if days in (None, "all"):
        days = list(range(7))
    elif days == "weekdays":
        days = [0, 1, 2, 3, 4]
    elif days == "weekends":
        days = [5, 6]
    length = max(1, int(rule.get("minutes", 30))) * 60
    out = []
    m = local_midnight(t0) - DAY
    while m < t1 + DAY:
        wday = time.localtime(m + 43200).tm_wday
        if wday in days:
            st = local_midnight(m + 43200) + hm(rule.get("start", "00:00"))
            if st < t1 and st + length > t0:
                out.append((st, st + length))
        m = local_midnight(m + DAY + 43200)
    return out


# ----------------------------------------------------------------- schedule
class ChannelSchedule(object):
    def __init__(self, ch, cfg):
        self.ch = ch
        self.cfg = cfg
        self.path = os.path.join(SCHEDULE_DIR, "%s.json" % ch["id"])
        self.mtime = 0
        self.lineup = None
        self.data = None
        self._starts = []
        self._bstarts = []
        self.reload()

    # -- persistence
    def reload(self):
        try:
            mt = os.path.getmtime(self.path)
        except OSError:
            mt = 0
        if self.data is not None and mt == self.mtime:
            return
        self.mtime = mt
        d = load_json(self.path, {})
        d.setdefault("hash", "")
        d.setdefault("entries", [])
        d.setdefault("blocks", [])
        d.setdefault("until", 0)
        d.setdefault("state", {})
        d["state"].setdefault("last", {})
        d["state"].setdefault("recent", {})
        self.data = d
        self._index()

    def save(self):
        ensure_dirs()
        bookmarks.flush()                # the shared bookmarks this plan moved
        save_json(self.path, self.data)
        try:
            self.mtime = os.path.getmtime(self.path)
        except OSError:
            pass

    def _index(self):
        self._starts = [e["s"] for e in self.data["entries"]]
        self._bstarts = [b["s"] for b in self.data["blocks"]]

    @property
    def slot(self):
        return int(self.ch.get("slot", 30)) * 60

    # -- series bookmarks (bookmarks.py) and the undo log
    def _shared(self, key):
        """Does this channel move the show's shared bookmark?  Never a summer rerun's
        own bookmark ('<key>:rerun'): it belongs to the channel.  A TV show: only on its
        home channel.  A show with no home (taken off every channel, but aired as a
        fill-in) keeps its shared bookmark untouched for when it comes back.  Pinned
        slots ('rule:...') and other channels airing the show keep their own run
        here.  Folder series (no home channels) share theirs."""
        if key.startswith(("rule:", "event:")) or key.endswith(RERUN_SUFFIX):
            return False                 # 'event:': a special's marathon keeps its own run too
        if not key.startswith("tv:"):
            return True
        home = ((self.assignment() or {}).get("home") or {}).get(key[3:].lower())
        return home == self.ch["id"]

    def _bm_get(self, key):
        if self._shared(key):
            known, last = bookmarks.get(key)
            if known:
                return last
        return self.data["state"]["last"].get(key)

    def _bm_set(self, key, path, label=None):
        """Move a bookmark while planning (undone by cut()).  label ('S01E04'):
        where the episode is in the series, should its file leave the library.
        A summer rerun (_next_episode just picked it as one) moves the series'
        rerun bookmark instead: the main one stays where the season stopped."""
        rr = getattr(self, "_rerun_pick", None)
        self._rerun_pick = None
        if rr == (key, path):
            key += RERUN_SUFFIX
            self._rr_path = path         # the block gets "(R)"
        else:
            self._rr_path = None
        bookmarks.remember(path, label)
        shared = self._shared(key)
        self._undo("s" if shared else "l", key, self._bm_get(key))
        if shared:
            bookmarks.put(key, path)
        else:
            self.data["state"]["last"][key] = path

    def _undo(self, kind, key, prev):
        """Note how to put a change back: [block start, kind, key, value before]."""
        t = getattr(self, "_plan_t", None)
        if t is not None:
            self.data.setdefault("undo", []).append([t, kind, key, prev])

    def _cut_point(self, now):
        """End of what's on air now: the start of the first planned block after now."""
        d = self.data
        later = [m for m in d.get("marks", []) if m > now]
        if later:
            return min(later)
        b = self.block_at(now)
        return b["e"] if b is not None else now

    def cut(self, now=None):
        """Forget the plan after the programme on air now (and its breaks), and put
        every bookmark it moved back, so the next plan airs the same episodes next.
        Returns True if anything was cut."""
        d = self.data
        now = now or time.time()
        c = self._cut_point(now)
        if c >= d["until"]:
            return False
        st = d["state"]
        if "undo" in d:
            for u in reversed(d["undo"]):
                if u[0] < c:
                    break
                self._restore(u)
            d["undo"] = [u for u in d["undo"] if u[0] < c]
        else:
            self._legacy_rollback(c)         # planned before the update: no undo log
        for p in [p for p, when in st.get("srecent", {}).items() if when >= c]:
            del st["srecent"][p]             # holiday specials that won't air after all
        ents = [e for e in d["entries"] if e["s"] < c]
        # Promos still to air in the breaks kept (the programme on air) may name
        # what was planned after the cut: they're named again from the new plan
        # (_resolve_promos), so a promo never names a show that won't air then.
        for i, e in enumerate(ents):
            if e["s"] <= now or (e.get("pt") or 0) < c:
                continue
            if e.get("k") == "promo":
                for k in ("pt", "t", "pp", "pw", "sub", "sp", "pe"):
                    e.pop(k, None)
                if e.pop("xs", None):        # a plain slot that named another channel's special
                    e.pop("xc", None)
            elif e.get("pr") == "extras":    # a show's own promo clip: back to its card
                ents[i] = {"s": e["s"], "e": e["e"], "k": "promo"}
        d["entries"] = ents
        d["blocks"] = [b for b in d["blocks"] if b["s"] < c]
        d["marks"] = [m for m in d.get("marks", []) if m < c]
        d["until"] = c
        self._index()
        return True

    def _restore(self, u):
        """Put one undo-log change back."""
        _t, kind, key, prev = u
        st = self.data["state"]
        if kind == "s":
            bookmarks.put(key, prev)
        elif kind == "l":
            if prev is None:
                st["last"].pop(key, None)
            else:
                st["last"][key] = prev
        elif kind == "rr":
            st.setdefault("rr", {})[key] = prev
        elif kind == "ra":
            rec = st["recent"].get(key)
            if rec and rec[-1] == prev:
                rec.pop()
        elif kind == "st":
            if prev is None:
                st.pop(key, None)
            else:
                st[key] = prev

    def unair(self, ts):
        """The programme on at ts didn't air (its file was missing): the bookmarks
        its block moved go back, so it isn't counted as aired.  Call after cut()
        (the plan after it is gone).  If the file is on the unplayable list, the
        next plan goes past it anyway; if its whole folder was offline, it's next."""
        b = self.block_at(ts)
        if b is None:
            return False
        undo = self.data.get("undo", [])
        mine = [u for u in undo if abs(u[0] - b["s"]) < 0.01 and u[1] in ("s", "l")]
        for u in reversed(mine):
            self._restore(u)
        self.data["undo"] = [u for u in undo if u not in mine]
        return bool(mine)

    def _legacy_rollback(self, c):
        """cut() for a schedule planned before bookmarks had an undo log: each series
        goes back to the episode before the first one cut, found in the library's
        episode order.  Bookmarks here are this channel's own (state 'last')."""
        st = self.data["state"]
        srcs = [{"type": "alltv"}] + list(self.ch.get("sources", []))
        for dp in self.ch.get("dayparts", []) or []:
            srcs += dp.get("sources", []) or []
        for rule in self._rules():
            srcs += rule.get("sources", []) or []
        where = {}                           # episode path -> (series key, its episodes)
        for src in srcs:
            try:
                pool = library.resolve([src])
            except Exception:
                continue
            for ser in pool["series"]:
                for e in ser["episodes"]:
                    where.setdefault(e["path"], (ser["key"], ser["episodes"]))
        done = set()
        for e in self.data["entries"]:
            if e["s"] < c or e.get("k") != "show" or not e.get("p") or e["p"] not in where:
                continue
            skey, eps = where[e["p"]]
            rule = self._rule_at(e["s"])[0]
            key = "rule:%s|%s" % (rule.get("id", ""), skey) if rule and rule.get("order") != "random" else skey
            if key in done:
                continue
            done.add(key)
            i = next((j for j, x in enumerate(eps) if x["path"] == e["p"]), 0)
            st["last"][key] = eps[i - 1]["path"] if i > 0 else None    # None: from the first episode
            if i > 0:
                bookmarks.remember(eps[i - 1]["path"], eps[i - 1].get("label"))

    # -- public api
    def assignment(self):
        return self.lineup.assignment if self.lineup is not None else None

    def full_hash(self):
        """Channel settings + which shows this channel may air automatically, + its
        specials (calendar.json), when it has any."""
        return self._plain_hash() + self._specials_hash()

    def _plain_hash(self):
        if self.ch.get("type") == "extras":
            # rebuild once when the first extras turn up (not each time the cache changes)
            return chmod.config_hash(self.ch) + ("x1" if self._extras_films() else "x0")
        if self.ch.get("type") == "musicvideos":
            # rebuild once when the first music videos have been measured
            return chmod.config_hash(self.ch) + ("m1" if library.mv_measured() else "m0")
        a = self.assignment() or {}
        if not a:
            return chmod.config_hash(self.ch)
        # ...and the shows whose home it is: when one moves away, this channel is cut
        # too, so the shared bookmark its plan moved goes back before the new home plans
        homes = sorted(t for t, cid in (a.get("home") or {}).items() if cid == self.ch["id"])
        return chmod.config_hash(self.ch) + a.get("digest", {}).get(self.ch["id"], "") + \
            hashlib.md5("\n".join(homes).encode("utf-8")).hexdigest()[:6]

    def needs_work(self, now=None):
        """Cheap check: is the schedule stale or running short?"""
        now = now or time.time()
        self.reload()
        d = self.data
        return (d["hash"] != self.full_hash() or not d["entries"] or
                d["until"] < now + self.cfg.get("low_water", 3 * 3600))

    def ensure(self, now=None, horizon=None, low_water=None):
        """Make sure the schedule covers now .. now+horizon.  Returns True if changed."""
        now = now or time.time()
        horizon = horizon or self.cfg.get("horizon", 12 * 3600)
        low_water = low_water or self.cfg.get("low_water", 3 * 3600)
        self.reload()
        d = self.data
        h = self.full_hash()
        changed = False
        if not d["entries"] or d["until"] < now:
            # nothing planned, or nothing left (Kodi was off): start at this half hour
            start = floor_slot(now, self.slot or 1800) - (1800 if self.slot else 0)
            d.update(hash=h, entries=[], blocks=[], until=start, undo=[], marks=[])
            changed = True
        elif d["hash"] != h:
            # the channel changed (its settings, or the shows it may air): what's on
            # air stays, the rest is planned again from the same episodes
            self.cut(now)
            d["hash"] = h
            changed = True
        if d["until"] < now + low_water or changed:
            target = now + horizon
            guard = 0
            marks = d.setdefault("marks", [])
            kind = self.ch.get("type")
            try:
                while d["until"] < target and guard < 5000:
                    self._plan_t = d["until"]        # bookmarks moved now are undone with this block
                    marks.append(d["until"])
                    if kind in ("extras", "musicvideos", "music"):   # their rotation, as it was before this block
                        name = {"extras": "x", "musicvideos": "mv", "music": "mu"}[kind]
                        self._undo("st", name, json.loads(json.dumps(d["state"].get(name))))
                    d["until"] = self._block(d["until"])
                    guard += 1
            finally:
                self._plan_t = None
            changed = True
        if changed:
            cut = now - 3600
            d["entries"] = [e for e in d["entries"] if e["e"] > cut]
            d["blocks"] = [b for b in d["blocks"] if b["e"] > cut]
            d["marks"] = [m for m in d.get("marks", []) if m > cut]
            d["undo"] = [u for u in d.get("undo", []) if u[0] > cut]
            self._index()
            try:
                self._resolve_promos(now)
            except Exception as exc:     # a promo never costs the channel its schedule
                log("promos %s: %s" % (self.ch.get("name"), exc))
            self.save()
        return changed

    def entry_at(self, ts):
        i = bisect.bisect_right(self._starts, ts) - 1
        if i >= 0:
            e = self.data["entries"][i]
            if e["s"] <= ts < e["e"]:
                return e
        return None

    def block_at(self, ts):
        i = bisect.bisect_right(self._bstarts, ts) - 1
        if i >= 0:
            b = self.data["blocks"][i]
            if b["s"] <= ts < b["e"]:
                return b
        return None

    def blocks_between(self, t0, t1):
        i = max(0, bisect.bisect_right(self._bstarts, t0) - 1)
        out = []
        for b in self.data["blocks"][i:]:
            if b["s"] >= t1:
                break
            if b["e"] > t0:
                out.append(b)
        return out

    def next_block(self, ts):
        i = bisect.bisect_right(self._bstarts, ts)
        if i < len(self.data["blocks"]):
            return self.data["blocks"][i]
        return None

    # -- generation
    def _daypart(self, t):
        for w in self.ch.get("offair", []):
            if in_window(t, w):
                return "offair", None, True, window_end(t, w)
        for i, dp in enumerate(self.ch.get("dayparts", [])):
            if in_window(t, dp):
                return "dp%d" % i, dp.get("sources", []), False, window_end(t, dp)
        return "base", self.ch.get("sources", []), False, None

    def _daypart_extra(self, key):
        """(part, fallback sources) of a broadcast network's time block."""
        if key and key.startswith("dp"):
            dp = self.ch.get("dayparts", [])[int(key[2:])]
            return dp.get("part"), dp.get("fallback"), dp.get("own"), dp.get("not_genres")
        return self.ch.get("part"), None, self.ch.get("own"), self.ch.get("not_genres")

    def _add(self, s, e, kind, **kw):
        if e - s <= 0.05:
            return
        ent = {"s": round(s, 3), "e": round(e, 3), "k": kind}
        ent.update({k: v for k, v in kw.items() if v not in (None, "")})
        self.data["entries"].append(ent)

    def _add_block(self, s, e, title, kind="show", sub="", label=""):
        b = {"s": round(s, 3), "e": round(e, 3), "t": title, "k": kind, "cf": planning_code()}
        if sub:
            b["sub"] = sub
        if label:
            b["lb"] = label
        self.data["blocks"].append(b)

    def _rules(self):
        return [r for r in self.ch.get("slots", []) if r.get("sources")]

    def _suspended(self, rule, st):
        """Automatic prime-time pins step aside on a holiday's big days."""
        return bool(rule.get("auto")) and seasons.phase(st, self.cfg)[1] >= seasons.FULL

    def _rule_at(self, t):
        """A pinned weekly slot airing at t (with at least a minute left)."""
        for r in self._rules():
            for st, en in rule_occurrences(r, t, t + 1):
                if st <= t < en - 60 and not self._suspended(r, st):
                    return r, st, en
        return None, None, None

    def _next_fixed(self, t, horizon=8 * DAY):
        """Start of the next pinned slot strictly after t (or None)."""
        best = None
        for r in self._rules():
            for st, _en in rule_occurrences(r, t + 1, t + horizon):
                if st > t + 0.5 and (best is None or st < best) and not self._suspended(r, st):
                    best = st
        return best

    def _busy(self, t, span=4 * 3600):
        """{title_lower: [(start, end)]} airing on *other* channels in [t, t+span):
        their scheduled programmes plus their pinned slots."""
        lu = self.lineup
        out = {}
        if lu is None:
            return out
        for c in lu.channels:
            if c["id"] == self.ch["id"] or c.get("type") not in assign.PROGRAM_TYPES:
                continue
            other = lu.sched.get(c["id"]) or lu.schedule(c, ensure=False)
            for b in other.blocks_between(t, t + span):
                if b.get("k") == "show":
                    out.setdefault(b["t"].lower(), []).append((b["s"], b["e"]))
            for r in c.get("slots", []):
                if r.get("order") == "random":
                    continue        # its actual pick shows up in that channel's schedule above
                occ = rule_occurrences(r, t, t + span)
                if occ and r.get("sources"):
                    for title in library.titles(library.resolve(r["sources"])):
                        out.setdefault(title.lower(), []).extend(occ)
        # ...and other channels' specials: their shows are theirs for those hours
        every = all_specials()
        if every:
            off = specials_shift(self.cfg)
            ids = set(c["id"] for c in lu.channels)
            for st, en, _sp, blk in specials.between(every, t + off, t + span + off):
                if blk.get("channel") == self.ch["id"] or blk.get("channel") not in ids:
                    continue
                for title in self._special_titles(blk):
                    out.setdefault(title.lower(), []).append((st - off, en - off))
        return out

    # -- holidays and specials (specials.py, calendar.json)
    def _specials(self):
        """The specials with programming on this channel (none, for most)."""
        cid = self.ch["id"]
        return [sp for sp in all_specials() if any(b.get("channel") == cid for b in sp["blocks"])]

    def _specials_hash(self):
        """Part of the channel's hash: a changed special cuts the plan after what is on
        air, like a changed pin.  Empty without specials (the hash is as it was)."""
        mine = self._specials()
        if not mine:
            return ""
        cid = self.ch["id"]
        data = [[sp["id"], sp.get("name"), sp["when"], sp["repeat"], sp.get("year"),
                 [b for b in sp["blocks"] if b.get("channel") == cid]] for sp in mine]
        return "s" + hashlib.md5(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()[:6]

    def _special_at(self, t):
        """(special, block, start, end) on this channel at t, with at least a minute
        left; Nones when there is none."""
        mine = self._specials()
        if mine:
            off = specials_shift(self.cfg)
            sp, blk, st, en = specials.at(mine, self.ch["id"], t + off)
            if sp is not None and t < en - off - 60:
                return sp, blk, st - off, en - off
        return None, None, None, None

    def _special_edge(self, t):
        """The next start or end of a special on this channel strictly after t (or None)."""
        mine = self._specials()
        if not mine:
            return None
        off = specials_shift(self.cfg)
        x = specials.next_change(mine, self.ch["id"], t + off)
        return None if x is None else x - off

    @staticmethod
    def _holiday_source(blk):
        """The holiday of a 'Holiday episodes of this channel's shows' block, or None."""
        for src in blk.get("sources") or ():
            if isinstance(src, dict) and src.get("type") == "holiday":
                return src.get("season") or ""
        return None

    def _special_titles(self, blk):
        """Titles a special's block keeps off the other channels for its hours: its
        shows, and in order its movies too (a pin does the same).  Not a random pick
        from a list of movies and not holiday episodes: what airs is in the schedule."""
        if self._holiday_source(blk) is not None:
            return []
        try:
            pool = library.resolve(blk.get("sources") or [])
        except Exception:
            return []
        out = [s["title"] for s in pool["series"]]
        if blk.get("order") != "random":
            out += [i["title"] for i in pool["singles"]]
        return out

    def _holiday_pool(self, season):
        """The holiday episodes and movies of this channel's own programming (its
        sources and its time blocks'), found by seasons.items(): each show with only
        its holiday episodes, in series order."""
        if season not in seasons.SEASONS and season not in ((self.cfg or {}).get("seasons") or {}):
            return {"series": [], "singles": []}
        hit = getattr(self, "_hol_pool", None)
        if hit and hit[0] == season and abs(time.time() - hit[1]) < 300:
            return hit[2]
        ch = self.ch
        pools = [library.keep_titles(
            library.without(library.share(ch.get("sources", []), ch.get("part"), ch.get("own"),
                                          ch.get("not_genres")), ch.get("exclude")),
            assign.allowed_fn(self.assignment(), ch["id"]))]
        for dp in ch.get("dayparts", []) or []:
            pools.append(library.without(library.share(dp.get("sources", []), dp.get("part"), dp.get("own"),
                                                       dp.get("not_genres")), ch.get("exclude")))
        series, singles, seen = [], [], set()
        for one in pools:
            for ser in one["series"]:
                if ser["key"] not in seen:
                    seen.add(ser["key"])
                    series.append(ser)
            for it in one["singles"]:
                if it["path"] not in seen:
                    seen.add(it["path"])
                    singles.append(it)
        want = set(i["path"] for i in seasons.items({"series": series, "singles": singles}, season, self.cfg))
        pool = {"series": [dict(ser, episodes=[e for e in ser["episodes"] if e["path"] in want])
                           for ser in series if any(e["path"] in want for e in ser["episodes"])],
                "singles": [i for i in singles if i["path"] in want]}
        self._hol_pool = (season, time.time(), pool)
        return pool

    def _special_pool(self, blk):
        season = self._holiday_source(blk)
        try:
            return self._holiday_pool(season) if season is not None else library.resolve(blk.get("sources") or [])
        except Exception as exc:
            log("special on %s: %s" % (self.ch.get("name"), exc))
            return {"series": [], "singles": []}

    def _special_block(self, t, sp, blk, s0, hard):
        """Plan the special's next programme at t.  Returns (end, True) when planned;
        (None, True) when nothing of it fits before its hours end and more than a slot
        is left (automatic programming fills in; pins and off-air stay away);
        (None, False) when it has nothing to air at all (no holiday episodes, an empty
        source): the channel's normal programming."""
        pool = self._special_pool(blk)
        if not pool["series"] and not pool["singles"]:
            return None, False
        first = len(self.data["blocks"])
        self._cont = None
        self._season_t = None            # never a summer rerun, never held back as out of season
        self._sp_spent = False
        prog = self._pick_special(sp, blk, pool, t, s0, hard - t - 2)
        if prog is None and self._sp_spent:
            return None, False           # every holiday episode has aired today: normal programming
        if prog:
            end = self._program(t, prog, hard)
            if self._holiday_source(blk) is not None:
                # shorts packed into the slot with it have aired today too
                st, hkey = self.data["state"], "hd:%s" % sp["id"]
                rec = st.get(hkey) or {}
                got = set(rec.get("p") or []) if rec.get("s0") == s0 else set()
                more = set(e["p"] for e in self.data["entries"]
                           if t <= e["s"] < end and e.get("k") == "show" and e.get("p")) - got
                if more:
                    self._undo("st", hkey, st.get(hkey))
                    st[hkey] = {"s0": s0, "p": sorted(got | more)}
            if sp.get("name"):
                for b in self.data["blocks"][first:]:
                    b["sp"] = sp["name"]         # the guide's description: "Turkey Day Marathon"
            return end, True
        if hard - t <= (self.slot or 1800):
            return self._no_programme(t, hard, pool), True      # the leftover: breaks
        return None, True

    def _pick_special(self, sp, blk, pool, t, s0, room):
        """A special's next programme that ends by the end of its hours (None: nothing
        does).  'continue' / 'first': each show in order from its own bookmark
        ('event:<id>|tv:<title>'), several shows in turn; 'first' starts them over on
        each new date.  'random': any episode or movie, none again until half have aired."""
        rid = "event:%s" % sp["id"]
        series, singles = pool["series"], pool["singles"]
        st = self.data["state"]
        # Movies: features take the main slots (the length rule that sends shorts to
        # Short Subjects); a short only fills time no feature fits, unless it was picked
        # by name or the special has nothing but shorts.
        features, shorts = self._special_movies(blk, singles)
        # Holiday episodes: none twice in one special day (aired: this date's paths);
        # when they've all aired, the rest of the hours are normal programming.
        hol = self._holiday_source(blk) is not None
        hkey = "hd:%s" % sp["id"]
        rec = st.get(hkey) if hol else None
        aired = set(rec["p"]) if rec and rec.get("s0") == s0 else set()

        def mark(path):
            if hol:
                old = st.get(hkey)
                self._undo("st", hkey, old)
                st[hkey] = {"s0": s0, "p": sorted(aired | {path})}

        if hol:
            left = [e for ser in series for e in ser["episodes"]] + singles
            if not [e for e in left if e["path"] not in aired and not library.is_bad(e["path"])]:
                self._sp_spent = True
                return None
        if blk.get("order") == "random":
            every = [e for ser in series for e in ser["episodes"]] + features
            recent = st["recent"].setdefault(rid, [])
            keep = min(len(every) // 2, 200)
            avoid = set(recent[-keep:]) if keep else set()
            for cands in (every, shorts):            # shorts only when no feature or episode fits
                fit = [e for e in cands if 0 < float(e["dur"]) <= room and not library.is_bad(e["path"])
                       and e["path"] not in aired]
                fit = [e for e in fit if e["path"] not in avoid] or ([] if hol else fit)
                rng = random.Random("%s|%.0f|%s" % (self.ch["id"], t, rid))
                while fit:
                    it = rng.choice(fit)
                    if library.stale(it["path"]):        # one at a time: a big list is never checked whole
                        fit = [e for e in fit if e is not it]
                        continue
                    recent.append(it["path"])
                    self._undo("ra", rid, it["path"])
                    del recent[:-max(keep, 1)]
                    mark(it["path"])
                    self._cont = ("singles", every + shorts, rid)
                    return it
            return None
        rr = st.setdefault("rr", {})
        if blk.get("order") == "first":
            # a new date: every show from its first episode again
            # (not `mark`: that's the holiday-episodes helper above, called below)
            ev = "ev:%s" % sp["id"]
            day = time.strftime("%Y-%m-%d", time.localtime(s0 + specials_shift(self.cfg)))
            if st.get(ev) != day:
                self._undo("st", ev, st.get(ev))
                st[ev] = day
                for k in [k for k in st["last"] if k.startswith(rid + "|")]:
                    self._undo("l", k, st["last"][k])
                    del st["last"][k]
                if rr.get(rid):
                    self._undo("rr", rid, rr[rid])
                    rr[rid] = 0
        shows = [("s", ser) for ser in series] + ([("m", None)] if features else [])
        i0 = rr.get(rid, 0)
        for k in range(len(shows)):
            kind, ser = shows[(i0 + k) % len(shows)]
            key = rid + "|" + (ser["key"] if kind == "s" else "movies")
            ep = self._next_episode(ser if kind == "s" else {"episodes": features}, key)
            if library.stale(ep["path"]) or float(ep["dur"]) > room or ep["path"] in aired:
                continue
            self._undo("rr", rid, i0)
            rr[rid] = i0 + k + 1
            self._bm_set(key, ep["path"], ep.get("label"))
            mark(ep["path"])
            self._cont = ("series", ser, key) if kind == "s" else None
            return ep
        # nothing in order fits the time left: a short, in order too, fills it
        if shorts:
            key = rid + "|shorts"
            ep = self._next_episode({"episodes": shorts}, key)
            if not library.stale(ep["path"]) and float(ep["dur"]) <= room and ep["path"] not in aired:
                self._bm_set(key, ep["path"], ep.get("label"))
                mark(ep["path"])
                self._cont = ("singles", shorts, rid)
                return ep
        return None

    def _special_movies(self, blk, singles):
        """(features, shorts) of a special's movies.  Shorts (up to short_limit) are
        features too when picked by name (Specific movies) or when the special has
        no longer movie at all."""
        thr = self.short_limit()
        long_ = [i for i in singles if float(i.get("dur") or 0) > thr]
        if not long_:
            return singles, []
        named = set()
        for src in blk.get("sources") or ():
            if isinstance(src, dict) and src.get("type") == "movie":
                try:
                    named |= set(i["path"] for i in library.resolve([src])["singles"])
                except Exception:
                    pass
        feats = [i for i in singles if float(i.get("dur") or 0) > thr or i["path"] in named]
        return feats, [i for i in singles if not (float(i.get("dur") or 0) > thr or i["path"] in named)]

    def _clash_free(self, pool, t):
        """Drop titles that would be on another channel at the same time."""
        busy = self._busy(t)
        if not busy:
            return pool
        slot = self.slot or 1800

        def free(title, dur):
            end = t + dur + slot
            return not any(s < end and e > t for s, e in busy.get(title.lower(), ()))
        return {"series": [s for s in pool["series"]
                           if free(s["title"], self._next_episode(s, s["key"])["dur"])],
                "singles": [i for i in pool["singles"] if free(i["title"], i["dur"])]}

    def _fillers(self, t=None):
        ch = self.ch
        ads = library.filler_pool(ch.get("commercials_path") or self.cfg.get("commercials_path")) \
            if ch.get("commercials") else []
        bumps = library.filler_pool(ch.get("bumps_path") or self.cfg.get("bumps_path")) \
            if ch.get("bumps") else []
        ids = library.filler_pool(ch.get("ids_path")) if ch.get("ids_path") else []
        if t is not None:
            ads, bumps, ids = self._station_fillers(t, ads, bumps, ids)
            ads, bumps = self._seasonal_fillers(t, ads, bumps)
        return ads, bumps, ids

    def _station_fillers(self, t, ads, bumps, ids):
        """The viewer's station folder: <channel>/bumps, ids, commercials - and the
        same inside a time block's folder (CAM Jr.'s own bumps in the morning)."""
        ch = self.ch
        try:
            if ch.get("commercials"):
                f = stations.clip_folder(ch, t, "commercials")
                ads = (library.filler_pool(f) or ads) if f else ads
            if ch.get("bumps"):
                f = stations.clip_folder(ch, t, "bumps")
                bumps = (library.filler_pool(f) or bumps) if f else bumps
            f = stations.clip_folder(ch, t, "ids")
            ids = (library.filler_pool(f) or ids) if f else ids
        except Exception as exc:
            log("station folders %s: %s" % (ch.get("name"), exc))
        return ads, bumps, ids

    def _seasonal_fillers(self, t, ads, bumps):
        """Holiday commercials/bumps: all of them on the big days, a growing
        share of breaks in the run-up."""
        sea, level = seasons.phase(t, self.cfg)
        if not sea:
            return ads, bumps
        sc = (self.cfg.get("seasons") or {}).get(sea, {})
        rng = random.Random("%s|%.0f|sfill" % (self.ch["id"], t))
        use = level >= seasons.FULL or rng.random() < max(level, 0.3)
        if not use:
            return ads, bumps
        if ads and sc.get("ads"):
            ads = library.filler_pool(sc["ads"]) or ads
        if bumps and sc.get("bumps"):
            bumps = library.filler_pool(sc["bumps"]) or bumps
        return ads, bumps

    def _pick_seasonal(self, sea, level, pool, t, room):
        """A holiday episode or movie from this channel's own programming that
        isn't on elsewhere right now and hasn't aired here lately."""
        its = [i for i in seasons.items(pool, sea, self.cfg)
               if not library.is_bad(i["path"]) and not library.stale(i["path"])]
        if not its:
            return None
        st = self.data["state"]
        rec = st.setdefault("srecent", {})
        for p in [p for p, when in rec.items() if when < t - 9 * DAY]:
            del rec[p]
        gap = 18 * 3600 if level >= seasons.FULL else 7 * DAY
        aired = dict(rec)          # holiday specials aired on any channel count
        for other in (self.lineup.sched.values() if self.lineup is not None else ()):
            if other is not self:
                for p, when in other.data.get("state", {}).get("srecent", {}).items():
                    if when > aired.get(p, 0):
                        aired[p] = when
        its = [i for i in its if aired.get(i["path"], 0) < t - gap and (room is None or i["dur"] <= room)]
        if its:
            its = self._clash_free({"series": [], "singles": its}, t)["singles"]
        if not its:
            return None
        rng = random.Random("%s|%.0f|spick" % (self.ch["id"], t))
        it = rng.choice(its)
        rec[it["path"]] = t
        self._cont = ("singles", its, "season")
        return it

    def _block(self, t):
        ch = self.ch
        if ch["type"] == "music":
            return self._music_block(t)
        if ch["type"] in ("guide", "weather"):
            e = floor_slot(t, 1800) + 1800
            self._add(t, e, ch["type"])
            self._add_block(t, e, _("Program Guide") if ch["type"] == "guide" else _("Local Forecast"),
                            ch["type"])
            return e

        hard = self._next_fixed(t)
        # Holidays and specials come first: over pins, off-air hours, holiday seasons,
        # summer reruns and automatic programming.  A special's start and end are
        # programme boundaries; during one, pins are not.
        sp, sblk, s0, _s1 = self._special_at(t)
        edge = self._special_edge(t)
        if edge is not None and (sp is not None or hard is None or edge < hard):
            hard = edge
        pins = True
        if sp is not None:
            end, mine = self._special_block(t, sp, sblk, s0, hard)
            if end is not None:
                return end
            pins = not mine
        rule, _rs, _re = self._rule_at(t) if pins else (None, None, None)
        if rule:
            pool = library.resolve(rule["sources"])
            if rule.get("order") == "random":       # e.g. "Movie at 8": don't pick what's on elsewhere
                free = self._clash_free(pool, t)
                if free["series"] or free["singles"]:
                    pool = free
            self._cont = None
            prog = self._pick_rule(pool, t, rule)
            if prog:
                return self._program(t, prog, hard)

        key, sources, offair, until = self._daypart(t)
        if offair and not pins:          # the rest of a special's hours: on the air
            key, sources, offair = "base", ch.get("sources", []), False
        if offair:
            end = until if hard is None else min(until, hard)
            return self._offair(t, end, until)
        if ch["type"] == "extras":
            return self._extras_block(t, hard)
        if ch["type"] == "musicvideos":
            return self._mv_block(t, hard)

        part, fallback, own, not_genres = self._daypart_extra(key)
        full = library.without(library.share(sources, part, own, not_genres), ch.get("exclude"))
        mine = full
        self._fallback = (fallback, part)
        if key == "base":    # time blocks are the user's own choice - never filtered
            mine = library.keep_titles(full, assign.allowed_fn(self.assignment(), ch["id"]))
        room = (hard - t - 2) if hard else None
        sea, level = seasons.phase(t, self.cfg)
        if sea:
            # Holiday programming: everything on the big days (when the channel
            # has any), a growing share in the run-up - more on movie channels.
            share = level if level >= seasons.FULL else \
                min(0.9, level * (1.6 if ch["type"] == "movies" else 1.0))
            if random.Random("%s|%.0f|season" % (ch["id"], t)).random() < share:
                self._cont = None
                prog = self._pick_seasonal(sea, level, self._skip_short(mine), t, room)
                if prog:
                    return self._program(t, prog, hard)
        # Never the same show on two channels at once.  Preference:
        # 1) this channel's own shows that are free, 2) anything else on its list
        # that is free, 3) any free show from the library (a fill-in, like a
        # network would run), 4) only if nothing at all is free, its own shows.
        prog = None
        self._season_t = t
        try:
            prog = self._auto_pick(mine, full, t, key, room)
        finally:
            self._season_t = None
        pool = full
        if prog:
            return self._program(t, prog, hard)
        return self._no_programme(t, hard, pool)

    def _skip_short(self, pool):
        """Automatic programming leaves out TV episodes shorter than the 'Skip episodes
        shorter than' setting (intros, trailers, recaps filed as episodes): the series
        goes on to its next real episode (its place moves on past them).  Not a series
        whose usual episode is that short (median under the limit: short-form shows go
        through shorts packing as before), not an episode of unknown length, never
        movies or other singles, never a pinned slot's own pool (_pick_rule)."""
        limit = skip_short_secs(self.cfg)
        if not limit or not pool or not pool.get("series"):
            return pool
        out = []
        changed = False
        for ser in pool["series"]:
            eps = ser.get("episodes") or []
            if not str(ser.get("key", "")).startswith("tv:"):
                out.append(ser)
                continue
            known = sorted(float(e.get("dur") or 0) for e in eps if float(e.get("dur") or 0) > 0)
            if not known or known[len(known) // 2] < limit:
                out.append(ser)                     # short-form series (or nothing measured)
                continue
            keep = [e for e in eps if not (0 < float(e.get("dur") or 0) < limit)]
            if len(keep) == len(eps):
                out.append(ser)
                continue
            changed = True
            with _SKIP_LOCK:
                for e in eps:
                    d = float(e.get("dur") or 0)
                    if 0 < d < limit and e["path"] not in _SKIP_LOGGED:
                        _SKIP_LOGGED.add(e["path"])
                        _SKIPPED[e["path"]] = [ser.get("title", ""), e.get("label") or "", round(d)]
                        log("skipped (shorter than %d min, %d s): %s" % (limit // 60, d, e["path"]),
                            level=xbmc.LOGINFO)
            if keep:                                # nothing left to air: like a show with no episodes
                out.append(dict(ser, episodes=keep))
        return dict(pool, series=out) if changed else pool

    def _auto_pick(self, mine, full, t, key, room):
        prog = None
        fb, part = getattr(self, "_fallback", (None, None)) or (None, None)
        backup = library.partition(library.resolve(fb), part) if fb else None
        for i, cand in enumerate((mine, full, backup, None, mine)):
            if cand is None:
                if i == 2:
                    continue
                cand = library.resolve([{"type": "alltv"}])
            cand = self._skip_short(cand)
            if i < 4:
                cand = self._clash_free(cand, t)
            self._cont = None
            prog = self._pick(cand, t, key, maxdur=room)
            if prog:
                break
        return prog

    def _no_programme(self, t, hard, pool):
        ch, slot = self.ch, self.slot
        room = (hard - t - 2) if hard else None
        if room is not None and (pool["series"] or pool["singles"]):
            # Nothing short enough before the next pinned show: station break.
            ads, bumps, ids = self._fillers(t)
            rng = random.Random("%s|%.0f|gap" % (ch["id"], t))
            self._breaks(ads)(t, hard - t, ads, bumps, rng, final=True, ids=ids)
            self._add_block(t, hard, _("Station Break"), "card")
            return hard
        e = t + (slot or 1800)
        if hard:
            e = min(e, hard)
        self._add(t, e, "card", sub="nosignal")
        self._add_block(t, e, _("No Programming"), "card")
        return e

    def _offair(self, t, end, real_end):
        """Sign-off clip or card, stand-by card (or bars), sign-on clip."""
        ch = self.ch
        style = ch.get("offair_style") or self.cfg.get("offair_style") or "standby"
        rng = random.Random("%s|%.0f|offair" % (ch["id"], t))
        pos = t
        # sign-off only at the real start of the off-air window: programming or a break
        # right before (a window starting mid-slot begins when that slot's programme
        # ends), never when planning continues mid-window after off-air or the card
        ents = self.data["entries"]
        if ents and ents[-1]["e"] >= t - 1:
            starting = ents[-1].get("k") not in ("offair", "signoff")
        else:
            starting = not any(in_window(t - 30, w) for w in ch.get("offair", []))
        mode = chmod.signoff_mode(ch) if starting else "none"
        if mode == "folder":
            # the user's own clip always wins; a folder with nothing that fits gets the card
            clips = [c for c in library.filler_pool(ch["signoff_path"]) if c["dur"] < end - pos - 60]
            if clips:
                c = rng.choice(clips)
                self._add(pos, pos + c["dur"], "clip", p=c["path"], o=0, t=_("Sign-off"))
                pos += c["dur"]
                mode = "none"
            else:
                mode = "card"
        if mode == "card" and SIGNOFF_CARD_SECS < end - pos - 60:
            # silent, like the station ID card; r: when the off-air hours end ("We return at")
            self._add(pos, pos + SIGNOFF_CARD_SECS, "signoff", r=round(real_end, 3))
            pos += SIGNOFF_CARD_SECS
        signon = None
        if end == real_end and ch.get("signon_path"):
            clips = [c for c in library.filler_pool(ch["signon_path"]) if c["dur"] < end - pos - 60]
            if clips:
                signon = rng.choice(clips)
        stop = end - (signon["dur"] if signon else 0)
        self._add(pos, stop, "offair", sub=style)
        if signon:
            self._add(stop, end, "clip", p=signon["path"], o=0, t=_("Sign-on"))
        self._add_block(t, end, _("Off the Air"), "offair")
        return end

    def _program(self, t, prog, hard):
        """Lay one programme out with commercial breaks, ending on a slot
        boundary and never running into the next pinned slot."""
        ch = self.ch
        slot = self.slot
        rng = random.Random("%s|%.0f" % (ch["id"], t))
        dur = float(prog["dur"])
        ads, bumps, ids = self._fillers(t)
        cont, self._cont = getattr(self, "_cont", None), None
        if slot and cont and dur <= self.short_limit() and \
                self.cfg.get("shorts_mode", 0) != SHORTS_ONE_PER_SLOT:
            more = self._more_shorts(t, prog, cont, hard, bool(ads), rng)
            if more:
                return self._shorts_block(t, [prog] + more, hard, ads, bumps, ids, rng, cont)

        if slot:
            end = ceil_slot(t + dur + 2, slot)
            nslots = max(1, int(round((end - t) / slot)))
        else:
            end, nslots = t + dur, 1
        if hard is not None and end > hard:
            end = hard
        dur = min(dur, end - t)      # runs into a pinned slot: the network cuts away
        gap = end - t - dur

        house = self._house_on(ads)
        fill = self._breaks(ads)
        k = 0
        if (ads or house) and gap >= 90:
            per = self.cfg.get("breaks_per_slot", 2)
            k = max(0, min(per * nslots * slot // 1800 if slot else per, int(gap // 75) - 1))
        midroll = ch.get("midroll", ch["type"] != "movies")
        if not midroll:
            k = 0
        # breaks at the episode's chapter marks (act breaks) when its chapters have
        # been read; else (and with the setting off) evenly spaced as always
        marks = self._chapter_points(prog, dur, gap, k, midroll) if (ads or house) and gap >= 90 else None
        if marks:
            k = len(marks)
        brk = gap / (k + 1)
        if house:
            brk = min(brk, HOUSE_MAX)    # short house breaks inside; the rest at the end
        points = [0.0] + marks + [dur] if marks else [dur * i / (k + 1) for i in range(k + 2)]
        credits = self._credits_at(prog, dur, cut=dur < float(prog["dur"]) - 1)
        pos = t
        for i in range(k + 1):
            seg = points[i + 1] - points[i]
            # the last part knows where its end credits start (file time): the squeeze
            cr = credits if i == k and credits is not None and credits >= prog.get("o0", 0) + points[i] - 0.5 else None
            self._add(pos, pos + seg, "show", p=prog["path"], o=round(prog.get("o0", 0) + points[i], 2),
                      t=prog["title"], sub=prog.get("sub"), lb=prog.get("label"), cr=cr)
            pos += seg
            # to the break's planned end: a part that started early (absorbed seconds) gives them back here
            blen = (t + points[i + 1] + brk * (i + 1) - pos) if i < k else end - pos
            pos = fill(pos, blen, ads, bumps, rng, final=(i == k), ids=ids if i == k else None,
                       absorb=i < k)
        self._add_block(t, end, prog["title"], "show", prog.get("sub", ""), prog.get("label", ""))
        if getattr(self, "_rr_path", None) == prog["path"]:
            self.data["blocks"][-1]["rr"] = 1     # a summer rerun: "(R)" in the guide and banner
        self._rr_path = None
        return end

    def _chapter_points(self, prog, dur, gap, timed_k, midroll):
        """Break points from the episode's chapters (chapters.points), or None for
        today's evenly spaced breaks: the setting off, a movie, a file not read yet,
        no / automatic chapters, the show set to Never.  One log line per episode."""
        if not self.cfg.get("chapter_breaks", True) or not prog.get("path") or not prog.get("label"):
            return None                  # TV episodes only (movies, clips: no label)
        info = library.chapter_info(prog["path"])
        if info is None:
            return None
        mode = library.chapter_mode(prog.get("title", ""))
        pts = chapters.points(info, dur, float(prog.get("o0", 0) or 0), gap, timed_k, midroll, mode)
        log("chapters: %s %s: %s%s -> %s" % (
            prog.get("title", ""), prog.get("label", ""), info.get("v"),
            (" (%s)" % info.get("why")) if info.get("why") else "", (mode + " ") if mode != "auto" else "") +
            ("breaks at %s" % ", ".join("%d:%02d" % (t // 60, t % 60) for t in pts) if pts else "timed breaks"),
            level=xbmc.LOGINFO)
        return pts

    SQUEEZE_TAIL = 30.0      # no chapters (or not read yet): the final 30 s
    SQUEEZE_MIN = 15 * 60.0  # ...of a TV episode this long or longer

    def _credits_at(self, prog, dur, cut=False):
        """Where the squeeze starts (file time) on the episode's last part: its end
        credits when its chapters show them, else - no chapters, or not read yet - the
        final 30 s of a TV episode of 15 min or more that plays to its natural end.
        None: no squeeze (movies, clips, shorts, a pinned slot cutting it off, a last
        chapter over 3 min).  Not before off-air: tv.squeeze_tick looks at what's next."""
        if not prog.get("path") or not prog.get("label"):
            return None                  # TV episodes only (movies, clips: no label)
        o0 = float(prog.get("o0", 0) or 0)
        info = library.chapter_info(prog["path"]) if self.cfg.get("chapter_breaks", True) else None
        if info is not None and info.get("why") not in ("no chapters", "one chapter"):
            cr = info.get("cr")          # the chapter rules
        elif cut or float(prog.get("dur") or 0) + o0 < self.SQUEEZE_MIN:
            return None
        else:
            cr = o0 + dur - self.SQUEEZE_TAIL
        if cr is None or not (o0 < cr < o0 + dur - 5):
            return None
        return round(cr, 2)

    # ------------------------------------------------- Behind the scenes (movie Extras)
    X_TURN = 3600          # at most an hour of one film's extras per turn; the rest airs on its next turn
    X_FILL = 22.0 / 30     # at least ~22 minutes of programme per half hour
    X_FILMS = 6            # films sharing one block, at most

    def _extras_films(self):
        """Films and their qualifying segments, from the Extras cache only."""
        try:
            return library.extras_programme(setting_bool("extras_unrecognised", False))
        except Exception as exc:
            log("extras programme: %s" % exc)
            return []

    def _x_next(self, films, st, skip, t):
        """The next film in the rotation: every film once per round, a new
        shuffled order each round; films new since the round began join its end."""
        by = dict((f["key"], f) for f in films)
        done = set(st["done"])
        q = [k for k in st["queue"] if k in by]
        if q or done:           # a round in progress: films new since it began join its end
            q += sorted((k for k in by if k not in done and k not in q),
                        key=lambda k: library.natural_key(by[k]["title"]))
        if not q:
            st["round"] += 1
            q = sorted(by)
            random.Random("%s|xround|%d" % (self.ch["id"], st["round"])).shuffle(q)
            last = st["done"][-1] if st["done"] else None
            if len(q) > 1 and q[0] in (last,) + tuple(skip):
                q.append(q.pop(0))          # don't start the new round with what just aired
            st["done"] = []
        for k in q:
            if k not in skip:
                q.remove(k)
                st["queue"] = q
                st["done"].append(k)
                return by[k]
        st["queue"] = q
        return None

    def _x_take(self, f, st):
        """This turn's segments for a film: from its bookmark, up to X_TURN (one
        longer segment airs whole); the rest waits for the film's next turn."""
        segs = f["segs"]
        pos = st["pos"]
        i = pos.get(f["key"], 0)
        if i >= len(segs):
            i = 0
        out, total, j = [], 0.0, i
        while j < len(segs):
            s = segs[j]
            if out and total + s["dur"] > self.X_TURN:
                break
            j += 1
            if library.is_bad(s["path"]):
                continue
            out.append(s)
            total += s["dur"]
        if j >= len(segs):
            pos.pop(f["key"], None)
        else:
            pos[f["key"]] = j
        return out

    def _extras_block(self, t, hard):
        films = self._extras_films()
        if not films:
            return self._no_programme(t, hard, {"series": [], "singles": []})
        st = self.data["state"].setdefault("x", {})
        for k, v in (("round", 0), ("queue", []), ("done", []), ("pos", {})):
            st.setdefault(k, v)
        slot = self.slot or 1800
        picks, total, skip = [], 0.0, set()
        for _guard in range(self.X_FILMS * 3):
            if len(picks) >= self.X_FILMS:
                break
            f = self._x_next(films, st, skip, t)
            if f is None:
                break
            skip.add(f["key"])
            segs = self._x_take(f, st)
            if not segs:
                continue
            picks.append((f, segs))
            total += sum(s["dur"] for s in segs)
            if total >= self.X_FILL * (ceil_slot(t + total + 2, slot) - t):
                break
        if not picks:
            return self._no_programme(t, hard, {"series": [], "singles": []})
        return self._extras_layout(t, picks, hard)

    def _extras_layout(self, t, picks, hard):
        """Segments back to back; breaks only between segments (the ones nearest
        evenly spaced points), the station ID in the last break."""
        ch = self.ch
        slot = self.slot or 1800
        rng = random.Random("%s|%.0f" % (ch["id"], t))
        segs = [s for _f, ss in picks for s in ss]
        dur = sum(s["dur"] for s in segs)
        end = ceil_slot(t + dur + 2, slot)
        if hard is not None and end > hard:
            end = max(hard, t + dur)
        nslots = max(1, int(round((end - t) / slot)))
        gap = max(0.0, end - t - dur)
        ads, bumps, ids = self._fillers(t)
        k = 0
        if ads and gap >= 90 and ch.get("midroll", True):
            per = self.cfg.get("breaks_per_slot", 2)
            k = max(0, min(per * nslots * slot // 1800, int(gap // 75) - 1, len(segs) - 1))
        cum, acc = [], 0.0
        for s in segs[:-1]:
            acc += s["dur"]
            cum.append(acc)
        after = set()
        for i in range(1, k + 1):
            free = [j for j in range(len(cum)) if j not in after]
            if not free:
                break
            target = dur * i / (k + 1)
            after.add(min(free, key=lambda j: abs(cum[j] - target)))
        brk = gap / (len(after) + 1)
        title = self._x_title([f for f, _ss in picks])
        pos = t
        for j, s in enumerate(segs):
            self._add(pos, pos + s["dur"], "show", p=s["path"], o=0, t=title, sub=s["title"])
            pos += s["dur"]
            if j in after:
                pos = self._breaks(ads)(pos, brk, ads, bumps, rng, final=False)
        self._breaks(ads)(pos, end - pos, ads, bumps, rng, final=True, ids=ids)
        self._add_block(t, end, title, "show", " · ".join(s["title"] for s in segs))
        return end

    # ------------------------------------------------- Boombox (music videos)
    MV_FILL = 0.8          # about 24 minutes of videos per half hour; the rest is breaks
    MV_ENOUGH = 0.65       # a video that doesn't fit waits for the next block once this much is filled
    MV_MAX = 40            # videos in one block, at most

    def _mv_videos(self):
        """{path: item} the channel can air.  Items from other sources than Music
        videos get their caption from the file's tags and name."""
        pool = library.resolve(self.ch.get("sources", []))
        out = {}
        for it in list(pool["singles"]) + [e for s in pool["series"] for e in s["episodes"]]:
            p = it["path"]
            if p in out or library.is_bad(p) or not it.get("dur"):
                continue
            if "mv" not in it:
                c = library.mv_cache_entry(p)
                if musicvideos.skip_reason(p, it["dur"], c.get("a")):
                    continue
                it = dict(it, mv=musicvideos.merge(None, c.get("t"), p), fps=c.get("f") or 0)
            out[p] = it
        return out

    def _mv_title(self):
        """'Boombox Music Videos' (a channel already called '... Videos' keeps its name)."""
        name = stations.brand(self.ch, None)["name"] if self.ch.get("station") else self.ch.get("name", "")
        name = (name or "").strip()
        if "video" in name.lower():
            return name
        if name.lower().endswith(" tv"):
            name = name[:-3].strip()
        return _("%s Music Videos") % name if name else _("Music Videos")

    def _mv_block(self, t, hard):
        """One block of music videos of one frame-rate group: the TV switches
        refresh rate only between blocks, inside a break."""
        vids = self._mv_videos()
        if not vids:
            return self._no_programme(t, hard, {"series": [], "singles": []})
        st = self.data["state"].setdefault("mv", {})
        gmap = musicvideos.groups([(p, it.get("fps"), it["dur"]) for p, it in vids.items()])
        members = {}
        for p, g in gmap.items():
            members.setdefault(g, {})[p] = musicvideos.artist_key(vids[p]["mv"], p)
        group = musicvideos.next_group(st, dict((g, len(m)) for g, m in members.items()))
        ads = self._fillers(t)[0]
        slot = self.slot or 1800
        reserve = 60 if ads else 0          # room for at least a short break
        end = ceil_slot(t + 2, slot)        # the block ends on the clock; a long video makes it longer
        picks, total = [], 0.0
        for _i in range(min(len(members[group]), self.MV_MAX)):
            before = json.dumps(st)
            it = vids[musicvideos.next_video(st, group, members[group], self.ch["id"])]
            put_back = hard is not None and t + total + it["dur"] > hard - 2
            if not put_back and t + total + it["dur"] + reserve > end:
                if picks and total >= self.MV_ENOUGH * (end - t):
                    put_back = True             # full enough: this one opens a later block
                else:
                    end = ceil_slot(t + total + it["dur"] + reserve + 2, slot)
            if put_back:
                st.clear()
                st.update(json.loads(before))   # rotation as if it hadn't been picked
                break
            picks.append(it)
            total += it["dur"]
            # with commercials, about 24 minutes of videos a half hour is a full block;
            # without, as many as fit (what's left is the station ID card)
            if (ads and total >= self.MV_FILL * (end - t)) or end - t - total < 90:
                break
        if not picks:
            return self._no_programme(t, hard, {"series": [], "singles": [None]})
        log("%s %s: block of %d videos at %s fps" % (
            self.ch.get("name"), time.strftime("%H:%M", time.localtime(t)), len(picks), group),
            level=xbmc.LOGINFO)
        return self._mv_layout(t, picks, hard, end)

    def _mv_layout(self, t, picks, hard, end):
        """Videos back to back; breaks only between videos (the ones nearest
        evenly spaced points), the station ID in the last break."""
        ch = self.ch
        slot = self.slot or 1800
        rng = random.Random("%s|%.0f" % (ch["id"], t))
        dur = sum(it["dur"] for it in picks)
        if hard is not None and end > hard:
            end = max(hard, t + dur)
        nslots = max(1, int(round((end - t) / slot)))
        gap = max(0.0, end - t - dur)
        ads, bumps, ids = self._fillers(t)
        k = 0
        if ads and gap >= 90 and ch.get("midroll", True):
            per = self.cfg.get("breaks_per_slot", 2)
            k = max(0, min(per * nslots * slot // 1800, int(gap // 75) - 1, len(picks) - 1))
        cum, acc = [], 0.0
        for it in picks[:-1]:
            acc += it["dur"]
            cum.append(acc)
        after = set()
        for i in range(1, k + 1):
            free = [j for j in range(len(cum)) if j not in after]
            if not free:
                break
            target = dur * i / (k + 1)
            after.add(min(free, key=lambda j: abs(cum[j] - target)))
        brk = gap / (len(after) + 1)
        title = self._mv_title()
        pos = t
        for j, it in enumerate(picks):
            info = it["mv"]
            self._add(pos, pos + it["dur"], "show", p=it["path"], o=0, t=title, sub=musicvideos.label(info),
                      cap=[list(x) for x in musicvideos.caption(info)], d=round(it["dur"], 2))
            pos += it["dur"]
            if j in after:
                pos = self._breaks(ads)(pos, brk, ads, bumps, rng, final=False)
        self._breaks(ads)(pos, end - pos, ads, bumps, rng, final=True, ids=ids)
        self._add_block(t, end, title, "show",
                        u" · ".join(it["mv"].get("artist") or it["mv"].get("title", "") for it in picks))
        return end

    # ------------------------------------------------- music channels (DMX-style)
    MU_MAX = 60            # songs in one hour, at most

    def _music_block(self, t):
        """Songs back to back from t until one runs past the next full hour: no
        breaks of any kind, songs cross the hour freely.  The guide gets one
        block per clock hour, its artists as the description.  Rotation as on
        Boombox: no artist twice in a row, no repeat before every song has
        played, every round shuffled anew.  With sample-rate groups on, an
        hour's songs share one sample rate (the output reopens at most there)."""
        songs = music.songs_for(self.ch.get("sources", []))
        hour = ceil_slot(t + 1, 3600)
        if len(songs) < 1:
            return self._no_programme(t, None, {"series": [], "singles": []})
        st = self.data["state"].setdefault("mu", {})
        by_path = dict((s["p"], s) for s in songs)
        gmap = music.rate_groups(songs)
        members = {}
        for p, g in gmap.items():
            members.setdefault(g, {})[p] = by_path[p]["ak"]
        group = musicvideos.next_group(st, dict((g, len(m)) for g, m in members.items()))             if len(members) > 1 else next(iter(members))
        pos = t
        for _i in range(self.MU_MAX):
            s = by_path[musicvideos.next_video(st, group, members[group], self.ch["id"])]
            self._add(pos, pos + s["d"], "song", p=s["p"], o=0, t=s["t"], a=s["a"], al=s["al"], y=s["y"],
                      tr=s["tr"], g=s["g"], cp=s["cp"], aid=s["aid"], arid=s["arid"], r=s["r"])
            pos += s["d"]
            if pos >= hour:
                break
        # the guide's hour blocks: the hour this run started in (again, if a replan cut it)
        blocks = self.data["blocks"]
        while blocks and blocks[-1]["e"] > t:
            blocks.pop()
        bs = blocks[-1]["e"] if blocks else floor_slot(t, 3600)
        h = hour
        while h <= pos:
            self._music_hour(bs, h)
            bs, h = h, h + 3600
        if len(members) > 1:
            log("%s %s: songs at %s Hz" % (self.ch.get("name"), time.strftime("%H:%M", time.localtime(t)), group),
                level=xbmc.LOGINFO)
        return pos

    def _music_hour(self, s, e):
        artists = []
        for x in self.data["entries"]:
            if x.get("k") == "song" and s <= x["s"] < e and x.get("a") and x["a"] not in artists:
                artists.append(x["a"])
        self._add_block(s, e, self.ch.get("name", ""), "show", u" · ".join(artists))

    @staticmethod
    def _x_title(films):
        if len(films) == 1:
            f = films[0]
            return _("Inside %s") % ("%s (%s)" % (f["title"], f["year"]) if f.get("year") else f["title"])
        return " · ".join(_("Inside %s") % f["title"] for f in films)

    # ------------------------------------------------------------- shorts
    def short_limit(self):
        """Anything up to 40% of a half hour (12 min) counts as a short."""
        return 0.4 * min(self.slot or 1800, 1800)

    def _shorts_end(self, t, dur, hard):
        end = ceil_slot(t + dur + 2, self.slot)
        return min(end, hard) if hard is not None else end

    def _more_shorts(self, t, first, cont, hard, have_ads, rng):
        """More shorts to fill the rest of the slot, like a cartoon block:
        the next episodes of the same series, or other short films."""
        end = self._shorts_end(t, float(first["dur"]), hard)
        reserve = 60 if have_ads else 0          # room for a break after each one
        total = float(first["dur"]) + reserve
        used = {first["path"]}
        out = []
        kind, src, ptr = cont
        st = self.data["state"]
        auto = not (ptr or "").startswith(("rule:", "event:")) and ptr != "season"
        if auto and kind == "singles":
            src = [it for it in src if not seasons.out_of_season(it, t, self.cfg)]
        self._season_t = t if auto else None
        try:
            return self._more_shorts_loop(t, end, reserve, total, used, out, kind, src, ptr, st, rng)
        finally:
            self._season_t = None

    def _more_shorts_loop(self, t, end, reserve, total, used, out, kind, src, ptr, st, rng):
        while len(out) < 11:
            room = end - t - total - reserve
            if kind == "series":
                ep = self._next_episode(src, ptr)
                if ep["path"] in used or ep["dur"] > room or ep["dur"] > self.short_limit()                         or library.stale(ep["path"]):
                    break
                self._bm_set(ptr, ep["path"], ep.get("label"))
            else:
                fit = [it for it in src if it["path"] not in used
                       and 0 < it["dur"] <= min(room, self.short_limit())]
                if not fit:
                    break
                ep = rng.choice(fit)
                if library.stale(ep["path"]):
                    used.add(ep["path"])         # not this one; try the others
                    continue
                if ptr == "season":
                    st.setdefault("srecent", {})[ep["path"]] = t
                elif ptr:
                    rec = st["recent"].setdefault(ptr, [])
                    rec.append(ep["path"])
                    self._undo("ra", ptr, ep["path"])
            used.add(ep["path"])
            out.append(ep)
            total += float(ep["dur"]) + reserve
        return out

    def _shorts_block(self, t, items, hard, ads, bumps, ids, rng, cont):
        """Several shorts back to back in one slot, a break after each."""
        total = sum(float(it["dur"]) for it in items)
        end = self._shorts_end(t, total, hard)
        gap = max(0.0, end - t - total)
        brk = gap / len(items)
        pos = planned = t
        for i, it in enumerate(items):
            self._add(pos, pos + float(it["dur"]), "show", p=it["path"], o=round(it.get("o0", 0), 2),
                      t=it["title"], sub=it.get("sub"), lb=it.get("label"))
            pos += float(it["dur"])
            planned += float(it["dur"]) + brk      # where this break was meant to end
            last = i == len(items) - 1
            pos = self._breaks(ads)(pos, (end - pos) if last else (planned - pos), ads, bumps, rng,
                             final=last, ids=ids if last else None, absorb=not last)
        titles = []
        for it in items:
            if it["title"] not in titles:
                titles.append(it["title"])
        if len(titles) == 1:
            title = titles[0]
            sub = ", ".join(x for x in (it.get("label") or it.get("sub") for it in items) if x)
        else:
            title = cont[1]["title"] if cont[0] == "series" else _("Short Subjects")
            sub = ", ".join(titles)
        self._add_block(t, end, title, "show", sub, "")
        return end

    CARD_MIN, CARD_MAX = 3.0, 10.0   # a station ID card stretched to fill what's left
    ABSORB = 3.0                     # smaller leftovers: the next programme part starts that much early

    def _pack(self, avail, ads, rng, absorb):
        """Commercials whose total lands as close to `avail` as possible.  A spot
        airs again in the same break only after every spot has had a turn, and
        never twice in a row (a channel with only a few spots).  Leftovers the
        card can't take (0.5 s up to CARD_MIN, unless the next part absorbs them)
        count as bad as a big gap."""
        def score(rem):
            if rem < 0.5 or (absorb and rem < self.ABSORB):
                return rem
            return rem + (1000 if rem < self.CARD_MIN else 0)

        best = None
        for _attempt in range(60):
            pick, rem, used, last = [], avail, set(), None
            while True:
                if len(used) == len(ads):
                    used = set()             # every spot has had a turn: a new round
                fit = [a for a in ads if a["dur"] <= rem and a["path"] not in used and a["path"] != last]
                if not fit:
                    break
                a = rng.choice(fit)
                used.add(a["path"])
                last = a["path"]
                pick.append(a)
                rem -= a["dur"]
            if best is None or score(rem) < score(best[1]):
                best = (pick, rem)
            if score(rem) < 0.5:
                break
        return best

    def _fill(self, pos, length, ads, bumps, rng, final, ids=None, absorb=False):
        """One break from pos, `length` seconds long, filled completely: commercials
        to fit, a bump or station ID, a promo, then the station ID card stretched to
        the seconds left.  Never planned black.  absorb: a mid-programme break that
        may end up to ABSORB s early (the next part starts early, ends on time);
        returns where the break really ends."""
        end = pos + length
        if length < 0.5:
            return end
        bump = None
        # Between programmes a station ID ("you're watching...") beats a bump.
        for pool in ([ids, bumps] if ids else [bumps]):
            fit = [b for b in (pool or []) if b["dur"] <= length]
            if fit:
                bump = rng.choice(fit)
                break
        avail = length - (bump["dur"] if bump else 0)
        promo = self._promo_for_break(pos, avail)
        if promo:
            avail -= promo["dur"]
        hitem = self._house_mix(pos, avail) if ads else None
        if hitem:
            avail -= hitem["dur"]

        chosen, remaining = self._pack(avail, ads, rng, absorb) if ads else ([], avail)
        if not absorb and 0.5 <= remaining < self.CARD_MIN and chosen:
            # too little for a card, too much to hide: one spot fewer, a longer card
            short = min(range(len(chosen)), key=lambda i: chosen[i]["dur"])
            remaining += chosen.pop(short)["dur"]
        # The viewer's own bumps before any built-in card.
        extra = []
        if remaining >= self.CARD_MIN:
            for b in rng.sample(list(bumps or []), min(len(bumps or []), 12)):
                if len(extra) < 2 and b["dur"] <= remaining - self.CARD_MIN and \
                        (bump is None or b["path"] != bump["path"]) and b not in extra:
                    extra.append(b)
                    remaining -= b["dur"]

        for i, a in enumerate(chosen):
            self._add(pos, pos + a["dur"], "ad", p=a["path"], o=0, t=a.get("title"))
            pos += a["dur"]
            if promo and i == 0:             # a promo after the first spot, like a real station
                pos = self._add_promo(pos, promo)
                promo = None
            if hitem and i == len(chosen) // 2:  # a house ad in the middle of the break
                pos = self._add_house(pos, hitem)
                hitem = None
        if promo:
            pos = self._add_promo(pos, promo)
        if hitem:
            pos = self._add_house(pos, hitem)
        for b in extra:
            self._add(pos, pos + b["dur"], "bump", p=b["path"], o=0)
            pos += b["dur"]
        short = absorb and remaining < self.ABSORB
        if remaining >= 0.5 and not short:
            # cards of at most CARD_MAX s; a channel without commercials keeps its one 'Up next' card
            n = max(1, int(-(-remaining // self.CARD_MAX))) if ads else 1
            for j in range(n):
                ln = remaining / n
                # at a programme's end the last card says 'Up next', right before the show
                last = j == n - 1
                sub = ("next" if last else "id") if final else ("id" if j % 2 == 0 else "next")
                self._add(pos, pos + ln, "card", sub=sub)
                pos += ln
            remaining = 0
        if bump:
            self._add(pos, pos + bump["dur"], "bump", p=bump["path"], o=0)
            pos += bump["dur"]
        if short:
            return round(pos, 3)             # the next part starts these few seconds early
        if self.data["entries"] and pos < end:
            self.data["entries"][-1]["e"] = round(end, 3)    # under half a second: the last item holds
        return end

    # ------------------------------------------------------------- house breaks
    def _breaks(self, ads):
        """The one way a break is filled: house breaks (promos, system ads, retro ads,
        the station ID card) where the channel runs them, else commercial breaks.
        Every layout (programmes, shorts, music videos, extras, empty hours) uses it."""
        return self._house_fill if self._house_on(ads) else self._fill

    def _house_on(self, ads):
        """House breaks instead of commercial breaks on this channel."""
        mode = int(self.cfg.get("house_breaks", HOUSE_NO_ADS))
        return mode in (HOUSE_NO_ADS, HOUSE_MIX) and not ads and bool(self.ch.get("commercials")) and \
            self.ch.get("type") in PROMO_TYPES

    def _house_others(self):
        """Other channels whose programmes a house break may promote."""
        if self.lineup is None:
            return []
        return [c for c in self.lineup.channels
                if c["id"] != self.ch["id"] and c.get("type") in PROMO_TYPES and not c.get("hidden")]

    def _house_systems(self):
        """System ads this lineup can truthfully run: the guide channel, the
        weather channel when it knows where you are, tonight's lineup."""
        out = []
        chans = self.lineup.channels if self.lineup is not None else []
        if any(c.get("type") == "guide" for c in chans):
            out.append("guide")
        if any(c.get("type") == "weather" for c in chans):
            try:
                from . import weather
                if weather.has_place():
                    out.append("weather")
            except Exception as exc:
                log("house ads: weather %s" % exc)
        if len([c for c in chans if c.get("type") in PROMO_TYPES]) >= 2:
            out.append("lineup")
        return out

    def _house_items(self, rng, n, own=True, skip=(), max_promos=None, last=None):
        """n house ads for one break, no two alike: this channel's promos,
        other channels' promos, system ads.  skip: system ads the gap has run;
        max_promos: at most this many promos (a long gap's break), the ad the
        break before ended on (last) the one left out."""
        others = self._house_others()
        rng.shuffle(others)
        pool = [{"k": "promo", "h": 1, "xc": c["id"]} for c in others[:2]]
        pool += [{"k": "house", "h": s, "ln": rng.randrange(3)} for s in self._house_systems() if s not in skip]
        rng.shuffle(pool)
        if own:
            pool.insert(rng.randrange(min(2, len(pool) + 1)), {"k": "promo", "h": 1})
        while own and len(pool) < n and max_promos is None:
            pool.append({"k": "promo", "h": 1})          # another of this channel's shows
        if max_promos is not None:
            if last is not None:
                pool = [it for it in pool if _house_key(it) != last] + [it for it in pool if _house_key(it) == last]
            out = []
            for it in pool:
                if it["k"] == "promo":
                    if max_promos <= 0:
                        continue
                    max_promos -= 1
                out.append(it)
            pool = out
        return pool[:n]

    def _run_so_far(self):
        """The gap being planned: (system ads it has run, promos in its break so far
        (since a long gap's last "sep" card))."""
        systems, promos_n = set(), 0
        in_break = True
        for e in reversed(self.data["entries"]):
            if e.get("k") not in BREAK_KINDS:
                break                    # the programme before the gap
            if e.get("sep"):
                in_break = False
            if e.get("k") == "house":
                systems.add(e.get("h"))
            elif in_break and e.get("k") == "promo":
                promos_n += 1
        return systems, promos_n

    def _house_fill(self, pos, length, ads, bumps, rng, final, ids=None, absorb=False):
        """A house break: about 30-60 s of house ads, a station ID card to round
        it off, the viewer's bump or ID clip at the edge.  At a programme's end
        the gap gets as many house breaks as it takes to keep the 'Up next' card,
        always the last card before the next show, at about UPNEXT_MAX seconds."""
        end = pos + length
        if length < 0.5:
            return end
        if final and length < HOUSE_FINAL_MIN:
            return self._fill(pos, length, [], bumps, rng, final, ids=ids)
        upnext = min(UPNEXT_MAX, max(UPNEXT_MIN, length - HOUSE_MAX)) if final else 0.0
        bump = None
        for pool in ([ids, bumps] if ids else [bumps]):
            fit = [x for x in (pool or []) if x["dur"] <= length - upnext - HOUSE_FINAL_MIN]
            if fit:
                bump = rng.choice(fit)
                break
        house = length - upnext - (bump["dur"] if bump else 0)
        last = None
        if final and house > GAP_SPLIT:
            # a long gap (a short episode in a long slot): normal breaks of 2-3 minutes,
            # each its own break for the retro-ad rules, the station ID card between them
            nb = max(2, int(round(house / GAP_BREAK)))
            for b in range(nb):
                m = max(1, int(math.ceil(house / nb / HOUSE_MAX - 0.001)))
                for j in range(m):
                    pos, last = self._house_block(pos, house / nb / m, rng, last, gap=True,
                                                  sep=(j == m - 1 and b < nb - 1))
        else:
            n = max(1, int(math.ceil(house / HOUSE_MAX - 0.001)))
            for _j in range(n):
                pos, last = self._house_block(pos, house / n, rng, last)
        if bump:
            self._add(pos, pos + bump["dur"], "bump", p=bump["path"], o=0)
            pos += bump["dur"]
        if upnext:
            self._add(pos, end, "card", sub="next")
            pos = end
        if self.data["entries"] and pos < end:
            self.data["entries"][-1]["e"] = round(end, 3)
        return end

    def _house_block(self, pos, avail, rng, last=None, gap=False, sep=False):
        """One house break of `avail` seconds from pos: house ads, then the station
        ID card.  last: the ad the house break before it ended on (back to back at
        a programme's end), never repeated next.  gap: one of a long gap's breaks;
        sep: its last card ends that break (see _house_fill).  Returns (end, last ad)."""
        if self._retro_on():
            return self._retro_block(pos, avail, rng, last, gap, sep)
        n = max(0, int(math.ceil((avail - 10.0) / HOUSE_ITEM)))
        skip, promos_n = self._run_so_far()
        items = self._house_items(rng, n, skip=skip, max_promos=max(0, GAP_PROMOS - promos_n) if gap else None,
                                  last=last)
        if items and last is not None and len(items) > 1 and _house_key(items[0]) == last:
            items.append(items.pop(0))
        if items and last is not None and _house_key(items[0]) == last:
            items.pop(0)                 # the only one left: the ID card instead
        n = len(items)
        ln = min(HOUSE_ITEM, (avail - HOUSE_ID) / n) if n else 0
        while n and ln < HOUSE_ITEM_MIN:
            n -= 1
            ln = min(HOUSE_ITEM, (avail - HOUSE_ID) / n) if n else 0
        for it in items[:n]:
            last = _house_key(it)
            kind = it.pop("k")
            self._add(pos, pos + ln, kind, **it)
            pos += ln
        rest = avail - n * ln
        cards = max(1, int(math.ceil(rest / self.CARD_MAX)))
        for j in range(cards):
            self._add(pos, pos + rest / cards, "card", sub="id", sep=1 if sep and j == cards - 1 else None)
            pos += rest / cards
        return pos, last

    def _house_mix(self, t, room):
        """Settings > House breaks > Mix in with commercials: now and then one
        house ad (another channel's promo or a system ad) inside a break."""
        if int(self.cfg.get("house_breaks", HOUSE_NO_ADS)) != HOUSE_MIX or room < HOUSE_ITEM + 30 or \
                self.ch.get("type") not in PROMO_TYPES:
            return None
        hrng = random.Random("%s|%.0f|house" % (self.ch["id"], t))
        if hrng.random() >= 0.5:
            return None
        if self._retro_on() and hrng.random() < 0.5:
            it = self._retro_pick(t, hrng, (), (), self._prev_break_video())
            self._retro_count("placed" if it else "none")
            if it:
                it["dur"] = ads.length(it)
                return it
        items = self._house_items(hrng, 1, own=False)
        if not items:
            return None
        it = items[0]
        it["dur"] = HOUSE_ITEM
        return it

    # ------------------------------------------------------------- retro ads
    def _retro_on(self):
        """Settings > House breaks > Retro ads (cfg: the promo style, '' when off)."""
        return bool(self.cfg.get("retro_ads")) and self.ch.get("type") in PROMO_TYPES

    def _retro_recent(self, t):
        """Retro ads this channel aired in the last ads.RECENT seconds."""
        out = set()
        ents = self.data["entries"]
        for e in reversed(ents):
            if e["s"] < t - ads.RECENT:
                break
            if e.get("k") == "retro":
                out.add(ads.key(e))
        return out

    def _retro_movies(self, t):
        """Library movies a 'Now on videocassette' card may name at t: none that
        a channel airs in the next PROMO_LOOKAHEAD (its promos may name them)."""
        movies = ads.library_movies()
        if not movies:
            return []
        busy = set()
        chans = self.lineup.channels if self.lineup is not None else [self.ch]
        for c in chans:
            if c.get("type") not in PROMO_TYPES:
                continue
            try:
                s = self if c["id"] == self.ch["id"] else self.lineup.schedule(c, ensure=False)
                busy.update(b["t"] for b in s.blocks_between(t - 3600, t + PROMO_LOOKAHEAD))
            except Exception as exc:
                log("retro ads: %s %s" % (c.get("id"), exc))
        return [m for m in movies if m["label"] not in busy and m["title"] not in busy]

    def _retro_share(self, t, more=()):
        """(video-themed, all) retro ads on this channel in the ads.VIDEO_WINDOW
        before t, plus `more` (items of the break being planned)."""
        v = n = 0
        for e in reversed(self.data["entries"]):
            if e["s"] <= t - ads.VIDEO_WINDOW:      # the window is (t - 6 h, t), as retro_check counts it
                break
            if e.get("k") == "retro" and e["s"] < t:
                n += 1
                v += ads.is_video(e)
        for it in more:
            if it.get("k") == "retro":
                n += 1
                v += ads.is_video(it)
        return v, n

    def _prev_break_video(self):
        """Did this channel's break before the one being planned have a video-themed
        retro ad?  (Never two breaks in a row; back-to-back breaks at a programme's
        end are one break: the walk skips the whole run.)"""
        ents = self.data["entries"]
        prog = ("show", "clip", "offair")
        i = len(ents) - 1
        while i >= 0 and ents[i].get("k") not in prog and not ents[i].get("sep"):
            i -= 1                                           # the break being planned, so far
        if i < 0:
            return False
        if not ents[i].get("sep"):                           # (a long gap's card ends the break before)
            while i >= 0 and ents[i].get("k") in prog:       # the programme before it
                i -= 1
        while i >= 0 and ents[i].get("k") not in prog:       # the break before that
            if ents[i].get("k") == "retro" and ads.is_video(ents[i]):
                return True
            i -= 1
            if i >= 0 and ents[i].get("sep"):
                break
        return False

    def _retro_count(self, what):
        """Planning statistics (schedule state 'retro_stats', for retro_check.py):
        every turn the planner asks for a retro ad - placed, nothing fits (every
        ad that fits ran within 2 hours, or the caps), or an ad too long for the room left."""
        st = self.data["state"].setdefault("retro_stats", {})
        st["turns"] = st.get("turns", 0) + 1
        st[what] = st.get(what, 0) + 1

    def _retro_pick(self, t, rng, used, gags, brk_video=False, more=()):
        """brk_video: the break already has a video-themed ad; more: the retro ads
        planned in this break so far (not added yet)."""
        flav = ads.flavour(self.ch)
        movies = (lambda: self._retro_movies(t)) if flav != "K" else None
        want = not brk_video and ads.video_ok(flav, *self._retro_share(t, more))
        return ads.pick(rng, flav, t, self.cfg.get("retro_ads"), recent=self._retro_recent(t),
                        used=used, gags=gags, movies=movies, want_video=want)

    def _retro_videos(self, now):
        """A 'Now on videocassette' card never names a movie a promo in the same
        break names (the movie channel's next film is planned after its break):
        such a card names another library movie.  Returns True if any changed."""
        ents = self.data["entries"]
        changed = False
        start = 0
        for i in range(len(ents) + 1):
            if i < len(ents) and ents[i].get("k") not in ("show", "clip", "offair"):
                continue
            brk = ents[start:i]
            start = i + 1
            vids = [e for e in brk if e.get("k") == "retro" and e.get("ad") == "video" and e["s"] > now]
            if not vids:
                continue
            named = set(e.get("t") for e in brk if e.get("k") == "promo" and e.get("t"))
            for v in vids:
                if v.get("t") not in named:
                    continue
                taken = named | set(e.get("t") for e in brk if e.get("k") == "retro")
                recent = self._retro_recent(v["s"])
                movies = [m for m in self._retro_movies(v["s"])
                          if m["label"] not in taken and "V%s" % m["movieid"] not in recent]
                if movies:
                    m = random.Random("%s|%.0f|vid" % (self.ch["id"], v["s"])).choice(movies)
                    v.update(mv=m["movieid"], t=m["label"])
                else:
                    v.update(k="card", sub="id")          # nothing else to name: the station ID
                    for key in ("ad", "mv", "t", "ln"):
                        v.pop(key, None)
                changed = True
        return changed

    def _retro_block(self, pos, avail, rng, last=None, gap=False, sep=False):
        """A house break with retro ads: ad, house ad, ad, house ad... (a retro
        ad stays up for its jingle, a house ad 8-15 s), then the station ID card
        for the seconds left.  Like a real break, it opens on a commercial.  At
        most ads.per_break retro ads, and ads.per_run in a run of back-to-back breaks
        (one of a long gap's breaks: ads.per_gap_break in all of it, at most
        GAP_PROMOS promos, each system ad once in the gap)."""
        budget = avail - HOUSE_ID
        # house breaks back to back at a programme's end are one long break to the
        # viewer: running gags once in all of it, and the house ad the one before
        # ended on doesn't open this one
        gags, last_house, brk_video = set(), None, self._prev_break_video()
        run = 0                          # retro ads in the breaks before this one in the run
        in_break = True                  # still in this break (not past a long gap's "sep" card)
        for e in reversed(self.data["entries"]):
            if e.get("k") not in ("retro", "promo", "house", "card", "bump"):
                break                    # a programme
            if e.get("sep"):
                in_break = False         # the break before: only the house ad it ended on matters
            if in_break and e.get("k") == "retro":
                run += 1
                brk_video = brk_video or ads.is_video(e)
                if ads.gag(e):
                    gags.add(ads.gag(e))
            elif last_house is None and e.get("k") in ("promo", "house"):
                last_house = _house_key(e)
            if not in_break and last_house is not None:
                break
        skip, promos_n = self._run_so_far()
        house = self._house_items(rng, 6, skip=skip, max_promos=max(0, GAP_PROMOS - promos_n) if gap else None,
                                  last=last_house)
        if house and last_house is not None and len(house) > 1 and _house_key(house[0]) == last_house:
            house.append(house.pop(0))
        if house and last_house is not None and _house_key(house[0]) == last_house:
            house.pop(0)                 # the only one left: a retro ad or the ID card instead
        flav = ads.flavour(self.ch)
        if gap:                          # a long gap's break: retro ads before system ads and the ID card
            allowed = max(0, ads.per_gap_break(flav) - run)
        else:
            allowed = max(0, min(ads.per_break(flav), ads.per_run(flav) - run))
        seq, used, total, placed = [], set(), 0.0, 0
        want_retro, misses = True, 0
        while misses < 2:                # stop when neither kind fits any more
            ok = False
            if want_retro and placed >= allowed:
                pass                     # this break has its retro ads: house ads only (not a picker turn)
            elif want_retro:
                it = self._retro_pick(pos + total, rng, used, gags, brk_video, [x for x, _l in seq])
                ln = ads.length(it) if it else 0
                place = bool(it) and total + ln <= budget and (seq or last is None or _house_key(it) != last)
                self._retro_count("placed" if place else "none" if not it else
                                  "long" if total + ln > budget else "repeat")
                if place:
                    placed += 1
                    used.add(ads.key(it))
                    brk_video = brk_video or ads.is_video(it)
                    if ads.gag(it):
                        gags.add(ads.gag(it))
                    seq.append((it, ln))
                    total += ln
                    ok = True
            elif house and total + HOUSE_ITEM_MIN <= budget:
                ln = min(HOUSE_ITEM, budget - total)
                seq.append((house.pop(0), ln))
                total += ln
                ok = True
            misses = 0 if ok else misses + 1
            want_retro = not want_retro
        for it, ln in seq:
            last = _house_key(it)
            it = dict(it)
            kind = it.pop("k")
            self._add(pos, pos + ln, kind, **it)
            pos += ln
        rest = avail - total
        cards = max(1, int(math.ceil(rest / self.CARD_MAX)))
        for j in range(cards):
            self._add(pos, pos + rest / cards, "card", sub="id", sep=1 if sep and j == cards - 1 else None)
            pos += rest / cards
        return pos, last

    def _add_house(self, pos, it):
        it = dict(it)
        kind, dur = it.pop("k"), it.pop("dur")
        self._add(pos, pos + dur, kind, **it)
        return pos + dur

    def _cross_target(self, e, avoid=None):
        """(block, path) of another channel's programme a cross-channel promo at e
        names: planned there, starting 10 minutes to 6 hours after e, not the show
        this channel promoted last.  (None, None): nothing; None: not planned yet."""
        if self.lineup is None:
            return None, None
        ch = next((c for c in self.lineup.channels if c["id"] == e.get("xc")), None)
        if ch is None:
            return None, None
        other = self.lineup.schedule(ch, ensure=False)
        if other.data["until"] < e["s"] + 3 * 3600:
            return None
        if avoid is None:                # at air time: the promo before it
            avoid = set()
            ents = self.data["entries"]
            j = bisect.bisect_left(self._starts, e["s"] - 0.001) - 1
            while j >= 0 and ents[j]["s"] > e["s"] - 2 * 3600:
                if ents[j].get("k") == "promo" and ents[j].get("t"):
                    avoid.add(ents[j]["t"])
                    break
                j -= 1
            avoid |= self.gap_avoid(e)
        shows = [b for b in other.blocks_between(e["s"] + 600, e["s"] + PROMO_LOOKAHEAD)
                 if b.get("k") == "show" and b["s"] >= e["s"] + 600 and b["t"] not in avoid]
        if not shows:
            return None, None
        pick = random.Random("%s|%.0f|xtgt" % (self.ch["id"], e["s"])).choice(shows)
        path = None
        oents = other.data["entries"]
        j = bisect.bisect_left(other._starts, pick["s"] - 0.001)
        while j < len(oents) and oents[j]["s"] < pick["e"]:
            if oents[j].get("k") == "show" and oents[j].get("p"):
                path = oents[j]["p"]
                break
            j += 1
        return pick, path

    # ------------------------------------------------------------- promos
    def _promo_for_break(self, t, room):
        """At most one promo per break (Settings > Programming > Promos).  The
        viewer's own clips in the station folder's promos/ win; otherwise a
        promo card for what this channel airs next, decided once the
        schedule after this break is known (_resolve_promos).  Uses its own
        random numbers, so with promos off breaks come out exactly as before."""
        cfg = self.cfg
        if not cfg.get("promos") or self.ch.get("type") not in PROMO_TYPES:
            return None
        if room < promos.PROMO_LEN + 10:
            return None
        prng = random.Random("%s|%.0f|promo" % (self.ch["id"], t))
        if prng.random() >= PROMO_RATES[min(max(int(cfg.get("promo_every", 1)), 0), len(PROMO_RATES) - 1)]:
            return None
        own = []
        try:
            f = stations.clip_folder(self.ch, t, "promos")
            own = [c for c in library.filler_pool(f) if c["dur"] <= room - 5] if f else []
        except Exception as exc:
            log("station promos %s: %s" % (self.ch.get("name"), exc))
        if own:
            c = prng.choice(own)
            return {"dur": float(c["dur"]), "path": c["path"], "title": c.get("title")}
        return {"dur": promos.PROMO_LEN}

    def _add_promo(self, pos, promo):
        if promo.get("path"):    # the viewer's own promo clip: a video like any spot
            self._add(pos, pos + promo["dur"], "ad", p=promo["path"], o=0, t=promo.get("title"), pr="own")
        else:
            self._add(pos, pos + promo["dur"], "promo")
        return pos + promo["dur"]

    def _final_break(self, e, cur):
        """True when the break e airs in is the last one of its programme:
        nothing but breaks and IDs between it and the next programme."""
        if cur is None:
            return True
        ents = self.data["entries"]
        j = bisect.bisect_right(self._starts, e["s"])
        while j < len(ents) and ents[j]["s"] < cur["e"] - 0.05:
            if ents[j].get("k") == "show":
                return False
            j += 1
        return True

    def _prev_promo_title(self, e, cur):
        """Title of the card promo before e in the same programme, if any."""
        if cur is None:
            return None
        ents = self.data["entries"]
        j = bisect.bisect_left(self._starts, e["s"] - 0.001) - 1
        while j >= 0 and ents[j]["s"] >= cur["s"] - 0.05:
            p = ents[j]
            if p.get("k") == "promo":
                if "pt" in p:
                    return p.get("t")
                tgt = self.promo_target(p)
                return tgt[0]["t"] if tgt and tgt[0] else None
            j -= 1
        return None

    def promo_target(self, e, avoid=None, house=False):
        """(block, programme path) a promo airing at e should name; (None, None)
        when there is nothing to promote; None while the schedule after it isn't
        planned yet.  Only ever this channel's own programmes.
        Promote (promo_target): 0 what's on next, 1 something later today,
        2 both - the break that ends a programme says 'Up next', the breaks
        inside it promote something later today."""
        d = self.data
        span = PROMO_LOOKAHEAD
        planned = d["until"] >= e["s"] + span
        cur = self.block_at(e["s"])
        shows = [b for b in self.blocks_between(e["s"], e["s"] + span)
                 if b["s"] > e["s"] and b.get("k") == "show"]
        nb = self.next_block(e["s"])
        pick = None
        mode = self.cfg.get("promo_target", 2)
        if house:
            mode = 2                     # house promos: something later today; 'Up next' is the card's job
        if mode == 2 and (house or not self._final_break(e, cur)):
            if d["until"] < e["s"] + 3 * 3600:      # pick from at least the next three hours
                return None
            # a mid-programme break: something later today, not the show we're
            # in, not the next programme (that's the last break's 'Up next') and
            # not the show this programme's previous promo named
            skip = {cur["t"]} if cur else set()
            prev = self._prev_promo_title(e, cur)
            if prev:
                skip.add(prev)
            skip |= set(avoid or ())
            pool = [b for b in shows if b is not nb and b["t"] not in skip]
            pool = [b for b in pool if not (nb and b["t"] == nb["t"])] or pool
            if pool:
                pick = random.Random("%s|%.0f|ptgt" % (self.ch["id"], e["s"])).choice(pool)
            else:
                mode = 0                 # nothing else today: promote the next programme
        if pick is None and mode == 1:
            if d["until"] < e["s"] + 3 * 3600:      # pick from at least the next three hours
                return None
            # something later today: not the show we're in the middle of
            pool = [b for b in shows if not (cur and b["t"] == cur["t"])] or shows
            pool = [b for b in pool if b["t"] not in (avoid or ())] or pool
            if pool:
                pick = random.Random("%s|%.0f|ptgt" % (self.ch["id"], e["s"])).choice(pool)
        elif pick is None:
            if nb is None and not planned:
                return None
            if nb is not None and nb.get("k") == "show":
                pick = nb
            elif shows:
                pick = shows[0]          # off the air / a card next: the next real programme
            elif not planned:
                return None
        if pick is None:
            return None, None
        path = None
        ents = d["entries"]
        j = bisect.bisect_left(self._starts, pick["s"] - 0.001)
        while j < len(ents) and ents[j]["s"] < pick["e"]:
            if ents[j].get("k") == "show" and ents[j].get("p"):
                path = ents[j]["p"]
                break
            j += 1
        return pick, path

    def _resolve_promos(self, now):
        """Name the programme each planned promo is for, once that's known.
        In time order, so a house break's promo never names the show the promo
        before it named (the promo-mix rule); Extras clips swap in afterwards."""
        ents = self.data["entries"]
        touched = False
        prev = None                      # (title, time) of the last promo named
        extras = []
        for i, e in enumerate(ents):
            if e.get("k") != "promo":
                continue
            if "pt" not in e:
                avoid = {prev[0]} if prev and e["s"] - prev[1] < 2 * 3600 else set()
                ga, gb = self._gap_bounds(i)
                if e.get("h"):
                    avoid |= self._gap_avoid(i, ga, gb)
                signon = self._signon_slot(i, ga, gb, avoid) if e.get("h") else None
                special = None if signon else self._special_promo(e, avoid)
                if signon:
                    e.pop("xc", None)            # the last promo before sign-off: tomorrow's first show
                    tgt = signon
                elif special:
                    tgt = special                # a special in the days ahead: 'Thursday, all day'
                elif e.get("xc"):
                    tgt = self._cross_target(e, avoid | self._own_titles_after(i))
                    if tgt is not None and tgt[0] is None and e.get("h"):
                        # nothing fresh on that channel: another channel's, or one of ours
                        tgt = self._house_cross_for(e, avoid) or self._own_fresh(e, avoid) or tgt
                elif e.get("h"):
                    tgt = self.promo_target(e, avoid, house=True)
                    nb = self.next_block(e["s"])
                    if tgt and tgt[0] is not None and (tgt[0] is nb or tgt[0]["t"] in avoid):
                        # nothing else here to promote, and the 'Up next' card before the
                        # next programme names it anyway - or it's the show the promo before
                        # named (a marathon: nothing else for hours): another channel's show
                        alt = self._house_cross_for(e, avoid | ({nb["t"]} if nb else set()))
                        if alt:
                            tgt = alt
                        elif tgt[0]["t"] in avoid:
                            tgt = (None, None)   # never the same show twice in a row: the station ID card
                else:
                    tgt = self.promo_target(e)
                if tgt is None:
                    continue
                b, path = tgt
                touched = True
                if b is None:
                    if e.get("h"):
                        # nothing fresh to name: a retro ad, a system ad the gap hasn't
                        # run, or the station ID card - never a promo repeated to fill
                        if self._gap_filler(i, ga, gb, now):
                            self._index()
                    else:
                        e["pt"] = 0          # nothing to promote: the station ID card
                    continue
                e.update(pt=b["s"], t=b["t"])
                if b.get("sp"):
                    e.update(sp=b["sp"], pe=b["e"])
                if path:
                    e["pp"] = path
                if b.get("sub"):
                    e["sub"] = b["sub"]
                if e.get("xc") or b is not self.next_block(e["s"]):
                    e["pw"] = "later"
                if self.cfg.get("promo_extras") and path and e["s"] > now + 30 and not e.get("xc") \
                        and not b.get("sp"):
                    extras.append((i, path, b))
            if e.get("t"):
                prev = (e["t"], e["s"])
        for i, path, b in reversed(extras):  # from the end: swaps don't move earlier entries
            if self._extras_promo(i, path, b):
                self._index()
        if self._retro_videos(now):
            touched = True
        if touched:
            self._index()
        return touched

    def _special_promo(self, e, avoid):
        """(block-like, path) when the promo slot e names a special instead of a
        programme: one on this channel (or on the channel a cross-channel promo is
        for) that starts within SPECIAL_PROMO_DAYS and hasn't begun; a share of the
        slots (SPECIAL_PROMO_RATES), never the break before the next programme
        ('Up next' stays), never a name in `avoid`.  The block-like has the
        special's start, end, name, id and what it airs; path: one of its
        programmes, for the card's picture.  None otherwise (always, without
        calendar.json)."""
        every = all_specials()
        if not every or self.lineup is None:
            return None
        if not e.get("xc") and not e.get("h") and self.cfg.get("promo_target", 2) != 1 and \
                self._final_break(e, self.block_at(e["s"])):
            return None
        got, had = self._special_promo_for(e, avoid, every, e.get("xc") or self.ch["id"], 1.0,
                                           "%s|%.0f|special" % (self.ch["id"], e["s"]))
        if got is not None or had or e.get("xc") or e.get("h"):
            return got
        # A plain promo slot (Promos on, House breaks off) on a channel with no special
        # coming: another channel's special, at SPECIAL_CROSS_SHARE of the rate, so
        # specials get cross-channel promos with or without House breaks.  (House
        # breaks plan their own cross-channel slots, xc, which come in above.)
        rng = random.Random("%s|%.0f|xspecial" % (self.ch["id"], e["s"]))
        others = sorted({b.get("channel") for sp in every for b in sp.get("blocks") or ()
                         if b.get("channel") != self.ch["id"]}, key=str)
        rng.shuffle(others)
        for cid in others:
            got, had = self._special_promo_for(e, avoid, every, cid, SPECIAL_CROSS_SHARE,
                                               "%s|%.0f|xspecial|%s" % (self.ch["id"], e["s"], cid))
            if got is not None:
                e.update(xc=cid, xs=1)       # xs: cut() turns it back into a plain slot
                return got
            if had:
                return None
        return None

    def _special_promo_for(self, e, avoid, every, cid, share, seed):
        """(_special_promo's answer for one channel's specials, whether that channel
        has one coming that the slot could have named).  share: of the rate."""
        ch = next((c for c in self.lineup.channels if c["id"] == cid), None)
        if ch is None or (cid != self.ch["id"] and ch.get("type") not in PROMO_TYPES):
            return None, False
        off = specials_shift(self.cfg)
        t = e["s"]
        day = datetime.date.fromtimestamp(t + off)
        for st, en, sp, blk in specials.between(every, t + off, t + off + (SPECIAL_PROMO_DAYS + 1) * 86400, cid):
            ahead = (datetime.date.fromtimestamp(st) - day).days
            if st - off < t + 600 or ahead > SPECIAL_PROMO_DAYS or sp["name"] in avoid:
                continue
            rate = SPECIAL_PROMO_RATES[min(ahead, len(SPECIAL_PROMO_RATES) - 1)] * share
            if random.Random(seed).random() >= rate:
                return None, True
            try:
                other = self if cid == self.ch["id"] else self.lineup.schedule(ch, ensure=False)
                pool = other._special_pool(blk)
            except Exception as exc:
                log("promo for %s: %s" % (sp.get("name"), exc))
                return None, True
            series, singles = pool["series"], pool["singles"]
            if not series and not singles:
                continue                         # nothing to air (no holiday episodes): nothing to promote
            names = [s["title"] for s in series] + ([singles[0]["title"]] if singles and not series else [])
            path = series[0]["episodes"][0]["path"] if series else singles[0]["path"]
            return ({"s": st - off, "e": en - off, "t": sp["name"], "sp": sp["id"],
                     "sub": ", ".join(names[:3])}, path), True
        return None, False

    def _house_cross_for(self, e, avoid):
        """Turn a house promo into a promo for another channel's show (sets its
        xc); None if no other channel has anything to promote."""
        # not a channel this house break already promotes
        used, ents = set(), self.data["entries"]
        i = bisect.bisect_left(self._starts, e["s"] - 0.001)
        for step in (-1, 1):
            j = i + step
            while 0 <= j < len(ents) and ents[j]["k"] != "show" and                     not (ents[j]["k"] == "card" and ents[j].get("sub") == "id"):
                if ents[j].get("xc"):
                    used.add(ents[j]["xc"])
                j += step
            # nor the one the house break before ended on / the one after starts with
            # (back to back at a programme's end: never the same ad either side of a card)
            # (cards and retro ads between - a long gap's break may have no house ad at
            # all - so the house ad behind them counts)
            while 0 <= j < len(ents) and ents[j]["k"] in ("card", "retro", "bump") and not ents[j].get("h"):
                j += step
            if 0 <= j < len(ents) and ents[j].get("h") and ents[j].get("xc"):
                used.add(ents[j]["xc"])
        others = [c for c in self._house_others() if c["id"] not in used]
        random.Random("%s|%.0f|xalt" % (self.ch["id"], e["s"])).shuffle(others)
        for c in others:
            tgt = self._cross_target(dict(e, xc=c["id"]), avoid)
            if tgt and tgt[0]:
                e["xc"] = c["id"]
                return tgt
        return None

    def _own_fresh(self, e, avoid):
        """One of this channel's later shows for a house promo slot (dropping its
        xc), not in avoid and not the next programme; None if there's none."""
        tgt = self.promo_target(e, avoid, house=True)
        if not tgt or tgt[0] is None or tgt[0]["t"] in avoid or tgt[0] is self.next_block(e["s"]):
            return None
        e.pop("xc", None)
        return tgt

    def _gap_bounds(self, i):
        """(first, last) entry index of the gap entry i is in: the run of
        back-to-back breaks between two programmes."""
        ents = self.data["entries"]
        a = i
        while a > 0 and ents[a - 1].get("k") in BREAK_KINDS:
            a -= 1
        b = i
        while b + 1 < len(ents) and ents[b + 1].get("k") in BREAK_KINDS:
            b += 1
        return a, b

    def _signon(self, a, b):
        """(block, path) of the programme after the off-air hours the gap a..b
        leads into ('tomorrow at 5:00'), None if it isn't followed by off-air."""
        ents = self.data["entries"]
        if b + 1 >= len(ents):
            return None
        off = self.block_at(ents[b + 1]["s"] + 0.5)
        if not off or off.get("k") != "offair":
            return None
        shows = [x for x in self.blocks_between(off["e"] - 1, off["e"] + PROMO_LOOKAHEAD)
                 if x.get("k") == "show" and x["s"] >= off["e"] - 1]
        if not shows:
            return None
        pick = min(shows, key=lambda x: x["s"])
        return pick, self._block_path(pick)

    def _block_path(self, pick):
        ents = self.data["entries"]
        j = bisect.bisect_left(self._starts, pick["s"] - 0.001)
        while j < len(ents) and ents[j]["s"] < pick["e"]:
            if ents[j].get("k") == "show" and ents[j].get("p"):
                return ents[j]["p"]
            j += 1
        return None

    @staticmethod
    def _last_promo(ents, a, b):
        return max([k for k in range(a, b + 1) if ents[k].get("k") == "promo"] or [-1])

    def _gap_avoid(self, i, a, b):
        """Shows a house promo at entry i (gap a..b) may not name: one the gap
        names within GAP_PROMO_SPACING, or GAP_PROMO_MAX times already; before
        off-air, tomorrow's first show once it's named (again only last)."""
        ents = self.data["entries"]
        e = ents[i]
        named = [(x["t"], x["s"]) for k, x in enumerate(ents[a:b + 1], a)
                 if k != i and x.get("k") == "promo" and x.get("t")]
        avoid = set(t for t, s in named if abs(s - e["s"]) < GAP_PROMO_SPACING)
        cnt = {}
        for t, _s in named:
            cnt[t] = cnt.get(t, 0) + 1
        avoid |= set(t for t, c in cnt.items() if c >= GAP_PROMO_MAX)
        so = self._signon(a, b)
        if so:
            t = so[0]["t"]
            if cnt.get(t, 0) >= OFFAIR_PROMOS or (cnt.get(t) and i != self._last_promo(ents, a, b)):
                avoid.add(t)
        return avoid

    def gap_avoid(self, e):
        """_gap_avoid for a planned entry (the TV naming a promo on air)."""
        ents = self.data["entries"]
        i = bisect.bisect_left(self._starts, e["s"] - 0.001)
        while i < len(ents) and ents[i]["s"] < e["s"] + 0.001:
            if ents[i] is e or ents[i] == e:
                a, b = self._gap_bounds(i)
                return self._gap_avoid(i, a, b)
            i += 1
        return set()

    def _signon_slot(self, i, a, b, avoid):
        """The last promo slot before sign-off names tomorrow's first show
        (unless the gap named it within GAP_PROMO_SPACING or twice already)."""
        ents = self.data["entries"]
        if i != self._last_promo(ents, a, b):
            return None
        so = self._signon(a, b)
        if not so or so[0]["t"] in avoid:
            return None
        return so

    def _gap_filler(self, i, a, b, now):
        """A house promo slot with nothing fresh to name: a retro ad (a long gap,
        retro ads on), else a system ad the gap hasn't run, else the station ID
        card.  True if entries moved (a retro ad's own length)."""
        ents = self.data["entries"]
        e = ents[i]
        if e["s"] > now + 120:
            if self._retro_on() and any(ents[k].get("sep") for k in range(a, b + 1)) and \
                    self._gap_retro(i, a, b):
                return True
            used = set(x.get("h") for x in ents[a:b + 1] if x.get("k") == "house")
            free = [s for s in self._house_systems() if s not in used]
            if free:
                rng = random.Random("%s|%.0f|gfill" % (self.ch["id"], e["s"]))
                e.pop("xc", None)
                e.update(k="house", h=rng.choice(free), ln=rng.randrange(3))
                return False
        e["pt"] = 0
        return False

    def _gap_retro(self, i, a, b):
        """Put a retro ad in promo slot i of a long gap (ads.per_gap_break, the
        2-hour rule, no gag or ad twice in its break, nothing video-themed); the
        station ID card that ends its house break takes up the difference."""
        ents = self.data["entries"]
        e = ents[i]
        lo = i
        while lo > a and not ents[lo - 1].get("sep"):
            lo -= 1
        hi = i
        while hi < b and not ents[hi].get("sep"):
            hi += 1
        brk = ents[lo:hi + 1]
        flav = ads.flavour(self.ch)
        rs = [x for x in brk if x.get("k") == "retro"]
        if len(rs) >= ads.per_gap_break(flav):
            return False
        c = i + 1
        while c <= hi and not (ents[c].get("k") == "card" and ents[c].get("sub") == "id"):
            c += 1
        if c > hi:
            return False
        card = ents[c]["e"] - ents[c]["s"]
        slot = e["e"] - e["s"]
        j0 = bisect.bisect_left(self._starts, e["s"] - ads.RECENT)
        j1 = bisect.bisect_right(self._starts, e["s"] + ads.RECENT)
        recent = set(ads.key(x) for x in ents[j0:j1] if x.get("k") == "retro")
        used = set(ads.key(x) for x in rs)
        gags = set(ads.gag(x) for x in rs if ads.gag(x))
        rng = random.Random("%s|%.0f|gretro" % (self.ch["id"], e["s"]))
        for _try in range(4):
            it = ads.pick(rng, flav, e["s"], self.cfg.get("retro_ads"), recent=recent, used=used,
                          gags=gags, movies=None, want_video=False)
            if not it:
                return False
            ln = ads.length(it)
            if card - (ln - slot) >= self.CARD_MIN:
                break
            used.add(ads.key(it))
        else:
            return False
        delta = ln - slot
        for k in range(i + 1, c):       # a retro ad that moves keeps the 2-hour rule too
            x = ents[k]
            if x.get("k") == "retro" and delta:
                ns, key = x["s"] + delta, ads.key(x)
                k0 = bisect.bisect_left(self._starts, ns - ads.RECENT - 1)
                k1 = bisect.bisect_right(self._starts, ns + ads.RECENT + 1)
                if any(y is not x and y.get("k") == "retro" and ads.key(y) == key and
                       abs(y["s"] - ns) < ads.RECENT + 0.5 for y in ents[k0:k1]):
                    return False
        new = dict(it)
        new.update(s=round(e["s"], 3), e=round(e["s"] + ln, 3))
        ents[i] = new
        for k in range(i + 1, c):
            ents[k]["s"] = round(ents[k]["s"] + delta, 3)
            ents[k]["e"] = round(ents[k]["e"] + delta, 3)
        ents[c]["s"] = round(ents[c]["s"] + delta, 3)
        rest = ents[c]["e"] - ents[c]["s"]
        if rest > self.CARD_MAX:         # a long card: two
            half = round(ents[c]["s"] + rest / 2, 3)
            second = dict(ents[c], s=half)
            ents[c]["e"] = half
            if ents[c].get("sep"):
                ents[c].pop("sep")       # the break still ends on the last card
            ents.insert(c + 1, second)
        return True

    def _own_titles_after(self, i):
        """Shows this channel's own promos later in the same break will name."""
        out = set()
        ents = self.data["entries"]
        j = i + 1
        while j < len(ents) and ents[j].get("k") != "show":
            p = ents[j]
            if p.get("k") == "promo" and not p.get("xc"):
                t = p.get("t")
                if not t and "pt" not in p:
                    tgt = self.promo_target(p, house=bool(p.get("h")))
                    t = tgt[0]["t"] if tgt and tgt[0] else None
                if t:
                    out.add(t)
            j += 1
        return out

    def _extras_promo(self, i, path, b):
        """Settings' promo_extras (on by default): a short 'Promo' / 'Trailer' video from the show's Extras
        folder airs instead of the card, now and then.  It takes the card's
        place and as much of the spots after it as it needs; a spot it runs
        into starts from the top and is cut off, like a late switch-over."""
        e = self.data["entries"][i]
        prng = random.Random("%s|%.0f|pextra" % (self.ch["id"], e["s"]))
        try:
            clips = [c for c in promos.extras_promos(path, b["t"]) if c["dur"] >= promos.PROMO_LEN - 3]
        except Exception as exc:
            log("extras promos: %s" % exc)
            return False
        if not clips or prng.random() >= 0.5:
            return False
        ents = self.data["entries"]
        clip = prng.choice(clips)
        s0 = e["s"]
        x = s0 + clip["dur"]
        j, room_end = i + 1, e["e"]
        while j < len(ents) and ents[j].get("k") == "ad" and abs(ents[j]["s"] - room_end) < 0.05 \
                and room_end < x:
            room_end = ents[j]["e"]
            j += 1
        if room_end < x:
            return False                 # not enough of the break left for it
        k, new_end = i + 1, max(x, e["e"])
        while k < j and ents[k]["e"] <= x + 3:
            new_end = max(new_end, ents[k]["e"])
            k += 1
        repl = [{"s": s0, "e": round(new_end, 3), "k": "ad", "p": clip["path"], "o": 0,
                 "t": clip["title"], "pr": "extras", "pt": e.get("pt")}]   # pt: for cut()
        if k < j and ents[k]["s"] < new_end - 0.05:
            repl.append(dict(ents[k], s=round(new_end, 3), o=0))
            k += 1
        ents[i:k] = repl
        return True

    def _next_episode(self, ser, ptr_key):
        eps = ser["episodes"]
        last = self._bm_get(ptr_key)
        self._rerun_pick = None
        when = getattr(self, "_season_t", None)
        if when is not None and last and not ptr_key.startswith("rule:") and                 rerun_channel(self.ch, self.cfg) and rerun_season(when, self.cfg):
            ep = self._rerun_episode(eps, ptr_key, last, when)
            if ep is not None:
                self._rerun_pick = (ptr_key, ep["path"])
                return ep
        idx = 0
        if last:
            for i, e in enumerate(eps):
                if e["path"] == last:
                    idx = (i + 1) % len(eps)
                    break
            else:
                # the bookmarked file has left the library (deleted, renamed, a new
                # copy): go on after the same season/episode, not from the start
                k = _episode_order(bookmarks.label_of(last))
                if k is not None:
                    idx = next((i for i, e in enumerate(eps)
                                if (_episode_order(e.get("label")) or k) > k), 0)
        when = getattr(self, "_season_t", None)
        # skip files Kodi couldn't open lately, files the library lists that aren't
        # there (renamed or deleted since the last Clean library), and (automatic
        # programming only) holiday episodes outside their season
        for k in range(len(eps)):
            e = eps[(idx + k) % len(eps)]
            if library.is_bad(e["path"]) or library.stale(e["path"]):
                continue
            if when is not None and seasons.out_of_season(e, when, self.cfg):
                continue
            return e
        return eps[idx]

    def _rerun_episode(self, eps, ptr_key, last, when):
        """Summer reruns (automatic programming only, never a pinned slot): the next
        episode, in order, of the season the series is in, up to the last that aired;
        round again from the season's start.  None: nothing to rerun (airs normally)."""
        last_i = next((i for i, e in enumerate(eps) if e["path"] == last), None)
        rng = rerun_range(eps, last_i)
        if not rng:
            return None
        prev = self._bm_get(ptr_key + RERUN_SUFFIX)
        pos = next((k for k, j in enumerate(rng) if eps[j]["path"] == prev), None)
        start = 0 if pos is None else (pos + 1) % len(rng)
        for k in range(len(rng)):
            e = eps[rng[(start + k) % len(rng)]]
            if library.is_bad(e["path"]) or library.stale(e["path"]):
                continue
            if seasons.out_of_season(e, when, self.cfg):
                continue
            return e
        return None

    def _pick_rule(self, pool, t, rule):
        """Programme for a pinned slot.  'inorder' continues each series where
        that slot left off (its own bookmark), rotating between shows if the
        slot has several; 'random' picks any episode/movie."""
        series, singles = pool["series"], pool["singles"]
        if not series and not singles:
            return None
        rid = "rule:%s" % rule.get("id", "")
        st = self.data["state"]
        if rule.get("order", "inorder") == "random":
            rng = random.Random("%s|%.0f|%s" % (self.ch["id"], t, rid))
            every = [e for ser in series for e in ser["episodes"]] + singles
            every = [e for e in every if not library.is_bad(e["path"])] or every
            self._cont = ("singles", every, None)
            it = rng.choice(every)
            while library.stale(it["path"]):
                every = [e for e in every if e is not it]
                if not every:
                    self._cont = None
                    return None
                it = rng.choice(every)
            return it
        shows = [("s", ser) for ser in series] + ([("m", None)] if singles else [])
        rr = st.setdefault("rr", {})
        i = rr.get(rid, 0) % len(shows)
        self._undo("rr", rid, rr.get(rid, 0))
        rr[rid] = i + 1
        kind, ser = shows[i]
        if kind == "s":
            ep = self._next_episode(ser, rid + "|" + ser["key"])
            if library.stale(ep["path"]):
                return None                  # every episode's file is missing
            self._bm_set(rid + "|" + ser["key"], ep["path"], ep.get("label"))
            self._cont = ("series", ser, rid + "|" + ser["key"])
            return ep
        self._cont = ("singles", singles, None)
        ep = self._next_episode({"episodes": singles}, rid + "|movies")
        if library.stale(ep["path"]):
            return None
        self._bm_set(rid + "|movies", ep["path"])
        return ep

    def _pick(self, pool, t, key, maxdur=None):
        series, singles = pool["series"], pool["singles"]
        if maxdur is not None:
            # Only shows whose next episode ends before the next pinned slot.
            series = [ser for ser in series
                      if self._next_episode(ser, ser["key"])["dur"] <= maxdur]
            singles = [it for it in singles if it["dur"] <= maxdur]
        if not series and not singles:
            return None
        if self.cfg.get("shorts_mode", 0) == SHORTS_PINNED_ONLY:
            # Shorts only where the viewer put them: skip them while there's
            # anything longer to air (a channel made only of shorts still runs them).
            thr = self.short_limit()
            ls = [ser for ser in series if self._next_episode(ser, ser["key"])["dur"] > thr]
            lg = [it for it in singles if it["dur"] > thr]
            if ls or lg:
                series, singles = ls, lg
        cands = [(s, math.sqrt(min(len(s["episodes"]), 60))) for s in series]
        if singles:
            cands.append((None, math.sqrt(min(len(singles), 60)) * (2 if not series else 1)))
        if self.ch.get("lineup", "strip") == "strip":
            tod, wd = local_tod(t)
            dtype = "wd" if wd < 5 else str(wd)
            seed = "%s|%s|%s|%d" % (self.ch["id"], key, dtype, int(tod // 60))
        else:
            seed = "%s|%s|%.0f" % (self.ch["id"], key, t)
        rng = random.Random(seed)
        total = sum(w for _, w in cands)
        x = rng.random() * total
        choice = cands[-1][0]
        for c, w in cands:
            x -= w
            if x <= 0:
                choice = c
                break
        st = self.data["state"]
        if choice is not None:
            ep = self._next_episode(choice, choice["key"])
            if library.stale(ep["path"]):
                # every episode the library lists for it is a missing file: the others
                rest = {"series": [s for s in series if s is not choice], "singles": singles}
                return self._pick(rest, t, key, maxdur)
            self._bm_set(choice["key"], ep["path"], ep.get("label"))
            self._cont = ("series", choice, choice["key"])
            return ep
        self._cont = ("singles", singles, key)
        recent = st["recent"].setdefault(key, [])
        keep = min(len(singles) // 2, 200)
        avoid = set(recent[-keep:]) if keep else set()
        singles = [s for s in singles if not library.is_bad(s["path"])] or singles
        when = getattr(self, "_season_t", None)
        if when is not None:
            singles = [s for s in singles if not seasons.out_of_season(s, when, self.cfg)] or singles
        fresh = [s for s in singles if s["path"] not in avoid] or singles
        r2 = random.Random("%s|%.0f|single" % (self.ch["id"], t))
        it = r2.choice(fresh)
        while library.stale(it["path"]):     # checked one pick at a time: a big movie list isn't stat'ed whole
            fresh = [s for s in fresh if s is not it]
            if not fresh:
                self._cont = None
                return self._pick({"series": series, "singles": []}, t, key, maxdur) if series else None
            it = r2.choice(fresh)
        recent.append(it["path"])
        self._undo("ra", key, it["path"])
        del recent[:-max(keep, 1)]
        return it


class Lineup(object):
    """All channels + their schedules."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.channels = chmod.load()
        self.sched = {}
        self.lock = threading.RLock()   # one schedule build at a time (TV + background builder)
        self.assignment = assign.load()  # one home channel per show (assign.py)

    def reload_channels(self):
        self.channels = chmod.load()
        ids = set(c["id"] for c in self.channels)
        for cid in list(self.sched):
            if cid not in ids:
                del self.sched[cid]
        for c in self.channels:
            if c["id"] in self.sched:
                self.sched[c["id"]].ch = c

    def by_number(self, n):
        for c in self.channels:
            if c["number"] == n:
                return c
        return None

    def schedule(self, ch, ensure=True, now=None):
        s = self.sched.get(ch["id"])
        if s is None:
            s = self.sched[ch["id"]] = ChannelSchedule(ch, self.cfg)
            s.lineup = self
        if ensure:
            if not bookmarks.exists():
                self.migrate(now)
            try:
                if s.needs_work(now):
                    with self.lock:
                        if s.data["entries"] and s.data["hash"] != s.full_hash():
                            # the other Kodi process may have worked out new homes
                            # already (and planned with them): use those first
                            self.assignment = assign.load() or self.assignment
                            if s.data["hash"] != s.full_hash():
                                self.cut_changed(now)
                        s.ensure(now)
            except Exception as exc:
                log("Schedule build failed for %s: %s" % (ch.get("name"), exc))
        return s

    def cut_changed(self, now=None, every=False):
        """Cut every changed channel (every channel, with every=True) after what's
        on air, all of them before any is planned again: a show that moved from one
        channel to another gets its bookmark back from the old one first.  The
        channels' hashes are brought up to date, so ensure() just plans on."""
        now = now or time.time()
        with self.lock:
            n = self.drop_removed(now)
            for c in self.channels:
                s = self.schedule(c, ensure=False)
                s.reload()
                h = s.full_hash()
                if not s.data["entries"] or (s.data["hash"] == h and not every):
                    continue
                if s.data["until"] >= now:
                    s.cut(now)
                s.data["hash"] = h
                s.save()
                n += 1
            return n

    def drop_removed(self, now=None):
        """Schedules of channels no longer in the lineup: cut first (the bookmarks
        their plans moved go back to what aired, so a show that moves on continues
        from there), then deleted."""
        now = now or time.time()
        ids = set(c["id"] for c in self.channels)
        try:
            names = [f for f in os.listdir(SCHEDULE_DIR) if f.endswith(".json") and f[:-5] not in ids]
        except OSError:
            return 0
        with self.lock:
            for f in names:
                s = ChannelSchedule({"id": f[:-5], "type": "network"}, self.cfg)
                s.lineup = self
                try:
                    if "undo" in s.data and s.data["until"] >= now:
                        s.cut(now)
                        bookmarks.flush()
                    os.remove(s.path)
                except Exception as exc:
                    log("Removed channel %s: %s" % (f, exc))
        return len(names)

    def refresh(self, now=None, progress=None, stage=None):
        """Refresh schedules, keep my place: settings, channels and clips as they are
        now apply from the end of each channel's programme on air; what's on air and
        every show's next episode stay.  progress(i, n, channel) is called per
        channel, stage("assign") before the home channels are worked out (the slow
        part before the first channel).  Returns how long it took (s)."""
        skip_short_begin()
        t0 = time.time()
        now = now or t0
        library.new_generation()             # the library and station clips as they are now,
        stations.clear_cache()               # in every Kodi process
        with self.lock:
            self.reload_channels()
            if stage:
                stage("assign")
            self.refresh_assignment()
            if not bookmarks.exists():
                self.migrate(now)
            n = self.cut_changed(now, every=True)
            for i, c in enumerate(self.channels):
                if progress:
                    progress(i, len(self.channels), c)
                try:
                    self.schedule(c, ensure=False).ensure(now)
                except Exception as exc:
                    log("Schedule build failed for %s: %s" % (c.get("name"), exc))
        took = time.time() - t0
        log("Refresh schedules: %d channels from the end of what's on air, %.1f s" % (n, took),
            level=xbmc.LOGINFO)
        skip_short_save()
        return took

    def reset_progress(self, kind, value=None, progress=None):
        """Start series over: kind 'all', 'channel' (value: its id - the shows whose
        home it is, its own runs and its pinned slots) or 'show' (value: the show's
        title, wherever it airs).  Everything after what's on air is cut first, then
        those bookmarks go back to the first episode and the plan is made again."""
        now = time.time()
        with self.lock:
            self.reload_channels()
            self.refresh_assignment()
            if not bookmarks.exists():
                self.migrate(now)
            self.cut_changed(now, every=True)
            home = (self.assignment or {}).get("home") or {}

            def chosen(key, cid):
                show = key.split("|", 1)[-1]         # 'rule:<id>|tv:Title' -> 'tv:Title'
                if kind == "all":
                    return True
                if kind == "show":
                    return show == "tv:%s" % value
                return cid == value
            if kind == "all":
                bookmarks.forget()
            else:
                bookmarks.forget([k for k in bookmarks.keys()
                                  if (kind == "show" and k == "tv:%s" % value) or
                                  (kind == "channel" and k.startswith("tv:") and home.get(k[3:].lower()) == value)])
            for c in self.channels:
                s = self.schedule(c, ensure=False)
                st = s.data["state"]
                for k in [k for k in st["last"] if chosen(k, c["id"])]:
                    del st["last"][k]
                if kind == "all" or (kind == "channel" and c["id"] == value):
                    st.pop("rr", None)               # pinned slots rotating shows: from the first
                s.save()
            for i, c in enumerate(self.channels):
                if progress:
                    progress(i, len(self.channels), c)
                try:
                    self.schedule(c, ensure=False).ensure(now)
                except Exception as exc:
                    log("Schedule build failed for %s: %s" % (c.get("name"), exc))
        log("Start series over: %s %s" % (kind, value or ""), level=xbmc.LOGINFO)

    def migrate(self, now=None):
        """The first run with shared bookmarks (no series.json yet).  Each channel's
        plan is cut after the programme on air, so its bookmarks go back to what has
        aired; a show's bookmark on its home channel becomes the shared one.  What's
        on air keeps playing, and the episodes cut are planned again, in order."""
        with self.lock:
            if bookmarks.exists():
                return
            now = now or time.time()
            shared, cut = {}, 0
            for c in self.channels:
                try:
                    s = self.schedule(c, ensure=False)
                    changed = bool(s.data["entries"]) and s.cut(now)
                    cut += changed
                    last = s.data["state"]["last"]
                    for k in [k for k in last if not k.startswith("rule:") and s._shared(k)]:
                        shared.setdefault(k, last.pop(k))
                        changed = True
                    if changed:
                        s.save()
                except Exception as exc:
                    log("Series bookmarks: %s not moved over: %s" % (c.get("name"), exc))
            bookmarks.save_all(shared)
            log("Series bookmarks: %d shows, from what has aired (%d channels planned again)"
                % (len(shared), cut), level=xbmc.LOGINFO)

    def refresh_assignment(self):
        """Work out every show's home channel again (slow: resolves all sources)."""
        self.assignment, changed = assign.refresh(self.channels)
        return changed

    def is_ready(self, ch, now=None):
        s = self.schedule(ch, ensure=False)
        return s.block_at(now or time.time()) is not None

    def ensure_all(self, now=None, abort=None):
        self.refresh_assignment()
        for c in self.channels:
            if abort and abort():
                return
            self.schedule(c, True, now)
        skip_short_save()

    def neighbour(self, ch, step):
        if not self.channels:
            return None
        nums = [c["number"] for c in self.channels]
        i = nums.index(ch["number"]) if ch and ch["number"] in nums else -1
        return self.channels[(i + step) % len(self.channels)]
