"""Holiday seasons: the editor (main menu > Holidays & events > Holiday seasons).

A menu of every season; each season's page is a menu too (changes save as you go,
Done at the bottom).  The built-ins keep their Settings ids as storage (on, tags,
genres, commercials and bumps folders); their dates, run-up intensity, extra title
words and 'save for its season' go to seasons.json as overrides (seasons.py).
Reset puts a built-in back as it ships.  The viewer's own seasons live whole in
seasons.json ('custom', in list order); adding one is step-by-step (a ready-made
holiday or your own date, a name, Cancel / Add season), then its page.

What a season is (dates as rules, which one wins, what counts as its material) is
seasons.py; a changed season is planned in by the refresh that follows every
Settings tool (manager.run_tool -> refresh_if_changed), from each channel's next
programme, like any changed setting.
"""
import json

import xbmcgui

from . import kodiutil as K
from . import scheduler
from . import seasons as S
from . import specials_editor as E
from . import manager as M
from .kodiutil import _

D = M.D
INTENSITY = (_("A little"), _("Some (grows toward the day)"), _("Lots"))


# ------------------------------------------------------------------ reading and writing
def config():
    """The seasons config as planning sees it now (settings + seasons.json)."""
    return K.seasons_cfg()


def name_of(sid, d=None):
    if (d or {}).get("name"):
        return d["name"]
    if sid in S.NAMES:
        return E.SEASON.get(sid, S.NAMES[sid])
    return _("(no name)")


def set_override(sid, key, value):
    """A built-in's override in seasons.json (None removes it)."""
    data = S.load()
    ov = data["builtin"].setdefault(sid, {})
    if value is None:
        ov.pop(key, None)
    else:
        ov[key] = value
    if not ov:
        data["builtin"].pop(sid, None)
    _save(data)


def _save(data):
    if not data["builtin"] and not data["custom"]:
        import os
        try:
            os.remove(S.path())          # nothing changed from the built-ins: no file at all
        except OSError:
            pass
        return
    S.save(data)


def set_value(sid, key, value):
    """on / tags / genres / ads / bumps: a built-in's Settings value."""
    setting = {"on": "%s_on", "tags": "%s_tags", "genres": "%s_genres", "ads": "%s_commercials",
               "bumps": "%s_bumps"}[key] % sid
    K.set_setting(setting, ("true" if value else "false") if key == "on" else value)


def custom_of(data, sid):
    for c in data["custom"]:
        if c["id"] == sid:
            return c
    return None


def put(sid, key, value):
    """Change one thing of a season, wherever it is kept."""
    if sid not in S.NAMES:
        data = S.load()
        c = custom_of(data, sid)
        if c is not None:
            if key == "name" and not value:
                return                          # one of yours always has a name
            c[key] = [] if key == "words" and value is None else value
            _save(data)
        return
    if key in ("on", "tags", "genres", "ads", "bumps"):
        set_value(sid, key, value)
    else:
        set_override(sid, key, value)


# ------------------------------------------------------------------ words
def _lower(text):
    """'The day after ...' inside a sentence: 'from the day after ...'."""
    return text[0].lower() + text[1:] if text.startswith(_("The day ")) else text


def run_up_text(rule):
    if not rule:
        return _("none")
    if rule.get("type") == "before":
        return _("%d days before the big days") % rule["days"]
    return _("from %s") % _lower(E.when_text(rule))


def big_text(frm, days):
    if days <= 1:
        return _("big day %s") % _lower(E.when_text(frm))
    return _("big days from %s, %d days") % (_lower(E.when_text(frm)), days)


def when_text(sid, d):
    """'From 1 October, big day 31 October' / 'Run-up 2 days, big day 23 December'."""
    run_up, frm, days = S.rules(sid, d)
    big = big_text(frm, days or 1)
    if not run_up:
        return big[0].upper() + big[1:]
    if run_up.get("type") == "before":
        return _("Run-up %d days, %s") % (run_up["days"], big)
    return _("From %s, %s") % (_lower(E.when_text(run_up)), big)


