"""Kodi JSON-RPC calls with a short response cache, library helpers and the add-on logger."""
from __future__ import annotations

from typing import Any, Dict, NamedTuple, Optional, Tuple, List, Callable, overload, Final
from time import monotonic
import threading

import xbmc
import xbmcaddon
from lib.kodi.settings import KodiSettings

# Kodi reloads only the first Addon() per id on a settings save
ADDON = xbmcaddon.Addon()

CACHE_DEFAULT_TTL: Final = 30
CACHE_CLEANUP_INTERVAL: Final = 60
CACHE_CLEANUP_REQUEST_INTERVAL: Final = 50
CACHE_MAX_SIZE: Final = 200


class MediaTypeSpec(NamedTuple):
    """Per-media-type Kodi JSON-RPC method names and keys; the `KODI_*` lookups derive from it."""
    get_method: str
    set_method: str
    id_key: str
    details_key: str
    library_method: str
    library_key: str


def _spec(noun: str, plural_noun: str, library: str = 'VideoLibrary') -> MediaTypeSpec:
    """Build a MediaTypeSpec from Kodi's conventional Get/Set method naming pattern."""
    return MediaTypeSpec(
        get_method=f'{library}.Get{noun}Details',
        set_method=f'{library}.Set{noun}Details',
        id_key=f'{noun.lower()}id',
        details_key=f'{noun.lower()}details',
        library_method=f'{library}.Get{plural_noun}',
        library_key=plural_noun.lower(),
    )


MEDIA_TYPE_SPECS: Dict[str, MediaTypeSpec] = {
    'movie':      _spec('Movie',      'Movies'),
    'tvshow':     _spec('TVShow',     'TVShows'),
    'season':     _spec('Season',     'Seasons'),
    'episode':    _spec('Episode',    'Episodes'),
    'musicvideo': _spec('MusicVideo', 'MusicVideos'),
    # 'set' breaks the pattern: id_key='setid' but library uses 'MovieSets'/'sets'
    'set': MediaTypeSpec(
        get_method='VideoLibrary.GetMovieSetDetails',
        set_method='VideoLibrary.SetMovieSetDetails',
        id_key='setid',
        details_key='setdetails',
        library_method='VideoLibrary.GetMovieSets',
        library_key='sets',
    ),
    'artist': _spec('Artist', 'Artists', library='AudioLibrary'),
    'album':  _spec('Album',  'Albums',  library='AudioLibrary'),
    'song':   _spec('Song',   'Songs',   library='AudioLibrary'),
}

KODI_GET_DETAILS_METHODS = {
    mt: (s.get_method, s.id_key, s.details_key) for mt, s in MEDIA_TYPE_SPECS.items()
}
KODI_SET_DETAILS_METHODS = {mt: (s.set_method, s.id_key) for mt, s in MEDIA_TYPE_SPECS.items()}
KODI_ID_KEYS = {mt: s.id_key for mt, s in MEDIA_TYPE_SPECS.items()}
KODI_GET_LIBRARY_METHODS = {
    mt: (s.library_method, s.library_key) for mt, s in MEDIA_TYPE_SPECS.items()
}

KODI_MOVIE_PROPERTIES = [
    "title", "streamdetails", "set", "setid", "ratings",
    "rating", "votes", "file", "year", "runtime", "mpaa",
    "plot", "plotoutline", "genre", "studio", "country",
    "writer", "director", "art", "tagline", "trailer",
    "originaltitle", "premiered", "lastplayed", "playcount",
    "cast", "imdbnumber", "top250", "resume", "dateadded",
    "tag", "userrating", "uniqueid"
]

_L1: Dict[str, Tuple[float, Any]] = {}
_last_cleanup = monotonic()
_request_count = 0

_CACHE_LOCK = threading.Lock()


def _cleanup_expired_cache(force: bool = False) -> None:
    """Evict expired entries, then the least recently used; runs only once a trigger fires."""
    global _last_cleanup, _request_count
    now = monotonic()

    should_cleanup = (
        force or
        (now - _last_cleanup >= CACHE_CLEANUP_INTERVAL) or
        (_request_count >= CACHE_CLEANUP_REQUEST_INTERVAL) or
        (len(_L1) > CACHE_MAX_SIZE)
    )

    if not should_cleanup:
        return

    with _CACHE_LOCK:
        _last_cleanup = now
        _request_count = 0

        expired = [k for k, v in _L1.items() if v[0] <= now]
        for k in expired:
            _L1.pop(k, None)

        while len(_L1) > CACHE_MAX_SIZE:
            _L1.pop(next(iter(_L1)), None)


