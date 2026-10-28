"""Add-on menus: lineup wizard and the channel manager.

Everything is done with Kodi's own dialogs, so it works with the remote on
any skin.  Channel changes take effect immediately - the schedule for an
edited channel simply rebuilds itself from 'now'.
"""
import os
import time

import xbmc
import xbmcgui

from . import kodiutil as K
from . import channels as C
from . import library
from . import scheduler
from .kodiutil import _

D = xbmcgui.Dialog()
TITLE = "CableBox 42"
TYPE_LABELS = {"network": _("Network (series + commercials)"), "movies": _("Movie channel"),
               "loop": _("Loop (back-to-back, no clock)"), "guide": _("Guide channel"),
               "weather": _("Weather channel")}
PROGRAM_TYPES = ("network", "movies", "loop")
ALL_TYPES = ["network", "movies", "loop", "guide", "weather"]


# ------------------------------------------------------------------ helpers
def describe_source(s):
    t = s.get("type")
    if t == "tvshow":
        v = s.get("value")
        v = v if isinstance(v, list) else [v]
        return _("Shows: ") + (", ".join(v[:3]) + (_(" +%d more") % (len(v) - 3) if len(v) > 3 else ""))
    if t == "tvgenre":
        return _("TV genre: %s") % s.get("value")
    if t == "tvdecade":
        return _("TV from the %ss") % s.get("value")
    if t == "movies":
        bits = [s.get("genre") or _("all genres")]
        if s.get("years"):
            bits.append("%s-%s" % tuple(s["years"]))
        if s.get("set"):
            bits.append(_("set: ") + s["set"])
        return _("Movies: ") + ", ".join(bits)
    if t == "folder":
        return _("Folder (%s): %s") % (s.get("mode", "shows"), s.get("path"))
    if t == "playlist":
        return _("Smart playlist: %s") % os.path.basename(s.get("path", ""))
    what = {"both": _("movies + shows"), "tv": "shows", "movies": "movies"}.get(s.get("what", "both"), "")
    v = s.get("value")
    v = ", ".join(v[:4]) + (_(" +%d more") % (len(v) - 4) if len(v) > 4 else "") if isinstance(v, list) else v
    if t == "studio":
        return _("Studio/network '%s' (%s)") % (v, what)
    if t == "tag":
        return _("Tag '%s' (%s)") % (v, what)
    if t == "keyword":
        return _("Title contains '%s' (%s)") % (s.get("value"), what)
    if t == "movie":
        v = s.get("value") or []
        return _("Movies: ") + ", ".join(v[:3]) + (_(" +%d more") % (len(v) - 3) if len(v) > 3 else "")
    return str(s)


def ask_what():
    j = D.select(_("Include"), [_("Movies and TV shows"), _("TV shows only"), _("Movies only")])
    return ["both", "tv", "movies"][j] if j >= 0 else None


# ------------------------------------------------------------------ searchable picker
CHECK = "[COLOR FF33FF66]\u2714[/COLOR]  "


def _matches(items, query):
    words = query.lower().split()
    if not words:
        return list(items)
    starts = [i for i in items if i.lower().startswith(query.lower())]
    rest = [i for i in items if i not in starts and all(w in i.lower() for w in words)]
    return starts + rest