def thanksgiving_kind(d):
    frm = S.rules("thanksgiving", d)[1]
    if frm == S.THANKSGIVING_US:
        return "us"
    if frm == S.THANKSGIVING_CA:
        return "ca"
    return "own"


def on_text(on):
    return _("On") if on else _("Off")


def list_text(text):
    return text if (text or "").strip() else _("none")


# ------------------------------------------------------------------ the list
def open_seasons():
    """Main menu > Holidays & events > Holiday seasons."""
    while True:
        sc = config()
        ids = list(S.order(sc))
        rows = []
        for sid in ids:
            d = sc.get(sid) or {}
            rows.append(M._menu_row("%s: %s" % (name_of(sid, d), on_text(d.get("on"))), when_text(sid, d)))
        if not sc.get("on"):
            head = _("Holiday seasons (Holiday programming is off in Settings)")
        else:
            head = _("Holiday seasons")
        rows.append(M._menu_row(_("[B]+ Add a season...[/B]"),
                                _("Any holiday, real or made up: Festivus, Bastille Day, Diwali...")))
        i = M.done_select(head, rows, useDetails=True)
        if i < 0:
            return
        if i == len(ids):
            sid = add_season()
            if sid:
                plan_for(sid)
                season_page(sid)
        else:
            season_page(ids[i])


# ------------------------------------------------------------------ a season's page
def season_page(sid):
    while True:
        sc = config()
        d = sc.get(sid)
        if d is None:
            return
        name = name_of(sid, d)
        intensity = d.get("intensity")
        hold = d.get("hold") if d.get("hold") is not None else sc.get("hold", True)
        tags, genres = S._season_words(sid, {"seasons": sc})
        extra = d.get("words") or []
        rows = [("on", _("On / Off: %s") % on_text(d.get("on")), ""),
                ("name", _("Name: %s") % name, _("Any name, any language")),
                ("when", _("When"), when_text(sid, d)),
                ("intensity", _("How much in the run-up: %s") % (
                    _("Same as Settings") if intensity is None else INTENSITY[intensity]), ""),
                ("tags", _("Tags: %s") % list_text(", ".join(tags)), _("Kodi tags containing these words count")),
                ("genres", _("Genres: %s") % list_text(", ".join(genres)), _("Kodi genres containing these words count")),
                ("words", _("Extra title words: %s") % list_text(", ".join(extra)),
                 _("Episode and movie titles with these words count too")),
                ("match", _("Show what matches"), _("How many episodes and films each channel has for it")),
                ("ads", _("Commercials folder: %s") % (d.get("ads") or _("none")), _("Optional: plays in its breaks")),
                ("bumps", _("Bumps folder: %s") % (d.get("bumps") or _("none")), _("Optional: plays in its breaks")),
                ("hold", _("Save its shows for its season: %s") % on_text(hold),
                 _("Keeps its episodes and films off the air the rest of the year"))]
        if sid in S.NAMES:
            rows.append(("reset", _("Reset to the built-in settings"), ""))
        else:
            mine = [x for x in S.order(sc) if x not in S.NAMES]
            if mine.index(sid) > 0:
                rows.append(("up", _("Move up"), _("Higher in the list wins when two seasons fall on the same days")))
            if mine.index(sid) < len(mine) - 1:
                rows.append(("down", _("Move down"), ""))
            rows.append(("delete", _("Delete this season"), ""))
        i = M.done_select(name, [M._menu_row(r[1], r[2]) for r in rows], useDetails=True)
        if i < 0:
            return
        key = rows[i][0]
        if key == "on":
            put(sid, "on", not d.get("on"))
        elif key == "when":
            edit_when(sid, d)
        elif key == "intensity":
            j = D.select(_("How much in the run-up?"), [_("Same as Settings")] + list(INTENSITY),
                         preselect=0 if intensity is None else intensity + 1)
            if j >= 0:
                put(sid, "intensity", None if j == 0 else j - 1)
        elif key in ("tags", "genres"):
            picked = pick_labels(key, name, tags if key == "tags" else genres)
            if picked is not None:
                put(sid, key, ", ".join(picked))
        elif key == "words":
            v = D.input(_("Extra title words for %s (comma separated)") % name, ", ".join(extra))
            if v is not None:
                w = S.words(v)
                put(sid, "words", w or None)
        elif key == "match":
            show_matches(sid, name)
        elif key in ("ads", "bumps"):
            edit_folder(sid, key, d.get(key) or "")
        elif key == "hold":
            if not hold:
                n = held_count(sid)
                if n is not None and not M.confirm(
                        _("%s: episodes and films that match: %d. They'll stay off the air the rest of the year.") % (name, n),
                        _("Save them")):
                    continue
            put(sid, "hold", not hold)
        elif key == "name":
            v = D.input(_("Name"), name)
            if v is not None:
                put(sid, "name", v.strip() or None)     # emptied: a built-in's own name again
        elif key in ("up", "down"):
            move(sid, -1 if key == "up" else 1)
        elif key == "delete":
            if M.confirm_remove(_("Delete the season %s?") % name, _("Delete")):
                data = S.load()
                data["custom"] = [c for c in data["custom"] if c["id"] != sid]
                _save(data)
                return
        elif key == "reset":
            if M.confirm(_("Put %s back as it ships: dates, tags, genres, title words, folders?") % name, _("Reset")):
                reset_builtin(sid)


