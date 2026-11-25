"""Add-on menus: lineup wizard and the channel manager.

Everything is done with Kodi's own dialogs, so it works with the remote on
any skin.  Changes apply from each channel's next programme: closing Settings,
the Channel manager, the Weekly planner or a tool refreshes the schedules if
anything they're planned from changed (refresh_if_changed); what's on air and
every show's next episode stay.
"""
import json
import os
import threading
import time

import xbmc
import xbmcgui

from . import kodiutil as K
from . import channels as C
from . import library
from . import scheduler
from . import assign
from . import stations
from .kodiutil import _

D = xbmcgui.Dialog()
TITLE = "CableBox 42"
TYPE_LABELS = {"network": _("Network (series + commercials)"), "movies": _("Movie channel"),
               "loop": _("Loop (back-to-back, no clock)"), "guide": _("Guide channel"),
               "weather": _("Weather channel"), "extras": _("Behind the scenes (movie extras)"),
               "musicvideos": _("Music videos (real clock, breaks between videos)"),
               "music": _("Music channel (songs around the clock, no breaks)")}
PROGRAM_TYPES = ("network", "movies", "loop")
AIR_TYPES = PROGRAM_TYPES + ("musicvideos",)    # channels whose programming comes from sources
CLIP_TYPES = AIR_TYPES + ("extras",)            # channels with breaks: station folders, clips
ALL_TYPES = ["network", "movies", "loop", "musicvideos", "music", "guide", "weather", "extras"]
# a channel's type in a word or two (Channel manager rows)
TYPE_SHORT = {"network": _("Network"), "movies": _("Movies"), "loop": _("Loop"), "guide": _("Guide"),
              "weather": _("Weather"), "extras": _("Behind the scenes"), "musicvideos": _("Music videos"),
              "music": _("Music channel")}
# channel editor rows that mean nothing on a Behind the scenes channel
EXTRAS_HIDDEN = ("sources", "planner", "dayparts", "shows", "lineup", "slot")
# ... or on a music video channel (Boombox)
MV_HIDDEN = ("planner", "dayparts", "shows", "lineup")
# a music channel's editor shows only these rows (no breaks, clips, time blocks or off-air hours;
# no built-in station either: using one adds its TV shows)
MUSIC_ROWS = ("name", "number", "callsign", "logo", "musrc", "mucheck")


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


# Every screen is one of five kinds (see .claude/CLAUDE.md): menu, step-by-step,
# question, remove/replace, info.  These make the question kinds one call each.
def ask(text, yes, no, cancel=None, heading=TITLE, focus_yes=False):
    """A question whose buttons say what they do.  Returns 'yes', 'no' or None.

    With `cancel`, three buttons (Kodi's yesnocustom; Estuary shows yes, no,
    cancel from left to right): Back and the cancel button both return None, so
    Back never answers 'no'.  Without it, `no` must be the answer that changes
    nothing: Back returns None like it.  Kodi focuses `no` unless focus_yes.
    The text box shows 4 lines; put a long question in `heading`."""
    kw = {}
    if focus_yes and hasattr(xbmcgui, "DLG_YESNO_YES_BTN"):
        kw["defaultbutton"] = xbmcgui.DLG_YESNO_YES_BTN
    if cancel:
        r = D.yesnocustom(heading, text, cancel, nolabel=no, yeslabel=yes, **kw)
        return {1: "yes", 0: "no"}.get(r)
    return "yes" if D.yesno(heading, text, nolabel=no, yeslabel=yes, **kw) else None


def confirm(text, yes, no=None, heading=TITLE):
    """Cancel / <yes> question.  True only for the yes button (Back = Cancel)."""
    return ask(text, yes, no or _("Cancel"), heading=heading) == "yes"


def confirm_remove(text, button=None):
    """Every removal asks first: Cancel / Remove (or Delete, Replace...)."""
    return confirm(text, button or _("Remove"))


