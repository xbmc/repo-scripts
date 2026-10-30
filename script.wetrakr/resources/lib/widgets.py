"""
widgets.py: WeTrakr folders for skin widgets (plugin://script.wetrakr/).

  plugin://script.wetrakr/                              menu
  plugin://script.wetrakr/?action=next_episodes         Next Episodes

Next Episodes is the same list as on wetrakr.com, so it includes what you
watched in other apps. An episode you have in the Kodi library plays the
library file (resume point, watched state and scrobble as usual); one you
don't have opens through TMDb Helper, which hands it to your video add-on.

The list is cached in a Home window property for CACHE_TTL seconds: skins
reload widgets every time Home comes back. The service drops the cache after
a scrobble or a sync that changed something, and bumps the Home property
WeTrakr.Widgets.Reload so skins can refresh with
  plugin://script.wetrakr/?action=next_episodes&reload=$INFO[Window(Home).Property(WeTrakr.Widgets.Reload)]
"""

import json
import sys
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from resources.lib import library
from resources.lib.sync_api import SyncApi, ApiError, InvalidToken

try:
    from urllib.parse import parse_qsl, urlencode
except ImportError:  # Kodi 18
    from urlparse import parse_qsl
    from urllib import urlencode

CACHE_TTL = 300
CACHE_PROP = "script.wetrakr.next_episodes"
RELOAD_PROP = "WeTrakr.Widgets.Reload"
TMDB_HELPER = "plugin.video.themoviedb.helper"
LIMIT = 50

EPISODE_PROPS = [
    "title", "season", "episode", "uniqueid", "firstaired", "file", "resume",
    "playcount", "art", "plot", "runtime", "rating", "showtitle", "tvshowid"
]


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log("[WeTrakr] Widgets: {}".format(msg), level)


def _home():
    return xbmcgui.Window(10000)


def invalidate():
    """Called by the service when the list may have changed."""
    try:
        home = _home()
        home.clearProperty(CACHE_PROP)
        home.setProperty(RELOAD_PROP, str(int(time.time())))
    except Exception as e:
        _log("invalidate error: {}".format(e), xbmc.LOGWARNING)


def _fetch(addon):
    """Next Episodes from WeTrakr, cached. None if not logged in or offline."""
    home = _home()
    raw = home.getProperty(CACHE_PROP)
    if raw:
        try:
            cached = json.loads(raw)
            if time.time() - cached.get("at", 0) < CACHE_TTL:
                return cached.get("items") or []
        except ValueError:
            pass
    token = addon.getSetting("api_token")
    if not token or addon.getSetting("auth_invalid") == "true":
        return None
    api = SyncApi(addon.getSetting("api_url") or "https://api.wetrakr.com", token, timeout=15)
    try:
        items = api.next_episodes(LIMIT).get("items") or []
    except InvalidToken:
        return None
    except ApiError as e:
        _log("next-episodes failed: {}".format(e), xbmc.LOGWARNING)
        # Better the last list than an empty widget while offline.
        if raw:
            try:
                return json.loads(raw).get("items") or []
            except ValueError:
                pass
        return None
    home.setProperty(CACHE_PROP, json.dumps({"at": time.time(), "items": items}))
    return items


# ─── Kodi library lookup ──────────────────────────────────────────

def _uid(item, key):
    v = (item.get("uniqueid") or {}).get(key)
    return str(v).strip() if v not in (None, "") else None


def _shows_by_id():
    """{('tmdb'|'tvdb'|'imdb', id): tvshowid} for the whole library."""
    out = {}
    res = library.rpc("VideoLibrary.GetTVShows", {"properties": ["uniqueid", "imdbnumber"]})
    for show in res.get("tvshows") or []:
        sid = show.get("tvshowid")
        for key in ("tmdb", "tvdb", "imdb"):
            v = _uid(show, key)
            if v:
                out[(key, v)] = sid
        imdb = str(show.get("imdbnumber") or "")
        if imdb.startswith("tt"):
            out.setdefault(("imdb", imdb), sid)
    return out