def drop_cached(prefix: str) -> None:
    """Forget every cached response under a key prefix, after Kodi wrote to that item."""
    with _CACHE_LOCK:
        for key in [k for k in _L1 if k.startswith(prefix)]:
            _L1.pop(key, None)


def get_cache_only(cache_key: str) -> Optional[dict]:
    """Read from the in-memory cache without making a JSON-RPC call. None on miss/expired."""
    now = monotonic()
    with _CACHE_LOCK:
        ent = _L1.get(cache_key)
        if ent and ent[0] > now:
            # a hit protects the entry from the capacity evict
            del _L1[cache_key]
            _L1[cache_key] = ent
            return ent[1]
    return None


@overload
def extract_result(resp: Optional[dict], result_key: str, default: list) -> list: ...
@overload
def extract_result(resp: Optional[dict], result_key: str, default: dict) -> dict: ...
@overload
def extract_result(resp: Optional[dict], result_key: str, default: None = None) -> Any: ...
def extract_result(resp: Optional[dict], result_key: str, default=None):
    """Extract `resp['result'][result_key]`, defaulting to the shape the key implies."""
    if default is None:
        default = [] if result_key.endswith("s") and result_key != "details" else {}

    if not resp:
        return default

    result = resp.get("result")
    if not result:
        return default

    value = result.get(result_key)
    if value is None:
        return default

    return value


def _call_jsonrpc(payload: Any, error_context: str) -> Any:
    """Execute a single or batch JSON-RPC payload and return the parsed body; None on any error."""
    import json
    try:
        raw = xbmc.executeJSONRPC(json.dumps(payload, separators=(",", ":")))
    except (OSError, IOError) as e:
        log("General", f"Network error in {error_context}: {str(e)}", xbmc.LOGWARNING)
        return None
    except Exception as e:
        log("General", f"Unexpected error in {error_context}: {str(e)}", xbmc.LOGERROR)
        return None

    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError as e:
        log("General", f"JSON decode error in {error_context}: {str(e)}", xbmc.LOGERROR)
        return None
    except Exception as e:
        log("General", f"Error processing response in {error_context}: {str(e)}", xbmc.LOGERROR)
        return None