def describe_source(s):
    t = s.get("type")
    from . import music
    if music.is_music_source(s):
        return music.describe_source(s)
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
    if t == "musicvideos":
        if s.get("paths"):
            return _("Music videos: %s") % ", ".join(s["paths"])
        return _("Music videos: Kodi's library and the folders they're in")
    what = {"both": _("movies + shows"), "tv": _("shows"), "movies": _("movies")}.get(s.get("what", "both"), "")
    v = s.get("value")
    v = ", ".join(v[:4]) + (_(" +%d more") % (len(v) - 4) if len(v) > 4 else "") if isinstance(v, list) else v
    if t == "network":
        return _("Shows that aired on %s") % v
    if t == "origtitle":
        return _("Korean and Chinese shows (by original title)")
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
    last_head = None
    while True:
        matches = _matches(items, query)
        rows, actions = [], []
        rows.append(xbmcgui.ListItem(_("[B]Search...[/B]") if not query else _("[B]Search: %s[/B]") % query,
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
        if last_head is not None and head != last_head and pos >= last_head:
            pos += head - last_head          # 'Show only selected' came or went: stay on the same item
        last_head = head
        for m in matches:
            rows.append(xbmcgui.ListItem((CHECK if multi and m in chosen else "") + m, details.get(m, "")))
        title = "%s%s" % (heading, (_("  (%d selected)") % len(chosen)) if multi else "")
        i = D.select(title, rows, useDetails=True, preselect=min(pos, len(rows) - 1))
        if i < 0:
            if multi and chosen != list(preselected or []):
                r = ask(_("Keep your %d selections?") % len(chosen), _("Keep"), _("Discard"),
                        cancel=_("Back to the list"))
                if r is None:
                    continue
                if r == "yes":
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
             _("Anything whose title contains..."), _("Specific movies"),
             _("Music videos (Kodi's library and/or a folder)")]
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
        # Back on any of these questions cancels the whole source
        r = ask(_("Limit to a range of years?"), _("Pick years"), _("Any year"), cancel=_("Cancel"))
        if r is None:
            return None
        if r == "yes":
            y0 = D.numeric(0, _("From year"), "1980")
            y1 = D.numeric(0, _("To year"), "1989") if y0 else None
            if not (y0 and y1):
                return None
            src["years"] = [int(y0), int(y1)]
        sets = sorted(set(m.get("set") for m in movies if m.get("set")))
        if sets:
            r = ask(_("Limit to one movie set/collection?"), _("Pick a set"), _("Any movies"), cancel=_("Cancel"))
            if r is None:
                return None
            if r == "yes":
                st = search_pick(_("Movie set"), sets)
                if not st:
                    return None
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
    if i == 10:
        return pick_musicvideos()
    return None


def pick_musicvideos():
    """A Music videos source: Kodi's music videos and every other video in their
    folders, or a folder the viewer picks (which replaces the automatic one)."""
    rows = [_menu_row(_("Kodi's music videos"),
                      _("Your library's music videos, plus every other video in the folders they're in")),
            _menu_row(_("Choose a folder"),
                      _('Every video in it and its subfolders. Name them "Artist - Title", '
                        'e.g. "a-ha - Take On Me (1985).mkv"')),
            _menu_row(_("Cancel"), "")]
    j = D.select(_("Music videos"), rows, useDetails=True)
    if j == 0:
        return {"type": "musicvideos"}
    if j == 1:
        p = D.browse(0, _("Music videos folder"), "video")
        return {"type": "musicvideos", "paths": [p]} if p else None
    return None


# ------------------------------------------------------------------ wizard
# Build my lineup.  Every screen has a way forward and a way out: Back (or a
# Cancel button/row) leaves with nothing changed.  Answers are kept in memory
# and written - settings, channels.json, presets, station folders - only after
# the final OK.
class _Cancelled(Exception):
    """Back or Cancel on a setup screen."""


def _ask3(message, yes, no, focus_yes=False):
    """Yes / No / Cancel question.  Back = Cancel (raises _Cancelled)."""
    r = ask(message, yes, no, cancel=_("Cancel"), focus_yes=focus_yes)
    if r is None:
        raise _Cancelled()
    return r == "yes"


def ask_commercials(pending):
    """Setup: the commercials folder (kept in pending until the final OK)."""
    if K.setting("commercials_path"):
        return
    msg = _("Do you have a folder of old commercials?[CR][CR]They fill the breaks "
            "like real cable TV. You can add this later in Settings.")
    while _ask3(msg, _("Choose folder"), _("Skip")):
        p = D.browse(0, _("Commercials folder"), "video")
        if p:
            pending["commercials_path"] = p
            return


def ask_bumpers(pending):
    """Setup: bumpers and station IDs - one shared folder, a folder per channel, or
    later.  Returns True if per-channel folders should be made once the channels exist."""
    if K.setting("bumps_path") or K.setting("stations_folder"):
        return False
    rows = [_menu_row(_("One folder for every channel"),
                      _("A folder of bumps / station IDs (short clips played right before the show "
                        "comes back), shared by all channels.")),
            _menu_row(_("A folder for each channel"),
                      _("Choose where (your media drive is best): CableBox makes a folder per channel "
                        "for bumps, IDs and commercials.")),
            _menu_row(_("Skip for now"), _("Add them later in Settings.")),
            _menu_row(_("Cancel setup"), _("Leave without changing anything."))]
    j = 0
    while True:
        j = D.select(_("Bumpers and station IDs"), rows, useDetails=True, preselect=max(j, 0))
        if j in (-1, 3):
            raise _Cancelled()
        if j == 2:
            return False
        if j == 0:
            p = D.browse(0, _("Bumps folder"), "video")
            if p:
                pending["bumps_path"] = p
                return False
        else:
            root = D.browse(3, _("Where should the channel folders go?"), "files", "", False, True)
            if root:
                pending["stations_folder"] = root
                return True


def ask_music(pending):
    """Background music for the guide and weather channels (setup wizard)."""
    if K.setting("guide_music_path") and K.setting("weather_music_path"):
        return
    msg = _("Do you have a folder of background music?[CR][CR]It plays behind the TV Guide "
            "and Weather channels - smooth jazz is the classic. You can add it later in Settings.")
    while True:
        if not _ask3(msg, _("Choose folder"), _("Skip")):
            return
        guide = D.browse(0, _("Music for the TV Guide channel"), "music")
        if guide:
            break
    while True:
        if _ask3(_("Use the same music for the Weather Channel?"), _("Yes, the same"), _("Choose another"),
                 focus_yes=True):
            weather = guide
            break
        weather = D.browse(0, _("Music for the Weather Channel"), "music")
        if weather:
            break
    pending["guide_music_path"] = guide
    pending["weather_music_path"] = weather


# ------------------------------------------------------------------ music channels
def music_sources_label(ch):
    from . import music
    srcs = [music.describe_source(x) for x in ch.get("sources", []) if music.is_music_source(x)]
    if not srcs:
        return _("nothing yet")
    return srcs[0] + (_(" +%d more") % (len(srcs) - 1) if len(srcs) > 1 else "")


def pick_music_source():
    """One source of songs: a genre, decade, artist, album, smart playlist or folder.
    Back or Cancel = None."""
    from . import music
    kinds = [("mgenre", _("A genre")), ("mdecade", _("A decade")), ("martist", _("An artist")),
             ("malbum", _("An album")), ("mplaylist", _("A smart playlist")), ("mfolder", _("A music folder"))]
    if not music.library_has_music():
        kinds = kinds[4:]                    # no music library: playlists and folders only
    j = D.select(_("Songs from"), [k[1] for k in kinds] + [_("Cancel")])
    if j < 0 or j >= len(kinds):
        return None
    kind = kinds[j][0]
    if kind == "mgenre":
        gs = music.genres()
        if not gs:
            D.ok(TITLE, _("Your music library has no genres."))
            return None
        i = D.select(_("Genre"), [_("%s  (%d songs)") % g for g in gs] + [_("Cancel")])
        return {"type": "mgenre", "value": gs[i][0]} if 0 <= i < len(gs) else None
    if kind == "mdecade":
        ds = music.decades()
        if not ds:
            D.ok(TITLE, _("None of your songs has a year."))
            return None
        i = D.select(_("Decade"), [_("The %ss  (%d songs)") % d for d in ds] + [_("Cancel")])
        return {"type": "mdecade", "value": ds[i][0]} if 0 <= i < len(ds) else None
    if kind == "martist":
        a = music.artists()
        i = D.select(_("Artist"), [x[1] for x in a] + [_("Cancel")])
        return {"type": "martist", "id": a[i][0], "value": a[i][1]} if 0 <= i < len(a) else None
    if kind == "malbum":
        a = music.albums()
        i = D.select(_("Album"), [x[1] for x in a] + [_("Cancel")])
        return {"type": "malbum", "id": a[i][0], "value": a[i][1]} if 0 <= i < len(a) else None
    if kind == "mplaylist":
        p = D.browse(1, _("Smart playlist"), "files", ".xsp", False, False, "special://profile/playlists/music/")
        return {"type": "mplaylist", "path": p} if p and p.lower().endswith(".xsp") else None
    p = D.browse(0, _("Music folder"), "music")
    return {"type": "mfolder", "path": p} if p else None


def add_music_sources(ch):
    """Add channel > Music channel: pick sources until Done.  False = cancelled."""
    while True:
        src = pick_music_source()
        if src:
            if src not in ch["sources"]:
                ch["sources"].append(src)
        elif not ch["sources"]:
            return False                     # Back before any songs: nothing added
        r = ask(_("Songs from: %s[CR]Add more?") % music_sources_label(ch),
                _("Add more"), _("Done"), cancel=_("Cancel"))
        if r is None:
            return False
        if r == "no":
            break
    return music_enough(ch)


def _music_songs(ch, fresh=False):
    from . import music
    if fresh:
        music.clear_cache()
    pd = xbmcgui.DialogProgress()
    pd.create(TITLE, _("Looking at the songs..."))
    try:
        return music.songs_for(ch["sources"])
    finally:
        pd.close()


def music_enough(ch):
    """Enough songs to make a channel?  Says so if not."""
    from . import music
    n = len(_music_songs(ch))
    if n >= music.MIN_SONGS:
        return True
    D.ok(TITLE, _("%s has only %d songs. A music channel needs at least %d.") % (ch["name"], n, music.MIN_SONGS))
    return False


def edit_music_sources(ch):
    while True:
        srcs = ch["sources"]
        rows = [_("[B]+ Add songs[/B]")] + [describe_source(x) for x in srcs]
        i = done_select(_("Songs on %s") % ch["name"], rows)
        if i < 0:
            return
        if i == 0:
            src = pick_music_source()
            if src and src not in srcs:
                srcs.append(src)
        elif len(srcs) == 1:
            D.ok(TITLE, _("A music channel needs at least one source of songs. Add another first."))
        elif confirm_remove(_("Remove this?[CR]%s") % rows[i]):
            del srcs[i - 1]


def check_music(ch):
    """Check songs: how many, how long, which artists and sample rates (read-only)."""
    from . import music
    songs = _music_songs(ch, fresh=True)
    if not songs:
        D.ok(TITLE, _("No songs found for %s. Check its sources, or scan your music into Kodi's library.")
             % ch["name"])
        return
    count = {}
    for x in songs:
        if x["a"]:
            count[x["a"]] = count.get(x["a"], 0) + 1
    rates = {}
    for x in songs:
        rates[x["r"]] = rates.get(x["r"], 0) + 1
    top = sorted(count.items(), key=lambda x: (-x[1], x[0].lower()))[:8]
    lines = [_("%d songs: %.1f hours before a song comes round again.") % (len(songs),
                                                                        sum(x["d"] for x in songs) / 3600.0),
             _("%d artists. Most songs: %s") % (len(count), ", ".join("%s (%d)" % a for a in top))]
    no_tags = len([x for x in songs if not x["a"]])
    if no_tags:
        lines.append(_("%d songs have no artist tag: their file name is shown instead.") % no_tags)
    lines.append(_("Sample rates: %s") % ", ".join(
        (("%.1f kHz" % (r / 1000.0)) if r else _("unknown")) + " (%d)" % n
        for r, n in sorted(rates.items(), key=lambda x: -x[1])))
    if len(songs) < music.MIN_SONGS:
        lines.append(_("A music channel needs at least %d songs.") % music.MIN_SONGS)
    D.textviewer(_("Songs on %s") % ch["name"], "[CR][CR]".join(lines))


def ask_musicvideos(old, mode):
    """Setup: a folder of music videos - asked only when Kodi's library has none
    (and the lineup kept has no music video channel).  Returns [folder] or None
    (Skip); Back = Cancel.  Kept in memory until the final OK."""
    if mode == "add" and any(c.get("type") == "musicvideos" for c in old):
        return None
    try:
        if library.all_musicvideos():
            return None
    except Exception:
        return None
    msg = _('Name them "Artist - Title", e.g. "a-ha - Take On Me (1985).mkv".')
    while True:
        r = ask(msg, _("Choose folder"), _("Skip"), cancel=_("Cancel"),
                heading=_("Do you have a folder of music videos?"))
        if r is None:
            raise _Cancelled()
        if r == "no":
            return None
        p = D.browse(0, _("Music videos folder"), "video")
        if p:
            return [p]


def _folders_label(folders):
    return ", ".join(f.rstrip("/\\") for f in folders or [])


def _mv_line(c):
    """Keep which channels?: 'Boombox TV - 210 music videos (136 from your library, 74 more in ...)'."""
    sv = c.get("_survey") or {}
    where = _folders_label(sv.get("folders"))
    if sv.get("lib") and sv.get("extra"):
        what = _("%d music videos (%d from your library, %d more in %s)") % (sv["total"], sv["lib"],
                                                                           sv["extra"], where)
    elif sv.get("lib"):
        what = _("%d music videos from your library") % sv["total"]
    else:
        what = _("%d music videos in %s") % (sv.get("total", 0), where)
    return u"%3d  %s \u2014 %s" % (c["number"], c["name"], what)


def _scan_library(mv_paths=None):
    """Looking through your library...  The progress dialog's Cancel stops it."""
    pd = xbmcgui.DialogProgress()
    pd.create(TITLE, _("Looking through your library..."))

    def report(msg, pct):
        pd.update(pct, msg)
        return pd.iscanceled()
    try:
        new = None if pd.iscanceled() else C.auto_lineup(report, mv_paths=mv_paths)
    finally:
        pd.close()
    if new is None:
        raise _Cancelled()
    return new


def _ask_extras():
    """Overnight sign-off and prime time: one list, both ticked.  Returns (overnight, prime)."""
    rows = [_menu_row(_("Sign off overnight"),
                      _("12 AM - 5 AM a 'Please stand by' card shows; the guide and weather stay on.")),
            _menu_row(_("Prime-time lineup"),
                      _("8 - 11 PM: each channel's best shows (movie channels: a movie at 8). Change "
                        "them in the weekly planner."))]
    sel = D.multiselect(_("Extras (untick what you don't want)"), rows, preselect=[0, 1], useDetails=True)
    if sel is None:
        raise _Cancelled()
    return 0 in sel, 1 in sel


def _span(chans):
    nums = sorted(c["number"] for c in chans)
    return ("%d" % nums[0]) if nums[0] == nums[-1] else ("%d-%d" % (nums[0], nums[-1]))


def _confirm_setup(plan):
    """The last screen before anything is saved: Cancel / OK (Back = Cancel)."""
    old, new, chans = plan["old"], plan["added"], plan["chans"]
    # the question goes in the heading: the text box only shows 4 lines
    if plan["mode"] == "add":
        question = _("Add %d channels (%s) after your current ones?") % (len(new), _span(new))
    elif old:
        question = _("Replace your %d channels with these %d?") % (len(old), len(chans))
    else:
        question = _("Set up these %d channels (%s)?") % (len(chans), _span(chans))
    lines = [_("Overnight sign-off: %s  ·  Prime time: %s") % (
        _("On") if plan["overnight"] else _("Off"), _("On") if plan["prime"] else _("Off"))]
    p = plan["pending"]
    also = []
    for key, label in (("commercials_path", _("Commercials: %s")), ("bumps_path", _("Bumps: %s")),
                       ("stations_folder", _("Channel folders: %s")), ("guide_music_path", _("Music: %s")),
                       ("weather_location", _("Weather city: %s"))):
        if p.get(key):
            also.append(label % (p[key] if key == "weather_location" else _folder_name(p[key])))
    if also:
        lines.append("  ·  ".join(also))
    for c in new:
        sv = c.get("_survey")
        if c.get("type") == "musicvideos" and sv:
            lines.append(_("Music videos: %s (%d)") % (_folders_label(sv.get("folders")), sv["total"]))
    return confirm("[CR]".join(lines), _("OK"), heading=question)


def _plain_name(c):
    """A channel's name without its built-in station's brand: the plain name it
    had before (Family Channel), else one after the station's first genre."""
    from . import stations
    st = stations.BY_ID.get(c.get("station") or "")
    if not st:
        return c["name"]
    plain = c.get("generic_name")
    if plain and plain != st["name"]:
        return plain
    genres = st["match"].get("genres")
    if genres:
        return C.GENRE_RENAMES.get(genres[0], _("%s TV") % genres[0])
    return _("Channel %d") % c["number"]


def _plain_names(added, chans):
    """Build my lineup > Plain names: the new channels keep everything a built-in
    station gave them to air (its networks and studios still match) but not its
    brand - no stock name, call letters, logo or time-of-day names."""
    from . import stations
    taken = set(c["name"] for c in chans if not any(c is a for a in added))
    for c in added:
        if c.get("station"):
            name = _plain_name(c)
            stations.drop(c)
            base, n = name, 2
            while name in taken:
                name, n = "%s %d" % (base, n), n + 1
            c["name"], c["callsign"] = name, C.callsign(name)
        taken.add(c["name"])


def _ask_names():
    """Customise: stock stations or plain names.  True = plain."""
    rows = [_menu_row(_("CableBox's stations"),
                      _("Comedy Corner, Orbit TV, Chameleon... each with its name, logo and call letters.")),
            _menu_row(_("Plain names, I'll brand them myself"),
                      _("Comedy Channel, Kids TV... the same shows, no logos. Rename them and add logos "
                        "in the Channel manager.")),
            _menu_row(_("Cancel setup"), _("Leave without changing anything."))]
    j = D.select(_("Channel names"), rows, useDetails=True)
    if j in (-1, 2):
        raise _Cancelled()
    return j == 1


def _wizard_plan(express=False):
    """Every question of Build my lineup; nothing is written.  Returns the plan,
    None if there's nothing to set up, or raises _Cancelled.

    The library is looked through first, so an empty one says so before any
    question.  express (a first setup): one screen - Start watching / Customise
    / Cancel; the folders (commercials, bumps, music...) wait for the main
    menu's Finish setting up.  Customise, and Build my lineup on a lineup that
    exists, ask everything."""
    old = C.load()
    mode = "replace"
    if old:
        express = False
        i = D.select(_("You already have %d channels") % len(old),
                     [_("Replace my lineup"), _("Add the auto channels after my current ones"), _("Cancel")])
        if i in (-1, 2):
            raise _Cancelled()
        mode = "add" if i == 1 else "replace"

    new = _scan_library()
    if not [c for c in new if c["type"] in AIR_TYPES]:
        D.ok(TITLE, _("I couldn't find any TV shows or movies in your Kodi library.[CR]"
                    "Scan your media into the library first, or add folder channels "
                    "in the Channel Manager."))
        return None

    custom = not express
    if express:
        r = ask(_("With overnight sign-off (12 AM - 5 AM) and prime-time lineups.[CR]Commercials, bumps and music "
                  "can wait: the menu shows what's left to set up."),
                _("Start watching"), _("Customise"), cancel=_("Cancel"), focus_yes=True,
                heading=_("%d channels found in your library") % len(new))
        if r is None:
            raise _Cancelled()
        custom = r == "no"

    pending, per_channel, plain, overnight, prime = {}, False, False, True, True
    if custom:
        ask_commercials(pending)
        per_channel = ask_bumpers(pending)
        ask_music(pending)
        mv_paths = ask_musicvideos(old, mode)
        if not K.setting("weather_location") and not xbmc.getCondVisibility("Weather.IsFetched"):
            city = D.input(_("Your city for the Weather Channel (optional, e.g. Springfield, IL)"), "")
            if city:                           # Back on the keyboard = skip
                pending["weather_location"] = city
        if mv_paths:
            new = _scan_library(mv_paths)       # again, with the music videos folder
            if not any(c["type"] == "musicvideos" for c in new):
                from . import musicvideos
                D.notification(TITLE, _("Boombox needs at least %d music videos - that folder has fewer")
                               % musicvideos.MIN_VIDEOS, time=4000)
        plain = _ask_names()
        if len(new) > 2:
            labels = [_mv_line(c) if c["type"] == "musicvideos" and c.get("_survey") else
                      _("%3d  %s   [COLOR grey]%s[/COLOR]") % (c["number"], _plain_name(c) if plain else c["name"],
                                                             ", ".join(describe_source(x) for x in c["sources"])[:80])
                      for c in new]
            keep = D.multiselect(_("Keep which channels? (you can fine-tune shows afterwards)"), labels,
                                 preselect=list(range(len(new))))
            if not keep:
                raise _Cancelled()
            new = [new[j] for j in keep]
            if not [c for c in new if c["type"] in AIR_TYPES]:
                raise _Cancelled()
            C.renumber(new)

    if mode == "add":
        from . import stations
        chans = list(old)
        added = []
        have = set(c["type"] for c in chans)
        used_stations = set(c.get("station") for c in chans if c.get("station"))
        used = set(c["number"] for c in chans)
        start = max(used) + 1
        for c in new:
            if c["type"] in ("guide", "weather", "musicvideos") and c["type"] in have:
                continue
            if c.get("broadcast") and any(x.get("broadcast") == c["broadcast"] for x in chans):
                continue                   # you already have that network
            if c.get("station") in used_stations:
                stations.drop(c, keep_shows=False)     # that station (and its shows) is already one of your channels
                if not c.get("sources"):
                    continue               # nothing left to air: it was that station's channel only
            fixed = C.fixed_number(c)
            if fixed is not None and fixed not in used:
                c["number"] = fixed
            else:
                while start in used or start in (C.WEATHER_NUMBER, C.NEWS_NUMBER):
                    start += 1
                c["number"] = start
            used.add(c["number"])
            chans.append(c)
            added.append(c)
        if not added:
            D.ok(TITLE, _("Your lineup already has all of these channels - nothing to add."))
            return None
    else:
        chans = added = new
        # music channels are the viewer's own (the wizard never makes one): they stay
        keep = [c for c in old if c.get("type") == "music"]
        if keep:
            used = set(c["number"] for c in new)
            nxt = max(used or [0]) + 1
            for c in keep:
                if c["number"] in used:
                    while nxt in used:
                        nxt += 1
                    c["number"] = nxt
                used.add(c["number"])
            chans = new + keep
    if plain:
        _plain_names(added, chans)
    for c in chans:
        c.setdefault("callsign", C.callsign(c["name"]))

    if custom:
        overnight, prime = _ask_extras()
    plan = {"mode": mode, "old": old, "chans": chans, "added": added, "pending": pending,
            "per_channel": per_channel, "overnight": overnight, "prime": prime, "express": not custom}
    if custom and not _confirm_setup(plan):
        raise _Cancelled()
    return plan


def _apply_setup(plan):
    """After the final OK: write everything the wizard collected."""
    from . import presets
    for key, value in plan["pending"].items():
        K.set_setting(key, value)
    chans = plan["chans"]
    if plan["overnight"]:
        presets.set_overnight(plan["added"])    # only the new channels: the others keep their hours
    C.save(chans)
    if plan["prime"]:
        pd = xbmcgui.DialogProgress()
        pd.create(TITLE, _("Building prime-time lineups..."))
        a, _changed = assign.refresh(chans)
        presets.prime_time(chans, a)
        pd.close()
        C.save(chans)
    prebuild()
    if plan["per_channel"]:
        make_station_folders(ask=False, report=False)   # the channels exist now: lay out their folders


def _lineup_ready():
    """Start watching / Not now / What I set up (which comes back here)."""
    while True:
        r = D.yesnocustom(TITLE, _("Your lineup is ready.[CR][CR]Start watching?"), _("What I set up"),
                          nolabel=_("Not now"), yeslabel=_("Start watching"))
        if r == 2:
            D.textviewer(_("What I set up"), setup_summary(C.load()))
            continue
        if r == 1:
            from . import tv
            tv.run()
            return True
        return False


def wizard(express=False):
    """Build my lineup (Welcome, main menu, Settings > Tools).  Returns True if the
    viewer went on to watch TV.  express: a first setup's short way (see
    _wizard_plan); its Start watching goes straight to the TV."""
    try:
        plan = _wizard_plan(express)
    except _Cancelled:
        D.notification(TITLE, _("Setup cancelled - nothing changed"), time=3000)
        return False
    if plan is None:
        return False
    _apply_setup(plan)
    if plan.get("express"):
        from . import tv
        tv.run()
        return True
    return _lineup_ready()


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
            lines.append(_("        Local forecast (Settings > Guide & Weather)"))
            continue
        srcs = [describe_source(s) for s in c.get("sources", []) if not s.get("orphans")]
        if c["type"] == "extras":
            srcs = [_("making-of pieces and interviews from your movies' Extras folders")]
        if c["type"] == "musicvideos":
            srcs.insert(0, _("music videos on the real clock, breaks between videos"))
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
            if c["type"] in CLIP_TYPES:
                lines += folder_lines(c)
    else:
        lines.append(_("[B]Station folders[/B]  not set up - Channel manager > Lineup tools > Station folders "
                       "gives each channel a folder for its own logo, bumps, IDs and commercials."))
    lines += ["", _("[B]Next steps[/B]"),
              _("  Channel manager > a channel > Breaks & clips: the commercials, bumps and IDs in use"),
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


# ------------------------------------------------------------------ keep my place
# Schedules are planned hours ahead.  When what they're planned from changes
# (scheduling settings, the lineup, station clips), they're refreshed: what's on
# air stays, the change applies from each channel's next programme, every show
# keeps its next episode (scheduler.Lineup.refresh).  applied.json remembers what
# the last refresh used, so whichever place notices a change first refreshes once.
APPLIED_FILE = os.path.join(K.PROFILE, "applied.json")
COSMETIC = ("name", "number", "callsign", "logo")      # never change a plan


def schedule_inputs(clips=True, lib=False):
    """Fingerprints of what schedules are planned from: the settings planning
    reads, the lineup (without names, numbers and logos), with clips=True the
    clip files in the station folders, with lib=True Kodi's video library."""
    import hashlib

    def md5(x):
        return hashlib.md5(json.dumps(x, sort_keys=True).encode("utf-8")).hexdigest()
    cfg = K.schedule_cfg()
    cfg.update(chapter_shows=K.load_json(library.CHAPTER_MODES_FILE, {}) or {})   # Check chapters' choices
    cfg.update(stations_folder=K.setting("stations_folder"), share_mode=K.setting_int("share_mode", 0),
               extras_unrecognised=K.setting_bool("extras_unrecognised", False),
               av1_mode=K.setting_int("av1_mode", 0),
               weather_location=K.setting("weather_location"))   # house breaks: a weather ad needs a place
    chans = C.load()
    out = {"settings": md5(cfg),
           "channels": md5([{k: v for k, v in c.items() if k not in COSMETIC} for c in chans])}
    if clips:
        out["clips"] = stations.clips_fingerprint(chans)
    if lib:
        out["library"] = library.fingerprint()
    out["code"] = code_fingerprint()
    return out


def code_fingerprint():
    """The add-on version and its planning code: a new build (test builds keep the
    version number) plans breaks differently, so the first run after one refreshes."""
    import hashlib
    h = hashlib.md5(K.ADDON.getAddonInfo("version").encode("utf-8"))
    for name in ("scheduler.py", "promos.py", "ads.py", "chapters.py", "specials.py",
                 os.path.join("..", "ads", "ads.json")):
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), name), "rb") as f:
                h.update(f.read())
        except OSError:
            pass
    return h.hexdigest()