def search_pick(heading, items, multi=False, preselected=None, details=None, query=""):
    """Kodi's select dialog has no search, which is painful with 1000 tags.

    Single mode returns the chosen string (or None).  Multi mode toggles items
    on and off and returns the final list of chosen strings (or None if the
    user backs out).  Searching matches every typed word anywhere in the
    name; names starting with the text come first.
    """
    details = details or {}
    chosen = list(preselected or [])
    pos = 0
    while True:
        matches = _matches(items, query)
        rows, actions = [], []
        rows.append(xbmcgui.ListItem("[B]Search...[/B]" if not query else _("[B]Search: %s[/B]") % query,
                                    _("Type part of a name  -  %d of %d shown") % (len(matches), len(items))))
        actions.append("search")
        if query:
            rows.append(xbmcgui.ListItem(_("[B]Show everything[/B]"), ""))
            actions.append("clear")
        if multi:
            rows.append(xbmcgui.ListItem(_("[B]Done  (%d selected)[/B]") % len(chosen),
                                         ", ".join(chosen[:6]) + (" ..." if len(chosen) > 6 else "")))
            actions.append("done")
            if chosen:
                rows.append(xbmcgui.ListItem(_("[B]Show only selected[/B]"), ""))
                actions.append("selected")
        head = len(rows)
        for m in matches:
            rows.append(xbmcgui.ListItem((CHECK if multi and m in chosen else "") + m, details.get(m, "")))
        title = "%s%s" % (heading, (_("  (%d selected)") % len(chosen)) if multi else "")
        i = D.select(title, rows, useDetails=True, preselect=min(pos, len(rows) - 1))
        if i < 0:
            if multi and chosen != list(preselected or []) and \
                    D.yesno(TITLE, _("Keep your %d selections?") % len(chosen)):
                return chosen
            return None
        pos = i
        if i < head:
            act = actions[i]
            if act == "search":
                q = D.input(_("Search %s") % heading.lower(), query)
                if q is not None and q.strip():
                    if not _matches(items, q.strip()):
                        xbmcgui.Dialog().notification(TITLE, _("Nothing matches '%s'") % q, time=2500)
                    else:
                        query = q.strip()
                        pos = head
            elif act == "clear":
                query = ""
                pos = 0
            elif act == "done":
                return chosen
            elif act == "selected":
                sel = search_pick(heading + _(" - selected"), list(chosen), True, chosen, details)
                if sel is not None:
                    chosen = sel
            continue
        item = matches[i - head]
        if not multi:
            search_pick.last_query = query
            return item
        if item in chosen:
            chosen.remove(item)
        else:
            chosen.append(item)


def ask_time(heading, default="00:00"):
    v = D.numeric(2, heading, default)
    return v.strip() if v else None


def pick_source():
    kinds = [_("TV shows from my library"), _("A TV genre"), _("TV shows from a decade"),
             _("Movies (by genre / years / set)"), _("A folder of videos"), _("A Kodi smart playlist"),
             _("A studio / network (e.g. Disney) - movies and shows"), _("A Kodi tag - movies and shows"),
             _("Anything whose title contains..."), _("Specific movies")]
    i = D.select(_("Add programming"), kinds)
    if i < 0:
        return None
    if i == 0:
        shows = sorted(library.all_tvshows(), key=lambda s: library.natural_key(s["title"]))
        if not shows:
            D.ok(TITLE, _("No TV shows found in your Kodi library."))
            return None
        sel = search_pick(_("Pick shows"), [s["title"] for s in shows], multi=True,
                          details=dict((s["title"], ", ".join(s.get("genre", []))) for s in shows))
        return {"type": "tvshow", "value": sel} if sel else None
    if i == 1:
        genres = sorted(set(g for s in library.all_tvshows() for g in s.get("genre", [])))
        g = search_pick(_("TV genre"), genres) if genres else None
        return {"type": "tvgenre", "value": g} if g else None
    if i == 2:
        decs = sorted(set(int(s.get("year") or 0) // 10 * 10 for s in library.all_tvshows()
                          if int(s.get("year") or 0) > 1900))
        j = D.select(_("Decade"), ["%ds" % d for d in decs]) if decs else -1
        return {"type": "tvdecade", "value": decs[j]} if j >= 0 else None
    if i == 3:
        movies = library.all_movies(["title", "genre", "year", "set"])
        genres = sorted(set(g for m in movies for g in m.get("genre", [])))
        g = search_pick(_("Genre"), [_("Any genre")] + genres)
        if not g:
            return None
        src = {"type": "movies"}
        if g != _("Any genre"):
            src["genre"] = g
        if D.yesno(TITLE, _("Limit to a range of years?")):
            y0 = D.numeric(0, _("From year"), "1980")
            y1 = D.numeric(0, _("To year"), "1989")
            if y0 and y1:
                src["years"] = [int(y0), int(y1)]
        sets = sorted(set(m.get("set") for m in movies if m.get("set")))
        if sets and D.yesno(TITLE, _("Limit to one movie set/collection?")):
            st = search_pick(_("Movie set"), sets)
            if st:
                src["set"] = st
        return src
    if i == 4:
        path = D.browse(0, _("Choose folder"), "video")
        if not path:
            return None
        modes = [_("Each sub-folder is a show (episodes in order)"),
                 _("Play files in random order"), _("Play files in order")]
        m = D.select(_("How should this folder air?"), modes)
        if m < 0:
            return None
        return {"type": "folder", "path": path, "mode": ["shows", "random", "sequential"][m]}
    if i == 5:
        path = D.browse(1, _("Choose smart playlist"), "video", ".xsp",
                        defaultt="special://profile/playlists/video/")
        return {"type": "playlist", "path": path} if path else None
    if i == 6:
        studios = library.all_studios()
        names = sorted(studios, key=lambda k: -(studios[k][0] + studios[k][1]))
        det = dict((k, _("%d shows, %d movies") % tuple(v)) for k, v in studios.items())
        sel = search_pick(_("Studios / networks (pick one or more)"), names, multi=True, details=det)
        if not sel:
            return None
        what = ask_what()
        return {"type": "studio", "value": sel, "what": what} if what else None
    if i == 7:
        counts = library.tag_counts()
        tags = sorted(counts, key=library.natural_key)
        if not tags:
            D.ok(TITLE, _("No tags in your Kodi library yet.[CR]Tip: in Kodi, open a movie or show's "
                        "information > Manage > Manage tags, e.g. tag everything 'Disney'."))
            return None
        det = dict((t, _("%d shows, %d movies") % tuple(counts[t])) for t in tags)
        sel = search_pick(_("Tags (pick one or more)"), tags, multi=True, details=det)
        if not sel:
            return None
        what = ask_what()
        return {"type": "tag", "value": sel, "what": what} if what else None
    if i == 8:
        val = D.input(_("Title contains"), "")
        what = ask_what() if val else None
        return {"type": "keyword", "value": val, "what": what} if what else None
    if i == 9:
        movies = sorted(library.all_movies(["title", "year"]), key=lambda m: library.natural_key(m["title"]))
        names = ["%s (%s)" % (m["title"], m.get("year")) if m.get("year") else m["title"] for m in movies]
        sel = search_pick(_("Pick movies"), names, multi=True) if names else None
        return {"type": "movie", "value": sel} if sel else None
    return None


