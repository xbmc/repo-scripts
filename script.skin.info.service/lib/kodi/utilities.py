"""Utility functions for properties, date formatting, and language handling.

`set_prop`/`batch_set_props`/`clear_prop`/`clear_group` cache-diff writes to the home window
only. Route any property also written by the service through these to avoid cache desync.
"""
from __future__ import annotations

import threading
import time
import xbmc
import xbmcgui
from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime
from collections import OrderedDict

from lib.kodi.settings import KodiSettings
from lib.kodi.client import log, request
HOME = xbmcgui.Window(10000)

MEDIA_TYPE_LABELS = {
    'movie': 'Movies',
    'tvshow': 'TV Shows',
    'episode': 'Episodes',
    'season': 'Seasons',
    'set': 'Movie Sets',
    'musicvideo': 'Music Videos',
    'artist': 'Artists',
    'album': 'Albums',
}

VALID_MEDIA_TYPES = frozenset(MEDIA_TYPE_LABELS.keys())


def validate_media_type(media_type: str) -> bool:
    """Validate that media_type is a known type."""
    return media_type in VALID_MEDIA_TYPES


def validate_dbid(dbid: Any) -> bool:
    """Validate that dbid is a positive integer."""
    try:
        return int(dbid) > 0
    except (ValueError, TypeError):
        return False


def resolve_infolabel(value: str) -> str:
    """Resolve a `$INFO[...]` or `$VAR[...]` wrapped string via Kodi, else pass through."""
    if value and value.startswith('$'):
        return xbmc.getInfoLabel(value)
    return value


class _TransitionGate:
    """Holds back ListItem/Container reads from other threads until a window or dialog change
    finishes; reading them while Kodi is still building the window can crash.
    """

    _SETTLE_SECONDS = 0.2

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_ids: Optional[Tuple[int, int]] = None
        self._settle_until = 0.0

    def settled(self) -> bool:
        """False while a window/dialog transition is within the settle window."""
        ids = (xbmcgui.getCurrentWindowId(), xbmcgui.getCurrentWindowDialogId())
        now = time.monotonic()
        with self._lock:
            if ids != self._last_ids:
                self._last_ids = ids
                self._settle_until = now + self._SETTLE_SECONDS
                return False
            return now >= self._settle_until


_transition_gate = _TransitionGate()


def gui_transition_settled() -> bool:
    """False while a window/dialog transition is in flight; gates off-thread ListItem reads."""
    return _transition_gate.settled()


def parse_pipe_list(value: str, separator: str = '|') -> list:
    """Split a separator-delimited string into a stripped, non-empty list."""
    if not value:
        return []
    return [item.strip() for item in value.split(separator) if item.strip()]


_CACHE_LOCK = threading.RLock()

_PREV_PROPS: OrderedDict[str, str] = OrderedDict()
_PREV_PROPS_MAX_SIZE = 500

_DATE_FORMAT_CACHE: Dict[str, str] = {}

LANGUAGE_OPTIONS: List[str] = [
    'en',      # English
    'es',      # Spanish
    'pt-br',   # Portuguese (Brazil)
    'pt',      # Portuguese (Portugal)
    'fr',      # French
    'de',      # German
    'zh-cn',   # Chinese (Simplified)
    'zh-tw',   # Chinese (Traditional)
    'it',      # Italian
    'pl',      # Polish
    'ru',      # Russian
    'nl',      # Dutch
    'sv',      # Swedish
    'ko',      # Korean
    'ja',      # Japanese
]
DEFAULT_LANGUAGE = 'en'

# Kodi's join separator for multi-value strings (genres, directors, cast).
MULTI_VALUE_SEP = " / "


def normalize_language_tag(value: Optional[str]) -> str:
    """Normalize to lowercase ISO 639-1; placeholder codes (`00`, `null`, `xx`) become empty and
    country codes get remapped (`cz` -> `cs`)."""
    normalized = (value or '').strip().lower()

    if normalized in ('00', 'null', 'none', 'xx', 'n/a'):
        return ''

    country_to_language_map = {
        'cz': 'cs',
    }

    return country_to_language_map.get(normalized, normalized)


def get_preferred_language_code() -> str:
    """Return the configured preferred language code."""
    try:
        value = normalize_language_tag(KodiSettings.preferred_language())
    except Exception:
        return DEFAULT_LANGUAGE

    if value in LANGUAGE_OPTIONS:
        return value

    if value.isdigit():
        try:
            index = int(value)
            if 0 <= index < len(LANGUAGE_OPTIONS):
                return LANGUAGE_OPTIONS[index]
        except ValueError:
            pass

    return DEFAULT_LANGUAGE


def _enforce_props_size_limit() -> None:
    """Evict oldest entries from `_PREV_PROPS` once it exceeds the size cap."""
    while len(_PREV_PROPS) > _PREV_PROPS_MAX_SIZE:
        _PREV_PROPS.popitem(last=False)


def set_prop(key: str, val: Optional[str]) -> None:
    """Set a home-window property, skipping the write if the cached value is unchanged."""
    sval = "" if val is None else str(val)

    needs_update = False
    with _CACHE_LOCK:
        existing = _PREV_PROPS.get(key)
        if existing != sval:
            needs_update = True
        elif existing is not None:
            _PREV_PROPS.move_to_end(key)

    if needs_update:
        HOME.setProperty(key, sval)

        with _CACHE_LOCK:
            _PREV_PROPS[key] = sval
            _PREV_PROPS.move_to_end(key)
            _enforce_props_size_limit()


def get_prop(key: str) -> str:
    """Read a home-window property value (empty string if unset)."""
    return HOME.getProperty(key)