def _find_show(shows, ids):
    for key in ("tmdb", "tvdb", "imdb"):
        v = ids.get(key)
        if v not in (None, "") and (key, str(v)) in shows:
            return shows[(key, str(v))]
    return None


def _find_episode(episodes, ep):
    """By episode id first, then by air date, then by season/number: a show
    scraped from TheTVDB can number seasons differently from TMDB, which is
    what WeTrakr uses."""
    ids = ep.get("ids") or {}
    for key in ("tmdb", "tvdb"):
        v = ids.get(key)
        if v not in (None, ""):
            for e in episodes:
                if _uid(e, key) == str(v):
                    return e
    aired = ep.get("aired")
    if aired:
        same_day = [e for e in episodes if str(e.get("firstaired") or "")[:10] == aired and e.get("season", 0) > 0]
        if len(same_day) == 1:
            return same_day[0]
    for e in episodes:
        if e.get("season") == ep.get("season") and e.get("episode") == ep.get("number"):
            return e
    return None


def _library_matches(items):
    """{index in items: Kodi episode dict} for the episodes in the library."""
    shows = _shows_by_id()
    if not shows:
        return {}
    wanted = {}
    for i, it in enumerate(items):
        sid = _find_show(shows, (it.get("show") or {}).get("ids") or {})
        if sid is not None:
            wanted.setdefault(sid, []).append(i)
    if not wanted:
        return {}
    sids = list(wanted)
    calls = [("VideoLibrary.GetEpisodes", {"tvshowid": sid, "properties": EPISODE_PROPS}) for sid in sids]
    out = {}
    for sid, resp in zip(sids, library.rpc_batch(calls)):
        episodes = ((resp or {}).get("result") or {}).get("episodes") or []
        for i in wanted[sid]:
            e = _find_episode(episodes, items[i].get("episode") or {})
            if e:
                out[i] = e
    return out


# ─── ListItems ────────────────────────────────────────────────────

def _set_info(li, info, dbid=None, resume=None):
    """InfoTagVideo on Kodi 20+, setInfo on Kodi 19."""
    try:
        tag = li.getVideoInfoTag()
        tag.setMediaType("episode")
        tag.setTitle(info["title"])
        tag.setTvShowTitle(info["tvshowtitle"])
        tag.setSeason(info["season"])
        tag.setEpisode(info["episode"])
        tag.setPlot(info["plot"])
        if info.get("aired"):
            tag.setFirstAired(info["aired"])
        if info.get("duration"):
            tag.setDuration(info["duration"])
        if info.get("genre"):
            tag.setGenres(info["genre"])
        if info.get("uniqueids"):
            tag.setUniqueIDs(info["uniqueids"], "tmdb" if "tmdb" in info["uniqueids"] else list(info["uniqueids"])[0])
        if dbid:
            tag.setDbId(dbid)
        if resume and resume[0] > 0 and resume[1] > 0:
            tag.setResumePoint(resume[0], resume[1])
        return
    except AttributeError:
        pass
    legacy = {
        "mediatype": "episode", "title": info["title"], "tvshowtitle": info["tvshowtitle"],
        "season": info["season"], "episode": info["episode"], "plot": info["plot"],
        "aired": info.get("aired") or "", "duration": info.get("duration") or 0,
        "genre": info.get("genre") or [],
    }
    if dbid:
        legacy["dbid"] = dbid
    li.setInfo("video", legacy)
    if resume and resume[0] > 0 and resume[1] > 0:
        li.setProperty("ResumeTime", str(resume[0]))
        li.setProperty("TotalTime", str(resume[1]))


def _tmdb_helper_url(show, ep):
    return "plugin://{}/?{}".format(TMDB_HELPER, urlencode({
        "info": "play", "tmdb_type": "tv", "tmdb_id": show["ids"]["tmdb"],
        "season": ep.get("season"), "episode": ep.get("number"),
    }))