# ------------------------------------------------------------------ wizard
def wizard():
    chans = C.load()
    if chans:
        i = D.select(_("You already have %d channels") % len(chans),
                     [_("Replace my lineup"), _("Add the auto channels after my current ones"), _("Cancel")])
        if i in (-1, 2):
            return
    else:
        i = 0
    if not K.setting("commercials_path") and D.yesno(
            TITLE, _("Do you have a folder of old commercials?[CR][CR]They fill the breaks "
                   "like real cable TV. You can add this later in Settings."), nolabel=_("Skip"),
            yeslabel=_("Choose folder")):
        p = D.browse(0, _("Commercials folder"), "video")
        if p:
            K.set_setting("commercials_path", p)
    if not K.setting("bumps_path") and D.yesno(
            TITLE, _("Do you have a folder of bumps / station IDs?[CR](Short clips played "
                   "right before the show comes back.)"), nolabel=_("Skip"), yeslabel=_("Choose folder")):
        p = D.browse(0, _("Bumps folder"), "video")
        if p:
            K.set_setting("bumps_path", p)

    if not K.setting("weather_location") and not xbmc.getCondVisibility("Weather.IsFetched"):
        city = D.input(_("Your city for the Weather Channel (optional, e.g. Dickson, TN)"), "")
        if city:
            K.set_setting("weather_location", city)

    pd = xbmcgui.DialogProgress()
    pd.create(TITLE, _("Looking through your library..."))
    new = C.auto_lineup(lambda msg, pct: pd.update(pct, msg))
    pd.close()
    if len(new) > 2:
        labels = [_("%3d  %s   [COLOR grey]%s[/COLOR]") % (c["number"], c["name"],
                                                       ", ".join(describe_source(x) for x in c["sources"])[:80])
                  for c in new]
        keep = D.multiselect(_("Keep which channels? (you can fine-tune shows afterwards)"), labels,
                             preselect=list(range(len(new))))
        if keep is None:
            return
        new = [new[j] for j in keep]
        num = 2
        for c in new:
            c["number"] = num
            num += 1
    if len([c for c in new if c["type"] in PROGRAM_TYPES]) == 0:
        D.ok(TITLE, _("I couldn't find any TV shows or movies in your Kodi library.[CR]"
                    "Scan your media into the library first, or add folder channels "
                    "in the Channel Manager."))
        return
    if i == 1:
        start = max(c["number"] for c in chans) + 1
        have = set(c["type"] for c in chans)
        for c in new:
            if c["type"] in ("guide", "weather") and c["type"] in have:
                continue
            c["number"] = start
            start += 1
            chans.append(c)
    else:
        chans = new
    for c in chans:
        c.setdefault("callsign", C.callsign(c["name"]))
    C.save(chans)
    names = "[CR]".join("%3d  %s" % (c["number"], c["name"]) for c in C.load())
    prebuild()
    if D.yesno(TITLE, _("Your lineup is ready:[CR]%s[CR][CR]Start watching?") % names):
        from . import tv
        tv.run()


