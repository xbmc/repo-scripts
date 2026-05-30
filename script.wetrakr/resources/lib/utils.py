"""
utils.py — Extract media metadata and IDs from Kodi's playback info.

Uses xbmc.Player().getVideoInfoTag() for basic info and JSON-RPC
Player.GetItem / VideoLibrary.GetTVShowDetails for external IDs.
"""

import json
import xbmc


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
            "tvshowid", "uniqueid", "imdbnumber", "file", "type"
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


def build_payload(event, item, show_item=None, progress=0.0):
    """
    Build the JSON payload to send to WeTrakr API.

    Args:
        event: 'scrobble' or 'playing'
        item: Kodi JSON-RPC item dict
        show_item: TV show details dict (for episodes)
        progress: Playback progress percentage (0-100)

    Returns: dict matching the WeTrakr Kodi webhook contract
    """
    item_type = item.get("type", "unknown")
    ids = extract_ids(item)

    # Add-on sources (Jellyfin for Kodi, Plex Kodi Connect, ...) bypass Kodi's
    # VideoLibrary and JSON-RPC returns an empty uniqueid dict for them. Pull
    # the IDs straight from the running player via infolabels as a fallback.
    if not ids["tmdb"] and not ids["imdb"] and not ids["tvdb"]:
        ids = get_player_uniqueids()

    if item_type == "episode":
        # We send the episode payload even when show_item is missing
        # (e.g. the show isn't in the Kodi library) — the backend can
        # resolve the show from the episode-level ids as a fallback,
        # but only if we ship season/episode numbers. Falling back to
        # the minimal payload here dropped those fields and turned
        # every "Now Playing"/"Scrobble" event into "Episode not found".
        show_ids = extract_ids(show_item) if show_item else {}
        show_title = item.get("showtitle") or (show_item.get("title", "") if show_item else "")
        return {
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

    if item_type == "movie":
        return {
            "event": event,
            "media_type": "movie",
            "title": item.get("title", ""),
            "year": item.get("year", 0),
            "ids": ids,
            "progress": round(progress, 1)
        }

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
