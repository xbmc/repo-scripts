"""
context_menu_runner.py — handler for the WeTrakr context-menu entry.

Shows the actions for the focused movie or episode (rate / remove rating /
mark watched / mark unwatched) and sends them to the WeTrakr webhook. Marking
watched and rating can carry a date and time picked by the user instead of
"now" (Settings > Context menu > Ask for the date).

The context menu only talks to WeTrakr: it never writes the Kodi library. With
library sync on, the change comes back on the next sync like any other.
"""

import time

import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.api import WeTrakrAPI
from resources.lib import auth
from resources.lib import utils
from resources.lib import rating as rating_mod
from resources.lib.notification import notify as _notify

MOVIE_PROPS = ["title", "year", "uniqueid", "imdbnumber", "premiered", "originaltitle", "runtime"]
EPISODE_PROPS = ["title", "showtitle", "season", "episode", "uniqueid", "firstaired", "tvshowid", "runtime"]


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log("[WeTrakr] Context: {}".format(msg), level)


def _addon():
    return xbmcaddon.Addon("script.wetrakr")


def _get_api():
    """Create WeTrakrAPI from saved settings."""
    addon = _addon()
    token = addon.getSetting("api_token")
    api_url = addon.getSetting("api_url") or "https://api.wetrakr.com"
    if not token:
        return None
    return WeTrakrAPI(api_url, token)


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


# -------------------------------------------------------
# Focused item -> webhook payload
# -------------------------------------------------------

def _library_payload(dbtype, dbid):
    """Payload for a Kodi library item, with the same ids, numbering hints
    and show ids as a scrobble (utils.build_payload)."""
    if dbtype == "movie":
        item = utils.get_json_rpc("VideoLibrary.GetMovieDetails",
                                  {"movieid": dbid, "properties": MOVIE_PROPS}).get("moviedetails")
        show = None
    else:
        item = utils.get_json_rpc("VideoLibrary.GetEpisodeDetails",
                                  {"episodeid": dbid, "properties": EPISODE_PROPS}).get("episodedetails")
        show = utils.get_tvshow_details(item.get("tvshowid", -1)) if item else None
    if not item:
        return None
    ids = utils.extract_ids(item)
    if not (ids.get("tmdb") or ids.get("imdb") or ids.get("tvdb")):
        # build_payload would fall back to the ids of whatever is playing
        # right now, which is not the focused item: use the list item instead.
        return None
    item["type"] = dbtype
    payload = utils.build_payload("watched", item, show)
    payload.pop("progress", None)
    return payload


def _listitem_payload(dbtype):
    """Payload from the focused list item's infolabels (items listed by
    video add-ons, which are not in the Kodi library)."""
    ids = {
        "tmdb": _int(xbmc.getInfoLabel("ListItem.UniqueID(tmdb)")) or None,
        "tvdb": _int(xbmc.getInfoLabel("ListItem.UniqueID(tvdb)")) or None,
        "imdb": xbmc.getInfoLabel("ListItem.UniqueID(imdb)") or None,
    }
    fallback = xbmc.getInfoLabel("ListItem.IMDBNumber")
    if not ids["imdb"] and fallback.startswith("tt"):
        ids["imdb"] = fallback
    elif not ids["tmdb"] and fallback:
        ids["tmdb"] = _int(fallback) or None
    if ids["imdb"] and not ids["imdb"].startswith("tt"):
        ids["imdb"] = None

    title = xbmc.getInfoLabel("ListItem.Title")
    if dbtype == "episode":
        payload = {
            "media_type": "episode",
            "title": title,
            "show_title": xbmc.getInfoLabel("ListItem.TVShowTitle"),
            "show_ids": {},
            "season": _int(xbmc.getInfoLabel("ListItem.Season")),
            "episode": _int(xbmc.getInfoLabel("ListItem.Episode")),
            "ids": ids,
            "ids_source": "listitem",
        }
        aired = utils._aired_date(xbmc.getInfoLabel("ListItem.Premiered"))
        if aired:
            payload["aired"] = aired
        return payload
    payload = {
        "media_type": "movie",
        "title": title,
        "year": _int(xbmc.getInfoLabel("ListItem.Year")),
        "ids": ids,
        "ids_source": "listitem",
    }
    premiered = utils._aired_date(xbmc.getInfoLabel("ListItem.Premiered"))
    if premiered:
        payload["premiered"] = premiered
    return payload


def _focused_payload():
    """(payload, label) for the focused item, or (None, None) when it is not
    a movie or an episode."""
    dbtype = xbmc.getInfoLabel("ListItem.DBType")
    if not dbtype:
        # Video add-ons do not always set a media type: an item with a show
        # and an episode number is an episode, anything else a movie (what
        # the context menu always assumed).
        has_ep = xbmc.getInfoLabel("ListItem.TVShowTitle") and xbmc.getInfoLabel("ListItem.Episode")
        dbtype = "episode" if has_ep else "movie"
    if dbtype not in ("movie", "episode"):
        return None, None
    dbid = _int(xbmc.getInfoLabel("ListItem.DBID"))
    payload = None
    if dbid > 0:
        payload = _library_payload(dbtype, dbid)
    if not payload:
        payload = _listitem_payload(dbtype)
    return payload, dbtype


# -------------------------------------------------------
# Date and time picker
# -------------------------------------------------------

NOW, RELEASE, OTHER = "now", "release", "other"


