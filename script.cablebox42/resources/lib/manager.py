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
from . import assign
from .kodiutil import _

D = xbmcgui.Dialog()
TITLE = "CableBox 42"
TYPE_LABELS = {"network": _("Network (series + commercials)"), "movies": _("Movie channel"),
               "loop": _("Loop (back-to-back, no clock)"), "guide": _("Guide channel"),
               "weather": _("Weather channel")}
PROGRAM_TYPES = ("network", "movies", "loop")
ALL_TYPES = ["network", "movies", "loop", "guide", "weather"]


# ------------------------------------------------------------------ helpers
def done_select(heading, rows, done_label=None, **kw):
    """Kodi's lists have no OK button: picking a row is the action and Back
    leaves.  Menus you come back to after each change get a 'Done' row at the
    bottom (Up from the first row jumps straight to it).  Done = Back = -1."""
    label = done_label or _("[B]Done[/B]")
    rows = list(rows)
    if rows and isinstance(rows[0], xbmcgui.ListItem):
        extra = xbmcgui.ListItem(label, _("Back to the previous screen"))
    else:
        extra = label
    i = D.select(heading, rows + [extra], **kw)
    return -1 if i == len(rows) else i


def describe_source(s):
    t = s.get("type")
    if t == "tvshow":
        v = s.get("value")
        v = v if isinstance(v, list) else [v]
        return _("Shows: ") + (", ".join(v[:3]) + (_(" +%d more") % (len(v) - 3) if len(v) > 3 else ""))
    if t == "tvgenre":
        return _("TV genre: %s") % s.get("value")
    if t == "alltv":
        return _("Every TV show")
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
    if t == "network":
        return _("Shows that aired on %s") % v
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
def ask_bumpers():
    """Setup: bumpers and station IDs - one shared folder, a folder per channel, or
    later.  Returns True if per-channel folders should be made once the channels exist."""
    if K.setting("bumps_path") or K.setting("stations_folder"):
        return False
    rows = [_menu_row(_("One folder for every channel"),
                      _("Choose a folder of bumps / station IDs (short clips played right before the "
                        "show comes back). All channels share it.")),
            _menu_row(_("A folder for each channel"),
                      _("Choose where (your media drive is best) - CableBox makes a folder per channel "
                        "with bumps, ids and commercials inside, ready for clips.")),
            _menu_row(_("Skip for now"), _("Add them later in Settings."))]
    j = D.select(_("Bumpers and station IDs"), rows, useDetails=True)
    if j == 0:
        p = D.browse(0, _("Bumps folder"), "video")
        if p:
            K.set_setting("bumps_path", p)
    elif j == 1:
        root = D.browse(3, _("Where should the channel folders go?"), "files", "", False, True)
        if root:
            K.set_setting("stations_folder", root)
            return True
    return False


def ask_music():
    """Background music for the guide and weather channels (setup wizard)."""
    if K.setting("guide_music_path") and K.setting("weather_music_path"):
        return
    if not D.yesno(TITLE, _("Do you have a folder of background music?[CR][CR]It plays behind the TV Guide "
                            "and Weather channels - smooth jazz and elevator music are the classic choice. "
                            "You can add this later in Settings."),
                   nolabel=_("Skip"), yeslabel=_("Choose folder")):
        return
    guide = D.browse(0, _("Music for the TV Guide channel"), "music")
    if not guide:
        return
    K.set_setting("guide_music_path", guide)
    if D.yesno(TITLE, _("Use the same music for the Weather Channel?"),
               nolabel=_("Choose another folder"), yeslabel=_("Yes, the same")):
        K.set_setting("weather_music_path", guide)
    else:
        weather = D.browse(0, _("Music for the Weather Channel"), "music")
        K.set_setting("weather_music_path", weather or guide)


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
    per_channel = ask_bumpers()

    ask_music()

    if not K.setting("weather_location") and not xbmc.getCondVisibility("Weather.IsFetched"):
        city = D.input(_("Your city for the Weather Channel (optional, e.g. Springfield, IL)"), "")
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
        C.renumber(new)
    if len([c for c in new if c["type"] in PROGRAM_TYPES]) == 0:
        D.ok(TITLE, _("I couldn't find any TV shows or movies in your Kodi library.[CR]"
                    "Scan your media into the library first, or add folder channels "
                    "in the Channel Manager."))
        return
    if i == 1:
        from . import stations
        have = set(c["type"] for c in chans)
        used_stations = set(c.get("station") for c in chans if c.get("station"))
        used = set(c["number"] for c in chans)
        start = max(used) + 1
        for c in new:
            if c["type"] in ("guide", "weather") and c["type"] in have:
                continue
            if c.get("broadcast") and any(x.get("broadcast") == c["broadcast"] for x in chans):
                continue                   # you already have that network
            if c.get("station") in used_stations:
                stations.drop(c)           # that station is already one of your channels
            fixed = C.fixed_number(c)
            if fixed is not None and fixed not in used:
                c["number"] = fixed
            else:
                while start in used or start in (C.WEATHER_NUMBER, C.NEWS_NUMBER):
                    start += 1
                c["number"] = start
            used.add(c["number"])
            chans.append(c)
    else:
        chans = new
    for c in chans:
        c.setdefault("callsign", C.callsign(c["name"]))
    overnight = D.yesno(TITLE, _("Sign channels off overnight, like real TV?[CR][CR]From 12 AM to 5 AM a "
                                 "'Please stand by' card shows; the guide and weather stay on."),
                        nolabel=_("No, run all night"), yeslabel=_("Yes (recommended)"))
    prime = D.yesno(TITLE, _("Give channels a prime-time lineup?[CR][CR]From 8 to 11 PM each channel airs its best "
                             "shows in fixed weekly slots (movie channels: a movie at 8). You can change any of "
                             "it in the weekly planner."),
                    nolabel=_("No thanks"), yeslabel=_("Yes (recommended)"))
    from . import presets
    if overnight:
        presets.set_overnight(chans)
    C.save(chans)
    if prime:
        pd = xbmcgui.DialogProgress()
        pd.create(TITLE, _("Building prime-time lineups..."))
        a, _changed = assign.refresh(chans)
        presets.prime_time(chans, a)
        pd.close()
        C.save(chans)
    prebuild()
    if per_channel:
        make_station_folders(ask=False, report=False)   # the channels exist now: lay out their folders
    D.textviewer(_("What I set up"), setup_summary(C.load()))
    if D.yesno(TITLE, _("Your lineup is ready.[CR][CR]Start watching?")):
        from . import tv
        tv.run()
        return True
    return False