class Busy(object):
    """Kodi's centred progress box, for work the viewer waits on (the refresh after
    Settings, the Channel manager, the planner...): *Updating your channels*, what
    is being done, *The menu comes back when this is done.* and a percentage.  It
    appears once the work has taken DELAY s, so a quick check never flashes, and
    stays until close().  Cancel / Back never stop the work (channels cut but not
    planned again): they say so for HOLD s; after STALL s with no progress they
    turn the box into Kodi's corner bar instead, so a stuck update never holds the
    screen.  Its own thread shows it and answers Cancel while the work gives no
    update.  quiet=True (the background service): nothing; never over the TV."""
    DELAY = 0.5
    HOLD = 3.0
    TICK = 0.2
    STALL = 60.0

    def __init__(self, text, quiet=False, later=False):
        """later=True: the DELAY starts only at go() (open_settings: not while it
        waits 2 s for a tool from Settings' Tools page, so OK with nothing changed
        never flashes the box)."""
        self.text, self.pct, self.box, self.done = text, 0, None, bool(quiet)
        self.bar = None                      # the corner bar, after Cancel on a stalled update
        self.hold_until = 0.0
        self.moved = time.time()             # the last change of stage or percentage
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.armed = threading.Event()
        if not later:
            self.armed.set()
        if not quiet:
            t = threading.Thread(target=self._run, name="cablebox42-busy")
            t.daemon = True
            t.start()

    def _message(self):
        line = _("Almost done - this can't be stopped") if time.time() < self.hold_until else self.text
        return "%s[CR]%s" % (line, _("The menu comes back when this is done."))

    def go(self):
        self.armed.set()

    def _open(self):
        """Under the lock."""
        self.box = xbmcgui.DialogProgress()
        self.box.create(_("Updating your channels"), self._message())
        self.box.update(self.pct, self._message())

    def _run(self):
        self.armed.wait()
        if self.stop.wait(self.DELAY):
            return
        with self.lock:
            if self.done:
                return
            if xbmcgui.Window(10000).getProperty("cablebox42.running") == "1":
                return                       # never over the TV
            try:
                self._open()
            except Exception as exc:
                K.log_err("progress box: %s" % exc)
                self.box = None
                return
        while not self.stop.wait(self.TICK):
            with self.lock:
                if self.done or self.box is None:
                    return
                try:
                    hit = self.box.iscanceled()
                except Exception:
                    hit = False
                if not hit:
                    if self.hold_until and time.time() >= self.hold_until:
                        self.hold_until = 0.0
                        self.box.update(self.pct, self._message())
                    continue
                old, self.box = self.box, None
                stalled = time.time() - self.moved >= self.STALL
            # Kodi 21 (rig): after Cancel / Back the box stays open, its heading gains
            # ' : Cancelling...' and iscanceled() stays True until the box has really
            # closed; a new box opened only then answers the next press again.
            old.close()
            self._gone()
            with self.lock:
                if self.done:
                    return
                try:
                    if stalled:
                        K.log("progress box: Cancel after %d s without progress - corner bar, the update goes on"
                              % (time.time() - self.moved), xbmc.LOGINFO)
                        self.bar = xbmcgui.DialogProgressBG()
                        self.bar.create(TITLE, _("Still working - the menu comes back when it's done"))
                        self.bar.update(self.pct, TITLE, _("Still working - the menu comes back when it's done"))
                        return
                    K.log("progress box: Cancel pressed - the update goes on", xbmc.LOGINFO)
                    self.hold_until = time.time() + self.HOLD
                    self._open()
                except Exception as exc:
                    K.log_err("progress box: %s" % exc)
                    self.box = None
                    return

    def _gone(self, most=1.0):
        t0 = time.time()
        while xbmc.getCondVisibility("Window.IsVisible(progressdialog)") and time.time() - t0 < most:
            time.sleep(0.02)

    def update(self, pct=None, text=None):
        with self.lock:
            old = (self.pct, self.text)
            if pct is not None:
                self.pct = max(0, min(100, int(pct)))
            if text:
                self.text = text
            if (self.pct, self.text) != old:
                self.moved = time.time()
            if self.done:
                return
            if self.box is not None:
                self.box.update(self.pct, self._message())
            elif self.bar is not None:
                self.bar.update(self.pct, TITLE, _("Still working - the menu comes back when it's done"))

    def close(self):
        with self.lock:
            self.done = True
            self.stop.set()
            self.armed.set()
            if self.box is not None:
                self.box.close()
                self.box = None
            if self.bar is not None:
                self.bar.close()
                self.bar = None

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()


def refresh_now(quiet=False, busy=None):
    """Refresh schedules, keep my place.  Holds TOOL_BUSY (open_settings waits for
    it, so the menu never opens over this).  Unless quiet (the background service),
    the centred box says what is happening from the start (Busy): working out home
    channels, then each channel's schedule.  busy: the caller's box to carry on."""
    home = xbmcgui.Window(10000)
    mine = not home.getProperty(TOOL_BUSY)
    if mine:
        home.setProperty(TOOL_BUSY, "refresh")
    own = busy is None
    if own:
        busy = Busy(_("Updating schedules..."), quiet)

    def stage(_name):
        busy.update(5, _("Working out which channel each show belongs on..."))

    def progress(i, n, _c):
        busy.update(10 + 90.0 * i / max(1, n), _("Updating schedules..."))
    try:
        scheduler.Lineup(K.schedule_cfg()).refresh(progress=progress, stage=stage)
        busy.update(100, _("Updating schedules..."))
        library.durations().save()
        K.save_json(APPLIED_FILE, schedule_inputs(lib=True))
        note_unplaced()
    finally:
        if own:
            busy.close()
        if mine:
            home.clearProperty(TOOL_BUSY)


def refresh_if_changed(clips=True, quiet=False, lib=False, busy=None):
    """Refresh if anything schedules are planned from changed since the last
    refresh (clips=False: settings and lineup only, cheap enough to poll;
    lib=True: Kodi's video library too, after a scan or clean).  True if it
    refreshed.  Unless quiet, the centred box shows from the first half second
    (reading the station folders can take a while on a USB drive), and a short
    notice says when the schedules were refreshed.  busy: a box the caller
    already put up (open_settings starts it as Settings closes)."""
    if busy is None:
        busy = Busy(_("Checking your changes..."), quiet)
    try:
        cur = schedule_inputs(clips, lib)
        old = K.load_json(APPLIED_FILE, None)
        if old is None:                      # first time: this is what the plans use
            K.save_json(APPLIED_FILE, cur)
            return False
        new_keys = [k for k in cur if k not in old and k != "code"]
        if new_keys:                         # e.g. the library, first seen: nothing to compare
            old.update((k, cur[k]) for k in new_keys)
            K.save_json(APPLIED_FILE, old)
        # no "code" yet: planned by a build from before this check - that's a change too
        if all(old.get(k) == v for k, v in cur.items()):
            return False
        K.log("Schedules: %s changed - refreshing" % ", ".join(k for k, v in cur.items() if old.get(k) != v),
              xbmc.LOGINFO)
        refresh_now(quiet, busy=busy)
        busy.close()
        if not quiet:
            D.notification(TITLE, _("Schedules refreshed"), time=2000)
        return True
    except Exception as exc:
        K.log_err("refresh after a change: %s" % exc)
        return False
    finally:
        busy.close()


def refresh_tool():
    """Settings > Tools > Refresh schedules (keep my place): no question asked."""
    refresh_now()
    D.notification(TITLE, _("Schedules refreshed"), time=2000)


def start_series_over():
    """Settings > Tools > Start series over...: the only thing that resets where
    shows are in their series."""
    j = D.select(_("Start series over"), [_("All shows"), _("One channel"), _("One show")])
    if j < 0:
        return
    if j == 0:
        scope, q = ("all", None), _("Every show will start again from its first episode.[CR]Continue?")
    elif j == 1:
        progs = [c for c in C.load() if c["type"] in PROGRAM_TYPES]
        if not progs:
            D.ok(TITLE, _("Add a channel first."))
            return
        k = D.select(_("Start which channel's shows over?"), ["%3d  %s" % (c["number"], c["name"]) for c in progs])
        if k < 0:
            return
        scope = ("channel", progs[k]["id"])
        q = _("Every show on %s will start again from its first episode.[CR]Continue?") % progs[k]["name"]
    else:
        shows = sorted(library.resolve([{"type": "alltv"}])["series"], key=lambda s: library.natural_key(s["title"]))
        if not shows:
            D.ok(TITLE, _("No TV shows in the library"))
            return
        k = D.select(_("Start which show over?"), [s["title"] for s in shows])
        if k < 0:
            return
        first = (shows[k]["episodes"] or [{}])[0].get("label") or _("its first episode")
        scope = ("show", shows[k]["title"])
        q = _("%s will start again from %s.[CR]Continue?") % (shows[k]["title"], first)
    if not confirm(q, _("Start over")):      # Cancel / Start over, focus on Cancel
        return
    home = xbmcgui.Window(10000)
    mine = not home.getProperty(TOOL_BUSY)
    if mine:
        home.setProperty(TOOL_BUSY, "restart_series")
    try:
        busy = xbmcgui.DialogProgressBG()
        busy.create(TITLE, _("Updating schedules..."))
        try:
            scheduler.Lineup(K.schedule_cfg()).reset_progress(
                scope[0], scope[1], progress=lambda i, n, _c: busy.update(int(100.0 * i / max(1, n))))
            library.durations().save()
            K.save_json(APPLIED_FILE, schedule_inputs())
        finally:
            busy.close()
    finally:
        if mine:
            home.clearProperty(TOOL_BUSY)
    D.notification(TITLE, _("Series started over"), time=2000)


# ------------------------------------------------------------------ manager
# A station-folder screen was opened since the Channel manager opened: its clips
# may have changed although channels.json didn't (manager() then reports a change).
_FOLDERS_TOUCHED = [False]


def _lineup_stamp():
    return json.dumps(C.load(), sort_keys=True)


def manager():
    """The Channel manager.  True if anything was saved (the lineup, or a station
    folder screen was used): only then are home channels worked out again (slow:
    every source of every channel) and the caller checks for a refresh."""
    start = _lineup_stamp()
    _FOLDERS_TOUCHED[0] = False
    while True:
        chans = C.load()
        top = [_("[B]+ Add a channel[/B]"), _("[B]Rearrange channel numbers[/B]"),
               _("[B]Lineup tools[/B]  [COLOR grey]build a lineup, move shows, sign-off, station folders[/COLOR]")]
        rows = list(top)
        for c in chans:
            what = TYPE_SHORT.get(c["type"], c["type"])
            if c["type"] in AIR_TYPES:
                what = (_("%s, 1 source") % what) if len(c["sources"]) == 1 else \
                    (_("%s, %d sources") % (what, len(c["sources"])))
            rows.append("%3d   %s   [COLOR grey](%s)[/COLOR]" % (c["number"], c["name"], what))
        i = done_select(_("Channel manager"), rows)
        if i < 0:
            changed = _lineup_stamp() != start
            if changed:
                refresh_assignments()
            return changed or _FOLDERS_TOUCHED[0]
        if i == 0:
            add_channel(chans)
        elif i == 1:
            rearrange()
        elif i == 2:
            lineup_tools()
        else:
            edit_channel(chans[i - len(top)]["id"])


def lineup_tools():
    """Channel manager > Lineup tools: everything that works on the whole lineup."""
    while True:
        rows = [(wizard, _("Build my lineup"),
                 _("Builds channels from your Kodi library: replace your lineup, or add to it.")),
                (shows_and_channels, _("Move shows between channels"),
                 _("Pick a show and tick the channels it airs on.")),
                (run_finder, _("Shows without a good channel"),
                 _("Shows no channel picks up, or that only just fit where they are.")),
                (quick_setup, _("Sign-off and prime time for all channels"),
                 _("Overnight sign-off hours and prime-time lineups, for every channel at once.")),
                (make_station_folders, _("Station folders"),
                 _("A folder per channel for its logo, bumps, IDs and commercials: create, repair, see what's used.")),
                (None, _("Lineup summary"), _("What's set up, and where."))]
        i = done_select(_("Lineup tools"), [_menu_row(r[1], r[2]) for r in rows], useDetails=True)
        if i < 0:
            return
        if rows[i][0] is None:
            D.textviewer(_("Lineup summary"), setup_summary(C.load()))
        elif rows[i][0]():
            return                          # Build my lineup went on to the TV


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
        rows = [_("[B]Close the gaps[/B] (renumber in order)")] + \
               ["%3d   %s" % (c["number"], c["name"]) for c in chans]
        i = done_select(_("Pick a channel to move"), rows)
        if i < 0:
            return
        if i == 0:
            first = D.numeric(0, _("Start numbering at"), str(chans[0]["number"] if chans else 2))
            if first and int(first) > 0:
                C.renumber(chans, int(first))    # Weather stays on 25, News on 42
                C.save(chans)
            elif first:
                D.notification(TITLE, _("Channel numbers start at 1"), time=2500)
            continue
        ch = chans[i - 1]
        v = D.numeric(0, _("Move %s to channel") % ch["name"], str(ch["number"]))
        if v and int(v) > 0 and move_channel(chans, ch, int(v)):
            C.save(chans)


def _new_number(chans):
    """Step of Add a channel: its number.  If that number is taken, move the other
    channel, slide the channels from there up by one, or pick another number.
    Changes `chans` in memory only; returns the number, or None for Cancel/Back."""
    v = str(C.next_free_number(chans))
    while True:
        v = D.numeric(0, _("Channel number"), v)
        if not v or int(v) <= 0:
            return None
        num = int(v)
        other = next((c for c in chans if c["number"] == num), None)
        if other is None:
            return num
        free = C.next_free_number(chans, num + 1)
        j = D.select(_("Channel %d is %s") % (num, other["name"]), [
            _("Move %s to %d") % (other["name"], free),
            _("Slide channels %d and up over by one") % num,
            _("Pick another number"),
            _("Cancel")])
        if j == 0:
            other["number"] = free
            return num
        if j == 1:
            n = num
            run = []
            while True:                     # only up to the first free number
                c = next((x for x in chans if x["number"] == n), None)
                if c is None:
                    break
                run.append(c)
                n += 1
            for c in run:
                c["number"] += 1
            return num
        if j != 2:
            return None