def _ask_date_mode(heading, allow_release):
    """Now / release date / another date. None when cancelled."""
    if _addon().getSetting("context_ask_date") == "false":
        return NOW
    options = [u"Now"]
    modes = [NOW]
    if allow_release:
        options.append(u"On the release date")
        modes.append(RELEASE)
    options.append(u"Choose date and time...")
    modes.append(OTHER)
    choice = xbmcgui.Dialog().select(heading, options)
    if choice < 0:
        return None
    return modes[choice]


def _pick_datetime(heading):
    """Date and time picked with Kodi's own numeric dialogs, as a Unix
    timestamp in the local time of this device. None when cancelled or in
    the future."""
    dialog = xbmcgui.Dialog()
    now = time.localtime()
    date_str = dialog.numeric(1, heading + u": date", time.strftime("%d/%m/%Y", now))
    if not date_str:
        return None
    time_str = dialog.numeric(2, heading + u": time", time.strftime("%H:%M", now))
    if not time_str:
        return None
    try:
        day, month, year = [int(p.strip()) for p in date_str.split("/")]
        hour, minute = [int(p.strip()) for p in time_str.split(":")]
        ts = time.mktime((year, month, day, hour, minute, 0, 0, 0, -1))
    except (ValueError, OverflowError) as e:
        _log("Bad date '{}' '{}': {}".format(date_str, time_str, e), xbmc.LOGWARNING)
        _notify("WeTrakr", "That date is not valid")
        return None
    if ts > time.time() + 60:
        _notify("WeTrakr", "The date cannot be in the future")
        return None
    # numeric() gives the default back when it is cancelled: confirm, so a
    # cancel never sends a date the user did not choose.
    label = time.strftime("%d %b %Y, %H:%M", time.localtime(ts))
    if not dialog.yesno(u"WeTrakr", u"{} on {}?".format(heading, label)):
        return None
    return int(ts)


# -------------------------------------------------------
# Actions
# -------------------------------------------------------

def _send(api, payload, event, extra=None):
    body = dict(payload)
    body["event"] = event
    body["manual"] = True
    if extra:
        body.update(extra)
    return api.send_event(body, debug=_addon().getSetting("debug") == "true")


def _handle_rate(api, payload, title, label):
    year = payload.get("year") or None
    poster = xbmc.getInfoLabel("ListItem.Art(poster)") or None
    rating_value = rating_mod.show_rating_dialog(title, year, poster_path=poster)
    if rating_value is None:
        return

    extra = {"rating": rating_value}
    mode = _ask_date_mode(u"When did you rate it?", False)
    if mode is None:
        return
    if mode == OTHER:
        ts = _pick_datetime(u"Rated")
        if ts is None:
            return
        extra["rated_at"] = ts

    if _send(api, payload, "rating", extra):
        _notify("WeTrakr", "Rated {}/10".format(rating_value))
        _log("Rated '{}': {}/10 via context menu ({})".format(title, rating_value, label))
    else:
        _notify("WeTrakr", "Could not send the rating")


def _handle_unrate(api, payload, title):
    if _send(api, payload, "unrate"):
        _notify("WeTrakr", "Rating removed")
        _log("Removed rating of '{}' via context menu".format(title))
    else:
        _notify("WeTrakr", "Could not remove the rating")


def _handle_mark_watched(api, payload, title):
    mode = _ask_date_mode(u"When did you watch it?", True)
    if mode is None:
        return
    extra = {}
    if mode == RELEASE:
        extra["use_release_date"] = True
    elif mode == OTHER:
        ts = _pick_datetime(u"Watched")
        if ts is None:
            return
        extra["watched_at"] = ts
    else:
        extra["watched_at"] = int(time.time())

    if _send(api, payload, "watched", extra):
        _notify("WeTrakr", "Marked as watched")
        _log("Marked '{}' as watched via context menu ({})".format(title, mode))
    else:
        _notify("WeTrakr", "Failed to mark as watched")


def _handle_mark_unwatched(api, payload, title):
    choice = xbmcgui.Dialog().select(u"Mark as unwatched", [
        u"Remove the last play",
        u"Remove all plays",
    ])
    if choice < 0:
        return
    scope = "all" if choice == 1 else "last"
    if scope == "all" and not xbmcgui.Dialog().yesno(
            u"WeTrakr", u"Remove every play of '{}' from your WeTrakr history?".format(title)):
        return

    if _send(api, payload, "unwatched", {"scope": scope}):
        _notify("WeTrakr", "Marked as unwatched")
        _log("Marked '{}' as unwatched via context menu ({})".format(title, scope))
    else:
        _notify("WeTrakr", "Failed to mark as unwatched")


def run():
    if not auth.is_authenticated():
        _notify("WeTrakr", "Not connected. Use Connect in the add-on settings.", 5000)
        return

    payload, label = _focused_payload()
    if not payload:
        _notify("WeTrakr", "Only movies and episodes can be tracked")
        return
    title = payload.get("title") or ""
    if label == "episode" and payload.get("show_title"):
        title = u"{} S{:02d}E{:02d}".format(payload["show_title"], payload.get("season") or 0,
                                           payload.get("episode") or 0)
    if not title:
        _log("No title found for context menu item")
        return

    options = [
        u"♥  Rate this {}".format(label),
        u"     Remove rating",
        u"✓  Mark as Watched",
        u"     Mark as Unwatched",
    ]
    result = xbmcgui.Dialog().select(u"WeTrakr: {}".format(title), options)
    if result < 0:
        return

    api = _get_api()
    if not api:
        _notify("WeTrakr", "Not connected")
        return

    if result == 0:
        _handle_rate(api, payload, title, label)
    elif result == 1:
        _handle_unrate(api, payload, title)
    elif result == 2:
        _handle_mark_watched(api, payload, title)
    elif result == 3:
        _handle_mark_unwatched(api, payload, title)