def setup_summary(chans):
    """Plain-language overview of the lineup: each channel, its identity, where
    its programmes come from, and the station folders - plus where to go next."""
    from . import stations
    lines = [_("[B]Your channels[/B]")]
    for c in chans:
        st = stations.BY_ID.get(c.get("station") or "")
        ident = "%3d  [B]%s[/B]" % (c["number"], c["name"])
        if c.get("callsign"):
            ident += "  (%s)" % c["callsign"]
        if st:
            ident += _("  [COLOR grey]built-in station[/COLOR]")
        lines.append(ident)
        if c["type"] == "guide":
            lines.append(_("        Program guide for every channel"))
            continue
        if c["type"] == "weather":
            lines.append(_("        Local forecast (Settings > Weather)"))
            continue
        srcs = [describe_source(s) for s in c.get("sources", []) if not s.get("orphans")]
        if any(s.get("orphans") for s in c.get("sources", [])):
            srcs.append(_("shows whose genres are too small for a channel of their own"))
        if c.get("broadcast"):
            srcs.insert(0, _("a share of every genre, in a network-style day"))
        lines.append("        " + (", ".join(srcs)[:160] or _("no programming yet")))
        extra = []
        if c.get("brand_blocks"):
            extra.append(_("goes by %s at times") % ", ".join(b.get("name", "") for b in c["brand_blocks"]))
        if c.get("offair"):
            extra.append(_("signs off %s") % ", ".join("%s-%s" % (w["start"], w["end"]) for w in c["offair"]))
        if c.get("slots"):
            extra.append(_("%d pinned shows") % len(c["slots"]))
        if extra:
            lines.append("        [COLOR grey]%s[/COLOR]" % "; ".join(extra))
    root = K.setting("stations_folder")
    lines.append("")
    if root:
        lines.append(_("[B]Station folders[/B]  [COLOR grey]%s[/COLOR]") % root)
        for c in chans:
            if c["type"] in PROGRAM_TYPES:
                lines += folder_lines(c)
    else:
        lines.append(_("[B]Station folders[/B]  not set up - Settings > Tools > 'Station folders' gives "
                       "each channel a folder for its own logo, bumps, IDs and commercials."))
    lines += ["", _("[B]Next steps[/B]"),
              _("  Channel manager > a channel > Branding & clips: logo, bumps, IDs, commercials in use"),
              _("  Channel manager > Shows without a good channel: shows nothing picks up, or that only "
                "just fit"),
              _("  Closed captions: main menu, or the Menu button while watching"),
              _("  This summary again: Channel manager > Lineup summary")]
    return "[CR]".join(lines)


def prebuild(chans=None):
    lineup = scheduler.Lineup(K.schedule_cfg())
    if chans is not None:
        lineup.channels = chans
    lineup.refresh_assignment()
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
        top = [_("[B]+ Add a channel[/B]"), _("[B]Rearrange channel numbers[/B]"),
               _("[B]Shows without a good channel[/B]  [COLOR grey]unplaced or weakly matched[/COLOR]"),
               _("[B]Lineup summary[/B]  [COLOR grey]what's set up, and where[/COLOR]")]
        rows = list(top)
        for c in chans:
            rows.append(_("%3d   %s   [COLOR grey](%s, %d source%s)[/COLOR]") % (
                c["number"], c["name"], c["type"], len(c["sources"]),
                "" if len(c["sources"]) == 1 else "s"))
        i = done_select(_("Channel manager"), rows)
        if i < 0:
            refresh_assignments()
            return
        if i == 0:
            add_channel(chans)
        elif i == 1:
            rearrange()
        elif i == 2:
            from . import finder
            finder.run()
        elif i == 3:
            D.textviewer(_("Lineup summary"), setup_summary(chans))
        else:
            edit_channel(chans[i - len(top)]["id"])


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
        i = done_select(_("Pick a channel to move"), rows)
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
    changed = False
    while True:
        chans, ch = _find(cid)
        if not ch:
            return
        onoff = lambda b: _("On") if b else _("Off")
        items = [
            ("name", _("Name: %s") % ch["name"]),
            ("number", _("Number: %d") % ch["number"]),
            ("callsign", _("Call letters: %s") % ch.get("callsign", "")),
            ("station", _("Station: %s") % _station_label(ch)),
            ("blocks", _("Branding by time of day: %s") % _blocks_label(ch)),
            ("logo", _("Station logo: %s") % _logo_label(ch)),
            ("branding", _("[B]Branding & clips[/B] (logo, bumps, IDs, commercials in use)")),
            ("type", _("Type: %s") % TYPE_LABELS.get(ch["type"], ch["type"])),
            ("sources", _("Programming: %d source(s)") % len(ch["sources"])),
            ("planner", _("[B]Weekly planner[/B] (%d pinned shows)") % len(ch.get("slots", []))),
            ("dayparts", _("Time blocks (prime time, Saturday mornings...): %d") % len(ch["dayparts"])),
            ("offair", _("Off-air hours: %s") % (", ".join("%s-%s" % (w["start"], w["end"])
                                                       for w in ch["offair"]) or _("never"))),
            ("shows", _("[B]What's on this channel[/B] (%d hidden)") % len(ch.get("exclude", []))),
            ("commercials", _("Commercials: %s") % onoff(ch.get("commercials"))),
            ("midroll", _("Break into shows for commercials: %s") % onoff(ch.get("midroll", ch["type"] != "movies"))),
            ("bumps", _("Bumps: %s") % onoff(ch.get("bumps"))),
            ("lineup", _("Lineup style: %s") % (_("Same show same time every day") if ch.get("lineup") == "strip"
                                             else _("Shuffle"))),
            ("slot", _("Programs start on: %s") % ({0: _("no clock (back to back)"), 15: ":00 :15 :30 :45",
                                                 30: _(":00 and :30"), 60: _("the hour")}.get(ch.get("slot"),
                                                                                       str(ch.get("slot"))))),
            ("cpath", _("Channel commercials folder: %s") % (ch.get("commercials_path") or _("global"))),
            ("bpath", _("Channel bumps folder: %s") % (ch.get("bumps_path") or _("global"))),
            ("ids", _("Station ID clips (between programs): %s") % (
                os.path.basename(ch.get("ids_path", "").rstrip("/\\")) or _("none"))),
            ("preview", _("[B]Preview today's schedule[/B]")),
            ("delete", _("[COLOR red]Delete channel[/COLOR]")),
        ]
        i = done_select("%d  %s" % (ch["number"], ch["name"]), [x[1] for x in items])
        if i < 0:
            if changed:
                D.notification(TITLE, _("%s saved") % ch["name"], time=2000)
            return
        changed = True
        key = items[i][0]
        if key == "name":
            v = D.input(_("Name"), ch["name"])
            if v and v != ch["name"]:
                from . import stations
                old_folder = stations.channel_folder(ch)
                ch["name"] = v
                _folder_follows(ch, old_folder)
        elif key == "number":
            v = D.numeric(0, _("Move %s to channel") % ch["name"], str(ch["number"]))
            if v and int(v) > 0:
                move_channel(chans, ch, int(v))
        elif key == "callsign":
            v = D.input(_("Call letters"), ch.get("callsign", ""))
            from . import stations
            old_folder = stations.channel_folder(ch)
            ch["callsign"] = v.upper()[:6]
            _folder_follows(ch, old_folder)
        elif key == "logo":
            pick_logo(ch)
        elif key == "station":
            from . import stations
            old_folder = stations.channel_folder(ch)
            pick_station(ch)
            _folder_follows(ch, old_folder)
        elif key == "branding":
            C.save(chans)
            branding(ch, chans)
        elif key == "blocks":
            edit_brand_blocks(ch)
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
        elif key == "ids":
            j = D.select(_("Station ID clips"), [_("None"), _("Choose folder...")])
            if j == 0:
                ch.pop("ids_path", None)
            elif j == 1:
                p = D.browse(0, _("Station ID clips"), "video")
                if p:
                    ch["ids_path"] = p
        elif key == "planner":
            C.save(chans)
            from . import planner
            planner.open_planner(cid)
            continue
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


def _station_label(ch):
    from . import stations
    st = stations.BY_ID.get(ch.get("station") or "")
    return st["name"] if st else _("none (your own)")


def _blocks_label(ch):
    bl = ch.get("brand_blocks") or []
    return ", ".join("%s %s-%s" % (b.get("name", ""), b.get("start", ""), b.get("end", "")) for b in bl) or _("none")