def reset_builtin(sid):
    data = S.load()
    data["builtin"].pop(sid, None)
    _save(data)
    set_value(sid, "on", True)
    set_value(sid, "tags", S.DEFAULT_TAGS[sid])
    set_value(sid, "genres", S.DEFAULT_GENRES[sid])
    set_value(sid, "ads", "")
    set_value(sid, "bumps", "")


# ------------------------------------------------------------------ when
def ask_rule(heading):
    """A date rule picked like a special's date (a date, a weekday of a month,
    Easter, a ready-made holiday, each movable by days); None on Back."""
    got = E.ask_when()
    return got[0] if got else None


def edit_when(sid, d):
    if sid == "thanksgiving":
        kind = thanksgiving_kind(d)
        j = D.select(_("Which Thanksgiving?"), [_("US (4th Thursday of November)"),
                                                 _("Canada (2nd Monday of October)"), _("My own rule...")],
                     preselect={"us": 0, "ca": 1}.get(kind, 2))
        if j < 0:
            return
        if j < 2:
            _set_rule(sid, "from", S.THANKSGIVING_US if j == 0 else S.THANKSGIVING_CA)
            return
    while True:
        d = config().get(sid) or {}
        run_up, frm, days = S.rules(sid, d)
        rows = [_("Big days start: %s") % E.when_text(frm),
                _("Big days last: %s") % (_("1 day") if days == 1 else _("%d days") % days),
                _("Run-up: %s") % run_up_text(run_up)]
        i = M.done_select(_("When"), rows)
        if i < 0:
            return
        if i == 0:
            rule = ask_rule(_("Big days start"))
            if rule:
                _set_rule(sid, "from", rule)
        elif i == 1:
            n = ask_days(days)
            if n:
                _set_rule(sid, "days", n)
        else:
            rule = ask_run_up(run_up)
            if rule is not False:
                _set_rule(sid, "run_up", rule)


def ask_days(current=1):
    """1-14 big days, or None on Back."""
    j = D.select(_("How many big days?"), [_("1 day")] + [_("%d days") % n for n in range(2, S.MAX_DAYS + 1)],
                 preselect=max(0, min(S.MAX_DAYS, current or 1) - 1))
    return None if j < 0 else j + 1


def ask_run_up(current=None):
    """The run-up: None (none), {'type': 'before', 'days': N} or a date rule; False on Back."""
    j = D.select(_("Run-up"), [_("No run-up"), _("Starts some days before the big days..."), _("Starts on a date...")])
    if j < 0:
        return False
    if j == 0:
        return None
    if j == 1:
        n = current.get("days") if isinstance(current, dict) and current.get("type") == "before" else 7
        v = D.numeric(0, _("How many days before the big days?"), str(n))
        if not v or not (1 <= int(v) <= S.MAX_BEFORE):
            return False
        return {"type": "before", "days": int(v)}
    rule = ask_rule(_("Run-up starts"))
    return rule if rule else False