def _listitem(it, local, use_helper):
    """(url, ListItem) or None when the episode can't be played here."""
    show = it.get("show") or {}
    ep = it.get("episode") or {}
    if local:
        url = local.get("file")
    elif use_helper and (show.get("ids") or {}).get("tmdb"):
        url = _tmdb_helper_url(show, ep)
    else:
        return None
    if not url:
        return None

    season, number = ep.get("season") or 0, ep.get("number") or 0
    title = ep.get("title") or "Episode {}".format(number)
    label = "{}x{:02d}. {}".format(season, number, title)
    li = xbmcgui.ListItem(label=label, label2=show.get("title") or "", offscreen=True)

    art = {"poster": show.get("poster"), "tvshow.poster": show.get("poster"),
           "fanart": show.get("fanart"), "tvshow.fanart": show.get("fanart"),
           "thumb": ep.get("thumb") or show.get("fanart"), "icon": ep.get("thumb") or show.get("poster")}
    if local:
        # The library art (local files, scraper artwork) wins over TMDB's.
        for k, v in (local.get("art") or {}).items():
            if v:
                art[k] = v
    li.setArt({k: v for k, v in art.items() if v})

    uniqueids = {k: str(v) for k, v in (ep.get("ids") or {}).items() if v not in (None, "")}
    runtime = (local or {}).get("runtime") or (ep.get("runtime") or 0) * 60
    resume = None
    if local:
        r = local.get("resume") or {}
        resume = (float(r.get("position") or 0), float(r.get("total") or 0))
    _set_info(li, {
        "title": title, "tvshowtitle": show.get("title") or "", "season": season,
        "episode": number, "plot": ep.get("overview") or (local or {}).get("plot") or "",
        "aired": ep.get("aired"), "duration": int(runtime or 0), "genre": show.get("genres") or [],
        "uniqueids": uniqueids,
    }, dbid=(local or {}).get("episodeid"), resume=resume)

    li.setProperty("IsPlayable", "true")
    li.setProperty("WeTrakr.InLibrary", "true" if local else "false")
    li.setProperty("WeTrakr.Status", it.get("status") or "")
    li.setProperty("tvshow.tmdb_id", str((show.get("ids") or {}).get("tmdb") or ""))
    return url, li


# ─── Routes ───────────────────────────────────────────────────────

def _menu(handle):
    li = xbmcgui.ListItem(label="Next Episodes", offscreen=True)
    li.setArt({"icon": "DefaultTVShows.png"})
    xbmcplugin.addDirectoryItem(handle, "plugin://script.wetrakr/?action=next_episodes", li, isFolder=True)
    xbmcplugin.endOfDirectory(handle)


def _next_episodes(handle, addon):
    xbmcplugin.setContent(handle, "episodes")
    items = _fetch(addon)
    if items is None:
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return
    library_only = addon.getSetting("widget_library_only") == "true"
    use_helper = (not library_only and addon.getSetting("widget_tmdb_helper") != "false"
                  and xbmc.getCondVisibility("System.HasAddon({})".format(TMDB_HELPER)))
    matches = _library_matches(items)
    rows = []
    for i, it in enumerate(items):
        entry = _listitem(it, matches.get(i), use_helper)
        if entry:
            rows.append((entry[0], entry[1], False))
    xbmcplugin.addDirectoryItems(handle, rows, len(rows))
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
    _log("next episodes: {} of {} ({} in the library)".format(len(rows), len(items), len(matches)), xbmc.LOGDEBUG)


def run(argv):
    handle = int(argv[1])
    params = dict(parse_qsl(argv[2][1:] if len(argv) > 2 else ""))
    addon = xbmcaddon.Addon("script.wetrakr")
    action = params.get("action")
    if action == "next_episodes":
        _next_episodes(handle, addon)
    else:
        _menu(handle)