def pick_station(ch):
    """Give the channel one of the built-in stations (name, call letters, logo,
    time-of-day branding), or go back to its own identity."""
    from . import stations
    opts = [_("None - use the channel's own name and logo")] + \
        ["%s   [COLOR grey]%s[/COLOR]" % (s["name"], ", ".join(b["name"] for b in s.get("blocks", [])))
         for s in stations.STATIONS]
    j = D.select(_("Station for channel %d") % ch["number"], opts)
    if j == 0:
        stations.drop(ch)
    elif j > 0:
        st = stations.STATIONS[j - 1]
        if D.yesno(TITLE, _("Rename this channel to %s and use its logo and call letters?") % st["name"]):
            stations.apply(ch, st)


def edit_brand_blocks(ch):
    """Times of day when the channel goes by another name and logo (CAM Jr. 6 AM-noon)."""
    while True:
        blocks = ch.setdefault("brand_blocks", [])
        rows = [_("[B]+ Add a time block[/B]")] + ["%s   %s - %s" % (b.get("name", ""), b.get("start", ""), b.get("end", ""))
                                                   for b in blocks]
        i = done_select(_("Branding by time of day"), rows)
        if i < 0:
            return
        if i == 0:
            name = D.input(_("Name during this block (e.g. CAM Jr.)"), "")
            if not name:
                continue
            a = ask_time(_("Starts at"), "06:00")
            b = ask_time(_("Ends at"), "12:00")
            if a and b:
                blocks.append({"name": name, "call": "", "start": a, "end": b})
            continue
        bl = blocks[i - 1]
        j = D.select(bl.get("name", ""), [_("Rename"), _("Change times"), _("Choose logo..."), _("Remove")])
        if j == 0:
            v = D.input(_("Name"), bl.get("name", ""))
            if v:
                bl["name"] = v
        elif j == 1:
            a = ask_time(_("Starts at"), bl.get("start", "06:00"))
            b = ask_time(_("Ends at"), bl.get("end", "12:00"))
            if a and b:
                bl["start"], bl["end"] = a, b
        elif j == 2:
            p = D.browse(2, _("Logo for %s") % bl.get("name", ""), "pictures", ".png|.jpg|.jpeg|.gif|.webp")
            if p:
                bl["logo_path"] = p
        elif j == 3:
            blocks.pop(i - 1)


# ------------------------------------------------------------------ branding & clips
def _folder_name(path):
    return path.rstrip("/\\").replace("\\", "/").split("/")[-1] if path else ""


def _logo_row(ch, ts=None):
    """(label, detail) for the logo the channel shows (at ts: a time block's own)."""
    from . import stations, logos
    br = stations.brand(ch, ts) if ts else stations.brand(dict(ch, brand_blocks=[]))
    path, src = br["logo"], br["logo_from"]
    if not path and src != "none":
        path = logos.logo_for(ch)
        src = "logofolder" if path else ""
    name = os.path.basename(path) if path else _("none")
    detail = {
        "picked": _("The image you chose in the channel editor (Station logo)."),
        "block_picked": _("The image you chose for this time block."),
        "folder": _("From the channel's station folder."),
        "block_folder": _("From this time block's own folder."),
        "builtin": _("CableBox's built-in station logo. Put a logo.png in the channel's folder to use your own."),
        "logofolder": _("Matched by name in the logo folder (Settings > Viewing)."),
        "none": _("Switched off in the channel editor (Station logo)."),
    }.get(src, _("No logo found. Put a logo.png in the channel's folder, or choose one under Station logo."))
    if src in ("folder", "block_folder") and os.path.splitext(name)[0].lower() != "logo":
        detail += _(" There's no logo.png, so the first image in the folder is used.")
    return _("Logo: %s") % name, detail


def _clip_row(ch, kind, folder):
    """(label, detail, switched_on) for bumps / ids / commercials, as the channel really uses them."""
    from . import stations
    label = {"bumps": _("Bumps"), "ids": _("Station IDs"), "commercials": _("Commercials")}[kind]
    on = True if kind == "ids" else bool(ch.get(kind))
    sub = stations.kind_folder(folder, kind)
    n = stations.count_clips(sub)
    own = {"bumps": ch.get("bumps_path"), "commercials": ch.get("commercials_path"), "ids": ch.get("ids_path")}[kind]
    glob = {"bumps": K.setting("bumps_path"), "commercials": K.setting("commercials_path"), "ids": ""}[kind]
    if not on:
        extra = _(" - %d clips in its folder aren't used") % n if n else ""
        return _("%s: off for this channel%s") % (label, extra), _("Select to switch them on."), False
    if n:
        return (_("%s: %d clips from the station folder") % (label, n),
                _("%s/%s - used before any other folder.") % (_folder_name(folder), _folder_name(sub)), True)
    note = _(" (its %s folder is empty)") % kind if sub else ""
    if own:
        return _("%s: channel folder %s") % (label, _folder_name(own)), _("Set in the channel editor.") + note, True
    if glob:
        return _("%s: shared folder %s") % (label, _folder_name(glob)), _("From Settings (all channels).") + note, True
    if kind == "commercials":
        return _("%s: none") % label, _("Breaks show an 'Up next' card. Add clips to the channel's "
                                         "commercials folder or set a folder in Settings.") + note, True
    return _("%s: none") % label, _("Add clips to the channel's %s folder.") % kind + note, True


def branding(ch, chans):
    """Channel editor > Branding & clips: what the channel really uses for its logo,
    bumps, station IDs and commercials, where each comes from, and its folders."""
    from . import stations
    while True:
        stations.clear_cache()
        root = K.setting("stations_folder")
        folder = stations.channel_folder(ch)
        rows, keys = [], []

        def add(key, label, detail=""):
            keys.append(key)
            rows.append(_menu_row(label, detail))
        add("logo", *_logo_row(ch))
        if not root:
            add("root", _("Station folder: not set up"),
                _("Select to choose where channel folders go (Settings > Viewing > Stations folder)."))
        elif folder:
            add("browse", _("Station folder: %s") % _folder_name(folder), _("Select to look inside. ") + folder)
        else:
            add("repair", _("Station folder: none yet"),
                _("Looking for a folder named %s in %s. Select to make it.") % (
                    " / ".join("'%s'" % n for n in stations.folder_names(ch)[:3]), root))
        for kind in ("bumps", "ids", "commercials"):
            label, detail, on = _clip_row(ch, kind, folder)
            add("" if on else "on:" + kind, label, detail)
        for b in ch.get("brand_blocks") or []:
            ts = _block_time(b)
            bf = stations.brand(ch, ts)["block_folder"] if ts is not None else ""
            counts = ", ".join("%s %d" % (k, stations.count_clips(stations.kind_folder(bf, k))) for k in CLIP_KINDS)
            add("", _("%s (%s-%s): %s") % (b.get("name", ""), b.get("start", ""), b.get("end", ""),
                                         _logo_row(ch, ts)[0] if ts is not None else ""),
                (_("Own folder %s: %s") % (_folder_name(bf), counts)) if bf else
                _("No folder of its own - the channel's clips are used. Repair folders to make one."))
        if root:
            add("repair", _("[B]Create or repair this channel's folders[/B]"),
                _("Adds what's missing (bumps, ids, commercials, time blocks). Never deletes anything."))
            orphans = stations.orphan_folders(chans)
            if orphans and not folder:
                add("adopt", _("Use an existing folder for this channel..."),
                    _("%d folders match no channel - e.g. one made before a rename.") % len(orphans))
        i = done_select(_("%s - branding & clips") % ch["name"], rows, useDetails=True)
        if i < 0:
            return
        key = keys[i]
        if key == "logo":
            pick_logo(ch)
        elif key == "root":
            _choose_root()
        elif key == "browse":
            D.browse(1, ch["name"], "files", "", False, False, folder)
        elif key == "repair":
            n = ensure_channel_folders(ch)
            D.notification(TITLE, _("%d folders made") % n if n else _("Nothing was missing"), time=2500)
        elif key == "adopt":
            orphans = stations.orphan_folders(chans)
            j = D.select(_("Which folder belongs to %s?") % ch["name"], orphans)
            if j >= 0:
                if stations.rename_folder(orphans[j], _safe_name(ch["name"])):
                    D.notification(TITLE, _("Renamed to %s") % _safe_name(ch["name"]), time=2500)
                else:
                    D.ok(TITLE, _("Couldn't rename the folder (a folder with that name may already exist)."))
        elif key.startswith("on:"):
            kind = key[3:]
            if D.yesno(TITLE, _("Switch %s on for %s?") % (kind, ch["name"])):
                ch[kind] = True
                C.save(chans)