def _set_rule(sid, key, rule):
    """A rule of a season; for a built-in, an override only when it differs from the
    built-in's own (so going back to it leaves no override)."""
    if sid not in S.NAMES:
        put(sid, key, rule)
        return
    if sid in S.RULES and json.dumps(S.RULES[sid][key], sort_keys=True) == json.dumps(rule, sort_keys=True):
        set_override(sid, key, None)
        return
    data = S.load()
    data["builtin"].setdefault(sid, {})[key] = rule
    _save(data)


# ------------------------------------------------------------------ tags and genres
def pick_labels(kind, name, current):
    """Tick tags or genres from what the library has; the season's words that no
    library label contains stay in the list (ticked) so nothing is lost silently."""
    try:
        labels = S._library_labels("tag" if kind == "tags" else "genre")
    except Exception as exc:
        K.log_err("season labels: %s" % exc)
        labels = []
    chosen = [l for l in labels if l.lower() in current]
    for w in current:
        if not any(w == l.lower() for l in labels):
            chosen.append(w)
    items = sorted(set(labels) | set(chosen), key=lambda x: x.lower())
    details = {}
    for w in chosen:
        if w not in labels:
            details[w] = (_("Any tag containing this word") if kind == "tags" else _("Any genre containing this word"))
    heading = (_("%s: tags") if kind == "tags" else _("%s: genres")) % name
    if not labels:
        D.notification(M.TITLE, _("Kodi lists none in your library"), time=3000)
    return M.search_pick(heading, items, multi=True, preselected=chosen, details=details)


def edit_folder(sid, key, cur):
    label = _("Commercials folder") if key == "ads" else _("Bumps folder")
    if cur:
        j = D.select(label, [_("Choose another folder..."), _("Don't use one")])
        if j < 0:
            return
        if j == 1:
            put(sid, key, "")
            return
    p = D.browse(0, label, "video", "", False, False, cur)
    if p and p != cur:
        put(sid, key, p)


# ------------------------------------------------------------------ what matches
def matches(sid):
    """[(channel, episodes, films, titles)] of the season's material in each channel's
    own programming - the same pool a special's 'holiday episodes' and the run-up
    draw from (scheduler._holiday_pool)."""
    S.clear_cache()
    lineup = scheduler.Lineup(K.schedule_cfg())
    out = []
    for c in lineup.channels:
        if c["type"] not in M.AIR_TYPES:
            continue
        pool = lineup.schedule(c, ensure=False)._holiday_pool(sid)
        eps = sum(len(s["episodes"]) for s in pool["series"])
        films = len(pool["singles"])
        if eps or films:
            titles = [s["title"] for s in pool["series"]] + [i.get("title") or "" for i in pool["singles"]]
            out.append((c, eps, films, titles))
    return out


def show_matches(sid, name):
    bar = xbmcgui.DialogProgress()
    bar.create(name, _("Looking through every channel..."))
    try:
        found = matches(sid)
    finally:
        bar.close()
    if not found:
        D.ok(name, _("No channel has anything for %s yet. Tag episodes or movies in Kodi, or add title words.") % name)
        return
    lines = []
    for c, eps, films, titles in found:
        lines.append(_("[B]%d %s[/B]: %d episodes, %d films") % (c["number"], c["name"], eps, films))
        lines.append("    " + ", ".join(titles[:6]) + (" ..." if len(titles) > 6 else ""))
    D.textviewer(_("%s: what matches") % name, "[CR]".join(lines))


def held_count(sid):
    """Episodes and films 'save for its season' would keep off the air outside the
    season (every channel's programming, each file once)."""
    bar = xbmcgui.DialogProgress()
    bar.create(M.TITLE, _("Counting..."))
    try:
        S.clear_cache()
        cfg = K.schedule_cfg()
        sc = dict(cfg["seasons"])
        sc[sid] = dict(sc.get(sid) or {}, hold=True)
        cfg = dict(cfg, seasons=sc)
        lineup = scheduler.Lineup(cfg)
        seen = set()
        for c in lineup.channels:
            if c["type"] not in M.AIR_TYPES:
                continue
            pool = lineup.schedule(c, ensure=False)._holiday_pool(sid)
            for it in [e for s in pool["series"] for e in s["episodes"]] + pool["singles"]:
                if it["path"] not in seen and S.holiday_of(it, cfg, tuple(S.held(sc))) == sid:
                    seen.add(it["path"])
        return len(seen)
    except Exception as exc:
        K.log_err("season hold count: %s" % exc)
        return None
    finally:
        bar.close()


