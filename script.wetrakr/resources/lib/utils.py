"""
utils.py — Extract media metadata and IDs from Kodi's playback info.

Uses xbmc.Player().getVideoInfoTag() for basic info and JSON-RPC
Player.GetItem / VideoLibrary.GetTVShowDetails for external IDs.
"""

import json
import xbmc
import xbmcaddon

try:
    from urllib.parse import urlsplit, parse_qs
except ImportError:
    # Python 2 fallback (Kodi 18 Leia and earlier)
    from urlparse import urlsplit, parse_qs


def user_agent():
    """'WeTrakr-Kodi/<version>' with the installed add-on version, so the server
    can tell which versions are out there (the string used to be hardcoded)."""
    try:
        version = xbmcaddon.Addon("script.wetrakr").getAddonInfo("version")
    except Exception:
        version = "unknown"
    return "WeTrakr-Kodi/{}".format(version)


def get_json_rpc(method, params):
    """Execute a Kodi JSON-RPC call and return the parsed result."""
    request = json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    })
    response = xbmc.executeJSONRPC(request)
    return json.loads(response).get("result", {})


def get_active_player_id():
    """Return the active video player ID, or None."""
    result = get_json_rpc("Player.GetActivePlayers", {})
    for player in result if isinstance(result, list) else []:
        if player.get("type") == "video":
            return player.get("playerid")
    return None


def get_playing_item(player_id):
    """Get currently playing item with full metadata via JSON-RPC."""
    return get_json_rpc("Player.GetItem", {
        "playerid": player_id,
        "properties": [
            "title", "showtitle", "season", "episode", "year",
            "tvshowid", "uniqueid", "imdbnumber", "file", "type",
            "firstaired", "originaltitle", "premiered", "runtime"
        ]
    }).get("item", {})


def get_tvshow_details(tvshow_id):
    """Fetch TV show details (including uniqueid) for episode resolution."""
    if not tvshow_id or tvshow_id < 0:
        return {}
    return get_json_rpc("VideoLibrary.GetTVShowDetails", {
        "tvshowid": tvshow_id,
        "properties": ["uniqueid", "imdbnumber", "title", "year"]
    }).get("tvshowdetails", {})


def get_player_uniqueids():
    """Read uniqueid values from the currently playing video via VideoPlayer
    infolabels. The only reliable path when an item is played from an add-on
    source (Jellyfin for Kodi, Plex Kodi Connect, ...) that bypasses Kodi's
    VideoLibrary — JSON-RPC returns an empty uniqueid dict in that case but
    the player still knows the IDs.
    """
    tmdb = _parse_int(xbmc.getInfoLabel('VideoPlayer.UniqueID(tmdb)'))
    tvdb = _parse_int(xbmc.getInfoLabel('VideoPlayer.UniqueID(tvdb)'))
    imdb = xbmc.getInfoLabel('VideoPlayer.UniqueID(imdb)') or None
    if imdb and not imdb.startswith('tt'):
        imdb = None
    return {"tmdb": tmdb, "imdb": imdb, "tvdb": tvdb}


# Query parameters that video add-ons put in their plugin:// play URLs.
# Umbrella: action=play_Item&title=..&year=..&imdb=tt..&tmdb=..
# Fen Light / POV: mode=playback.media&media_type=movie&tmdb_id=..
_URL_ID_PARAMS = {
    "tmdb": ("tmdb", "tmdb_id", "tmdbid"),
    "imdb": ("imdb", "imdb_id", "imdbid"),
    "tvdb": ("tvdb", "tvdb_id", "tvdbid"),
}


def extract_ids_from_url(file_url):
    """IDs from the plugin:// URL of the playing item.

    The resolved stream usually carries no uniqueid, but the ORIGINAL plugin
    URL (what Player.GetItem returns as `file`) names the title by id in most
    video add-ons. Only whitelisted parameters are read and only the ids leave
    the device: the URL itself can embed debrid links with tokens.
    """
    empty = {"tmdb": None, "imdb": None, "tvdb": None}
    if not file_url or not str(file_url).startswith("plugin://"):
        return empty
    try:
        params = parse_qs(urlsplit(str(file_url)).query, keep_blank_values=False)
    except Exception:
        return empty
    ids = dict(empty)
    for key, names in _URL_ID_PARAMS.items():
        for name in names:
            values = params.get(name)
            if not values:
                continue
            value = str(values[0]).strip()
            if key == "imdb":
                if value.startswith("tt") and value[2:].isdigit():
                    ids[key] = value
            else:
                ids[key] = _parse_int(value)
            if ids[key]:
                break
    return ids


def _has_ids(ids):
    return bool(ids.get("tmdb") or ids.get("imdb") or ids.get("tvdb"))


def extract_ids(item):
    """
    Extract external IDs (tmdb, imdb, tvdb) from a Kodi item.

    Checks:
      1. item.uniqueid dict: {"imdb": "tt...", "tmdb": "12345", "tvdb": "67890"}
      2. item.imdbnumber field (fallback for IMDB)

    Returns: { "tmdb": int|None, "imdb": str|None, "tvdb": int|None }
    """
    uniqueid = item.get("uniqueid", {}) or {}

    tmdb = _parse_int(uniqueid.get("tmdb"))
    tvdb = _parse_int(uniqueid.get("tvdb"))
    imdb = uniqueid.get("imdb") or None

    # Fallback: imdbnumber field
    if not imdb:
        imdb_fallback = item.get("imdbnumber", "")
        if imdb_fallback and imdb_fallback.startswith("tt"):
            imdb = imdb_fallback
        elif imdb_fallback and not tmdb:
            # Some scrapers put TMDB ID in imdbnumber
            tmdb = _parse_int(imdb_fallback)

    return {"tmdb": tmdb, "imdb": imdb, "tvdb": tvdb}