def _choose_root():
    root = D.browse(3, _("Stations folder"), "files", "", False, True)
    if root:
        K.set_setting("stations_folder", root)


def _block_time(b):
    """A moment inside a branding block today (its start time), or None."""
    try:
        h, m = (int(x) for x in b.get("start", "").split(":"))
    except Exception:
        return None
    lt = time.localtime()
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, h, m, 30, 0, 0, -1))


def _folder_follows(ch, old_folder):
    """After a rename: if the channel's station folder no longer matches, offer to
    rename the folder too (never overwriting anything)."""
    from . import stations
    if not old_folder:
        return
    stations.clear_cache()
    if stations.channel_folder(ch):
        return
    old, new = _folder_name(old_folder), _safe_name(ch["name"])
    if D.yesno(TITLE, _("Rename its station folder too?[CR][CR]%s  ->  %s[CR][CR]Otherwise the channel stops using "
                        "that folder's logo and clips.") % (old, new),
               nolabel=_("Leave it"), yeslabel=_("Rename folder")):
        if not stations.rename_folder(old, new):
            D.ok(TITLE, _("Couldn't rename the folder (a folder with that name may already exist)."))


def _logo_label(ch):
    from . import logos
    if ch.get("logo") == "none":
        return _("none")
    if ch.get("logo"):
        return os.path.basename(ch["logo"])
    from . import stations
    st = stations.brand(dict(ch, brand_blocks=[]))["logo"]
    if st:
        return _("%s (station)") % os.path.basename(st)
    found = logos.logo_for(ch)
    return (_("%s (from the logo folder)") % os.path.basename(found)) if found else _("none")


def pick_logo(ch):
    from . import logos
    j = D.select(_("Station logo for %s") % ch["name"],
                 [_("Choose an image..."), _("Use the logo folder (matched by name, call letters or number)"),
                  _("No logo")])
    if j == 0:
        p = D.browse(2, _("Station logo (PNG with a transparent background looks best)"), "pictures",
                     "|".join(logos.IMAGE_EXT + (".svg",)))
        if p:
            if p.lower().endswith(".svg"):
                D.ok(TITLE, _("Kodi can't show SVG images.  Convert the logo to PNG (keeping the transparent "
                              "background) and choose that instead."))
                return
            ch["logo"] = p
    elif j == 1:
        ch.pop("logo", None)
        logos.clear_cache()
        if not K.setting("logo_folder"):
            D.ok(TITLE, _("Set the logo folder first: Settings > Viewing > Logo folder."))
    elif j == 2:
        ch["logo"] = "none"


def edit_sources(sources, name):
    while True:
        rows = [_("[B]+ Add programming[/B]")] + [describe_source(s) for s in sources]
        i = done_select(_("Programming on %s") % name, rows)
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
        i = done_select(_("Time blocks override the normal programming"), rows)
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


def _days_label(days):
    return dict((str(k), v) for k, v in DAY_OPTS).get(str(days if days is not None else "all"), _("Custom days"))


def pick_days(heading, current="all"):
    """Every day / weekdays / weekends / Saturdays / Sundays / pick days."""
    names = [_("Monday"), _("Tuesday"), _("Wednesday"), _("Thursday"), _("Friday"), _("Saturday"), _("Sunday")]
    opts = [x[1] for x in DAY_OPTS] + [_("Pick days...")]
    j = D.select(heading, opts)
    if j < 0:
        return None
    if j < len(DAY_OPTS):
        return DAY_OPTS[j][0]
    pre = current if isinstance(current, list) else []
    sel = D.multiselect(heading, names, preselect=pre)
    return sorted(sel) if sel else None


def edit_offair(ch):
    styles = [("standby", _("1950s 'Please stand by' test card")), ("bars", _("Color bars"))]
    while True:
        style = ch.get("offair_style", "standby")
        rows = [_("[B]+ Add off-air hours[/B]")]
        rows += ["%s - %s   %s" % (w["start"], w["end"], _days_label(w.get("days"))) for w in ch["offair"]]
        n = len(rows)
        rows += [_("Off-air screen: %s") % dict(styles).get(style, style),
                 _("Sign-off clip (anthem, farewell...): %s") % (
                     os.path.basename(ch.get("signoff_path", "").rstrip("/\\")) or _("none")),
                 _("Sign-on clip (morning start-up): %s") % (
                     os.path.basename(ch.get("signon_path", "").rstrip("/\\")) or _("none"))]
        i = done_select(_("Off-air hours"), rows)
        if i < 0:
            return
        if i == 0:
            a = ask_time(_("Sign off at"), "00:00")
            b = ask_time(_("Sign on at"), "07:00")
            if not (a and b):
                continue
            days = pick_days(_("Which nights?"))
            if days is None:
                continue
            ch["offair"].append({"start": a, "end": b, "days": days})
        elif i < n:
            w = ch["offair"][i - 1]
            j = D.select(rows[i], [_("Change times"), _("Change days"), _("Remove")])
            if j == 0:
                a = ask_time(_("Sign off at"), w["start"])
                b = ask_time(_("Sign on at"), w["end"])
                if a and b:
                    w["start"], w["end"] = a, b
            elif j == 1:
                days = pick_days(_("Which nights?"), w.get("days", "all"))
                if days is not None:
                    w["days"] = days
            elif j == 2:
                del ch["offair"][i - 1]
        elif i == n:
            j = D.select(_("Off-air screen"), [x[1] for x in styles])
            if j >= 0:
                ch["offair_style"] = styles[j][0]
        else:
            field = "signoff_path" if i == n + 1 else "signon_path"
            j = D.select(rows[i], [_("None"), _("Choose folder...")])
            if j == 0:
                ch.pop(field, None)
            elif j == 1:
                p = D.browse(0, rows[i], "video")
                if p:
                    ch[field] = p


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


def effective_titles(ch, assignment):
    """Titles this channel actually airs: its home shows + your explicit picks
    (automatic part), everything in its time blocks, minus anything hidden."""
    ok = assign.allowed_fn(assignment, ch["id"])
    hidden = set(x.lower() for x in ch.get("exclude", []))
    out = []
    pool = library.share(ch.get("sources", []), ch.get("part"), ch.get("own"), ch.get("not_genres"))
    out += [s["title"] for s in pool["series"] if ok(s["title"].lower(), False)]
    out += [i["title"] for i in pool["singles"] if ok(i["title"].lower(), True)]
    for dp in ch.get("dayparts", []):
        out += library.titles(library.share(dp.get("sources", []), dp.get("part"), dp.get("own"), dp.get("not_genres")))
    seen, res = set(), []
    for t in out:
        if t.lower() not in seen and t.lower() not in hidden:
            seen.add(t.lower())
            res.append(t)
    return res