def prebuild(chans=None):
    lineup = scheduler.Lineup(K.schedule_cfg())
    if chans is not None:
        lineup.channels = chans
    pd = xbmcgui.DialogProgress()
    pd.create(TITLE, _("Programming the channels..."))
    n = max(1, len(lineup.channels))
    for i, c in enumerate(lineup.channels):
        if pd.iscanceled():
            break
        pd.update(int(100.0 * i / n), "%d  %s" % (c["number"], c["name"]))
        lineup.schedule(c)
    pd.close()
    library.durations().save()


def rebuild_all():
    if not D.yesno(TITLE, _("Rebuild every channel's schedule from now?[CR]Episode progress is kept.")):
        return
    library.clear_cache()
    for c in C.load():
        p = os.path.join(K.SCHEDULE_DIR, "%s.json" % c["id"])
        d = K.load_json(p, None)
        if d:
            d.update(hash="", entries=[], blocks=[], until=0)
            K.save_json(p, d)
    prebuild()


# ------------------------------------------------------------------ manager
def manager():
    while True:
        chans = C.load()
        rows = [_("[B]+ Add a channel[/B]"), _("[B]Rearrange channel numbers[/B]")]
        for c in chans:
            rows.append(_("%3d   %s   [COLOR grey](%s, %d source%s)[/COLOR]") % (
                c["number"], c["name"], c["type"], len(c["sources"]),
                "" if len(c["sources"]) == 1 else "s"))
        i = D.select(_("Channel manager"), rows)
        if i < 0:
            return
        if i == 0:
            add_channel(chans)
        elif i == 1:
            rearrange()
        else:
            edit_channel(chans[i - 2]["id"])


def move_channel(chans, ch, new):
    """Give `ch` number `new`.  If it's taken, offer to swap or slide channels over.

    Schedules belong to the channel, not the number, so nothing gets rebuilt -
    the show that's on stays on, just at its new spot on the dial.
    """
    old = ch["number"]
    if new == old:
        return False
    other = next((c for c in chans if c["number"] == new and c["id"] != ch["id"]), None)
    if other is None:
        ch["number"] = new
        return True
    j = D.select(_("Channel %d is %s") % (new, other["name"]), [
        _("Swap them  (%s goes to %d)") % (other["name"], old),
        _("Slide the channels in between over by one"),
        _("Cancel")])
    if j == 0:
        other["number"] = old
        ch["number"] = new
    elif j == 1:
        lo, hi = min(old, new), max(old, new)
        step = 1 if new < old else -1
        for c in chans:
            if c["id"] != ch["id"] and lo <= c["number"] <= hi:
                c["number"] += step
        ch["number"] = new
    else:
        return False
    return True


def rearrange():
    """Pick a channel, type where it goes; repeat.  Plus 'close the gaps'."""
    while True:
        chans = C.load()
        rows = [_("[B]Close the gaps (renumber 2, 3, 4...)[/B]")] + \
               ["%3d   %s" % (c["number"], c["name"]) for c in chans]
        i = D.select(_("Pick a channel to move"), rows)
        if i < 0:
            return
        if i == 0:
            first = D.numeric(0, _("Start numbering at"), str(chans[0]["number"] if chans else 2))
            if first:
                for n, c in enumerate(chans):
                    c["number"] = int(first) + n
                C.save(chans)
            continue
        ch = chans[i - 1]
        v = D.numeric(0, _("Move %s to channel") % ch["name"], str(ch["number"]))
        if v and int(v) > 0 and move_channel(chans, ch, int(v)):
            C.save(chans)


