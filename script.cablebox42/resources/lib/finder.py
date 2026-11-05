"""Shows without a good channel (Channel manager, or Settings > Tools).

Lists the library's shows (and movies, when movies get one channel each) that
no channel picks up, or whose home channel is only a weak fit - with the reason
in plain words - and lets the viewer put them on a channel, keep them where
they are, or keep them off the air.  Nothing here changes how assignment works:
it reads assign.compute(explain=True) and acts through the same explicit picks
and hidden lists as 'Move shows between channels'.
"""
import os

import xbmcgui

from . import kodiutil as K
from . import channels as C
from . import library
from . import assign
from .kodiutil import _

D = xbmcgui.Dialog()
TITLE = "CableBox 42"
PROGRAM_TYPES = ("network", "movies", "loop")
REVIEWED_FILE = os.path.join(K.PROFILE, "finder.json")
OK_SCORE = 50               # the show's main genre, or anything more specific
VIEWS = ("look", "unplaced", "weak", "reviewed")


def _view_label(v):
    return {"look": _("Needs a look"), "unplaced": _("Not on any channel"),
            "weak": _("Weak matches"), "reviewed": _("Marked as fine")}[v]


# ------------------------------------------------------------------ reasons
def _ordinal(pos):
    return {0: _("main genre"), 1: _("2nd genre"), 2: _("3rd genre")}.get(pos, _("minor genre"))


def _vals(v):
    v = v if isinstance(v, list) else [v]
    return [str(x) for x in v if x]


def reason(src, title_l, meta, studios):
    """Why a source picks up this title, in a few words."""
    t = src.get("type")
    genres = meta.get(title_l, [])
    if src.get("orphans"):
        return _("Auto-placed: its genres are too small for a channel of their own")
    if src.get("explicit") or t in ("tvshow", "movie"):
        return _("Your pick") if src.get("explicit") or len(_vals(src.get("value"))) <= assign.BROAD_LIST \
            else _("On a long show list")
    if t == "folder":
        return _("Folder %s") % os.path.basename(src.get("path", "").rstrip("/\\"))
    if t == "network":
        hit = [s for s in studios.get(title_l, []) if s.lower() in set(v.lower() for v in _vals(src.get("value")))]
        return _("%s network match") % (hit[0] if hit else ", ".join(_vals(src.get("value"))[:2]))
    if t == "studio":
        return _("Studio contains '%s'") % ", ".join(_vals(src.get("value")))
    if t == "tag":
        return _("Kodi tag %s") % ", ".join("'%s'" % v for v in _vals(src.get("value"))[:2])
    if t == "playlist":
        return _("Playlist %s") % os.path.basename(str(src.get("value") or src.get("path") or ""))
    if t == "keyword":
        return _("Title contains '%s'") % ", ".join(_vals(src.get("value")))
    if t in ("tvgenre", "movies") and (src.get("value") if t == "tvgenre" else src.get("genre")):
        g = src.get("value") if t == "tvgenre" else src.get("genre")
        if g.lower() in genres:
            return _("%s (%s)") % (g, _ordinal(genres.index(g.lower())))
        return _("%s genre") % g
    if t == "movies":
        if src.get("set"):
            return _("Movie set '%s'") % src["set"]
        if src.get("tag"):
            return _("Kodi tag '%s'") % src["tag"]
        if src.get("years"):
            return _("Movies from %s to %s") % tuple(src["years"])
        return _("All movies (catch-all)")
    if t == "tvdecade":
        return _("Shows from the %ss") % src.get("value")
    if t == "alltv":
        return _("Every show (catch-all)")
    return _("Other source")


def strength(sc):
    if sc >= 70:
        return _("strong")
    if sc >= OK_SCORE:
        return _("good")
    if sc >= 30:
        return _("weak")
    return _("very weak")


# ------------------------------------------------------------------ the analysis
def _load_reviewed():
    return set(K.load_json(REVIEWED_FILE, {}).get("ok", []))


def _save_reviewed(ok):
    K.save_json(REVIEWED_FILE, {"ok": sorted(ok)})