def request(method: str, params: Optional[Dict[str, Any]] = None,
            cache_key: Optional[str] = None, ttl_seconds: Optional[int] = None) -> Optional[dict]:
    """Make a JSON-RPC request with optional read-through caching; None on any error."""
    global _request_count
    ttl = CACHE_DEFAULT_TTL if ttl_seconds is None else max(1, int(ttl_seconds))

    if cache_key:
        cached = get_cache_only(cache_key)
        if cached is not None:
            return cached

    _request_count += 1
    _cleanup_expired_cache()

    data = _call_jsonrpc(
        {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": 1},
        f"call to {method}",
    )
    if data is None:
        return None

    if not isinstance(data, dict):
        log("General", f"Invalid response type for {method}: {type(data)}", xbmc.LOGWARNING)
        return None

    if "error" in data:
        error = data.get("error", {})
        error_code = error.get("code") if isinstance(error, dict) else None
        level = xbmc.LOGDEBUG if error_code == -32602 else xbmc.LOGWARNING
        log("General", f"JSON-RPC error for {method}: {error}", level)
        return None

    if cache_key:
        with _CACHE_LOCK:
            try:
                result_only = data.get("result")
                entry = {"result": result_only} if result_only is not None else data
                _L1.pop(cache_key, None)
                _L1[cache_key] = (monotonic() + float(ttl), entry)
            except Exception as e:
                log(
                    "General",
                    f"Failed to cache result for key '{cache_key}': {str(e)}",
                    xbmc.LOGWARNING,
                )

    return data


def batch_request(calls: List[Dict[str, Any]],
                  ttl_seconds: Optional[int] = None) -> List[Optional[dict]]:
    """Execute several JSON-RPC calls as one batch; responses in input order, None per failure."""
    global _request_count

    if not calls:
        return []

    ttl = CACHE_DEFAULT_TTL if ttl_seconds is None else max(1, int(ttl_seconds))
    all_cached: List[Optional[dict]] = []
    all_hit = True

    for c in calls:
        key = c.get("cache_key")
        if key:
            cached = get_cache_only(key)
            all_cached.append(cached)
            if cached is None:
                all_hit = False
        else:
            all_cached.append(None)
            all_hit = False

    if all_hit:
        return all_cached

    _request_count += len(calls)
    _cleanup_expired_cache()

    payloads = []
    for i, c in enumerate(calls, 1):
        payloads.append({
            "jsonrpc": "2.0",
            "method": c.get("method"),
            "params": c.get("params") or {},
            "id": i,
        })

    data = _call_jsonrpc(payloads, "batch request")
    if data is None:
        return [None] * len(calls)

    if not isinstance(data, list):
        log("General", f"Invalid batch response type: {type(data)}", xbmc.LOGWARNING)
        return [None] * len(calls)

    by_id = {}
    for item in data:
        if isinstance(item, dict) and "id" in item:
            by_id[item["id"]] = item

    results: List[Optional[dict]] = []
    now = monotonic()

    with _CACHE_LOCK:
        for i, c in enumerate(calls, 1):
            resp = by_id.get(i)
            if not resp:
                results.append(None)
                continue

            results.append(resp)

            key = c.get("cache_key")
            if key and "error" not in resp:
                try:
                    result_only = resp.get("result")
                    entry = {"result": result_only} if result_only is not None else resp
                    _L1.pop(key, None)
                    _L1[key] = (now + float(ttl), entry)
                except Exception as e:
                    log(
                        "General",
                        f"Failed to cache batch result for key '{key}': {str(e)}",
                        xbmc.LOGWARNING,
                    )

    return results


def get_item_details(media_type: str, dbid: int, properties: List[str], cache_key: str = "",
                     ttl_seconds: Optional[int] = None, **extra_params: Any) -> Any:
    """Fetch item details via the right GetXDetails method and result key for the media type."""
    method_info = KODI_GET_DETAILS_METHODS.get(media_type)
    if not method_info:
        log("API", f"Unknown media type: {media_type}", xbmc.LOGERROR)
        return None

    method, id_key, result_key = method_info
    payload = {id_key: dbid, 'properties': properties}
    payload.update(extra_params)

    resp = request(method, payload, cache_key=cache_key, ttl_seconds=ttl_seconds)
    if not resp:
        return None

    return extract_result(resp, result_key)


def get_item_uniqueids(dbtype: str, dbid: str, cache_key: str = "") -> Tuple[str, str]:
    """Fetch `(imdb_id, tmdb_id)` for a library item via JSON-RPC `GetXDetails`."""
    details = get_item_details(dbtype, int(dbid), ["uniqueid"], cache_key=cache_key)
    if not details or not isinstance(details, dict):
        return "", ""
    uniqueid = details.get("uniqueid", {})
    return uniqueid.get("imdb", ""), str(uniqueid.get("tmdb", "") or "")


def decode_image_url(url: str) -> str:
    """Decode an `image://` URL to the form Kodi stores; `image://video@...` stays wrapped."""
    if not url or not url.startswith('image://'):
        return url

    inner = url[8:-1] if url.endswith('/') else url[8:]

    if '@' in inner:
        return url

    from urllib.parse import unquote
    return unquote(inner)


def encode_image_url(decoded_url: str) -> str:
    """Wrap URL in `image://` for `xbmcvfs.File()`/texture cache; inverse of `decode_image_url`."""
    if not decoded_url:
        return decoded_url

    if decoded_url.startswith('image://'):
        return decoded_url

    from urllib.parse import quote
    encoded = quote(decoded_url, safe='')
    return f'image://{encoded}/'


def is_inherited_art(media_type: str, art_type: str) -> bool:
    """True for parent art Kodi folds into an item's map, never to be written to its own path."""
    if media_type == 'movie':
        return art_type.startswith('set.')
    if media_type == 'episode':
        return art_type.startswith('tvshow.') or art_type.startswith('season.')
    if media_type == 'season':
        return art_type.startswith('tvshow.')
    if media_type == 'album':
        # Kodi folds every album artist in as artist.*, artist1.*, artist2.* and so on
        return art_type.startswith('artist')
    return False


def _decode_art_dict(art: Dict[str, str]) -> Dict[str, str]:
    """Decode URLs in an art dict, dropping entries that decode to `image://video@...` wrappers."""
    if not art:
        return art

    decoded = {}
    for art_type, url in art.items():
        result = decode_image_url(url)

        if result.startswith('image://') and '@' in result:
            continue

        decoded[art_type] = result

    return decoded


class LibraryScanAborted(Exception):
    """Raised by `get_library_items` when `abort_check` signals cancellation mid-scan."""


def get_library_items(media_types: List[str], properties: List[str], *,
                      decode_urls: bool = False, include_nested_seasons: bool = False,
                      season_properties: Optional[List[str]] = None,
                      filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
                      progress_callback: Optional[Callable[[str, int, int], None]] = None,
                      abort_check: Optional[Callable[[], bool]] = None,
                      sort: Optional[Dict[str, str]] = None,
                      page_size: int = 2000) -> List[Dict[str, Any]]:
    """Fetch library items, optionally decoding art and folding in seasons."""
    all_items: List[Dict[str, Any]] = []

    for media_type in media_types:
        if media_type not in KODI_GET_LIBRARY_METHODS:
            continue

        method, result_key = KODI_GET_LIBRARY_METHODS[media_type]
        id_key = KODI_ID_KEYS.get(media_type, 'id')

        start = 0
        total = 0
        done = 0

        while True:
            params: Dict[str, Any] = {
                "properties": properties,
                "limits": {"start": start, "end": start + page_size},
            }
            if sort:
                params["sort"] = sort
            resp = request(method, params)
            if not resp:
                log("General", f"Failed to fetch {media_type} from library", xbmc.LOGWARNING)
                break

            result = resp.get("result") or {}
            items = result.get(result_key) or []
            total = result.get("limits", {}).get("total", len(items))

            for item in items:
                if not isinstance(item, dict):
                    continue

                item['media_type'] = media_type

                dbid = item.get(id_key)
                if dbid:
                    item['dbid'] = dbid

                if decode_urls and 'art' in item and isinstance(item['art'], dict):
                    item['art'] = _decode_art_dict(item['art'])

                if filter_func and not filter_func(item):
                    continue

                all_items.append(item)

                if include_nested_seasons and media_type == 'tvshow' and dbid:
                    tvshowid = dbid
                    season_props = season_properties or properties
                    seasons_resp = request("VideoLibrary.GetSeasons", {
                        "tvshowid": tvshowid,
                        "properties": season_props
                    })

                    if seasons_resp:
                        seasons = extract_result(seasons_resp, 'seasons', [])
                        for season in seasons:
                            if not isinstance(season, dict):
                                continue

                            season['media_type'] = 'season'
                            season['tvshowid'] = tvshowid

                            if 'file' not in season and 'file' in item:
                                season['file'] = item['file']

                            if 'showtitle' not in season and 'title' in item:
                                season['showtitle'] = item['title']

                            season_id = season.get('seasonid')
                            if season_id:
                                season['dbid'] = season_id

                            if decode_urls and 'art' in season and isinstance(season['art'], dict):
                                season['art'] = _decode_art_dict(season['art'])

                            if filter_func and not filter_func(season):
                                continue

                            all_items.append(season)

                if include_nested_seasons:
                    done += 1
                    if progress_callback:
                        progress_callback(media_type, done, total)
                    if abort_check and abort_check():
                        raise LibraryScanAborted()

            if not include_nested_seasons:
                done += len(items)
                if progress_callback:
                    progress_callback(media_type, done, total)
                if abort_check and abort_check():
                    raise LibraryScanAborted()

            start += page_size
            if not items or start >= total:
                break

    return all_items


API_KEY_CONFIG = {
    "tmdb_api_key": {
        "name": "TMDB",
        "get_url": "https://www.themoviedb.org/settings/api",
        "setting_path": "tmdb_api_key"
    },
    "fanarttv_api_key": {
        "name": "Fanart.tv",
        "get_url": "https://fanart.tv/get-an-api-key/",
        "setting_path": "fanarttv_api_key"
    },
    "mdblist_api_key": {
        "name": "MDBList",
        "get_url": "https://mdblist.com/",
        "setting_path": "mdblist_api_key"
    },
    "omdb_api_key": {
        "name": "OMDb",
        "get_url": "https://www.omdbapi.com/apikey.aspx",
        "setting_path": "omdb_api_key"
    },
}


def get_api_key(key_id: str) -> Optional[str]:
    """Get an API key by `API_KEY_CONFIG` id; None when unknown or unset."""
    config = API_KEY_CONFIG.get(key_id)
    if not config:
        return None
    return KodiSettings.get_string(config["setting_path"]) or None


def format_item_label(item: Dict, media_type: str) -> str:
    """Display label for an item; episodes get show title with SxxExx."""
    if media_type == "episode":
        showtitle = item.get("showtitle")
        season = item.get("season")
        episode = item.get("episode")
        if showtitle and season is not None and episode is not None:
            return f"{showtitle} S{int(season):02d}E{int(episode):02d}"
    return item.get("title", "")


def log(category: str, message: str, level: int = xbmc.LOGDEBUG) -> None:
    """Log a categorized message; DEBUG escalates to INFO when the debug setting is on."""
    if level == xbmc.LOGDEBUG:
        try:
            if KodiSettings.debug_enabled():
                level = xbmc.LOGINFO
        except Exception:
            pass
    xbmc.log(f"script.skin.info.service: [{category}] {message}", level)