def add_channel(chans):
    types = ALL_TYPES
    t = D.select(_("Channel type"), [TYPE_LABELS[x] for x in types])
    if t < 0:
        return
    name = D.input(_("Channel name"), {"guide": _("TV Guide"), "weather": _("Weather Channel")}.get(types[t], ""))
    if not name:
        return
    num = D.numeric(0, _("Channel number"), str(C.next_free_number(chans)))
    if not num:
        return
    num = int(num)
    if any(c["number"] == num for c in chans):
        D.ok(TITLE, _("Channel %d is already taken.") % num)
        return
    ch = C.new_channel(num, name, types[t], callsign=C.callsign(name))
    if types[t] in PROGRAM_TYPES:
        while True:
            src = pick_source()
            if src:
                ch["sources"].append(src)
            if not D.yesno(TITLE, _("Add more programming to %s?") % name):
                break
    chans.append(ch)
    C.save(chans)
    edit_channel(ch["id"])


def _find(cid):
    chans = C.load()
    for c in chans:
        if c["id"] == cid:
            return chans, c
    return chans, None


def edit_channel(cid):
    while True:
        chans, ch = _find(cid)
        if not ch:
            return
        onoff = lambda b: _("On") if b else _("Off")
        items = [
            ("name", _("Name: %s") % ch["name"]),
            ("number", _("Number: %d") % ch["number"]),
            ("callsign", _("Call letters: %s") % ch.get("callsign", "")),
            ("type", _("Type: %s") % TYPE_LABELS.get(ch["type"], ch["type"])),
            ("sources", _("Programming: %d source(s)") % len(ch["sources"])),
            ("dayparts", _("Time blocks (prime time, Saturday mornings...): %d") % len(ch["dayparts"])),
            ("offair", _("Off-air hours: %s") % (", ".join("%s-%s" % (w["start"], w["end"])
                                                       for w in ch["offair"]) or "never")),
            ("shows", _("[B]What's on this channel[/B] (%d hidden)") % len(ch.get("exclude", []))),
            ("commercials", _("Commercials: %s") % onoff(ch.get("commercials"))),
            ("midroll", _("Break into shows for commercials: %s") % onoff(ch.get("midroll", ch["type"] != "movies"))),
            ("bumps", _("Bumps: %s") % onoff(ch.get("bumps"))),
            ("lineup", _("Lineup style: %s") % (_("Same show same time every day") if ch.get("lineup") == "strip"
                                             else _("Shuffle"))),
            ("slot", _("Programs start on: %s") % ({0: _("no clock (back to back)"), 15: ":00 :15 :30 :45",
                                                 30: _(":00 and :30"), 60: _("the hour")}.get(ch.get("slot"),
                                                                                       str(ch.get("slot"))))),
            ("cpath", _("Channel commercials folder: %s") % (ch.get("commercials_path") or "global")),
            ("bpath", _("Channel bumps folder: %s") % (ch.get("bumps_path") or "global")),
            ("preview", _("[B]Preview today's schedule[/B]")),
            ("delete", _("[COLOR red]Delete channel[/COLOR]")),
        ]
        i = D.select("%d  %s" % (ch["number"], ch["name"]), [x[1] for x in items])
        if i < 0:
            return
        key = items[i][0]
        if key == "name":
            v = D.input(_("Name"), ch["name"])
            if v:
                ch["name"] = v
        elif key == "number":
            v = D.numeric(0, _("Move %s to channel") % ch["name"], str(ch["number"]))
            if v and int(v) > 0:
                move_channel(chans, ch, int(v))
        elif key == "callsign":
            v = D.input(_("Call letters"), ch.get("callsign", ""))
            ch["callsign"] = v.upper()[:6]
        elif key == "type":
            types = ALL_TYPES
            j = D.select(_("Type"), [TYPE_LABELS[x] for x in types])
            if j >= 0:
                ch["type"] = types[j]
                ch.update(C.DEFAULTS[types[j]])
        elif key == "sources":
            edit_sources(ch["sources"], ch["name"])
        elif key == "dayparts":
            edit_dayparts(ch)
        elif key == "offair":
            edit_offair(ch)
        elif key in ("commercials", "bumps"):
            ch[key] = not ch.get(key)
        elif key == "midroll":
            ch["midroll"] = not ch.get("midroll", ch["type"] != "movies")
        elif key == "shows":
            whats_on(ch)
        elif key == "lineup":
            ch["lineup"] = "shuffle" if ch.get("lineup") == "strip" else "strip"
        elif key == "slot":
            opts = [30, 60, 15, 0]
            j = D.select(_("Programs start on"), [_(":00 and :30 (classic TV)"), _("the hour"),
                                               _("every 15 minutes"), _("no clock - back to back")])
            if j >= 0:
                ch["slot"] = opts[j]
        elif key in ("cpath", "bpath"):
            field = "commercials_path" if key == "cpath" else "bumps_path"
            j = D.select(_("Folder"), [_("Use global setting"), _("Choose folder...")])
            if j == 0:
                ch.pop(field, None)
            elif j == 1:
                p = D.browse(0, _("Folder"), "video")
                if p:
                    ch[field] = p
        elif key == "preview":
            C.save(chans)
            preview(ch)
            continue
        elif key == "delete":
            if D.yesno(TITLE, _("Delete %d %s?") % (ch["number"], ch["name"])):
                chans = [c for c in chans if c["id"] != cid]
                C.save(chans)
                try:
                    os.remove(os.path.join(K.SCHEDULE_DIR, "%s.json" % cid))
                except OSError:
                    pass
                return
            continue
        C.save(chans)