def refresh_assignments():
    """Recompute every show's home channel after an edit (shows a progress box)."""
    pd = xbmcgui.DialogProgress()
    pd.create(TITLE, _("Working out which channel each show belongs on..."))
    try:
        a, _changed = assign.refresh(C.load())
    finally:
        pd.close()
    return a


def whats_on(ch):
    busy = xbmcgui.DialogProgress()
    busy.create(TITLE, _("Reading %s...") % ch["name"])
    others = [c for c in C.load() if c["id"] != ch["id"]] + [ch]
    a = assign.compute(others)
    titles = sorted(effective_titles(ch, a), key=library.natural_key)
    elsewhere = len(raw_titles(ch)) - len(titles) - len(ch.get("exclude", []))
    busy.close()
    if not titles:
        D.ok(TITLE, _("Nothing on this channel yet - add programming first."))
        return
    head = _("Untick what doesn't belong on %s") % ch["name"]
    if elsewhere > 0 and a.get("mode") != assign.MODE_OFF:
        D.notification(TITLE, _("%d more shows from this channel's sources air on their own home channels") % elsewhere,
                       time=4000)
    sel = search_pick(head, titles, multi=True, preselected=list(titles))
    if sel is None:
        return
    keep = set(t.lower() for t in sel)
    ch["exclude"] = [x for x in ch.get("exclude", []) if x.lower() not in set(t.lower() for t in titles)] + \
        [t for t in titles if t.lower() not in keep]


def _add_title(ch, title, is_movie):
    """Your explicit pick: airs on this channel even if its home is elsewhere."""
    kind = "movie" if is_movie else "tvshow"
    for src in ch["sources"]:
        if src.get("type") == kind and src.get("explicit"):
            v = src.get("value")
            v = v if isinstance(v, list) else [v]
            if title not in v:
                v.append(title)
            src["value"] = v
            return
    ch["sources"].append({"type": kind, "value": [title], "explicit": True})


def _remove_pick(ch, title):
    for src in ch.get("sources", []):
        if src.get("explicit") and isinstance(src.get("value"), list):
            src["value"] = [v for v in src["value"] if v.lower() != title.lower()]
    ch["sources"] = [s for s in ch.get("sources", []) if not (s.get("explicit") and not s.get("value"))]


def shows_and_channels():
    """Pick a show, tick the channels it should air on."""
    k = D.select(_("Move shows between channels"), [_("TV shows"), _("Movies")])
    if k < 0:
        return
    is_movie = k == 1
    if not [c for c in C.load() if c["type"] in PROGRAM_TYPES]:
        D.ok(TITLE, _("No program channels yet."))
        return
    pd = xbmcgui.DialogProgress()
    pd.create(TITLE, _("Working out what airs where..."))
    state = {}

    def recompute():
        chans = [c for c in C.load() if c["type"] in PROGRAM_TYPES]
        a = assign.compute(C.load())
        state["chans"] = chans
        state["on"] = dict((c["id"], set(t.lower() for t in effective_titles(c, a))) for c in chans)
    recompute()
    if is_movie:
        movies = library.all_movies(["title", "year"])
        items = sorted(set("%s (%s)" % (m["title"], m["year"]) if m.get("year") else m["title"]
                           for m in movies), key=library.natural_key)
    else:
        items = sorted(set(s["title"] for s in library.all_tvshows()), key=library.natural_key)
    pd.close()

    def on(c, title):
        return title.lower() in state["on"][c["id"]]

    query = ""
    changed = False
    while True:
        chans = state["chans"]
        det = {}
        for title in items:
            where = ", ".join("%d %s" % (c["number"], c["name"]) for c in chans if on(c, title))
            det[title] = where or _("[COLOR grey]not on any channel[/COLOR]")
        title = search_pick(_("Pick a %s, then tick its channels") % ("movie" if is_movie else "show"),
                            items, details=det, query=query)
        if not title:
            break
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
                _add_title(c, title, is_movie)
            else:
                _remove_pick(c, title)
                c["exclude"] = ex + [title]
        C.save(all_chans)
        changed = True
        recompute()
    if changed:
        refresh_assignments()