def analyse():
    """[{title, movie, home, score, reason, kind}] for everything worth a look,
    plus the assignment and channels it was worked out from."""
    chans = C.load()
    a = assign.compute(chans, explain=True)
    by_id = dict((c["id"], c) for c in chans)
    progs = [c for c in chans if c["type"] in PROGRAM_TYPES and not c.get("broadcast")]
    meta = assign._metadata()
    studios = {}
    try:
        for s in library.all_tvshows_with("studio"):
            studios[s["title"].lower()] = s.get("studio", [])
    except Exception:
        pass
    # shows a broadcast network's time blocks can still air (no home of their own)
    blocks = {}
    for c in chans:
        if c.get("broadcast"):
            srcs = list(c.get("sources", [])) + [s for dp in c.get("dayparts", []) for s in dp.get("sources", [])]
            for t in library.titles(library.resolve(srcs)):
                blocks.setdefault(t.lower(), c["name"])
    hidden = {}
    for c in chans:
        for x in c.get("exclude", []):
            hidden.setdefault(x.lower(), []).append(c["name"])
    items = [(s["title"], False) for s in library.all_tvshows()]
    if a["mode"] == assign.MODE_ALL:
        items += [("%s (%s)" % (m["title"], m["year"]) if m.get("year") else m["title"], True)
                  for m in library.all_movies(["title", "year"])]
    reviewed = _load_reviewed()
    out, seen = [], set()
    for title, is_movie in items:
        tl = title.lower()
        if tl in seen:
            continue
        seen.add(tl)
        home = a["home"].get(tl)
        why = a["why"].get(tl, {})
        if home is None or home not in by_id:
            if tl in blocks:
                r = _("No channel of its own - only in %s's time blocks") % blocks[tl]
            elif tl in hidden:
                r = _("Hidden on %s") % ", ".join(hidden[tl][:3])
            else:
                r = _("No channel's programming includes it")
            out.append({"title": title, "movie": is_movie, "home": None, "score": 0, "reason": r,
                        "kind": "unplaced"})
            continue
        sc, src = why.get(home, (0, {}))
        if src.get("explicit"):
            continue                                    # the viewer's own choice
        first = a["first"].get(tl, home)
        name = by_id[home]["name"]
        if first != home and first in by_id:
            fsc, fsrc = why.get(first, (0, {}))
            r = _("Moved here so %s has enough shows (best fit: %s, %s)") % (
                name, by_id[first]["name"], reason(fsrc, tl, meta, studios))
        else:
            r = "%s  ->  %s" % (reason(src, tl, meta, studios), name)
        weak = sc < OK_SCORE or first != home or src.get("orphans")
        if not weak:
            continue
        if src.get("orphans"):
            sc = min(sc, 30)                            # an automatic guess, whatever it scored
        out.append({"title": title, "movie": is_movie, "home": home, "score": sc, "reason": r,
                    "kind": "reviewed" if tl in reviewed else "weak"})
    out.sort(key=lambda e: (e["home"] is not None, e["score"], library.natural_key(e["title"])))
    return out, a, chans, progs, meta, studios


# ------------------------------------------------------------------ the screens
def _busy(text):
    pd = xbmcgui.DialogProgress()
    pd.create(TITLE, text)
    return pd


def _channel_choice(e, a, progs, meta, studios):
    """Program channels for this title, the best fits first."""
    tl = e["title"].lower()
    why = a["why"].get(tl, {})
    ranked = sorted(progs, key=lambda c: (-why.get(c["id"], (-1, {}))[0], c["number"]))
    labels = []
    for c in ranked:
        if c["id"] in why:
            sc, src = why[c["id"]]
            note = "%s, %s" % (reason(src, tl, meta, studios), strength(sc))
        else:
            note = _("manual pick - none of its sources match")
        if c["id"] == e["home"]:
            note = _("now - ") + note
        labels.append(xbmcgui.ListItem("%3d  %s" % (c["number"], c["name"]), note))
    return ranked, labels