def edit_sources(sources, name):
    while True:
        rows = [_("[B]+ Add programming[/B]")] + [describe_source(s) for s in sources]
        i = D.select(_("Programming on %s") % name, rows)
        if i < 0:
            return
        if i == 0:
            s = pick_source()
            if s:
                sources.append(s)
        elif D.yesno(TITLE, _("Remove this?[CR]%s") % rows[i]):
            del sources[i - 1]


DAY_OPTS = [("all", _("Every day")), ("weekdays", _("Weekdays")), ("weekends", _("Weekends")),
            ([5], _("Saturdays")), ([6], _("Sundays"))]


def edit_dayparts(ch):
    while True:
        rows = [_("[B]+ Add a time block[/B]")]
        for dp in ch["dayparts"]:
            days = dict((str(k), v) for k, v in DAY_OPTS).get(str(dp.get("days", "all")), "")
            rows.append(_("%s  %s-%s  %s  (%d sources)") % (dp.get("label", _("Block")), dp["start"], dp["end"],
                                                         days, len(dp.get("sources", []))))
        i = D.select(_("Time blocks override the normal programming"), rows)
        if i < 0:
            return
        if i == 0:
            label = D.input(_("Name (e.g. Prime Time, Saturday Cartoons)"), _("Prime Time"))
            a = ask_time(_("Starts at"), "20:00")
            b = ask_time(_("Ends at"), "23:00")
            if not (a and b):
                continue
            j = D.select(_("On"), [x[1] for x in DAY_OPTS])
            dp = {"label": label or _("Block"), "start": a, "end": b,
                  "days": DAY_OPTS[max(j, 0)][0], "sources": []}
            edit_sources(dp["sources"], dp["label"])
            if dp["sources"]:
                ch["dayparts"].append(dp)
        else:
            dp = ch["dayparts"][i - 1]
            j = D.select(dp.get("label", _("Block")), [_("Edit programming"), _("Change times"), _("Remove")])
            if j == 0:
                edit_sources(dp["sources"], dp.get("label", _("Block")))
            elif j == 1:
                a = ask_time(_("Starts at"), dp["start"])
                b = ask_time(_("Ends at"), dp["end"])
                if a and b:
                    dp["start"], dp["end"] = a, b
            elif j == 2:
                del ch["dayparts"][i - 1]


def edit_offair(ch):
    while True:
        rows = [_("[B]+ Add off-air hours[/B]")] + ["%s - %s" % (w["start"], w["end"]) for w in ch["offair"]]
        i = D.select(_("Sign-off hours (color bars)"), rows)
        if i < 0:
            return
        if i == 0:
            a = ask_time(_("Sign off at"), "02:00")
            b = ask_time(_("Sign on at"), "06:00")
            if a and b:
                ch["offair"].append({"start": a, "end": b})
        elif D.yesno(TITLE, _("Remove %s?") % rows[i]):
            del ch["offair"][i - 1]


def preview(ch):
    lineup = scheduler.Lineup(K.schedule_cfg())
    busy = xbmcgui.DialogProgress()
    busy.create(TITLE, _("Building schedule..."))
    s = lineup.schedule(ch)
    busy.close()
    from .tv import fmt_time
    now = time.time()
    lines = []
    for b in s.blocks_between(now, now + 12 * 3600):
        extra = " ".join(x for x in (b.get("lb", ""), b.get("sub", "")) if x)
        lines.append(_("[B]%8s[/B]   %s   [COLOR grey]%s[/COLOR]") % (fmt_time(b["s"]), b["t"], extra))
    D.textviewer(_("%d %s - next 12 hours") % (ch["number"], ch["name"]),
                 "[CR]".join(lines) or _("Nothing scheduled - add programming to this channel."))