def detect_show_id_source(show_item):
    """
    Which scraper matched the TV show in the Kodi library: 'tvdb' or 'tmdb'.

    Kodi stores the id of the scraper that matched the show as its *default*
    unique id, and JSON-RPC returns that value in `imdbnumber` (a legacy name,
    it is not always an IMDb id). Comparing it with the uniqueid dict tells the
    scraper, and with it the episode numbering: TheTVDB and TMDB number some
    shows differently (The Great British Bake Off is season 17 on TheTVDB and
    season 10 on TMDB), and WeTrakr translates TheTVDB numbers when it knows.

    Returns None when it cannot tell (no library item, or an IMDb default).
    """
    if not show_item:
        return None
    default_id = str(show_item.get("imdbnumber") or "").strip()
    if not default_id:
        return None
    uniqueid = show_item.get("uniqueid", {}) or {}
    for source in ("tvdb", "tmdb"):
        value = uniqueid.get(source)
        if value is not None and str(value).strip() == default_id:
            return source
    return None


def _aired_date(value):
    """'YYYY-MM-DD' from Kodi's firstaired, or None."""
    value = str(value or "").strip()[:10]
    if len(value) == 10 and value[4] == "-" and value[7] == "-" and value[:4].isdigit():
        return value
    return None


def _original_title(item):
    value = item.get("originaltitle") or xbmc.getInfoLabel("VideoPlayer.OriginalTitle") or ""
    value = str(value).strip()
    return value if value and value != str(item.get("title") or "").strip() else None


def build_payload(event, item, show_item=None, progress=0.0, runtime=0):
    """
    Build the JSON payload to send to WeTrakr API.

    Args:
        event: 'scrobble' or 'playing'
        item: Kodi JSON-RPC item dict
        show_item: TV show details dict (for episodes)
        progress: Playback progress percentage (0-100)
        runtime: real duration of the playing file in seconds (Player.getTotalTime)

    Returns: dict matching the WeTrakr Kodi webhook contract
    """
    item_type = item.get("type", "unknown")
    ids = extract_ids(item)
    ids_source = "library"

    # Add-on sources (Jellyfin for Kodi, Plex Kodi Connect, ...) bypass Kodi's
    # VideoLibrary and JSON-RPC returns an empty uniqueid dict for them. Pull
    # the IDs straight from the running player via infolabels as a fallback,
    # and after that from the add-on's own plugin:// URL.
    if not _has_ids(ids):
        ids = get_player_uniqueids()
        ids_source = "player"
    if not _has_ids(ids):
        ids = extract_ids_from_url(item.get("file"))
        ids_source = "url"
    if not _has_ids(ids):
        ids_source = None

    # Without ids the server falls back to the title: the real file duration,
    # the original title and the release date break ties between homonyms.
    try:
        runtime = int(round(float(runtime or 0)))
    except (TypeError, ValueError):
        runtime = 0
    if runtime <= 0:
        runtime = _parse_int(item.get("runtime")) or 0

    if item_type == "episode":
        # We send the episode payload even when show_item is missing
        # (e.g. the show isn't in the Kodi library) — the backend can
        # resolve the show from the episode-level ids as a fallback,
        # but only if we ship season/episode numbers. Falling back to
        # the minimal payload here dropped those fields and turned
        # every "Now Playing"/"Scrobble" event into "Episode not found".
        show_ids = extract_ids(show_item) if show_item else {}
        show_title = item.get("showtitle") or (show_item.get("title", "") if show_item else "")
        payload = {
            "event": event,
            "media_type": "episode",
            "title": item.get("title", ""),
            "show_title": show_title,
            "show_ids": show_ids,
            "season": item.get("season", 0),
            "episode": item.get("episode", 0),
            "ids": ids,
            "progress": round(progress, 1)
        }
        # Numbering hints for shows that TheTVDB and TMDB number differently:
        # the library scraper and the episode air date.
        show_id_source = detect_show_id_source(show_item)
        if show_id_source:
            payload["show_id_source"] = show_id_source
        aired = _aired_date(item.get("firstaired"))
        if aired:
            payload["aired"] = aired
        if ids_source:
            payload["ids_source"] = ids_source
        if runtime:
            payload["runtime"] = runtime
        return payload

    if item_type == "movie":
        payload = {
            "event": event,
            "media_type": "movie",
            "title": item.get("title", ""),
            "year": item.get("year", 0),
            "ids": ids,
            "progress": round(progress, 1)
        }
        if ids_source:
            payload["ids_source"] = ids_source
        if runtime:
            payload["runtime"] = runtime
        original_title = _original_title(item)
        if original_title:
            payload["original_title"] = original_title
        premiered = _aired_date(item.get("premiered"))
        if premiered:
            payload["premiered"] = premiered
        return payload

    # Unknown type — return minimal payload for server-side ignore
    return {
        "event": event,
        "media_type": item_type,
        "title": item.get("title", ""),
        "ids": ids,
        "progress": round(progress, 1)
    }


def _parse_int(value):
    """Safely parse a value to int, returning None on failure."""
    if value is None:
        return None
    try:
        result = int(value)
        return result if result > 0 else None
    except (ValueError, TypeError):
        return None