def batch_set_props(props: Dict[str, Optional[str]]) -> None:
    """Set many home-window properties, skipping writes where the cached value is unchanged."""
    props_to_set = []
    with _CACHE_LOCK:
        for key, val in props.items():
            sval = "" if val is None else str(val)
            existing = _PREV_PROPS.get(key)
            if existing != sval:
                props_to_set.append((key, sval))
            elif existing is not None:
                _PREV_PROPS.move_to_end(key)

    for key, sval in props_to_set:
        HOME.setProperty(key, sval)

    if props_to_set:
        with _CACHE_LOCK:
            for key, sval in props_to_set:
                _PREV_PROPS[key] = sval
                _PREV_PROPS.move_to_end(key)
            _enforce_props_size_limit()


def clear_prop(key: str) -> None:
    """Clear a single home-window property."""
    with _CACHE_LOCK:
        _PREV_PROPS.pop(key, None)
    HOME.clearProperty(key)


def clear_group(prefix: str) -> None:
    """Clear all tracked home-window properties whose key starts with `prefix`."""
    with _CACHE_LOCK:
        keys_to_clear = [k for k in _PREV_PROPS.keys() if k.startswith(prefix)]
        for k in keys_to_clear:
            _PREV_PROPS.pop(k, None)

    for k in keys_to_clear:
        HOME.clearProperty(k)


def extract_cast_names(cast_list) -> List[str]:
    """Pull just the `name` fields out of a Kodi cast list."""
    if not cast_list:
        return []
    return [str(c.get("name")) for c in cast_list if isinstance(c, dict) and c.get("name")]


def extract_media_ids(item: dict) -> Dict[str, Optional[str]]:
    """Return `{tmdb, imdb, tvdb, trakt}` IDs from a Kodi item, normalizing to string or None.

    Kodi's TMDB scraper writes the TMDB id into `imdbnumber`; only `uniqueid` is trusted here.
    """
    uniqueid = item.get("uniqueid", {})

    tmdb_id = uniqueid.get("tmdb") or uniqueid.get("themoviedb")
    imdb_id = uniqueid.get("imdb")
    tvdb_id = uniqueid.get("tvdb")
    trakt_id = uniqueid.get("trakt")

    return {
        "tmdb": str(tmdb_id) if tmdb_id else None,
        "imdb": str(imdb_id) if imdb_id else None,
        "tvdb": str(tvdb_id) if tvdb_id else None,
        "trakt": str(trakt_id) if trakt_id else None,
    }


def format_date(date_str: str, include_time: bool = False) -> str:
    """Reformat an ISO date/datetime into Kodi's region-configured format."""
    if not date_str:
        return ""

    try:
        if " " in date_str:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")

        if include_time:
            with _CACHE_LOCK:
                if "datetime" not in _DATE_FORMAT_CACHE:
                    date_format = xbmc.getRegion("dateshort")
                    time_format = xbmc.getRegion("time")
                    _DATE_FORMAT_CACHE["datetime"] = f"{date_format} {time_format}"
                format_str = _DATE_FORMAT_CACHE["datetime"]
            return dt.strftime(format_str)
        else:
            with _CACHE_LOCK:
                if "date" not in _DATE_FORMAT_CACHE:
                    _DATE_FORMAT_CACHE["date"] = xbmc.getRegion("dateshort")
                format_str = _DATE_FORMAT_CACHE["date"]
            return dt.strftime(format_str)
    except (ValueError, TypeError):
        return date_str
    except Exception as e:
        log("General", f"Unexpected error formatting date '{date_str}': {str(e)}", xbmc.LOGERROR)
        return date_str


_build_version: Optional[str] = None
_piers_or_later: Optional[bool] = None
_tvshow_status_gettable: Optional[bool] = None


def kodi_build_version() -> str:
    """Kodi build version string (e.g. '22.0.0'), cached; re-reads until Kodi reports one."""
    global _build_version
    if not _build_version:
        _build_version = xbmc.getInfoLabel("System.BuildVersionCode") or ""
    return _build_version


def is_kodi_piers_or_later() -> bool:
    """True on Kodi v22 (Piers, build 21.90+) or newer. Cached; build can't change mid-session."""
    global _piers_or_later
    if _piers_or_later is None:
        raw = kodi_build_version()
        if not raw:
            return False
        try:
            _piers_or_later = tuple(int(p) for p in raw.split(".")[:3]) >= (21, 90, 0)
        except ValueError:
            _piers_or_later = False
    return _piers_or_later


def tvshow_status_gettable() -> bool:
    """True if this Kodi build exposes tvshow `status` as a readable JSON-RPC field.

    `status` was write-only until xbmc/xbmc#28520; older builds return Invalid params on Get.
    """
    global _tvshow_status_gettable
    if _tvshow_status_gettable is None:
        resp = request(
            "VideoLibrary.GetTVShows",
            {"properties": ["status"], "limits": {"start": 0, "end": 1}},
        )
        _tvshow_status_gettable = resp is not None
    return _tvshow_status_gettable


def wait_for_kodi_ready(monitor: xbmc.Monitor, initial_wait: float = 0.5,
                        check_interval: float = 0.5) -> bool:
    """Poll `JSONRPC.Ping` until Kodi responds. Returns False if the monitor aborts first."""
    if monitor.waitForAbort(initial_wait):
        return False

    while not monitor.waitForAbort(check_interval):
        try:
            result = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"JSONRPC.Ping","id":1}')
            if "pong" in result.lower():
                return True
        except Exception:
            pass

    return False