def clean_in_progress():
    """Clear resume points left by channel surfing (before CableBox protected them)."""
    from . import progress
    items = progress.in_progress_items()
    if not items:
        D.ok(TITLE, _("Nothing is marked 'in progress'."))
        return
    labels = [i[0] for i in items]
    det = dict((i[0], _("stopped at %d of %d min") % (int(i[3].get("position", 0)) // 60,
                                                      int(i[3].get("total", 0)) // 60)) for i in items)
    keep = search_pick(_("Tick what you're REALLY in the middle of - the rest is cleared"), labels,
                       multi=True, preselected=[], details=det)
    if keep is None:
        return
    keep = set(keep)
    clear = [i for i in items if i[0] not in keep]
    if not clear or not D.yesno(TITLE, _("Clear the resume point of %d items?[CR](%d kept)") % (len(clear), len(keep))):
        return
    for _label, kind, item, _r in clear:
        progress.clear_resume(kind, item)
    D.notification(TITLE, _("Cleared %d items") % len(clear), time=3000)


def quick_setup():
    """One-step changes for every channel at once."""
    from . import presets
    while True:
        opts = [_("Sign off overnight on all channels (choose hours)"),
                _("Never sign off (remove off-air hours from all channels)"),
                _("Build prime-time lineups on all channels (choose hours)"),
                _("Remove the automatic prime-time lineups")]
        i = done_select(_("Quick setup"), opts)
        if i < 0:
            return
        chans = C.load()
        if i == 0:
            a = ask_time(_("Sign off at"), presets.OFF_START)
            b = ask_time(_("Back on the air at"), presets.OFF_END)
            if not (a and b):
                continue
            presets.set_overnight(chans, a, b)
            C.save(chans)
            D.notification(TITLE, _("Channels now sign off %s - %s") % (a, b), time=3000)
        elif i == 1:
            presets.clear_overnight(chans)
            C.save(chans)
        elif i == 2:
            a = ask_time(_("Prime time starts at"), presets.PRIME_START)
            b = ask_time(_("Prime time ends at"), presets.PRIME_END)
            if not (a and b):
                continue
            pd = xbmcgui.DialogProgress()
            pd.create(TITLE, _("Building prime-time lineups..."))
            asg, _changed = assign.refresh(chans)
            made = presets.prime_time(chans, asg, a, b)
            pd.close()
            C.save(chans)
            D.ok(TITLE, _("Prime-time lineups built for %d channels.[CR]See them in the weekly planner - "
                          "change or remove any slot there.") % len(made))
        elif i == 3:
            presets.clear_prime(chans)
            C.save(chans)
        refresh_assignments()


def check_fillers():
    paths = []
    for label, key in ((_("Commercials"), "commercials_path"), (_("Bumps"), "bumps_path")):
        if K.setting(key):
            paths.append((label, K.setting(key)))
    for c in C.load():
        for label, key in ((_("Commercials"), "commercials_path"), (_("Bumps"), "bumps_path")):
            if c.get(key):
                paths.append((_("%s for %s") % (label, c["name"]), c[key]))
    chans = [c for c in C.load() if c["type"] in PROGRAM_TYPES]
    pd = xbmcgui.DialogProgress()
    pd.create(TITLE, _("Checking every clip (first time can take a while)..."))
    out = []
    if library.av1_blocked():
        out.append(_("[B]AV1 videos[/B]  [COLOR grey]this box can't decode AV1 in hardware, so CableBox skips them[/COLOR]"))
        library.clear_cache()
        found = False
        for n, c in enumerate(chans):
            pd.update(int(50.0 * n / max(1, len(chans))), c["name"])
            for srcs in [c.get("sources", [])] + [dp.get("sources", []) for dp in c.get("dayparts", [])] + \
                    [r.get("sources", []) for r in c.get("slots", [])]:
                library.resolve(srcs)
                skipped = library.SKIPPED.get(library.json.dumps(srcs, sort_keys=True)) or []
                if skipped:
                    found = True
                    out.append(_("  %d  %s: %s") % (c["number"], c["name"], ", ".join(skipped[:8]) +
                                                     (" ..." if len(skipped) > 8 else "")))
        if not found:
            out.append(_("  None in your channels."))
        out.append("")
    for n, (label, path) in enumerate(paths):
        pd.update(int(100.0 * n / len(paths)), label)
        ok, bad, long_, av1 = library.filler_report(path)
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
        if av1:
            out.append(_("  [COLOR orange]%d AV1 clips skipped (no hardware decoding):[/COLOR]") % len(av1))
            out += ["     " + os.path.basename(b) for b in av1[:12]]
            if len(av1) > 12:
                out.append("     ...")
        out.append("")
    pd.close()
    library.clear_cache()
    bad_now = library.bad_files()
    out.insert(0, "")
    if bad_now:
        out[0:0] = [_("[B]Videos that wouldn't play[/B]  [COLOR grey]kept off the air for 3 days, "
                      "then tried again[/COLOR]")] + \
            ["  %s  [COLOR grey]%s[/COLOR]" % (os.path.basename(p), time.strftime("%b %d %H:%M", time.localtime(at)))
             for p, at, _why in bad_now[:30]] + (["  ..."] if len(bad_now) > 30 else []) + \
            [_("  Check that each file plays from Kodi's own menus.  A damaged file can often be "
               "re-downloaded or remuxed.")]
    else:
        out[0:0] = [_("[B]Videos that wouldn't play[/B]  [COLOR grey]none[/COLOR]")]
    out.append(_("Tip: a few dozen clips of mixed lengths (15/30/60s) fill breaks almost exactly. "
               "Unreadable files can be remuxed to .mp4 or .mkv; AV1 videos can be re-encoded to H.264 or H.265."))
    D.textviewer(_("Video check"), "[CR]".join(out))
    if bad_now and D.yesno(TITLE, _("%d videos are being kept off the air because they wouldn't play.[CR][CR]"
                                    "Fixed them?  Put them back on the schedule now.") % len(bad_now),
                           nolabel=_("Leave them off"), yeslabel=_("Try them again")):
        library.forget_bad()


def help_text():
    return _("""[B]Remote control[/B]
CH+ / CH-, Up / Down, Page Up / Down ... change channel
Number keys ...................................... go to channel
Left ................................................... last channel
Right ................................................ what's on now
OK / Info ........................................... channel banner
Menu / Context ............ captions, sleep timer & more
Back / Stop ...................................... turn off the TV

[B]Closed captions[/B]
Main menu > Closed captions, or the Menu button while watching, switches captions
on or off for every programme (like a TV's CC setting).  'Caption options' in that
menu picks a track or loads a subtitle file.  To use the remote's subtitle button,
run Settings > Tools > Remote CC button once.

[B]Station folders[/B]
Set a Stations folder (Settings > Viewing) and CableBox keeps one folder per channel,
named after the channel (or its call letters, or 'Channel 7'): logo.png, bumps/,
ids/ and commercials/, plus a folder per time block such as CAM Jr.  Channel
manager > channel > Branding & clips shows what the channel really uses and where
it comes from, and makes or repairs its folders.  Renaming a channel offers to
rename its folder too.

[B]How the schedule works[/B]
Nothing to compile.  Each channel pulls from your Kodi library (shows, genres,
decades, movies, smart playlists) or from folders, and its schedule writes itself
as time goes by.  'Same show same time every day' channels air a fixed daily
lineup and series always continue with the next episode.  Time blocks let you put
cartoons on Saturday mornings or movies in prime time.

Edit a channel and its schedule rebuilds itself from now on - episode progress is kept.

[B]One channel per show[/B]
Each TV show has one home channel - the one it fits best (your own picks first,
then folders/tags/studios, then its main genre).  A show whose genres are too
small for a channel of their own goes on the biggest genre network.  And the same show is never on two channels at the same time.
Settings > Programming > 'Shows on more than one channel' changes this.

[B]Menu and tools[/B]
The menu keeps to the everyday things: Watch TV, What's on now (tune straight to a
show), the Channel manager, the Weekly planner, Settings and Help.  Lineup tools
(build a new lineup, quick setup, move shows) and maintenance (check my videos,
clean up In progress, rebuild schedules, start over) are on the Tools page in Settings.

[B]Fine-tuning[/B]
Settings > Tools > 'Move shows between channels': pick a show (say, Good Eats) and tick the channels it
should air on.
Unticking hides it there even if the channel's genre includes it.
Each channel also has 'What's on this channel' - a checklist of everything it airs.
Channel manager > 'Shows without a good channel' lists shows no channel picks up
and shows that only just fit where they are, with the reason, so you can move them.

[B]Studio channels[/B]
Add programming > 'A studio / network' makes e.g. a Disney channel from every movie
and show whose studio contains 'Disney'.  Kodi tags work the same way.

[B]Weekly planner[/B]
Each channel has a 7-day grid (Channel manager > channel > Weekly planner, or
Weekly planner in the main menu).  Press OK on a half-hour to pin a show there -
e.g. Seinfeld, Fridays 8:00 PM, one hour, in order: every week it continues with
the next episodes.  Pinned slots always start on time; the automatic scheduler
fills everything else and never runs into them.  You can also paint off-air
hours, copy a day to other days, or clear a day (Menu button).

[B]Your watch progress[/B]
CableBox puts back resume points, watched status and last-played dates after it
airs something, so surfing doesn't fill your 'In progress' list (Settings >
Viewing).  Settings > Tools > 'Clean up my In progress list' tidies up an older list.

[B]Quick setup[/B]
Settings > Tools > Quick setup: overnight sign-off (default 12 AM - 5 AM) and automatic
prime-time lineups (default 8 - 11 PM) for every channel at once.  Prime-time
slots appear in the weekly planner; edit any of them and it becomes yours.

[B]Holidays[/B]
Halloween (October, all-out on the 31st), Thanksgiving Day and Christmas (from the day
after Thanksgiving, all-out on the 24th and 25th): each channel mixes in its own holiday
episodes and movies (Kodi tags first, then genres such as Horror and Mystery, then titles) - a few at
first, more as the day gets closer, all day on the day itself.  Optional holiday
commercial and bump folders.  The rest of the year Christmas and Thanksgiving episodes
are saved for their season.  Settings > Seasons.

[B]Off the air[/B]
Off-air hours show a 1950s 'Please stand by' test card (or color bars), with an
optional sign-off clip (anthem, farewell) and sign-on clip from your own folders.

[B]Station IDs[/B]
Give a channel a folder of station ID clips ("You're watching...") and one plays
between programs, right before the next show starts.

[B]Commercials & bumps[/B]
Point Settings at a folder of commercials and (optionally) bumps.  Breaks are cut
into shows to fill each half hour, like real cable.  Movie channels play commercials
between films.  Without commercials the gap is filled with an 'Up next' card.
'Check my commercials & bumps' shows which clips can't be used.

[B]Files[/B]
Your lineup lives in userdata/addon_data/script.cablebox42/channels.json if you
prefer editing it by hand.

[B]Step-by-step guide[/B]
HOWTO.md in the add-on's folder, or online:
github.com/SeadogMcGrog/script.cablebox42/blob/main/HOWTO.md

[B]About[/B]
CableBox 42 is designed, tested and maintained by Seadog McGrog.  Much of the code
was written with the help of Claude, an AI assistant made by Anthropic.  Anthropic is
not affiliated with this project and has not reviewed or endorsed it.
Inspired by FieldStation42 by Shane Mason (no shared code).""")


def _menu_row(label, desc):
    li = xbmcgui.ListItem(label, desc)
    return li


def whats_on_now():
    """Every channel with what's airing right now; pick one to tune straight to it."""
    from .tv import fmt_time
    lineup = scheduler.Lineup(K.schedule_cfg())
    now = time.time()
    chans = [c for c in lineup.channels]
    rows = []
    for c in chans:
        b = lineup.schedule(c, ensure=False).block_at(now)
        if b:
            title = b["t"]
            when = "%s - %s" % (fmt_time(b["s"]), fmt_time(b["e"]))
            sub = " ".join(x for x in (b.get("lb", ""), b.get("sub", "")) if x)
            desc = "%s   %s" % (when, sub) if sub else when
        else:
            title, desc = _("Listings not ready yet"), ""
        rows.append(_menu_row("%3d  %s   [COLOR grey]%s[/COLOR]" % (c["number"], c["name"], title), desc))
    if not rows:
        return None
    i = D.select(_("What's on now"), rows, useDetails=True)
    return chans[i]["number"] if i >= 0 else None


def pick_planner_channel():
    progs = [c for c in C.load() if c["type"] in PROGRAM_TYPES]
    if not progs:
        D.ok(TITLE, _("Add a channel first."))
        return
    j = D.select(_("Plan which channel?"), ["%3d  %s" % (c["number"], c["name"]) for c in progs])
    if j >= 0:
        from . import planner
        planner.open_planner(progs[j]["id"])


# Tools reached from Settings > Tools (RunScript(script.cablebox42,tool,<name>)).
TOOLS = {
    "wizard": lambda: wizard(),
    "quick": lambda: quick_setup(),
    "shows": lambda: shows_and_channels(),
    "fillers": lambda: check_fillers(),
    "progress": lambda: clean_in_progress(),
    "rebuild": lambda: rebuild_all(),
    "folders": lambda: make_station_folders(),
    "reset": lambda: factory_reset(),
    "cckeys": lambda: cc_button(),
    "finder": lambda: run_finder(),
}


def run_finder():
    from . import finder
    finder.run()


def cc_button():
    """Settings > Tools > Remote CC button."""
    from . import captions
    captions.keymap_tool()
TOOL_BUSY = "script.cablebox42.tool"

CLIP_KINDS = ("bumps", "ids", "commercials")

# CableBox's own data (in its profile folder).  durations.json / codecs.json are
# only a cache of how long each video is and how it's encoded - kept, so a fresh
# setup doesn't have to measure the whole library again.
RESET_FILES = ("channels.json", "assign.json", "state.json", "unplayable.json", "weather_cache.json",
               "finder.json")


def default_settings():
    """{setting id: default value} from resources/settings.xml."""
    import xml.dom.minidom
    out = {}
    try:
        doc = xml.dom.minidom.parse(os.path.join(K.ADDON_PATH, "resources", "settings.xml"))
        for el in doc.getElementsByTagName("setting"):
            sid = el.getAttribute("id")
            if sid and el.getAttribute("type") not in ("action", "lsep", "sep"):
                out[sid] = el.getAttribute("default")
    except Exception as exc:
        K.log_err("settings defaults: %s" % exc)
    return out


def factory_reset():
    """Settings > Tools: back to a fresh install - channels, schedules, planner pins,
    show assignments, weather cache, 'wouldn't play' list; optionally all settings.
    Never touches videos, bumps, commercials or station folders."""
    import shutil
    from . import progress, library, stations
    if not D.yesno(TITLE, _("Start over with a fresh CableBox?[CR][CR]This deletes your channels, weekly-planner "
                            "pins and schedules. Your videos, bumps, commercials and station folders are not "
                            "touched."), nolabel=_("Cancel"), yeslabel=_("Continue")):
        return False
    j = D.select(_("Also reset all CableBox settings?"),
                 [_("Keep my settings (commercials, bumps, music folders, weather...)"),
                  _("Reset settings to the defaults too")])
    if j < 0:
        return False
    if not D.yesno(TITLE, _("Last chance: this can't be undone.[CR][CR]Start over now?"),
                   nolabel=_("Cancel"), yeslabel=_("Start over")):
        return False
    # put back any watch progress CableBox still owes the library before wiping
    try:
        progress.repair_pending()
    except Exception as exc:
        K.log_err("reset: progress repair: %s" % exc)
    for name in RESET_FILES:
        try:
            os.remove(os.path.join(K.PROFILE, name))
        except OSError:
            pass
    shutil.rmtree(K.SCHEDULE_DIR, ignore_errors=True)
    if j == 1:
        for sid, val in default_settings().items():
            try:
                K.set_setting(sid, val)
            except Exception as exc:
                K.log_err("reset setting %s: %s" % (sid, exc))
    library.clear_cache()
    stations.clear_cache()
    K.ensure_dirs()
    D.notification(TITLE, _("CableBox has been reset"), time=3000)
    welcome()
    return True


def _safe_name(name):
    """A channel name usable as a folder name on any system."""
    import re
    return re.sub(r'[\\/:*?"<>|]+', " ", name).strip(" .") or "Channel"


def make_station_folders(ask=True, report=True):
    """Settings > Tools: one folder per channel (bumps / ids / commercials, plus a
    folder per time block) inside the stations folder, so clips can just be dropped
    in - then a report of which folder each channel uses and what's in it."""
    root = K.setting("stations_folder")
    if not root:
        if ask and not D.yesno(TITLE, _("Choose where your station folders should go.[CR][CR]CableBox makes one folder per "
                                "channel, with bumps, ids and commercials inside - drop clips (and a logo.png) in "
                                "and CableBox picks them up."), nolabel=_("Cancel"),
                       yeslabel=_("Choose folder")):
            return
        root = D.browse(3, _("Stations folder"), "files", "", False, True)
        if not root:
            return
        K.set_setting("stations_folder", root)
    from . import stations
    stations.clear_cache()
    chans = C.load()
    made = 0
    for c in chans:
        if c["type"] in PROGRAM_TYPES:
            made += ensure_channel_folders(c)
    stations.clear_cache()
    if not report:
        return made
    lines = [_("[B]Station folders[/B]  [COLOR grey]%s[/COLOR]") % root,
             _("%d new folders made - nothing that was already there was changed.") % made, ""]
    for c in chans:
        if c["type"] in PROGRAM_TYPES:
            lines += folder_lines(c)
    orphans = stations.orphan_folders(chans)
    if orphans:
        lines += ["", _("[B]Folders no channel uses[/B]  [COLOR grey]renamed channels? Rename the folder to the "
                        "channel's name, or use the channel's Branding & clips screen[/COLOR]")]
        lines += ["  " + o for o in orphans]
    lines += ["", STATION_FOLDER_GUIDE]
    D.textviewer(_("Station folders"), "[CR]".join(lines))


STATION_FOLDER_GUIDE = _("[B]What goes where[/B]  (in each channel's folder)[CR]"
                         "  logo.png ............ the channel's logo (transparent PNG looks best)[CR]"
                         "  bumps/ .............. short clips before the show comes back[CR]"
                         "  ids/ .................. station IDs, between programmes[CR]"
                         "  commercials/ ...... this channel's own commercials[CR]"
                         "  <time block>/ ...... the same again, used only in that block (e.g. CAM Jr.)[CR]"
                         "A folder is matched by the channel's name, call letters or number ('Channel 7'). "
                         "A new logo shows within a couple of minutes; new clips go into the breaks CableBox "
                         "plans from then on (Tools > Rebuild schedules uses them straight away).")


def ensure_channel_folders(c):
    """Make what's missing of a channel's folder: its existing folder (by name,
    call letters or number) is used as it is, never a second copy.  Returns the
    number of folders made."""
    import xbmcvfs
    from . import stations
    root = K.setting("stations_folder")
    if not root:
        return 0
    sep = "" if root.endswith(("/", "\\")) else "/"
    made = 0
    base = stations.channel_folder(c) or (root + sep + _safe_name(c["name"]) + "/")
    targets = [base]
    for b in c.get("brand_blocks") or []:
        stations.clear_cache()
        bf = stations._subfolder(base, b.get("name"), b.get("call"), loose=True) if xbmcvfs.exists(base) else ""
        targets.append(bf or (base + _safe_name(b.get("name", "")) + "/"))
    for t in targets:
        for k in CLIP_KINDS:
            stations.clear_cache()
            if xbmcvfs.exists(t) and stations.kind_folder(t, k):
                continue
            d = t + k + "/"
            if not xbmcvfs.exists(d):
                xbmcvfs.mkdirs(d)
                made += 1
    stations.clear_cache()
    return made


def folder_lines(c):
    """One channel in the folder report: its folder and what's in it."""
    from . import stations
    f = stations.channel_folder(c)
    head = "%3d  %s" % (c["number"], c["name"])
    if not f:
        return [_("%s   [COLOR orange]no folder[/COLOR]") % head]
    counts = ", ".join("%s %d" % (k, stations.count_clips(stations.kind_folder(f, k))) for k in CLIP_KINDS)
    logo = stations._image_in(f)
    out = [_("%s   [COLOR grey]%s[/COLOR]") % (head, f.rstrip("/\\").replace("\\", "/").split("/")[-1]),
           _("        %s   logo: %s") % (counts, os.path.basename(logo) if logo else _("none"))]
    for b in c.get("brand_blocks") or []:
        bf = stations._subfolder(f, b.get("name"), b.get("call"), loose=True)
        if bf:
            bc = ", ".join("%s %d" % (k, stations.count_clips(stations.kind_folder(bf, k))) for k in CLIP_KINDS)
            out.append(_("        %s: %s") % (b.get("name", ""), bc))
    return out


def run_tool(name):
    fn = TOOLS.get(name)
    if fn is None:
        return
    home = xbmcgui.Window(10000)
    home.setProperty(TOOL_BUSY, name)
    try:
        fn()
    finally:
        home.clearProperty(TOOL_BUSY)


def open_settings():
    """Settings; if a tool was started from its Tools page, wait for it to
    finish before showing the menu again (so two dialogs never collide)."""
    K.ADDON.openSettings()
    home = xbmcgui.Window(10000)
    mon = xbmc.Monitor()
    for _i in range(8):                      # the tool starts a moment after Settings closes
        if home.getProperty(TOOL_BUSY) or mon.waitForAbort(0.25):
            break
    while home.getProperty(TOOL_BUSY) and not mon.waitForAbort(0.3):
        pass


def welcome():
    """First start on a new install.  Returns True if the viewer went on to watch TV."""
    rows = [_menu_row(_("[B]Set it all up for me[/B]"),
                      _("Reads your Kodi library and builds a full lineup - channels, guide, weather, "
                        "overnight sign-off, prime time. About a minute.")),
            _menu_row(_("I'll set it up myself"),
                      _("Starts with just the TV Guide and Weather Channel. You add channels in the "
                        "Channel manager.")),
            _menu_row(_("Not now"), _("Go to the menu. You'll be asked again next time."))]
    i = D.select(_("Welcome to CableBox 42"), rows, useDetails=True)
    if i == 0:
        return bool(wizard())
    if i == 1:
        from . import stations
        chans = [C.new_channel(2, _("TV Guide"), "guide"), C.new_channel(C.WEATHER_NUMBER, _("Weather Channel"), "weather")]
        stations.assign(chans)
        for c in chans:
            c["callsign"] = C.callsign(c["name"])
        C.save(chans)
        D.ok(TITLE, _("You have a TV Guide on 2 and Retrocast Weather on 25.[CR][CR]"
                      "Next: Channel manager > Add a channel.  Commercials, bumps and music folders are "
                      "in Settings, and Settings > Tools > 'Build my lineup automatically' can still build "
                      "channels for you any time."))
        manager()
    return False


def captions_on():
    """The TV's CC setting, the same one the in-TV menu switches."""
    return K.load_json(K.STATE_FILE, {}).get("cc_on") is True


def main_menu():
    if not os.path.exists(K.CHANNELS_FILE) and welcome():
        return
    while True:
        chans = C.load()
        if chans:
            start = K.setting_int("start_channel", 0)
            opts = [("watch", _("[B]Watch TV[/B]"),
                     (_("Start on channel %d") % start) if start else _("Pick up where you left off")),
                    ("now", _("What's on now"), _("See every channel's current show and tune straight to it")),
                    ("cc", _("Closed captions: %s") % (_("On") if captions_on() else _("Off")),
                     _("On or off for every programme. While watching: the Menu button")),
                    ("manager", _("Channel manager"), _("Add, edit, rename and renumber channels")),
                    ("planner", _("Weekly planner"), _("Pin shows to days and times")),
                    ("settings", _("Settings and tools"),
                     _("Commercials, music, weather, picture - plus lineup tools and maintenance")),
                    ("help", _("Help"), _("How everything works"))]
        else:
            opts = [("wizard", _("[B]Set up my channels[/B]"), _("Builds a lineup from your Kodi library in a minute")),
                    ("settings", _("Settings and tools"), _("Commercials, music, weather, picture")),
                    ("help", _("Help"), _("How everything works"))]
        i = done_select(TITLE, [_menu_row(o[1], o[2]) for o in opts], useDetails=True, done_label=_("[B]Close[/B]"))
        if i < 0:
            return
        k = opts[i][0]
        if k == "watch":
            from . import tv
            tv.run()
            return
        if k == "now":
            n = whats_on_now()
            if n is not None:
                from . import tv
                tv.run(n)
                return
        elif k == "wizard":
            if wizard():
                return  # watched TV straight after the wizard - don't reopen the menu
        elif k == "cc":
            on = not captions_on()
            st = K.load_json(K.STATE_FILE, {})
            st["cc_on"] = on
            K.save_json(K.STATE_FILE, st)
            D.notification(TITLE, _("Closed captions on") if on else _("Closed captions off"), time=2000)
        elif k == "manager":
            manager()
        elif k == "planner":
            pick_planner_channel()
        elif k == "settings":
            open_settings()
        elif k == "help":
            D.textviewer(TITLE, help_text())