def _another_extras_ok(chans, cid=None):
    """Before a second Behind the scenes channel: warn first.  True = go on
    (Add another); Cancel and Back = False."""
    have = [c for c in chans if c.get("type") == "extras" and c.get("id") != cid]
    if not have:
        return True
    return confirm(_("Both channels would air the same movie extras."), _("Add another"),
                   heading=_("You already have %s on %d. Add another?") % (have[0]["name"], have[0]["number"]))


def _extras_air():
    """(seconds, films) a Behind the scenes channel can air now, from the cache only."""
    films = library.extras_programme(K.setting_bool("extras_unrecognised", False))
    return int(sum(s["dur"] for f in films for s in f["segs"])), len(films)


def _pick_kind(chans):
    """First step of Add a channel: what kind of channel.  Returns "station",
    "own", "musicvideos", "music", "guide", "weather" or "extras" (None for Back).  The
    Guide and the Weather channel are only offered while the lineup has none."""
    have = set(c["type"] for c in chans)
    rows = [("station", _("A built-in station"),
             _("Comedy Corner, Orbit TV, Chameleon... with its name, logo and shows")),
            ("own", _("My own channel"), _("Your name, your programming, your logo")),
            ("musicvideos", _("Music videos"), _("Music videos on the real clock, breaks between videos")),
            ("music", _("Music channel"), _("Songs around the clock, no breaks")),
            ("guide", _("TV Guide"), _("What's on every channel, scrolling")),
            ("weather", _("Weather"), _("Your local forecast")),
            ("extras", _("Behind the scenes"), _("Making-of pieces and interviews from your movies' Extras folders"))]
    rows = [r for r in rows if not (r[0] in ("guide", "weather") and r[0] in have)]
    i = D.select(_("What kind of channel?"), [_menu_row(r[1], r[2]) for r in rows], useDetails=True)
    return rows[i][0] if i >= 0 else None


def _pick_new_station(chans):
    """Add a channel > A built-in station: one that isn't in the lineup yet."""
    from . import stations
    used = dict((c.get("station"), c["number"]) for c in chans if c.get("station"))
    sts = stations.addable()
    while True:
        rows = []
        for s in sts:
            if s["id"] in used:
                rows.append("[COLOR grey]%s   %s[/COLOR]" % (s["name"], _("already on channel %d") % used[s["id"]]))
            else:
                rows.append("%s   [COLOR grey]%s[/COLOR]" % (s["name"], stations.tagline({"station": s["id"]})))
        i = D.select(_("Which station?"), rows)
        if i < 0:
            return None
        if sts[i]["id"] not in used:
            return sts[i]
        D.notification(TITLE, _("%s is already on channel %d") % (sts[i]["name"], used[sts[i]["id"]]), time=2500)


def _programming_step(ch, listed=False):
    """Step of Add a channel: its programming.  listed: the channel already has
    some (a built-in station's), so show it and offer more.  False = cancelled."""
    first = listed and bool(ch["sources"])
    while True:
        if not first:
            src = pick_source()
            if src:
                ch["sources"].append(src)
            elif not ch["sources"]:
                return False                # Back before any programming: nothing added
        first = False
        if listed:
            lines = [describe_source(x)[:70] for x in ch["sources"]]
            if len(lines) > 4:
                lines = lines[:3] + [_(" +%d more") % (len(lines) - 3)]
            r = ask("[CR]".join(lines), _("Add more"), _("Done"), cancel=_("Cancel"),
                    heading=_("%s airs these. Add more?") % ch["name"])
        else:
            r = ask(_("%s has %d source(s) of programming.[CR]Add more?") % (ch["name"], len(ch["sources"])),
                    _("Add more"), _("Done"), cancel=_("Cancel"))
        if r is None:
            return False
        if r == "no":
            return True


def add_channel(chans, kind=None):
    """Step by step: what kind of channel, then only what that kind needs.
        A built-in station: which one, number, its shows (add more / done)
        My own channel: type, name, number, programming, logo (now / later)
        Music channel: name, number, songs (add more / done)
        Music videos, TV Guide, Weather, Behind the scenes: name, number
    Back on any step adds nothing.  `kind` preselects the kind (Check extras
    offers a Behind the scenes channel)."""
    import copy
    from . import stations
    chans = copy.deepcopy(chans)            # a number swap only counts if the channel is added
    kind = kind if kind in ("extras", "musicvideos", "music", "guide", "weather", "own", "station") else _pick_kind(chans)
    if not kind:
        return
    extras = kind == "extras"
    if extras and not _another_extras_ok(chans):
        return
    backlot_look = False
    if kind == "station":
        st = _pick_new_station(chans)
        if not st:
            return
        ctype, sources = stations.starter(st)
        name = st["name"]
    else:
        st = None
        ctype = kind
        if kind == "own":
            t = D.select(_("Channel type"), [TYPE_LABELS[x] for x in PROGRAM_TYPES])
            if t < 0:
                return
            ctype = PROGRAM_TYPES[t]
        name = D.input(_("Channel name"), {"guide": _("TV Guide"), "weather": _("Weather Channel"),
                                           "extras": "BACKLOT"}.get(kind, ""))
        if not name:
            return
        if extras:
            backlot_look = name.strip().upper() == "BACKLOT" or ask(
                _("Otherwise %s has no logo until you give it one.") % name, _("Use them"), _("No logo"),
                heading=_("Use the BACKLOT logo and corner bug?")) == "yes"
        sources = []
    num = _new_number(chans)
    if num is None:
        return
    ch = C.new_channel(num, name, ctype, sources, callsign=C.callsign(name))
    if st:
        stations.apply(ch, st)
        if ctype in ("network", "movies"):
            ch["home_guard"] = True         # as on a channel Build my lineup makes
        if not ch["sources"]:
            D.ok(TITLE, _("Nothing in your library matches %s yet. Choose its programming yourself.") % name)
        if not _programming_step(ch, listed=True):
            return
    elif ctype == "music":
        if not add_music_sources(ch):
            return                          # Back or Cancel: nothing added
    elif ctype == "musicvideos":
        src = pick_musicvideos()
        if not src:
            return
        ch["sources"].append(src)
    elif ctype in PROGRAM_TYPES:
        if not _programming_step(ch):
            return
        if ask(_("A logo shows in the corner and on the channel banner. You can add one later in the "
                 "channel editor."), _("Choose an image"), _("Later"),
               heading=_("Give %s a logo now?") % name) == "yes":
            _browse_logo(ch)
    if backlot_look:
        stations.apply(ch, stations.BY_ID["backlot"])     # the built-in station: logo, corner bug, call letters
        if name.strip().upper() != "BACKLOT":             # renamed: only the look, the name stays the viewer's
            ch["name"], ch["callsign"] = name, C.callsign(name)
    chans.append(ch)
    C.save(chans)
    D.notification(TITLE, _("Channel %d %s added") % (num, name), time=2500)
    if extras and not _extras_air()[0]:
        # only now that the channel is saved: a long job never starts inside Add a channel
        if confirm(_("It can take a few minutes the first time. Otherwise CableBox does it while the TV is off."),
                   _("Look now"), _("Later"), heading=_("Look for movie extras now?")):
            look_for_extras()
    edit_channel(ch["id"])


def _find(cid):
    chans = C.load()
    for c in chans:
        if c["id"] == cid:
            return chans, c
    return chans, None


# The channel editor: four groups, each a short menu of its own.
EDIT_GROUPS = ("identity", "programming", "breaks", "schedule")