# ------------------------------------------------------------------ fine tuning
def raw_titles(ch):
    """Every show/movie title the channel's sources pull in (before hiding)."""
    out = set()
    for srcs in [ch.get("sources", [])] + [dp.get("sources", []) for dp in ch.get("dayparts", [])]:
        out.update(library.titles(library.resolve(srcs)))
    return out


def whats_on(ch):
    busy = xbmcgui.DialogProgress()
    busy.create(TITLE, _("Reading %s...") % ch["name"])
    titles = sorted(raw_titles(ch), key=library.natural_key)
    busy.close()
    if not titles:
        D.ok(TITLE, _("Nothing on this channel yet - add programming first."))
        return
    hidden = set(x.lower() for x in ch.get("exclude", []))
    pre = [t for t in titles if t.lower() not in hidden]
    sel = search_pick(_("Untick what doesn't belong on %s") % ch["name"], titles, multi=True, preselected=pre)
    if sel is None:
        return
    keep = set(t.lower() for t in sel)
    others = [x for x in ch.get("exclude", []) if x.lower() not in set(t.lower() for t in titles)]
    ch["exclude"] = others + [t for t in titles if t.lower() not in keep]


def _add_title(ch, title, is_movie):
    kind = "movie" if is_movie else "tvshow"
    for src in ch["sources"]:
        if src.get("type") == kind:
            v = src.get("value")
            v = v if isinstance(v, list) else [v]
            if title not in v:
                v.append(title)
            src["value"] = v
            return
    ch["sources"].append({"type": kind, "value": [title]})


def shows_and_channels():
    """Pick a show, tick the channels it should air on."""
    k = D.select(_("Move shows between channels"), [_("TV shows"), _("Movies")])
    if k < 0:
        return
    is_movie = k == 1
    chans = [c for c in C.load() if c["type"] in PROGRAM_TYPES]
    if not chans:
        D.ok(TITLE, _("No program channels yet."))
        return
    pd = xbmcgui.DialogProgress()
    pd.create(TITLE, _("Working out what airs where..."))
    raw = {}
    for i, c in enumerate(chans):
        pd.update(int(100.0 * i / len(chans)), c["name"])
        raw[c["id"]] = set(t.lower() for t in raw_titles(c))
    if is_movie:
        movies = library.all_movies(["title", "year"])
        items = sorted(set("%s (%s)" % (m["title"], m["year"]) if m.get("year") else m["title"]
                           for m in movies), key=library.natural_key)
    else:
        items = sorted(set(s["title"] for s in library.all_tvshows()), key=library.natural_key)
    pd.close()

    def on(c, title):
        t = title.lower()
        return t in raw[c["id"]] and t not in set(x.lower() for x in c.get("exclude", []))

    query = ""
    while True:
        det = {}
        for title in items:
            where = ", ".join("%d %s" % (c["number"], c["name"]) for c in chans if on(c, title))
            det[title] = where or _("[COLOR grey]not on any channel[/COLOR]")
        title = search_pick(_("Pick a %s, then tick its channels") % ("movie" if is_movie else "show"),
                            items, details=det, query=query)
        if not title:
            return
        query = getattr(search_pick, "last_query", "")
        labels = ["%3d  %s" % (c["number"], c["name"]) for c in chans]
        pre = [j for j, c in enumerate(chans) if on(c, title)]
        sel = D.multiselect(title, labels, preselect=pre)
        if sel is None:
            continue
        sel = set(sel)
        all_chans = C.load()
        by_id = dict((c["id"], c) for c in all_chans)
        for j, c0 in enumerate(chans):
            c = by_id[c0["id"]]
            was, want = on(c0, title), j in sel
            if want == was:
                continue
            ex = [x for x in c.get("exclude", []) if x.lower() != title.lower()]
            if want:
                c["exclude"] = ex
                if title.lower() not in raw[c["id"]]:
                    _add_title(c, title, is_movie)
                    raw[c["id"]].add(title.lower())
            else:
                c["exclude"] = ex + [title]
            c0.clear()
            c0.update(c)
        C.save(all_chans)


