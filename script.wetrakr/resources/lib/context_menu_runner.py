"""
context_menu_runner.py — handler for the WeTrakr context-menu entry.

Shows action options (rate / mark watched) for the focused movie or
episode and dispatches them to the WeTrakr API.
"""

import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.api import WeTrakrAPI
from resources.lib import auth
from resources.lib import rating as rating_mod
from resources.lib.notification import notify as _notify


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log("[WeTrakr] Context: {}".format(msg), level)


def _get_item_info():
    """Extract media info from the currently focused list item."""
    return {
        "title": xbmc.getInfoLabel('ListItem.Title'),
        "year": xbmc.getInfoLabel('ListItem.Year'),
        "imdbnumber": xbmc.getInfoLabel('ListItem.IMDBNumber'),
        "type": xbmc.getInfoLabel('ListItem.DBType') or "movie",
        "season": xbmc.getInfoLabel('ListItem.Season'),
        "episode": xbmc.getInfoLabel('ListItem.Episode'),
        "showtitle": xbmc.getInfoLabel('ListItem.TVShowTitle'),
        "poster": xbmc.getInfoLabel('ListItem.Art(poster)'),
    }


def _get_api():
    """Create WeTrakrAPI from saved settings."""
    addon = xbmcaddon.Addon("script.wetrakr")
    token = addon.getSetting("api_token")
    api_url = addon.getSetting("api_url") or "https://api.wetrakr.com"
    if not token:
        return None
    return WeTrakrAPI(api_url, token)


def _build_ids(item):
    """Extract external IDs from item info."""
    ids = {}
    imdb = item.get("imdbnumber", "")
    if imdb and imdb.startswith("tt"):
        ids["imdb"] = imdb
    elif imdb:
        try:
            ids["tmdb"] = int(imdb)
        except ValueError:
            pass
    return ids


def _handle_rate(api, item, title, ids):
    media_label = "episode" if item["type"] == "episode" else "movie"
    year = None
    try:
        year = int(item["year"]) if item["year"] else None
    except ValueError:
        pass

    poster = item.get("poster") or None
    rating_value = rating_mod.show_rating_dialog(title, year, poster_path=poster)
    if rating_value is None:
        return

    if item["type"] == "episode":
        api.send_rating(
            "episode", title, ids, rating_value,
            show_title=item["showtitle"],
            season=int(item.get("season") or 0),
            episode=int(item.get("episode") or 0)
        )
    else:
        api.send_rating("movie", title, ids, rating_value, year=year)

    _notify("WeTrakr", "Rated {}/10".format(rating_value))
    _log("Rated '{}': {}/10 via context menu ({})".format(title, rating_value, media_label))


def _handle_mark_watched(api, item, title, ids):
    payload = {
        "event": "scrobble",
        "media_type": item["type"] or "movie",
        "title": title,
        "ids": ids,
        "progress": 100.0
    }
    if item["type"] == "episode":
        payload["show_title"] = item["showtitle"]
        payload["season"] = int(item.get("season") or 0)
        payload["episode"] = int(item.get("episode") or 0)
    else:
        try:
            payload["year"] = int(item["year"]) if item["year"] else 0
        except ValueError:
            payload["year"] = 0

    addon = xbmcaddon.Addon("script.wetrakr")
    debug = addon.getSetting("debug") == "true"
    success = api.send_event(payload, debug=debug)

    if success:
        _notify("WeTrakr", "Marked as watched")
        _log("Marked '{}' as watched via context menu".format(title))
    else:
        _notify("WeTrakr", "Failed to mark as watched")


def run():
    if not auth.is_authenticated():
        _notify("WeTrakr", "Not connected. Go to Settings to connect.", 5000)
        return

    item = _get_item_info()
    title = item["title"]
    if not title:
        _log("No title found for context menu item")
        return

    media_label = "episode" if item["type"] == "episode" else "movie"
    options = [
        u"♥  Rate this {}".format(media_label),
        u"✓  Mark as Watched",
    ]

    result = xbmcgui.Dialog().select(
        "WeTrakr  —  {}".format(title),
        options
    )

    if result < 0:
        return

    api = _get_api()
    if not api:
        _notify("WeTrakr", "Not connected")
        return

    ids = _build_ids(item)

    if result == 0:
        _handle_rate(api, item, title, ids)
    elif result == 1:
        _handle_mark_watched(api, item, title, ids)