def _editor_rows(ch, chans):
    """Every row of the channel editor for this channel: [(key, group, label,
    detail)].  Rows that mean nothing for the channel's type are left out."""
    from . import stations
    onoff = lambda b: _("On") if b else _("Off")
    rows = []

    def add(group, key, label, detail=""):
        rows.append((key, group, label, detail))

    # -- identity: who the channel is
    add("identity", "name", _("Name: %s") % ch["name"])
    add("identity", "number", _("Number: %d") % ch["number"])
    add("identity", "callsign", _("Call letters: %s") % ch.get("callsign", ""))
    add("identity", "logo", *_logo_row(ch))
    add("identity", "blocks", _("Names by time of day: %s") % _blocks_label(ch),
        _("Times when the channel goes by another name and logo (CAM Jr. in the morning)."))
    root, folder = K.setting("stations_folder"), stations.channel_folder(ch)
    add("identity", "folder",
        _("Station folder: %s") % _folder_name(folder) if folder else
        _("Station folder: none yet") if root else _("Station folder: not set up"),
        _("The channel's own folder for a logo, bumps, station IDs and commercials."))
    if ch.get("station"):
        add("identity", "station", _("Built-in station: %s") % _station_label(ch),
            _("Use another built-in station, or make this channel your own."))
    else:
        add("identity", "station", _("Use a built-in station..."),
            _("Gives the channel a built-in station's name, call letters, logo and shows."))

    # -- programming: what it airs
    add("programming", "type", _("Type: %s") % TYPE_LABELS.get(ch["type"], ch["type"]))
    if ch["type"] == "extras":
        secs, n = _extras_air()
        add("programming", "extras",
            _("Movie extras: %d h %02d min to air from %d films") % (secs // 3600, secs % 3600 // 60, n)
            if secs else _("Movie extras: none to air yet"))
    if ch["type"] == "musicvideos":
        add("programming", "mvcheck", _("[B]Check music videos[/B] (what airs, what's skipped)"))
        add("programming", "mvcaps", _("Video captions: %s") % onoff(ch.get("mv_captions", True)))
    if ch["type"] == "music":
        add("programming", "musrc", _("Songs from: %s") % music_sources_label(ch))
        add("programming", "mucheck", _("[B]Check songs[/B] (how many, which artists)"))
    add("programming", "sources", _("Programming: %d source(s)") % len(ch["sources"]))
    add("programming", "shows", _("[B]What's on this channel[/B] (%d hidden)") % len(ch.get("exclude", [])))

    # -- breaks & clips: what the channel really uses, and its switches
    folder = stations.channel_folder(ch)
    for kind in ("commercials", "bumps", "ids"):
        label, detail, on = _clip_row(ch, kind, folder)
        if kind == "ids":
            detail += " " + _("Select to choose this channel's own folder of station ID clips.")
        elif on:
            detail += " " + _("Select to switch them off.")
        add("breaks", "clip:" + kind, label, detail)
    add("breaks", "midroll", _("Break into shows for commercials: %s") % onoff(ch.get("midroll", ch["type"] != "movies")))
    add("breaks", "adflavour", _("Ad flavour: %s") % _ad_flavour_label(ch),
        _("Which retro ads its house breaks run."))
    add("breaks", "cpath", _("Channel commercials folder: %s") % (ch.get("commercials_path") or _("global")),
        _("This channel's own commercials, instead of the shared folder in Settings."))
    add("breaks", "bpath", _("Channel bumps folder: %s") % (ch.get("bumps_path") or _("global")),
        _("This channel's own bumps, instead of the shared folder in Settings."))

    # -- schedule: when things air
    add("schedule", "planner", _("[B]Weekly planner[/B] (%d pinned shows)") % len(ch.get("slots", [])))
    if ch["type"] in AIR_TYPES:
        from . import specials_editor
        add("schedule", "specials", _("[B]Holidays and specials[/B] (%d)") % len(specials_editor.on_channel(ch["id"])),
            _("Marathons and holiday programming on dates, back every year."))
    add("schedule", "dayparts", _("Time blocks (prime time, Saturday mornings...): %d") % len(ch["dayparts"]))
    add("schedule", "offair", _("Off-air hours: %s") % (", ".join("%s-%s" % (w["start"], w["end"])
                                                               for w in ch["offair"]) or _("never")))
    add("schedule", "lineup", _("Lineup style: %s") % (_("Same show same time every day") if ch.get("lineup") == "strip"
                                                     else _("Shuffle")))
    add("schedule", "slot", _("Programs start on: %s") % ({0: _("no clock (back to back)"), 15: ":00 :15 :30 :45",
                                                         30: _(":00 and :30"), 60: _("the hour")}.get(ch.get("slot"),
                                                                                               str(ch.get("slot")))))
    hidden = set()
    if ch["type"] not in AIR_TYPES:
        hidden.add("adflavour")                 # retro ads run in house breaks only
    if ch["type"] == "extras":
        hidden.update(EXTRAS_HIDDEN)
    if ch["type"] == "musicvideos":
        hidden.update(MV_HIDDEN)
    if ch["type"] == "music":
        return [r for r in rows if r[0] in MUSIC_ROWS]
    return [r for r in rows if r[0] not in hidden]


def _group_rows(ch, chans):
    """The editor's top level: one row per group, saying what's in it now."""
    rows = _editor_rows(ch, chans)
    label = dict((r[0], r[2]) for r in rows)
    dot = u"  \u00b7  "
    out = [("identity", _("[B]Identity[/B]"),
            dot.join(x for x in (ch["name"], ch.get("callsign", ""), label["logo"]) if x)),
           ("programming", _("[B]Programming[/B]"),
            dot.join(label[k] for k in ("type", "sources") if k in label)),
           ("breaks", _("[B]Breaks & clips[/B]"),
            dot.join(label[k] for k in ("clip:commercials", "clip:bumps") if k in label)),
           ("schedule", _("[B]Schedule[/B]"),
            dot.join(label[k] for k in ("offair", "lineup") if k in label)),
           ("preview", _("[B]Preview today's schedule[/B]"), ""),
           ("delete", _("[COLOR red]Delete channel[/COLOR]"), _("Your videos and its station folder are not touched."))]
    if ch["type"] == "music":           # songs only: no breaks, clips or schedule rows
        out[1] = ("programming", _("[B]Programming[/B]"), label["musrc"])
        out = [r for r in out if r[0] not in ("breaks", "schedule")]
    return out


def edit_channel(cid):
    """The channel editor: Identity, Programming, Breaks & clips, Schedule (each
    a menu of its own, changes save as you go), Preview and Delete."""
    changed = False
    while True:
        chans, ch = _find(cid)
        if not ch:
            return
        rows = _group_rows(ch, chans)
        i = done_select("%d  %s" % (ch["number"], ch["name"]), [_menu_row(r[1], r[2]) for r in rows],
                        useDetails=True)
        if i < 0:
            if changed:
                D.notification(TITLE, _("%s saved") % ch["name"], time=2000)
            return
        key = rows[i][0]
        if key in EDIT_GROUPS:
            changed = _edit_group(cid, key) or changed
        elif key == "preview":
            preview(ch)
        elif key == "delete":
            from . import specials_editor
            names = specials_editor.on_channel(cid)
            text = _("Delete %d %s?[CR][CR]Its schedule and pinned shows go with it. Your videos "
                     "and its station folder are not touched.") % (ch["number"], ch["name"])
            head = TITLE
            if names:        # more to say: the question goes in the heading (the box shows 4 lines)
                head = _("Delete %d %s?") % (ch["number"], ch["name"])
                text = _("Its schedule, pinned shows and its part in these specials go with it: %s.[CR]"
                         "Your videos and its station folder are not touched.") % (
                             ", ".join(names[:3]) + (" ..." if len(names) > 3 else ""))
            if confirm(text, _("Delete"), heading=head):
                chans = [c for c in chans if c["id"] != cid]
                C.save(chans)
                specials_editor.drop_channel(cid)   # its blocks; a special left with none goes too
                # its schedule goes; its shows keep their place (their bookmarks go
                # back to what it aired)
                scheduler.Lineup(K.schedule_cfg()).drop_removed()
                return


def _edit_group(cid, group):
    """One group of the channel editor.  True if anything changed (it's saved)."""
    titles = {"identity": _("%s - identity"), "programming": _("%s - programming"),
              "breaks": _("%s - breaks & clips"), "schedule": _("%s - schedule")}
    changed = False
    while True:
        chans, ch = _find(cid)
        if not ch:
            return changed
        before = json.dumps(chans, sort_keys=True)
        rows = [r for r in _editor_rows(ch, chans) if r[1] == group]
        details = any(r[3] for r in rows)
        i = done_select(titles[group] % ch["name"],
                        [_menu_row(r[2], r[3]) for r in rows] if details else [r[2] for r in rows],
                        useDetails=details)
        if i < 0:
            return changed
        _edit_row(rows[i][0], ch, chans, cid)
        chans2, _ch = _find(cid)
        if json.dumps(chans, sort_keys=True) != before:
            changed = True
            C.save(chans)
        elif json.dumps(chans2, sort_keys=True) != before:
            changed = True                  # a screen of its own saved it (the planner, the station folder)


def _edit_row(key, ch, chans, cid):
    """Act on one editor row.  Changes `ch` in memory; _edit_group saves."""
    from . import stations
    if key == "name":
        v = D.input(_("Name"), ch["name"])
        if v and v != ch["name"]:
            old_folder = stations.channel_folder(ch)
            _rename(ch, v)
            _folder_follows(ch, old_folder)
    elif key == "number":
        v = D.numeric(0, _("Move %s to channel") % ch["name"], str(ch["number"]))
        if v and int(v) > 0:
            move_channel(chans, ch, int(v))
    elif key == "callsign":
        v = D.input(_("Call letters"), ch.get("callsign", ""))
        if v and v.upper()[:6] != ch.get("callsign"):     # Back leaves them as they are
            old_folder = stations.channel_folder(ch)
            ch["callsign"] = v.upper()[:6]
            _folder_follows(ch, old_folder)
    elif key == "logo":
        pick_logo(ch)
    elif key == "station":
        old_folder = stations.channel_folder(ch)
        pick_station(ch, chans)
        _folder_follows(ch, old_folder)
    elif key == "folder":
        C.save(chans)
        station_folder(ch, chans)
    elif key == "blocks":
        edit_brand_blocks(ch)
    elif key == "type":
        change_type(ch, chans)
    elif key == "extras":
        C.save(chans)
        check_extras()
    elif key == "mvcheck":
        C.save(chans)
        check_musicvideos(ch)
    elif key == "mvcaps":
        ch["mv_captions"] = not ch.get("mv_captions", True)
    elif key == "musrc":
        edit_music_sources(ch)
    elif key == "mucheck":
        C.save(chans)
        check_music(ch)
    elif key == "sources":
        edit_sources(ch["sources"], ch["name"])
    elif key == "dayparts":
        edit_dayparts(ch)
    elif key == "offair":
        edit_offair(ch)
    elif key in ("clip:commercials", "clip:bumps"):
        kind = key[5:]
        ch[kind] = not ch.get(kind)
    elif key == "midroll":
        ch["midroll"] = not ch.get("midroll", ch["type"] != "movies")
    elif key == "adflavour":
        pick_ad_flavour(ch)
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
    elif key == "clip:ids":
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
    elif key == "specials":
        C.save(chans)
        from . import specials_editor
        specials_editor.open_specials(cid)


def _ad_flavour_label(ch):
    from . import ads
    f = ch.get("ad_flavour") or "auto"
    if f == "auto":
        return _("Auto (%s)") % ads.flavour_label(ads.auto_flavour(ch))
    return ads.flavour_label(f)


def pick_ad_flavour(ch):
    """Channel settings > Ad flavour: which retro ads the channel's house breaks
    run.  Auto follows its type and genres; Kids runs only kids' ads."""
    from . import ads
    codes = list(ads.FLAVOURS)
    rows = [_("Auto (%s)") % ads.flavour_label(ads.auto_flavour(ch))] + [ads.flavour_label(c) for c in codes[1:]]
    cur = ch.get("ad_flavour") or "auto"
    j = D.select(_("Ad flavour"), rows + [_("Cancel")], preselect=codes.index(cur) if cur in codes else 0)
    if j < 0 or j >= len(codes):
        return
    if codes[j] == "auto":
        ch.pop("ad_flavour", None)
    else:
        ch["ad_flavour"] = codes[j]


def change_type(ch, chans=()):
    """Change a channel's type; ask before its settings go back to that type's defaults."""
    # one TV Guide and one Weather channel: not offered while another channel is one
    taken = set(c["type"] for c in chans if c.get("id") != ch.get("id")) & set(("guide", "weather"))
    taken.add("music")                  # a music channel is made from Add a channel only
    types = [x for x in ALL_TYPES if x not in taken]
    j = D.select(_("Type"), [TYPE_LABELS[x] for x in types], preselect=types.index(ch["type"])
                 if ch["type"] in types else -1)
    if j < 0 or types[j] == ch["type"]:
        return
    new = types[j]
    if new == "extras" and not _another_extras_ok(chans, ch.get("id")):
        return
    # Behind the scenes, Guide and Weather don't use programming sources: say so (they're kept)
    unused = (_("Its programming sources aren't used by this type - they're kept, not deleted.")
              if ch.get("sources") and new not in AIR_TYPES else "")
    defaults = C.DEFAULTS[new]
    onoff = lambda b: _("On") if b else _("Off")
    show = {"commercials": lambda v: _("Commercials: %s") % onoff(v),
            "midroll": lambda v: _("Break into shows for commercials: %s") % onoff(v),
            "bumps": lambda v: _("Bumps: %s") % onoff(v),
            "lineup": lambda v: _("Lineup style: %s") % (_("Same show same time every day") if v == "strip"
                                                         else _("Shuffle")),
            "slot": lambda v: _("Programs start on: %s") % {0: _("no clock (back to back)"), 15: ":00 :15 :30 :45",
                                                          30: _(":00 and :30"), 60: _("the hour")}.get(v, str(v))}
    current = dict(ch, midroll=ch.get("midroll", ch["type"] != "movies"))
    differ = [show[k](v) for k, v in defaults.items() if k in show and current.get(k) != v]
    if differ:
        text = _("Its usual settings: %s[CR]Use these, or keep this channel's own?") % "  ·  ".join(differ)
        r = ask((unused + "[CR]" + text) if unused else text,
                _("Use defaults"), _("Keep my settings"), cancel=_("Cancel"),
                heading=_("Change to %s?") % TYPE_LABELS[new])
        if r is None:
            return
        if r == "yes":
            ch.update(defaults)
    elif unused and not confirm(unused, _("Change type"), heading=_("Change to %s?") % TYPE_LABELS[new]):
        return
    ch["type"] = new
    if new == "musicvideos" and not ch.get("sources"):
        ch["sources"] = [{"type": "musicvideos"}]


MV_REASONS = {"trailer or sample": _("trailer or sample"), "no audio track": _("no audio track"),
              "shorter than 30 s": _("shorter than 30 s")}


def check_musicvideos(ch):
    """Check music videos (info): what a music video channel airs, by frame-rate
    group, what's skipped and why, and what isn't measured yet - from the cache.
    Measuring can be started from here (it otherwise happens in the background)."""
    from . import musicvideos as MV
    while True:
        srcs = [s for s in ch.get("sources", []) if s.get("type") == "musicvideos"] or [{"type": "musicvideos"}]
        airs, skipped, unreadable, waiting, found, lib, folders = [], [], [], 0, 0, 0, []
        for s in srcs:
            r = library.musicvideos_report(s)
            airs += r["airs"]
            skipped += r["skipped"]
            unreadable += r["unreadable"]
            waiting += r["waiting"]
            found += r["total"]
            lib += r["lib"]
            folders += r["folders"]
        groups = MV.groups([(it["path"], it.get("fps"), it["dur"]) for it in airs])
        count = {}
        for g in groups.values():
            count[g] = count.get(g, 0) + 1
        secs = int(sum(it["dur"] for it in airs))
        lines = [_("[B]%d music videos found[/B] (%d from your library, %d more in %s)") % (
                     found, lib, found - lib, _folders_label(folders) or "-"),
                 _("Airing: %d (%d h %02d min)") % (len(airs), secs // 3600, secs % 3600 // 60)]
        if count:
            lines.append(_("Frame rates (one per block): %s") % u"  \u00b7  ".join(
                _("%s fps: %d") % (g, n) for g, n in sorted(count.items(), key=lambda x: -x[1])))
        if waiting:
            lines.append(_("Not measured yet: %d. CableBox reads them while the TV is off.") % waiting)
        if skipped:
            lines += ["", _("[B]Skipped[/B]")] + ["  %s  [COLOR grey](%s)[/COLOR]" % (n, MV_REASONS.get(w, w))
                                                  for n, w in skipped]
        if unreadable:
            lines += ["", _("[B]Couldn't be read[/B]")] + ["  " + n for n in unreadable]
        D.textviewer(_("Check music videos"), "[CR]".join(lines))
        if not waiting or not confirm(_("CableBox reads each file's length, frame rate and tags. Your files "
                                        "are not changed."), _("Read them now"), _("Not now"),
                                      heading=_("Read the %d music videos not measured yet?") % waiting):
            return
        pd = xbmcgui.DialogProgress()
        pd.create(TITLE, _("Reading music videos..."))
        done = [0]

        def pause():
            done[0] += 1
            pd.update(int(100.0 * done[0] / max(1, waiting)), _("%d of %d") % (done[0], waiting))
        try:
            library.musicvideos_refresh(abort=pd.iscanceled, pause=pause, sources=srcs)
        finally:
            pd.close()


def _station_label(ch):
    from . import stations
    st = stations.BY_ID.get(ch.get("station") or "")
    if st and ch.get("name") != st["name"]:
        return _("%s (renamed; its logo and shows)") % st["name"]
    return st["name"] if st else _("none (your own)")


def _rename(ch, new):
    """A new name, followed through: call letters that were still the automatic
    ones follow the name, and a built-in station's time-of-day names (CAM Jr.)
    are kept only if the viewer says so."""
    from . import stations
    st = stations.BY_ID.get(ch.get("station") or "")
    old = ch["name"]
    auto = set([C.callsign(old)] + ([st["call"]] if st else []))
    ch["name"] = new
    if not ch.get("callsign") or ch["callsign"] in auto:
        ch["callsign"] = C.callsign(new)
        D.notification(TITLE, _("Call letters are now %s") % ch["callsign"], time=2500)
    kit = [b for b in ch.get("brand_blocks") or [] if stations.is_kit_block(b)]
    if st and kit:
        names = ", ".join(b.get("name", "") for b in kit)
        if ask(_("At those times %s would still go by %s, with their logos.") % (new, names),
               _("Remove them"), _("Keep them"), heading=_("Keep the names %s?") % names) == "yes":
            ch["brand_blocks"] = [b for b in ch["brand_blocks"] if not stations.is_kit_block(b)]


def _blocks_label(ch):
    bl = ch.get("brand_blocks") or []
    return ", ".join("%s %s-%s" % (b.get("name", ""), b.get("start", ""), b.get("end", "")) for b in bl) or _("none")


def pick_station(ch, chans=()):
    """Give the channel one of the built-in stations (name, call letters, logo,
    time-of-day names and its shows), or make it the viewer's own again: the
    station's logo and names go, the name and all the programming stay."""
    from . import stations
    cur = stations.BY_ID.get(ch.get("station") or "")
    used = dict((c.get("station"), c["number"]) for c in chans if c.get("station") and c.get("id") != ch.get("id"))
    rows, keys = [], []
    if cur:
        rows.append(_("[B]Make this channel my own[/B]"))
        keys.append(None)
    for s in stations.STATIONS:
        note = ", ".join(b["name"] for b in s.get("blocks", []))
        if s["id"] in used:
            note = _("already on channel %d") % used[s["id"]]
        elif cur and s["id"] == cur["id"]:
            note = _("this channel's station")
        rows.append("%s   [COLOR grey]%s[/COLOR]" % (s["name"], note))
        keys.append(s)
    j = D.select(_("Station for channel %d") % ch["number"], rows + [_("Cancel")])
    if j < 0 or j >= len(keys):
        return
    st = keys[j]
    if st is None:
        lines = [_("Name: %s  ·  Call letters: %s") % (stations.own_name(ch), stations.own_callsign(ch)),
                 _("All of its programming stays."),
                 _("%s's logo goes. Choose your own under Logo.") % cur["name"]]
        kit = [b.get("name", "") for b in ch.get("brand_blocks") or [] if stations.is_kit_block(b)]
        if kit:
            lines.append(_("It no longer goes by %s.") % ", ".join(kit))
        if confirm("[CR]".join(lines), _("Make it my own"), heading=_("Make channel %d your own?") % ch["number"]):
            stations.drop(ch)
        return
    if cur and st["id"] == cur["id"] and ch["name"] == st["name"]:
        return
    what = stations.changes(ch, st)
    own_logo = ch.get("logo") and ch["logo"] != "none"
    lines = [_("Name: %s  ·  Call letters: %s") % (what["name"], what["call"]),
             _("Logo: your own image stays") if own_logo else _("Logo: its built-in logo")]
    if what["blocks"]:
        lines[-1] += "  ·  " + _("goes by %s at times") % ", ".join(what["blocks"])
    lines.append(_("Adds: %s") % (", ".join(describe_source(s) for s in what["adds"])[:150]
                                  or _("no programming")))
    if what["removes"]:
        lines.append(_("Removes %s's: %s") % (cur["name"], ", ".join(describe_source(s) for s in what["removes"])[:120]))
    if confirm("[CR]".join(lines), _("Use this station"), heading=_("Use %s on channel %d?") % (st["name"], ch["number"])):
        stations.apply(ch, st)


def edit_brand_blocks(ch):
    """Times of day when the channel goes by another name and logo (CAM Jr. 6 AM-noon)."""
    while True:
        blocks = ch.setdefault("brand_blocks", [])
        rows = [_("[B]+ Add a name[/B]")] + ["%s   %s - %s" % (b.get("name", ""), b.get("start", ""), b.get("end", ""))
                                             for b in blocks]
        i = done_select(_("Names by time of day"), rows)
        if i < 0:
            return
        if i == 0:
            name = D.input(_("Name at this time of day (e.g. CAM Jr.)"), "")
            if not name:
                continue
            a = ask_time(_("Starts at"), "06:00")
            b = ask_time(_("Ends at"), "12:00") if a else None
            if a and b:
                blocks.append({"name": name, "call": "", "start": a, "end": b})
                D.notification(TITLE, _("%s added (%s - %s)") % (name, a, b), time=2500)
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
        elif j == 3 and confirm_remove(_("Remove the name %s?") % bl.get("name", "")):
            blocks.pop(i - 1)


# ------------------------------------------------------------------ branding & clips
def _folder_name(path):
    return path.rstrip("/\\").replace("\\", "/").split("/")[-1] if path else ""


def _logo_row(ch, ts=None):
    """(label, detail) for the logo the channel shows (at ts: a time block's own)."""
    from . import stations
    br = stations.brand(ch, ts) if ts else stations.brand(dict(ch, brand_blocks=[]))
    path, src = br["logo"], br["logo_from"]
    name = os.path.basename(path) if path else _("none")
    detail = {
        "picked": _("The image you chose for this channel."),
        "block_picked": _("The image you chose for this time-of-day name."),
        "folder": _("From the channel's station folder."),
        "block_folder": _("From this time-of-day name's own folder."),
        "builtin": _("CableBox's built-in logo. Any logo of your own replaces it."),
        "logofolder": _("Matched by name in the logo folder (Settings > Channels)."),
        "block_logofolder": _("Matched by this time-of-day name in the logo folder (Settings > Channels)."),
        "none": _("Switched off for this channel. Select to choose a logo."),
    }.get(src, _("No logo found. Select to choose an image, or put a logo.png in the channel's folder."))
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


def station_folder(ch, chans):
    """Channel editor > Identity > Station folder: the channel's own folder (logo,
    bumps, IDs, commercials, one folder per time-of-day name), what's in it, and
    making or repairing it.  Never deletes anything."""
    from . import stations
    _FOLDERS_TOUCHED[0] = True
    while True:
        stations.clear_cache()
        root = K.setting("stations_folder")
        folder = stations.channel_folder(ch)
        rows, keys = [], []

        def add(key, label, detail=""):
            keys.append(key)
            rows.append(_menu_row(label, detail))
        if not root:
            add("root", _("Station folder: not set up"),
                _("Select to choose where channel folders go (Settings > Channels > Stations folder)."))
        elif folder:
            add("browse", _("Station folder: %s") % _folder_name(folder), _("Select to look inside. ") + folder)
        else:
            add("repair", _("Station folder: none yet"),
                _("Looking for a folder named %s in %s. Select to make it.") % (
                    " / ".join("'%s'" % n for n in stations.folder_names(ch)[:3]), root))
        for kind in ("bumps", "ids", "commercials"):
            label, detail, _on = _clip_row(ch, kind, folder)
            add("", label, detail)
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
                _("Adds what's missing (bumps, ids, commercials, names by time of day). Never deletes anything."))
            orphans = stations.orphan_folders(chans)
            if orphans and not folder:
                add("adopt", _("Use an existing folder for this channel..."),
                    _("%d folders match no channel - e.g. one made before a rename.") % len(orphans))
        i = done_select(_("%s - station folder") % ch["name"], rows, useDetails=True)
        if i < 0:
            return
        key = keys[i]
        if key == "root":
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
    if ch.get("logo") == "none":
        return _("none")
    if ch.get("logo"):
        return os.path.basename(ch["logo"])
    from . import stations
    br = stations.brand(dict(ch, brand_blocks=[]))
    if not br["logo"]:
        return _("none")
    how = {"folder": _("%s (station folder)"), "logofolder": _("%s (from the logo folder)"),
           "builtin": _("%s (built-in)")}.get(br["logo_from"], "%s")
    return how % os.path.basename(br["logo"])


def _browse_logo(ch):
    """Choose an image file as the channel's logo (Kodi can't show SVG)."""
    from . import logos
    p = D.browse(2, _("Station logo (PNG with a transparent background looks best)"), "pictures",
                 "|".join(logos.IMAGE_EXT + (".svg",)))
    if not p:
        return
    if p.lower().endswith(".svg"):
        D.ok(TITLE, _("Kodi can't show SVG images.  Convert the logo to PNG (keeping the transparent "
                      "background) and choose that instead."))
        return
    ch["logo"] = p


def pick_logo(ch):
    from . import logos
    j = D.select(_("Station logo for %s") % ch["name"],
                 [_("Choose an image..."), _("Use the logo folder (matched by name, call letters or number)"),
                  _("No logo")])
    if j == 0:
        _browse_logo(ch)
    elif j == 1:
        ch.pop("logo", None)
        logos.clear_cache()
        if not K.setting("logo_folder"):
            D.ok(TITLE, _("Set the logo folder first: Settings > Channels > Logo folder."))
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
        elif confirm_remove(_("Remove this?[CR]%s") % rows[i]):
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
            # step by step: Back on any step adds nothing
            label = D.input(_("Name (e.g. Prime Time, Saturday Cartoons)"), _("Prime Time"))
            if not label:
                continue
            a = ask_time(_("Starts at"), "20:00")
            b = ask_time(_("Ends at"), "23:00") if a else None
            if not (a and b):
                continue
            j = D.select(_("On"), [x[1] for x in DAY_OPTS])
            if j < 0:
                continue
            dp = {"label": label, "start": a, "end": b, "days": DAY_OPTS[j][0], "sources": []}
            edit_sources(dp["sources"], dp["label"])
            if dp["sources"]:
                ch["dayparts"].append(dp)
                D.notification(TITLE, _("%s added (%s - %s)") % (label, a, b), time=2500)
            else:
                D.notification(TITLE, _("%s not added - it had no programming") % label, time=3000)
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
            elif j == 2 and confirm_remove(_("Remove the time block %s?") % dp.get("label", _("Block"))):
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


def _signoff_label(ch):
    mode = C.signoff_mode(ch)
    if mode == "folder":
        return os.path.basename(ch["signoff_path"].rstrip("/\\")) or ch["signoff_path"]
    return _("Built-in sign-off card") if mode == "card" else _("none")


def edit_offair(ch):
    styles = [("standby", _("1950s 'Please stand by' test card")), ("bars", _("Color bars")),
              ("bars_tone", _("Color bars with tone"))]
    while True:
        style = ch.get("offair_style", "standby")
        rows = [_("[B]+ Add off-air hours[/B]")]
        rows += ["%s - %s   %s" % (w["start"], w["end"], _days_label(w.get("days"))) for w in ch["offair"]]
        n = len(rows)
        rows += [_("Off-air screen: %s") % dict(styles).get(style, style),
                 _("Sign-off clip (anthem, farewell...): %s") % _signoff_label(ch),
                 _("Sign-on clip (morning start-up): %s") % (
                     os.path.basename(ch.get("signon_path", "").rstrip("/\\")) or _("none"))]
        i = done_select(_("Off-air hours"), rows)
        if i < 0:
            return
        if i == 0:
            a = ask_time(_("Sign off at"), "00:00")
            b = ask_time(_("Sign on at"), "07:00") if a else None
            if not (a and b):
                continue
            days = pick_days(_("Which nights?"))
            if days is None:
                continue
            ch["offair"].append({"start": a, "end": b, "days": days})
            D.notification(TITLE, _("Off the air %s - %s, %s") % (a, b, _days_label(days)), time=2500)
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
            elif j == 2 and confirm_remove(_("Remove the off-air hours %s?") % rows[i]):
                del ch["offair"][i - 1]
        elif i == n:
            j = D.select(_("Off-air screen"), [x[1] for x in styles])
            if j >= 0:
                ch["offair_style"] = styles[j][0]
        elif i == n + 1:
            modes = ["none", "card", "folder"]
            j = D.select(rows[i], [_("None"), _("Built-in sign-off card"), _("Choose folder...")],
                         preselect=modes.index(C.signoff_mode(ch)))
            if j in (0, 1):
                ch["signoff_mode"] = modes[j]
                ch.pop("signoff_path", None)
            elif j == 2:
                p = D.browse(0, rows[i], "video", defaultt=ch.get("signoff_path", ""))
                if p:
                    ch["signoff_mode"] = "folder"
                    ch["signoff_path"] = p
        else:
            field = "signon_path"
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
    if not clear or not confirm(_("Clear the resume point of %d items?[CR](%d kept)") % (len(clear), len(keep)),
                                _("Clear them")):
        return
    for _label, kind, item, _r in clear:
        progress.clear_resume(kind, item)
    D.notification(TITLE, _("Cleared %d items") % len(clear), time=3000)


def _names(chans, most=3):
    """'Keystone, Beacon +4 more' for a question about several channels."""
    names = [c["name"] for c in chans]
    return ", ".join(names[:most]) + (_(" +%d more") % (len(names) - most) if len(names) > most else "")


def quick_setup():
    """One-step changes for every channel at once."""
    from . import presets
    while True:
        opts = [_("Sign off overnight on all channels (choose hours)"),
                _("Never sign off (remove off-air hours from all channels)"),
                _("Build prime-time lineups on all channels (choose hours)"),
                _("Remove the automatic prime-time lineups")]
        i = done_select(_("Sign-off and prime time for all channels"), opts)
        if i < 0:
            return
        chans = C.load()
        if i == 0:
            a = ask_time(_("Sign off at"), presets.OFF_START)
            b = ask_time(_("Back on the air at"), presets.OFF_END)
            if not (a and b):
                continue
            only_empty = False
            have = presets.with_hours(chans)
            if have:                             # never over a channel's own hours unasked
                r = ask(_("%s already sign off at times of their own.") % _names(have),
                        _("Replace theirs"), _("Only the others"), cancel=_("Cancel"),
                        heading=_("Replace the off-air hours on %d channels?") % len(have))
                if r is None:
                    continue
                only_empty = r == "no"
            n = presets.set_overnight(chans, a, b, only_empty=only_empty)
            C.save(chans)
            D.notification(TITLE, _("Channels signing off %s - %s: %d") % (a, b, n), time=3000)
        elif i == 1:
            have = presets.with_hours(chans)
            if not have:
                D.notification(TITLE, _("No channel signs off"), time=2500)
                continue
            if not confirm_remove(_("%s would stay on the air around the clock.") % _names(have)):
                continue
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


def _extras_reasons():
    # extras.REASONS keys -> translated labels (literal strings for strings.po)
    return {"deleted": _("deleted, extended or alternate"), "bloopers": _("bloopers"),
            "trailer": _("trailer or promo"), "gallery": _("gallery or storyboards"),
            "reel": _("demo reel"), "newsreel": _("newsreel"), "music": _("music"),
            "short": _("short film"), "commentary": _("commentary"), "other": _("disc extra"),
            "short_length": _("under 60 s"), "unrecognised": _("name not recognised"),
            "unreadable": _("length can't be read")}


def look_for_extras():
    """Look for movie extras: look through the Extras folders and measure every
    extra that hasn't been measured, with a progress dialog whose Cancel works.
    Progress is saved as it goes; a finished look always says how it went.
    Only ever started by an explicit choice.  Returns True when it finished."""
    if not library.extras_take_over():
        D.ok(TITLE, _("CableBox is already looking for extras - try again in a minute."))
        return False
    pd = xbmcgui.DialogProgress()
    pd.create(_("Look for movie extras"), _("Looking through your movies' Extras folders..."))

    def progress(frac, phase, n, total):
        if phase == "list":
            line = _("Looking through Extras folders: %d of %d movies") % (n, total)
        else:
            line = _("Measuring extras: %d of %d") % (n, total)
        pd.update(int(100 * frac), line)

    try:
        done = library.extras_refresh(abort=pd.iscanceled, progress=progress, retry=True)
    finally:
        pd.close()
    if not done:
        D.notification(TITLE, _("Stopped - what was found so far is kept"), time=3000)
        return done
    secs, n = _extras_air()
    if secs:
        own = next((c["name"] for c in C.load() if c.get("type") == "extras"), "")
        D.notification(TITLE, (_("%s has %d h %02d min to air from %d films") %
                               (own, secs // 3600, secs % 3600 // 60, n)) if own else
                       (_("%d h %02d min of movie extras to air from %d films") % (secs // 3600, secs % 3600 // 60, n)),
                       time=5000)
    else:
        D.notification(TITLE, _("No extras to air found - see Settings > Tools > Check extras"), time=5000)
    return done


def check_extras():
    """Settings > Tools > Check extras: every movie Extras file as the Behind the
    scenes channel will treat it.  Reads the cache only (the service lists and
    measures the folders in the background); looking now is always the viewer's
    choice.  After the list, offers what can be done next."""
    scanned, measured, total, unreadable = library.extras_status()
    if not scanned:
        if not confirm(_("CableBox does it in the background while the TV is off.[CR]Kodi looks for extras in a "
                         "folder named Extras next to the movie's file (or inside VIDEO_TS or BDMV)."),
                       _("Look now"), heading=_("Look through your movies' Extras folders now?")):
            return
        look_for_extras()
    elif total - measured - unreadable > 0:
        r = ask((_("Lengths measured: %d of %d") % (measured, total)) + "[CR]" +
                _("CableBox measures the rest in the background while the TV is off, or it can look now."),
                _("Look now"), _("Show the list"), cancel=_("Cancel"), heading=_("Check extras"))
        if r is None:
            return
        if r == "yes":
            look_for_extras()
    while True:
        enough = _extras_list()
        if enough is None:
            return
        scanned, measured, total, unreadable = library.extras_status()
        if total - measured - unreadable > 0:
            if confirm(_("Lengths measured: %d of %d") % (measured, total), _("Look now"), _("Done"),
                       heading=_("Look for the rest now?")):
                look_for_extras()
                continue                    # the list again, with what was found
        if enough and not any(c.get("type") == "extras" for c in C.load()):
            secs, n = _extras_air()
            if confirm(_("Your movies have %d h %02d min of extras to air from %d films.") %
                       (secs // 3600, secs % 3600 // 60, n), _("Add channel"), _("Not now"),
                       heading=_("Add a Behind the scenes channel?")):
                add_channel(C.load(), kind="extras")
        return


def _extras_list():
    """Check extras' list (Info).  True when there's enough for a Behind the
    scenes channel, False when not, None when there was no list to show."""
    from . import extras
    scanned, measured, total, unreadable = library.extras_status()
    films = library.extras_films()
    if not films:
        D.ok(_("Check extras"), _("None of your movies has an Extras folder.[CR][CR]Kodi looks for extras in a "
                                  "folder named Extras next to the movie's file (or inside VIDEO_TS or BDMV).")
             if scanned else _("CableBox hasn't looked through your movies' Extras folders yet."))
        return None
    loose = K.setting_bool("extras_unrecognised", False)
    labels = _extras_reasons()

    def mmss(s):
        return "%2d:%02d" % (s // 60, s % 60) if s else "--:--"

    body, reasons = [], {}
    n_films = n_files = air_files = air_secs = air_films = shared = pending = 0
    unreadable_paths = library.extras_unreadable()
    for f in films:
        rows = []
        for rel, path, dur in f["files"]:
            info = extras.classify(rel, f["title"], f["year"], dur, loose)
            if info["air"] and not dur:
                # only measured extras air (BACKLOT plans by length)
                if path in unreadable_paths:
                    info = dict(info, air=False, reason="unreadable")
                else:
                    info = dict(info, air=False, reason="", pending=True)
            rows.append((rel, info, dur))
        if not rows:
            continue
        name = "%s (%s)" % (f["title"], f["year"]) if f["year"] else f["title"]
        if f["shared"]:
            shared += 1
            body.append(_("[B]%s[/B]  [COLOR orange]this Extras folder is shared by several movies, so it "
                          "isn't used - give each movie its own folder[/COLOR]") % name)
            body.append("")
            continue
        n_films += 1
        n_files += len(rows)
        durs = dict((r, d) for r, _i, d in rows)
        air = extras.segment_order([(r, i) for r, i, _d in rows if i["air"]])
        secs = int(sum(durs[r] for r, _i in air))
        if air:
            air_films += 1
        air_files += len(air)
        air_secs += secs
        body.append(_("[B]%s[/B]  [COLOR grey]%d to air, %d min[/COLOR]") % (name, len(air), secs // 60))
        for r, i in air:
            body.append(_("  Air  %s  %s  [COLOR grey]%s[/COLOR]") % (mmss(durs[r]), i["title"], r))
        for r, i, d in rows:
            if i.get("pending"):
                pending += 1
                body.append(_("  [COLOR grey]Not measured yet  %s  %s[/COLOR]") % (i["title"], r))
            elif not i["air"]:
                reasons[i["reason"]] = reasons.get(i["reason"], 0) + 1
                body.append(_("  [COLOR grey]Skipped: %s  %s  %s[/COLOR]") % (labels.get(i["reason"], ""), mmss(d), r))
        body.append("")
    skipped = n_files - air_files - pending
    enough = air_secs >= 2 * 3600 and air_films >= 5
    head = [_("[B]Summary[/B]"),
            _("  %d films with extras, %d videos") % (n_films, n_files),
            _("  Air: %d videos, %d h %02d min, from %d films") % (air_files, air_secs // 3600,
                                                                  air_secs % 3600 // 60, air_films),
            _("  Skipped: %d videos") % skipped]
    for k, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        head.append("      %s: %d" % (labels.get(k, k), n))
    head.append(_("  Enough for a Behind the scenes channel (2 hours from 5 films): %s") %
                (_("yes") if enough else _("not yet")))
    head.append(_("  Lengths measured: %d of %d") % (measured, total))
    if total - measured - unreadable > 0:
        head.append(_("      the rest are measured in the background while the TV is off, or with Look now"))
    if shared:
        head.append(_("  %d Extras folders are shared by several movies and aren't used.") % shared)
    head += ["", _("To change what airs, rename files or put them in a subfolder of Extras named Behind the scenes, "
                   "Making of, Interviews, Featurettes or Documentaries (those always air).  CableBox never "
                   "changes your files."), ""]
    D.textviewer(_("Check extras"), "[CR]".join(head + body))
    return enough


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

Back takes you to where you switched the TV on: this menu if you chose Watch TV
here, otherwise Kodi.  Menu > CableBox menu turns the TV off and opens this menu
from anywhere; Watch TV turns it back on, on the same channel.

[B]Closed captions[/B]
Main menu > Closed captions, or the Menu button while watching, switches captions
on or off for every programme (like a TV's CC setting).  'Caption options' in that
menu picks a track or loads a subtitle file.  To use the remote's subtitle button,
run Settings > On screen > Remote CC button once.

[B]Station folders[/B]
Set a Stations folder (Settings > Channels) and CableBox keeps one folder per channel,
named after the channel (or its call letters, or 'Channel 7'): logo.png, bumps/,
ids/ and commercials/, plus a folder per time-of-day name such as CAM Jr.  Channel
manager > channel > Breaks & clips shows the clips the channel really uses and where
they come from; Identity > Station folder makes or repairs its folders.  Renaming a
channel offers to rename its folder too.

[B]Stations and your own channels[/B]
A built-in station (Comedy Corner, Chameleon...) is a brand - name, call letters,
logo, names by time of day - plus its shows.  Channel manager > channel > Identity:
'Make this channel my own' takes the brand away and keeps the name and all the
programming; rename it and give it your own logo.  Any logo of yours (the image you
picked, the station folder's, the logo folder's) beats a built-in one.

[B]How the schedule works[/B]
Nothing to compile.  Each channel pulls from your Kodi library (shows, genres,
decades, movies, smart playlists) or from folders, and its schedule writes itself
as time goes by.  'Same show same time every day' channels air a fixed daily
lineup and series always continue with the next episode.  Time blocks let you put
cartoons on Saturday mornings or movies in prime time.

Edit a channel and the change applies from its next programme - every show keeps its place.

[B]One channel per show[/B]
Each TV show has one home channel - the one it fits best (your own picks first,
then folders/tags/studios, then its main genre).  A show whose genres are too
small for a channel of their own goes on the biggest genre network.  And the same show is never on two channels at the same time.
Settings > Channels > 'Shows on more than one channel' changes this.

[B]Menu and tools[/B]
The menu keeps to the everyday things: Watch TV, What's on now (tune straight to a
show), the Channel manager, the Weekly planner, Holidays & events, Settings and
Help.  Lineup tools (build my lineup, move shows, sign-off and prime time, station
folders) are in the Channel manager; maintenance (check my videos, refresh schedules,
start series over, start over) is on the Tools page in Settings.  In Settings, OK
saves and Back cancels; a button row there (a tool, Preview a promo) saves what you changed before it, like OK.
Changes to settings, channels and station clips apply from
each channel's next programme on their own: what's on stays on, and every show keeps
its next episode.  Only Tools > Start series over sends shows back to episode one.

[B]Fine-tuning[/B]
Channel manager > Lineup tools > 'Move shows between channels': pick a show (say, Good Eats)
and tick the channels it should air on.
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
Right past Sunday goes to the next week, Left past Monday to the week before;
holidays and specials show in their own week, with a star on the day.

[B]Your watch progress[/B]
CableBox puts back resume points, watched status and last-played dates after it
airs something, so surfing doesn't fill your 'In progress' list (Settings >
Start-up & library).  'Clean up my In progress list' on the same page tidies up an older list.

[B]Sign-off and prime time for all channels[/B]
Channel manager > Lineup tools: overnight sign-off (default 12 AM - 5 AM) and automatic
prime-time lineups (default 8 - 11 PM) for every channel at once.  Channels that
already have off-air hours keep them unless you say otherwise.  Prime-time
slots appear in the weekly planner; edit any of them and it becomes yours.

[B]Holidays[/B]
Halloween (October, all-out on the 31st), Thanksgiving Day and Christmas (from the day
after Thanksgiving, all-out on the 24th and 25th): each channel mixes in its own holiday
episodes and movies (Kodi tags first, then genres such as Horror, then titles) - a few at
first, more as the day gets closer, all day on the day itself.  Optional holiday
commercial and bump folders.  The rest of the year Christmas and Thanksgiving episodes
are saved for their season.  Main menu > Holidays & events > Holiday seasons: each
season's dates (Canadian Thanksgiving too), how much in the run-up, tags and genres
ticked from your library, extra title words, and Show what matches.  + Add a
season adds any holiday, real or made up (Festivus, Bastille Day, Diwali with
the dates you type for each year).

[B]Holidays and specials[/B]
Main menu > Holidays & events > Calendar (also Channel manager > channel >
Schedule): a month calendar - OK on a day adds a special
there, Menu shows them as a list.  The holiday seasons are shaded on it (big days red,
run-up plum) and seasons and specials share one list of holidays: When? > A holiday
from my list, and Holiday episodes work for every holiday.
A special is a marathon or a holiday lineup on a date - 31 December, the 4th Thursday of
November, Good Friday - on one channel or several, all day or for hours you
choose, back every year.  It airs instead of the channel's usual schedule for
those hours, and breaks promote it in the days before.

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
Settings > Tools > 'Check my videos' shows which clips can't be used.

[B]Promos[/B]
Settings > Breaks > Promos: breaks now and then include a short promo for
what this channel airs next - the episode's still, the show's logo, the episode
title, a short synopsis when one fits, 'Up next' or the day and time, and the show's
theme.mp3, all from your own library (nothing in it is changed).  Your own promo
clips in a station folder's promos/ come first.  Settings > Breaks > Preview a promo
plays one channel's next promo (or a later one) straight away.

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
        return planner.open_planner(progs[j]["id"])     # True if it saved a change
    return False


# Tools reached from Settings action rows (RunScript(script.cablebox42,tool,<name>)): the Tools
# page, plus Remote CC button and Clean up my 'In progress' list.  'specials' and 'seasons' stay
# for old favourites / skin shortcuts: Holidays & events is in the main menu only.
TOOLS = {
    "wizard": lambda: wizard(),
    "quick": lambda: quick_setup(),
    "shows": lambda: shows_and_channels(),
    "fillers": lambda: check_fillers(),
    "extras": lambda: check_extras(),
    "progress": lambda: clean_in_progress(),
    "refresh": lambda: refresh_tool(),
    "rebuild": lambda: refresh_tool(),      # the old Rebuild schedules (favourites, skins)
    "restart_series": lambda: start_series_over(),
    "folders": lambda: make_station_folders(),
    "reset": lambda: factory_reset(),
    "cckeys": lambda: cc_button(),
    "finder": lambda: run_finder(),
    "skipped": lambda: check_skipped(),
    "chapters": lambda: check_chapters(),
    "specials": lambda: open_specials(),
    "seasons": lambda: open_seasons(),       # refreshes after (not in NO_REFRESH): seasons are settings
}


def _chapter_word(info, raw):
    if raw is None:
        return _("not read yet")
    if "x" in raw:
        return _("unreadable")
    return {"act": _("act breaks"), "dense": _("scene chapters"), "auto": _("automatic chapters")}.get(
        (info or {}).get("v"), _("no chapters"))


def read_chapters_now():
    """Check chapters' Read now: every episode file not read yet, with a progress
    dialog whose Cancel keeps what's read; planned episodes whose breaks change are
    planned again (keep my place)."""
    pd = xbmcgui.DialogProgress()
    pd.create(_("Reading chapters"), _("Reading chapters: %d of %d") % (0, 0))
    try:
        n, got = library.chapters_read_all(abort=pd.iscanceled, progress=lambda i, t: pd.update(
            int(100.0 * i / max(1, t)), _("Reading chapters: %d of %d") % (i, t)))
        canceled = pd.iscanceled()
    finally:
        pd.close()
    if got:
        refresh_now()
    r, total = library.chapters_status()
    if canceled:
        D.notification(TITLE, _("Stopped - the chapters read so far are kept"), time=3000)
    else:
        D.notification(TITLE, (_("Chapters read: %d of %d - schedules updated") if got else
                               _("Chapters read: %d of %d")) % (r, total), time=4000)


def check_chapters():
    """Settings > Tools > Check chapters: each show's episodes by verdict (act breaks,
    scene chapters, automatic, none, not read yet); pick a show for Automatic /
    Always use chapters / Never use chapters (its own choice wins), or its episodes
    with where their breaks and credits go.  A menu: changes save as you go."""
    if not K.setting_bool("chapter_breaks", True):
        D.ok(_("Check chapters"), _("Commercial breaks at chapter marks is off (Settings > Breaks)."))
        return
    shows = sorted(library.all_tvshows(), key=lambda s: library.natural_key(s["title"]))
    if not shows:
        D.ok(_("Check chapters"), _("No TV shows in the library."))
        return
    library.chapter_reload()                 # what the service's reader has added
    r, total = library.chapters_status()
    if total and r < total:
        a = ask((_("Chapters read: %d of %d") % (r, total)) + "[CR]" +
                _("CableBox reads them in the background: whenever Kodi is idle, and while the TV is on the "
                  "episodes airing in the next 6 hours first. Episodes not read yet get evenly spaced breaks."),
                _("Read now"), _("Show the list"), cancel=_("Cancel"), heading=_("Check chapters"))
        if a is None:
            return
        if a == "yes":
            read_chapters_now()
    cache = library.chapter_cache()
    modes = {"auto": _("Automatic"), "always": _("Always use chapters"), "never": _("Never use chapters")}
    eps_of = {}
    while True:
        rows = []
        for s in shows:
            if s["tvshowid"] not in eps_of:
                eps_of[s["tvshowid"]] = library.episodes_for(s["tvshowid"])
            counts = {"act": 0, "dense": 0, "auto": 0, "none": 0, "todo": 0}
            for e in eps_of[s["tvshowid"]]:
                raw = cache.raw(e["file"])
                v = (cache.info(e["file"]) or {}).get("v") if raw else None
                counts["todo" if raw is None else v if v in ("act", "dense", "auto") else "none"] += 1
            mode = library.chapter_mode(s["title"])
            li = xbmcgui.ListItem(s["title"] + (("  " + _("[%s]") % modes[mode]) if mode != "auto" else ""),
                                  _("%d act breaks, %d scene, %d automatic, %d none, %d not read yet") % (
                                      counts["act"], counts["dense"], counts["auto"], counts["none"], counts["todo"]))
            rows.append(li)
        i = done_select(_("Check chapters"), rows, useDetails=True)
        if i < 0:
            return
        show = shows[i]
        while True:
            mode = library.chapter_mode(show["title"])
            opts = [("auto", modes["auto"]), ("always", modes["always"]), ("never", modes["never"])]
            labels = [("[B]%s[/B]" % lab) if key == mode else lab for key, lab in opts] + \
                [_("Episodes and their breaks")]
            j = done_select(_("%s: commercial breaks") % show["title"], labels)
            if j < 0:
                break
            if j < 3:
                library.set_chapter_mode(show["title"], opts[j][0])
                continue
            lines = [_("CableBox reads them in the background: whenever Kodi is idle, and while the TV is on the "
                       "episodes airing in the next 6 hours first. Episodes not read yet get evenly spaced breaks."), ""]
            fm = lambda t: "%d:%02d" % (int(t) // 60, int(t) % 60)
            for e in eps_of[show["tvshowid"]]:
                raw = cache.raw(e["file"])
                info = cache.info(e["file"]) if raw else None
                bits = [_chapter_word(info, raw)]
                if info and info.get("m") and info.get("v") in ("act", "dense"):
                    bits.append(_("breaks at %s") % ", ".join(fm(t) for t in info["m"]))
                if info and info.get("cr") is not None:
                    bits.append(_("credits at %s") % fm(info["cr"]))
                label = "S%02dE%02d" % (e.get("season", 0), e.get("episode", 0))
                lines.append("%s  %s  -  %s" % (label, e.get("title", ""), "; ".join(bits)))
            D.textviewer(_("%s: commercial breaks") % show["title"], "[CR]".join(lines))


def check_skipped():
    """Settings > Tools > Check skipped episodes: the TV episodes the last refresh
    left out for being shorter than Skip episodes shorter than (scheduler._skip_short),
    by series.  Read-only; nothing is moved or hidden in Kodi."""
    from . import scheduler
    data = K.load_json(scheduler.SKIPPED_FILE, {}) or {}
    eps = data.get("episodes") or []
    limit = scheduler.skip_short_secs(K.schedule_cfg()) // 60
    if not eps:
        xbmcgui.Dialog().ok(_("Check skipped episodes"), _("No episodes are skipped.") + "[CR]" +
                            _("Episodes are only listed after a refresh: Tools > Refresh schedules."))
        return
    lines = [_("Shorter than %d min (Settings > Channels > Skip episodes shorter than). "
               "Their series go on to the next real episode; the files stay where they are.") % limit, ""]
    for path, series, label, secs in sorted(eps, key=lambda e: (e[1].lower(), e[2], e[0])):
        lines.append(_("%s  %s  (%d:%02d)") % (series, label or os.path.basename(path), int(secs) // 60, int(secs) % 60))
        lines.append("    " + path)
    xbmcgui.Dialog().textviewer(_("Skipped episodes"), "[CR]".join(lines))


def open_specials():
    """Holidays and specials: main menu > Holidays & events > Calendar (tool 'specials')."""
    from . import specials_editor
    specials_editor.open_specials()


def holidays_menu():
    """Main menu > Holidays & events: one place for the exact kind (specials) and the
    automatic kind (holiday seasons).  A saved special replans in the service
    (specials_replan.json); a changed season is checked for a refresh on the way out."""
    from . import specials_editor as E
    from . import seasons_editor
    while True:
        rows = [_menu_row(_("Calendar"), _("Specials on their days, the seasons shaded")),
                _menu_row(_("Add a special"), _("A marathon or a holiday lineup on a date, back every year")),
                _menu_row(_("Holiday seasons (automatic)"),
                          _("Halloween, Christmas, your own: dates and what counts"))]
        i = done_select(_("Holidays & events"), rows, useDetails=True)
        if i < 0:
            return
        if i == 0:
            E.set_view("calendar")
            E.open_specials()
        elif i == 1:
            chans = C.load()
            if not [c for c in chans if c["type"] in AIR_TYPES]:
                D.ok(TITLE, _("Add a channel first."))
                continue
            sid = E.add_special(E.load(chans), chans)
            if sid:
                E.special_page(sid)
        else:
            seasons_editor.open_seasons()
            refresh_if_changed()


def open_seasons():
    """Main menu > Holidays & events > Holiday seasons (tool 'seasons')."""
    from . import seasons_editor
    seasons_editor.open_seasons()


def run_finder():
    from . import finder
    finder.run()


def cc_button():
    """Settings > On screen > Remote CC button..."""
    from . import captions
    captions.keymap_tool()
TOOL_BUSY = "script.cablebox42.tool"

CLIP_KINDS = ("bumps", "ids", "commercials")

# CableBox's own data (in its profile folder).  durations.json / codecs.json are
# only a cache of how long each video is and how it's encoded - kept, so a fresh
# setup doesn't have to measure the whole library again.
RESET_FILES = ("channels.json", "assign.json", "state.json", "unplayable.json", "weather_cache.json", "calendar.json",
               "finder.json", "seasons.json")


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
                  _("Reset settings to the defaults too"), _("Cancel")])
    if j not in (0, 1):
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
    _FOLDERS_TOUCHED[0] = True
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
        if c["type"] in CLIP_TYPES:
            made += ensure_channel_folders(c)
    stations.clear_cache()
    if not report:
        return made
    lines = [_("[B]Station folders[/B]  [COLOR grey]%s[/COLOR]") % root,
             _("%d new folders made - nothing that was already there was changed.") % made, ""]
    for c in chans:
        if c["type"] in CLIP_TYPES:
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
                         "  promos/ ............ your own promos for its shows (Settings > Breaks > Promos)[CR]"
                         "  <time block>/ ...... the same again, used only in that block (e.g. CAM Jr.)[CR]"
                         "A folder is matched by the channel's name, call letters or number ('Channel 7'). "
                         "A new logo shows within a couple of minutes; new clips are used from each channel's "
                         "next programme once you close the Channel manager (or Tools > Refresh schedules).")


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


NO_REFRESH = ("refresh", "rebuild", "restart_series", "reset", "skipped", "specials")   # "chapters" refreshes: a show's choice changes breaks


def run_tool(name):
    fn = TOOLS.get(name)
    if fn is None:
        return
    home = xbmcgui.Window(10000)
    home.setProperty(TOOL_BUSY, name)
    try:
        fn()
        if name not in NO_REFRESH:
            refresh_if_changed()             # e.g. Build my lineup, Move shows, Station folders
    finally:
        home.clearProperty(TOOL_BUSY)
    if tv_wants_menu() and not home.getProperty(MENU_OPEN):
        main_menu()        # Build my lineup > Start watching > Menu > CableBox menu


def open_settings():
    """Settings, then (once Settings and whatever was started from it are done) a
    refresh if anything schedules are planned from changed."""
    refresh_if_changed(busy=_settings_and_tools())


def _settings_and_tools():
    """Settings; if a tool was started from its Tools page, wait for it to
    finish before showing the menu again (so two dialogs never collide).
    Preview promo marks itself busy too (it sets TOOL_BUSY like the tools) and
    opens Settings again when its promo is over: then wait for that Settings
    and for whatever is picked there.  Returns the box it started as Settings
    closed (for refresh_if_changed to carry on), or None after a tool."""
    K.ADDON.openSettings()
    home = xbmcgui.Window(10000)
    mon = xbmc.Monitor()
    while True:
        busy = Busy(_("Checking your changes..."), later=True)   # from the moment Settings closes
        for _i in range(8):                  # the tool starts a moment after Settings closes
            if home.getProperty(TOOL_BUSY) or mon.waitForAbort(0.25):
                break
        name = home.getProperty(TOOL_BUSY)
        if not name:
            busy.go()                        # no tool: the box after DELAY of the check
            return busy
        busy.close()                         # the tool shows its own progress
        while home.getProperty(TOOL_BUSY) and not mon.waitForAbort(0.3):
            pass
        if name != "preview_promo" or mon.abortRequested():
            return None


def welcome():
    """First start on a new install.  Returns True if the viewer went on to watch TV."""
    rows = [_menu_row(_("[B]Build my lineup[/B]"),
                      _("Builds channels, guide, weather, sign-off and prime time from your Kodi "
                        "library. About a minute.")),
            _menu_row(_("I'll set it up myself"),
                      _("Starts with just the TV Guide and Weather Channel. You add channels in the "
                        "Channel manager.")),
            _menu_row(_("Not now"), _("Go to the menu. You'll be asked again next time."))]
    i = D.select(_("Welcome to CableBox 42"), rows, useDetails=True)
    if i == 0:
        return bool(wizard(express=True))
    if i == 1:
        # plain channels: the viewer brands them (a built-in station is one row away in the editor)
        chans = [C.new_channel(2, _("TV Guide"), "guide"), C.new_channel(C.WEATHER_NUMBER, _("Weather Channel"), "weather")]
        for c in chans:
            c["callsign"] = C.callsign(c["name"])
        C.save(chans)
        D.ok(TITLE, _("You have a TV Guide on 2 and a Weather Channel on 25.[CR][CR]"
                      "Next: Channel manager > Add a channel.  The main menu's Finish setting up has the "
                      "commercials, bumps and music folders, and the Channel manager's Build my lineup can "
                      "still build channels for you any time."))
        manager()
    return False


# ------------------------------------------------------------------ finish setting up
# What a first setup leaves for later.  Each stays on the main menu's Finish
# setting up until it is chosen or the viewer says they don't need it
# (state.json "setup_skipped").
SETUP_ITEMS = ("commercials", "bumps", "music", "musicvideos", "city")


def setup_todo(chans):
    """[(key, label, detail)] of what's still not set (and not dismissed)."""
    skipped = set(K.load_state().get("setup_skipped") or [])
    todo = []

    def add(key, unset, label, detail):
        if unset and key not in skipped:
            todo.append((key, label, detail))
    add("commercials", not K.setting("commercials_path"), _("Commercials: not set"),
        _("A folder of old commercials fills the breaks like real cable TV."))
    add("bumps", not (K.setting("bumps_path") or K.setting("stations_folder")), _("Bumps and station IDs: not set"),
        _("Short clips right before the show comes back: one shared folder, or a folder per channel."))
    add("music", not K.setting("guide_music_path"), _("Guide and weather music: not set"),
        _("Background music for the TV Guide and the Weather Channel."))
    add("musicvideos", chans and not any(c["type"] == "musicvideos" for c in chans), _("Music videos: no channel"),
        _("A folder of music videos makes a music video channel."))
    add("city", any(c["type"] == "weather" for c in chans) and not K.setting("weather_location")
        and not xbmc.getCondVisibility("Weather.IsFetched"), _("Weather city: not set"),
        _("Your city for the Weather Channel's forecast."))
    return todo


def _setup_skip(key):
    def add(st):
        st["setup_skipped"] = sorted(set(st.get("setup_skipped") or []) | set([key]))
    K.update_state(fn=add)


def _setup_choose(key, chans):
    """Set one item now.  Nothing is written when the viewer backs out."""
    pending = {}
    try:
        if key == "commercials":
            p = D.browse(0, _("Commercials folder"), "video")
            if p:
                pending["commercials_path"] = p
        elif key == "bumps":
            if ask_bumpers(pending):
                K.set_setting("stations_folder", pending.pop("stations_folder"))
                make_station_folders(ask=False, report=False)
        elif key == "music":
            ask_music(pending)
        elif key == "city":
            city = D.input(_("Your city for the Weather Channel (optional, e.g. Springfield, IL)"), "")
            if city:
                pending["weather_location"] = city
        elif key == "musicvideos":
            from . import musicvideos
            p = D.browse(0, _("Music videos folder"), "video")
            if p:
                mv = C.music_channel(C.next_free_number(chans), [p])
                if mv is None:
                    D.notification(TITLE, _("Boombox needs at least %d music videos - that folder has fewer")
                                   % musicvideos.MIN_VIDEOS, time=4000)
                else:
                    mv.setdefault("callsign", C.callsign(mv["name"]))
                    chans.append(mv)
                    C.save(chans)
                    D.notification(TITLE, _("Channel %d %s added") % (mv["number"], mv["name"]), time=2500)
    except _Cancelled:
        return
    for k, v in pending.items():
        K.set_setting(k, v)


def finish_setup():
    """Main menu > Finish setting up: the folders and the city a first setup
    didn't ask for.  A menu: each row leaves once it's set or dismissed."""
    while True:
        chans = C.load()
        todo = setup_todo(chans)
        if not todo:
            D.notification(TITLE, _("Everything is set up"), time=2500)
            return
        i = done_select(_("Finish setting up"), [_menu_row(t[1], t[2]) for t in todo], useDetails=True)
        if i < 0:
            return
        key, label = todo[i][0], todo[i][1]
        j = D.select(label, [_("Choose now"), _("I don't need this (stop showing it)"), _("Cancel")])
        if j == 0:
            _setup_choose(key, chans)
        elif j == 1:
            _setup_skip(key)


def captions_on():
    """The TV's CC setting, the same one the in-TV menu switches."""
    return K.load_state().get("cc_on") is True


MENU_OPEN = "cablebox42.main_menu"     # home-window property while the main menu is open


def tv_wants_menu():
    """The last TV session ended with Menu > CableBox menu."""
    from . import tv
    return tv.last_exit == "menu"


def watch_from_menu(channel=None):
    """Watch TV / What's on now from the main menu.  True: come back to the main
    menu (Back, Stop, Turn off TV or CableBox menu); False: go to Kodi (sleep
    timer, the viewer left the TV, Kodi closing)."""
    from . import tv
    return tv.run(channel) in ("back", "menu")


def main_menu():
    home = xbmcgui.Window(10000)
    if home.getProperty(MENU_OPEN):
        # the menu that opened Settings (or a tool) is waiting for it and comes back
        # on its own: a second one would stack on top of it
        D.notification(TITLE, _("The menu comes back in a moment"), time=3000)
        return
    home.setProperty(MENU_OPEN, "1")
    try:
        _main_menu()
    finally:
        home.clearProperty(MENU_OPEN)


def note_unplaced():
    """After a refresh: shows in the library no channel airs (and none hides).
    Those that weren't there last time are kept for the menu to mention once
    (menu_notes).  The very first time, they're only taken note of."""
    try:
        a = assign.load() or {}
        placed = set(a.get("home") or {})
        for group in ("explicit", "shared"):
            for titles in (a.get(group) or {}).values():
                placed |= set(titles)
        hidden = set(x.lower() for c in C.load() for x in c.get("exclude", []))
        unplaced = sorted(s["title"] for s in library.all_tvshows()
                          if s["title"].lower() not in placed and s["title"].lower() not in hidden)
        def note(st):
            known = st.get("unplaced_known")
            fresh = [] if known is None else [t for t in unplaced if t not in known]
            st["unplaced_known"] = unplaced
            st["unplaced_new"] = [t for t in sorted(set(st.get("unplaced_new", [])) | set(fresh)) if t in unplaced]
        K.update_state(fn=note)
    except Exception as exc:
        K.log_err("new shows: %s" % exc)


def menu_notes():
    """Things the TV and the background service noticed, said once in the menu
    (never over the TV)."""
    home = xbmcgui.Window(10000)
    st = K.load_state()
    new = st.get("unplaced_new") or []
    if new:
        K.update_state({"unplaced_new": []})     # once per batch of new shows
        text = (_("A new show isn't on a channel yet: %s") % new[0]) if len(new) == 1 else \
            (_("%d new shows aren't on a channel yet.") % len(new))
        if D.yesno(TITLE, text, nolabel=_("Not now"), yeslabel=_("OK")):
            run_finder()
            refresh_if_changed()
        st = K.load_state()
    at = st.get("missing_at", 0)
    if at > st.get("missing_told", 0) and not home.getProperty("cablebox42.missing_told"):
        home.setProperty("cablebox42.missing_told", "1")         # at most once per Kodi session
        K.update_state({"missing_told": at})
        D.notification(TITLE, _("Some planned episodes are missing; schedules updated"), time=5000)


def _main_menu():
    if not os.path.exists(K.CHANNELS_FILE) and welcome() and not tv_wants_menu():
        return
    menu_notes()
    mon = xbmc.Monitor()
    while not mon.abortRequested():
        chans = C.load()
        if chans:
            start = K.setting_int("start_channel", 0)
            opts = [("watch", _("[B]Watch TV[/B]"),
                     (_("Start on channel %d") % start) if start else _("Pick up where you left off")),
                    ("now", _("What's on now"), _("See every channel's current show and tune straight to it")),
                    ("finish", _("Finish setting up"), ""),
                    ("cc", _("Closed captions: %s") % (_("On") if captions_on() else _("Off")),
                     _("On or off for every programme. While watching: the Menu button")),
                    ("manager", _("Channel manager"), _("Add, edit and renumber channels - plus the lineup tools")),
                    ("planner", _("Weekly planner"), _("Pin shows to days and times")),
                    ("holidays", _("Holidays & events"),
                     _("The calendar, specials on exact dates, and the automatic holiday seasons")),
                    ("settings", _("Settings and tools"),
                     _("Breaks, holidays, picture, weather - plus maintenance tools")),
                    ("help", _("Help"), _("How everything works"))]
        else:
            opts = [("wizard", _("[B]Build my lineup[/B]"), _("Builds a lineup from your Kodi library in a minute")),
                    ("settings", _("Settings and tools"), _("Breaks, holidays, picture, weather")),
                    ("help", _("Help"), _("How everything works"))]
        todo = setup_todo(chans) if chans else []
        if todo:                                # what a first setup left for later
            opts = [(k, label, _("%d left: %s") % (len(todo), ", ".join(t[1].split(":")[0] for t in todo)))
                    if k == "finish" else (k, label, d) for k, label, d in opts]
        else:
            opts = [o for o in opts if o[0] != "finish"]
        i = done_select(TITLE, [_menu_row(o[1], o[2]) for o in opts], useDetails=True, done_label=_("[B]Close[/B]"))
        if i < 0:
            return
        k = opts[i][0]
        if k == "watch":
            if not watch_from_menu():
                return
        elif k == "now":
            n = whats_on_now()
            if n is not None and not watch_from_menu(n):
                return
        elif k == "wizard":
            if wizard(express=True) and not tv_wants_menu():
                return  # watched TV straight after the wizard - Back goes to Kodi
        elif k == "finish":
            finish_setup()
            refresh_if_changed()             # new clip folders, a new channel
        elif k == "cc":
            on = not captions_on()
            K.update_state({"cc_on": on})
            D.notification(TITLE, _("Closed captions on") if on else _("Closed captions off"), time=2000)
        elif k == "manager":
            if manager():                    # only after a saved change: channels, branding, station clips
                refresh_if_changed()
        elif k == "planner":
            if pick_planner_channel():       # left with no change: nothing to check
                refresh_if_changed()
        elif k == "holidays":
            holidays_menu()
        elif k == "settings":
            open_settings()
        elif k == "help":
            D.textviewer(TITLE, help_text())