def check_fillers():
    paths = []
    for label, key in ((_("Commercials"), "commercials_path"), (_("Bumps"), "bumps_path")):
        if K.setting(key):
            paths.append((label, K.setting(key)))
    for c in C.load():
        for label, key in ((_("Commercials"), "commercials_path"), (_("Bumps"), "bumps_path")):
            if c.get(key):
                paths.append((_("%s for %s") % (label, c["name"]), c[key]))
    if not paths:
        D.ok(TITLE, _("No commercials or bumps folder is set.[CR]Set them in Settings > Programming."))
        return
    pd = xbmcgui.DialogProgress()
    pd.create(TITLE, _("Checking every clip (first time can take a while)..."))
    out = []
    for n, (label, path) in enumerate(paths):
        pd.update(int(100.0 * n / len(paths)), label)
        ok, bad, long_ = library.filler_report(path)
        out.append(_("[B]%s[/B]  [COLOR grey]%s[/COLOR]") % (label, path))
        if ok:
            out.append(_("  %d usable clips, %d minutes total, %ds to %ds long") % (
                len(ok), sum(ok) // 60, min(ok), max(ok)))
        else:
            out.append(_("  [COLOR red]No usable clips found[/COLOR]"))
        if bad:
            exts = sorted(set(os.path.splitext(b)[1].lower() for b in bad))
            out.append(_("  [COLOR orange]%d clips skipped - length unreadable (%s):[/COLOR]") % (len(bad), " ".join(exts)))
            out += ["     " + os.path.basename(b) for b in bad[:12]]
            if len(bad) > 12:
                out.append("     ...")
        if long_:
            out.append(_("  %d clips longer than 10 minutes skipped") % len(long_))
        out.append("")
    pd.close()
    library.clear_cache()
    out.append(_("Tip: a few dozen clips of mixed lengths (15/30/60s) fill breaks almost exactly. "
               "Unreadable files can be remuxed to .mp4 or .mkv."))
    D.textviewer(_("Commercial check"), "[CR]".join(out))


def help_text():
    return _("""[B]Remote control[/B]
CH+ / CH-, Up / Down, Page Up / Down ... change channel
Number keys ...................................... go to channel
Left ................................................... last channel
Right ................................................ what's on now
OK / Info ........................................... channel banner
Menu / Context ................................. sleep timer & more
Back / Stop ...................................... turn off the TV

[B]How the schedule works[/B]
Nothing to compile.  Each channel pulls from your Kodi library (shows, genres,
decades, movies, smart playlists) or from folders, and its schedule writes itself
as time goes by.  'Same show same time every day' channels air a fixed daily
lineup and series always continue with the next episode.  Time blocks let you put
cartoons on Saturday mornings or movies in prime time.

Edit a channel and its schedule rebuilds itself from now on - episode progress is kept.

[B]Fine-tuning[/B]
'Move shows between channels': pick a show (say, Good Eats) and tick the channels it
should air on.  Unticking hides it there even if the channel's genre includes it.
Each channel also has 'What's on this channel' - a checklist of everything it airs.

[B]Studio channels[/B]
Add programming > 'A studio / network' makes e.g. a Disney channel from every movie
and show whose studio contains 'Disney'.  Kodi tags work the same way.

[B]Commercials & bumps[/B]
Point Settings at a folder of commercials and (optionally) bumps.  Breaks are cut
into shows to fill each half hour, like real cable.  Movie channels play commercials
between films.  Without commercials the gap is filled with an 'Up next' card.
'Check my commercials & bumps' shows which clips can't be used.

[B]Files[/B]
Your lineup lives in userdata/addon_data/script.cablebox42/channels.json if you
prefer editing it by hand.""")


def main_menu():
    while True:
        chans = C.load()
        opts = []
        if chans:
            opts.append(("watch", _("[B]Watch TV[/B]")))
        opts += [("wizard", _("Build my lineup automatically")),
                 ("manager", _("Channel manager")),
                 ("shows", _("Move shows between channels")),
                 ("fillers", _("Check my commercials & bumps")),
                 ("rebuild", _("Rebuild schedules")),
                 ("settings", _("Settings")),
                 ("help", _("Help"))]
        i = D.select(TITLE, [o[1] for o in opts])
        if i < 0:
            return
        k = opts[i][0]
        if k == "watch":
            from . import tv
            tv.run()
            return
        if k == "wizard":
            wizard()
        elif k == "manager":
            manager()
        elif k == "shows":
            shows_and_channels()
        elif k == "fillers":
            check_fillers()
        elif k == "rebuild":
            rebuild_all()
        elif k == "settings":
            K.ADDON.openSettings()
        elif k == "help":
            D.textviewer(TITLE, help_text())