# ------------------------------------------------------------------ your own seasons
def _date(m, d):
    return {"type": "date", "month": m, "day": d}


# the ready-made holidays: (name, first big day, title words); all fixed dates or Easter
READY = [
    (_("New Year's Day"), _date(1, 1), ["new year", "new year's", "new years"]),
    (_("Valentine's Day"), _date(2, 14), ["valentine", "valentines", "valentine's", "cupid"]),
    (_("St. Patrick's Day"), _date(3, 17), ["st. patrick", "st patrick", "saint patrick", "leprechaun", "shamrock"]),
    (_("Easter"), {"type": "easter", "offset": 0}, ["easter", "easter bunny", "egg hunt"]),
    (_("May the 4th"), _date(5, 4), ["may the 4th", "may the fourth"]),
    (_("Towel Day"), _date(5, 25), ["towel day"]),
    (_("Canada Day"), _date(7, 1), ["canada day", "dominion day"]),
    (_("Independence Day"), _date(7, 4), ["fourth of july", "4th of july", "independence day"]),
    (_("Bastille Day"), _date(7, 14), ["bastille day", "bastille"]),
    (_("Festivus"), _date(12, 23), ["festivus"]),
    (_("Boxing Day"), _date(12, 26), ["boxing day"]),
]


def add_season():
    """Step-by-step: a ready-made holiday or your own date, how many big days, the
    run-up, a name, Cancel / Add season.  Back on any step cancels it.  Returns the
    new season's id, or None.  Its shows (tags, genres, words) are set on its page."""
    j = D.select(_("Add a season"), [r[0] for r in READY] + [_("My own date...")])
    if j < 0:
        return None
    if j < len(READY):
        name, frm, words = READY[j]
    else:
        got = E.ask_when()
        if not got:
            return None
        (frm, name), words = got, []
    days = ask_days(1)
    if not days:
        return None
    run_up = ask_run_up(None)
    if run_up is False:
        return None
    v = D.input(_("Name of the season"), name)
    if not v or not v.strip():
        return None
    c = {"id": "s_" + S.specials.new_id(), "name": v.strip(), "on": True, "run_up": run_up, "from": frm,
         "days": days, "intensity": None, "tags": "", "genres": "", "words": list(words), "ads": "", "bumps": "",
         "hold": False}
    if not M.confirm(_("%s: %s.[CR]Next, on its page: the Kodi tags, genres and title words that count as its shows.")
                     % (c["name"], when_text(c["id"], c)), _("Add season")):
        return None
    data = S.load()
    data["custom"].append(c)
    _save(data)
    return c["id"]


def plan_for(sid):
    """A new holiday: plan a special on it straight away?  (One list of holidays:
    its name and date fill in When?.)"""
    sc = config()
    d = sc.get(sid) or {}
    name = name_of(sid, d)
    if not M.confirm(_("Plan something for %s too: a marathon or a lineup on the day?") % name, _("Plan a special"),
                     _("Not now")):
        return
    from . import channels as C
    chans = C.load()
    rule = S.rules(sid, d)[1]
    new = E.add_special(E.load(chans), chans, picked=(json.loads(json.dumps(rule)), name, ("yearly", None)))
    if new:
        E.special_page(new)


def move(sid, step):
    """One of your own seasons up or down among yours (the built-ins stay first)."""
    data = S.load()
    ids = [c["id"] for c in data["custom"]]
    i = ids.index(sid)
    j = i + step
    if 0 <= j < len(ids):
        data["custom"][i], data["custom"][j] = data["custom"][j], data["custom"][i]
        _save(data)