def _act(e, a, chans, progs, meta, studios):
    """What to do with one title.  Returns True if anything changed."""
    from . import manager
    by_id = dict((c["id"], c) for c in chans)
    home = by_id.get(e["home"]) if e["home"] else None
    tl = e["title"].lower()
    opts = [("move", _("Put it on a channel..."))]
    if home:
        if e["kind"] == "reviewed":
            opts.append(("unok", _("Show it here again")))
        else:
            opts.append(("ok", _("It's fine on %s") % home["name"]))
        opts.append(("hide", _("Don't air it on %s") % home["name"]))
    opts.append(("never", _("Don't air it on any channel automatically")))
    j = D.select(e["title"], [o[1] for o in opts])
    if j < 0:
        return False
    key = opts[j][0]
    if key == "move":
        ranked, labels = _channel_choice(e, a, progs, meta, studios)
        k = D.select(_("Put %s on...") % e["title"], labels, useDetails=True)
        if k < 0:
            return False
        c = ranked[k]
        c["exclude"] = [x for x in c.get("exclude", []) if x.lower() != tl]
        manager._add_title(c, e["title"], e["movie"])
        C.save(chans)
        D.notification(TITLE, _("%s now airs on %s") % (e["title"], c["name"]), time=2500)
        return True
    if key in ("ok", "unok"):
        ok = _load_reviewed()
        if key == "ok":
            ok.add(tl)
        else:
            ok.discard(tl)
        _save_reviewed(ok)
        return True
    if key == "hide":
        home["exclude"] = sorted(set(home.get("exclude", [])) | {e["title"]})
        C.save(chans)
        D.notification(TITLE, _("%s hidden on %s") % (e["title"], home["name"]), time=2500)
        return True
    if key == "never":
        targets = [c for c in chans if c["id"] in a["why"].get(tl, {}) or c.get("broadcast")]
        if not D.yesno(TITLE, _("Keep %s off every channel's automatic programming?[CR][CR]It's hidden on %d "
                                "channels. Pinned slots in the weekly planner still air it. 'What's on this "
                                "channel' brings it back.") % (e["title"], len(targets))):
            return False
        for c in targets:
            if tl not in set(x.lower() for x in c.get("exclude", [])):
                c["exclude"] = c.get("exclude", []) + [e["title"]]
        C.save(chans)
        return True
    return False


def run():
    if not [c for c in C.load() if c["type"] in PROGRAM_TYPES]:
        D.ok(TITLE, _("No program channels yet."))
        return
    pd = _busy(_("Checking where every show airs..."))
    try:
        data = analyse()
    finally:
        pd.close()
    view = "look"
    changed = False
    while True:
        items, a, chans, progs, meta, studios = data
        counts = dict((v, 0) for v in VIEWS)
        for e in items:
            counts[e["kind"]] += 1
        counts["look"] = counts["unplaced"] + counts["weak"]
        shown = [e for e in items if (e["kind"] in ("unplaced", "weak") if view == "look" else e["kind"] == view)]
        movie_note = "" if a["mode"] == assign.MODE_ALL else \
            _("TV shows only (movies may repeat).")
        rows = [xbmcgui.ListItem(_("[B]Showing: %s (%d)[/B]") % (_view_label(view), len(shown)),
                                 _("Select to change. Not on any channel %d, weak %d, marked as fine %d. %s") % (
                                     counts["unplaced"], counts["weak"], counts["reviewed"], movie_note))]
        for e in shown:
            where = _("[COLOR orange]not on any channel[/COLOR]") if not e["home"] else \
                next((c["name"] for c in chans if c["id"] == e["home"]), "")
            tag = "" if not e["home"] else "  [COLOR grey](%s)[/COLOR]" % strength(e["score"])
            rows.append(xbmcgui.ListItem("%s  ->  %s%s" % (e["title"], where, tag), e["reason"]))
        if len(rows) == 1 and view == "look" and not counts["reviewed"]:
            D.ok(TITLE, _("Every show has a good home channel."))
            break
        i = D.select(_("Shows without a good channel"), rows, useDetails=True)
        if i < 0:
            break
        if i == 0:
            labels = ["%s (%d)" % (_view_label(v), counts[v]) for v in VIEWS]
            j = D.select(_("Show"), labels, preselect=VIEWS.index(view))
            if j >= 0:
                view = VIEWS[j]
            continue
        if _act(shown[i - 1], a, chans, progs, meta, studios):
            changed = True
            pd = _busy(_("Checking where every show airs..."))
            try:
                data = analyse()
            finally:
                pd.close()
    if changed:
        from . import manager
        manager.refresh_assignments()
