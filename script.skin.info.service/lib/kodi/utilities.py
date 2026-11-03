"""Kodi helpers for window properties, dates, language codes and build checks."""
from __future__ import annotations

import re
import threading
import xbmc
import xbmcgui
from datetime import datetime
from typing import Any, Dict, Final, Iterable, List, Optional, Tuple
from collections import OrderedDict

from lib.kodi.settings import KodiSettings
from lib.kodi.client import ADDON, log, request
HOME = xbmcgui.Window(10000)


def resolve_infolabel(value: str) -> str:
    """Resolve a `$`-prefixed skin label on Kodi's main thread, else pass it through."""
    if value and value.startswith('$'):
        from lib.skin.labels import resolve_label
        return resolve_label(value)
    return value


WINDOW_INVALID: Final = 9999


def read_labels(labels: Iterable[str]) -> Dict[str, str]:
    """Read infolabels on Kodi's main thread in one call; '' for each one the call loses."""
    wanted = list(dict.fromkeys(labels))
    response = request('XBMC.GetInfoLabels', {'labels': wanted}) if wanted else None
    result = (response or {}).get('result') or {}
    return {label: result.get(label) or '' for label in wanted}


def focused_item(dbid: Optional[str], dbtype: Optional[str]) -> Tuple[str, str]:
    """Fill a missing id or type from the focused ListItem via the main thread; type normalized."""
    if not dbid or not dbtype:
        focused = read_labels(("ListItem.DBID", "ListItem.DBType"))
        dbid = dbid or focused["ListItem.DBID"]
        dbtype = dbtype or focused["ListItem.DBType"]
    return dbid or "", normalize_dbtype(dbtype)


def read_conditions(conditions: Iterable[str]) -> Dict[str, bool]:
    """Read conditions on Kodi's main thread in one call; False for each one the call loses."""
    wanted = list(dict.fromkeys(conditions))
    response = request('XBMC.GetInfoBooleans', {'booleans': wanted}) if wanted else None
    result = (response or {}).get('result') or {}
    return {condition: bool(result.get(condition)) for condition in wanted}


class LabelSnapshot:
    """Infolabels read on Kodi's main thread a batch at a time, then served from memory."""

    def __init__(self, labels: Iterable[str]) -> None:
        self._values = read_labels(labels)

    def read(self, labels: Iterable[str]) -> None:
        """Read the labels not yet held, in one call."""
        missing = [label for label in labels if label not in self._values]
        if missing:
            self._values.update(read_labels(missing))

    def get(self, label: str) -> str:
        """Get a label's value, reading it alone when no batch held it."""
        if label not in self._values:
            self.read((label,))
        return self._values[label]

    def skin_bool(self, setting: str) -> bool:
        """True when a skin bool is set, read through its `skin_bool_label` in the batch."""
        return self.get(skin_bool_label(setting)) != ""


def modal_dialog_active() -> bool:
    """True while a modal dialog is on top, when ListItem.* answers from the dialog's own list."""
    return xbmcgui.getCurrentWindowDialogId() != WINDOW_INVALID


def parse_pipe_list(value: str, separator: str = '|') -> list:
    """Split a separator-delimited string into a stripped, non-empty list."""
    if not value:
        return []
    return [item.strip() for item in value.split(separator) if item.strip()]


def int_param(params: dict, name: str, default: int) -> int:
    """Read an integer plugin argument, falling back when it is missing or unparseable."""
    try:
        return int(params.get(name, [str(default)])[0])
    except (ValueError, TypeError):
        return default


_CACHE_LOCK = threading.RLock()

_PREV_PROPS: OrderedDict[str, str] = OrderedDict()
_PREV_PROPS_MAX_SIZE: Final = 500

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
DEFAULT_LANGUAGE: Final = 'en'

# Kodi's join separator for multi-value strings such as genres and cast
MULTI_VALUE_SEP: Final = " / "


_MEDIA_TYPE_LABELS: Final = {
    'movie': 342, 'tvshow': 20343, 'season': 33054, 'episode': 20360,
    'musicvideo': 20389, 'set': 20434, 'artist': 133, 'album': 132,
}


def media_type_label(media_type: str) -> str:
    """Get Kodi's own translated name for a library section, the raw type when it has none."""
    string_id = _MEDIA_TYPE_LABELS.get(media_type)
    return xbmc.getLocalizedString(string_id) if string_id else media_type


def join_multi(items: Optional[List[Any]], separator: str = MULTI_VALUE_SEP) -> str:
    """Join a list into a Kodi-style multi-value string, dropping falsy entries."""
    if not items:
        return ""
    return separator.join(str(i) for i in items if i)


_CERT_RATED = re.compile(r'^rated\s*:?\s*', re.IGNORECASE)
_CERT_COUNTRY = re.compile(r'^([A-Za-z ]{1,20})[:/](.*)$')
_CERT_COUNTRY_ALIAS = {
    'USA': 'US', 'UNITED KINGDOM': 'UK', 'DENMARK': 'DK', 'GERMANY': 'DE', 'FRANCE': 'FR',
    'BRAZIL': 'BR', 'AUSTRALIA': 'AU', 'NETHERLANDS': 'NL', 'GREECE': 'GR',
}


def normalize_dbtype(value: Optional[str]) -> str:
    """Normalize a media type to lowercase; Kodi stores what an add-on set, verbatim."""
    return (value or "").lower()


_VALID_SORT_METHODS = frozenset((
    "none", "label", "date", "size", "file", "path", "drivetype", "title", "track",
    "time", "artist", "album", "albumtype", "genre", "country", "year", "rating",
    "userrating", "votes", "top250", "programcount", "playlist", "episode", "season",
    "totalepisodes", "watchedepisodes", "tvshowstatus", "tvshowtitle", "sorttitle",
    "productioncode", "mpaa", "studio", "dateadded", "lastplayed", "playcount",
    "listeners", "bitrate", "random", "totaldiscs", "originaldate", "bpm", "originaltitle",
))


def validate_sort_method(method: str, fallback: str) -> str:
    """Return the sort method if Kodi's JSON-RPC accepts it, else the fallback."""
    return method if method in _VALID_SORT_METHODS else fallback


def normalize_certificate(value: Optional[str]) -> Tuple[str, str]:
    """Normalize a certificate to `(country, rating)` for comparison, so `NL:16` != `GR:16`."""
    text = _CERT_RATED.sub('', (value or '').strip()).strip().upper()
    if not text:
        return '', ''

    match = _CERT_COUNTRY.match(text)
    if not match:
        return '', ' '.join(text.split())

    country = ' '.join(match.group(1).split())
    return _CERT_COUNTRY_ALIAS.get(country, country), ' '.join(match.group(2).lstrip('-').split())


def normalize_language_tag(value: Optional[str]) -> str:
    """Normalize to lowercase ISO 639-1, emptying placeholders like `xx`; `cz` becomes `cs`."""
    normalized = (value or '').strip().lower()

    if normalized in ('00', 'null', 'none', 'xx', 'n/a'):
        return ''

    country_to_language_map = {
        'cz': 'cs',
    }

    return country_to_language_map.get(normalized, normalized)


def get_preferred_language_code() -> str:
    """Return the preferred language code, stored as a code or a list index; English when unset."""
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
    """Set a home-window property, skipping the write when this process last set the same value."""
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


def set_window_prop(key: str, value: object, window: str = 'home') -> None:
    """Set a property on a named window, keeping any commas and brackets in the value."""
    if window.lower() in ('home', '10000'):
        HOME.setProperty(key, str(value))
        return
    escaped = str(value).replace('\\', '\\\\').replace('"', '\\"')
    xbmc.executebuiltin(f'SetProperty({key},"{escaped}",{window})')


def clear_window_prop(key: str, window: str = 'home') -> None:
    """Clear a property on a named window."""
    if window.lower() in ('home', '10000'):
        clear_prop(key)
        return
    xbmc.executebuiltin(f'ClearProperty({key},{window})')


def clear_prop(key: str) -> None:
    """Clear a single home-window property."""
    with _CACHE_LOCK:
        _PREV_PROPS.pop(key, None)
    HOME.clearProperty(key)


def clear_group(prefix: str) -> None:
    """Clear all tracked home-window properties under a key prefix."""
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
    """Return `{tmdb, imdb, tvdb, trakt}` from a Kodi item's `uniqueid` only, as strings or None."""
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


def setting_float(key: str) -> float:
    """Read a numeric addon setting uncached, treating unset or unparseable as 0.0."""
    stored = ADDON.getSetting(key)
    if stored:
        try:
            return float(stored)
        except (ValueError, TypeError):
            pass
    return 0.0


def format_date(date_str: str, include_time: bool = False) -> str:
    """Reformat an ISO date/datetime into Kodi's region-configured format."""
    if not date_str:
        return ""

    from datetime import datetime
    try:
        dt = datetime.fromisoformat(date_str)

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


_NAME_TOKEN: Final = re.compile(r'(%[AaBb])')


def format_region_date(when: datetime, region: str) -> str:
    """Format a datetime in a Kodi region format, its day and month names in Kodi's language."""
    names = {
        '%A': 11 + when.weekday(), '%a': 41 + when.weekday(),
        '%B': 20 + when.month, '%b': 50 + when.month,
    }
    return ''.join(
        xbmc.getLocalizedString(names[part]) if part in names else when.strftime(part)
        for part in _NAME_TOKEN.split(xbmc.getRegion(region)) if part
    )


_TIME_TOKEN: Final = re.compile(r"'[^']*'|h+|H+|m+|.?s+|x+")


def format_region_time(when: datetime) -> str:
    """Format a time as Kodi's clock shows it: the region time format, seconds left out."""
    hour12 = when.hour % 12 or 12
    meridiem = xbmc.getRegion('meridiem').split('/')

    def part(match) -> str:
        token = match.group(0)
        if token.startswith("'"):
            return token[1:-1]
        if token[0] in 'hH':
            hour = hour12 if token[0] == 'h' else when.hour
            return str(hour) if len(token) == 1 else f'{hour:02}'
        if token[0] == 'm':
            return str(when.minute) if len(token) == 1 else f'{when.minute:02}'
        if token[0] == 'x':
            return meridiem[when.hour > 11] if len(meridiem) == 2 else ''
        return ''

    return _TIME_TOKEN.sub(part, xbmc.getRegion('timeraw'))


_build_version: Optional[str] = None
_piers_or_later: Optional[bool] = None
_tvshow_status_gettable: Optional[bool] = None


def kodi_build_version() -> str:
    """Kodi build version string (e.g. '22.0.0'), cached; re-reads until Kodi reports one."""
    global _build_version
    if not _build_version:
        _build_version = xbmc.getInfoLabel("System.BuildVersionCode") or ""
    return _build_version


def skin_bool_label(setting: str) -> str:
    """Infolabel that reads a set skin bool as a localized `True`, an unset one as empty."""
    return f"Skin.HasSetting({setting})"


def skin_bool(setting: str) -> bool:
    """True when a skin bool is set, read alone under the GUI lock."""
    return xbmc.getCondVisibility(skin_bool_label(setting))


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


def tvshow_version_fields() -> List[str]:
    """TV show fields only Kodi v22 or newer can read over JSON-RPC; empty on older builds."""
    return ["trailer"] if is_kodi_piers_or_later() else []


def tvshow_status_gettable() -> bool:
    """True if this Kodi build can read tvshow `status` over JSON-RPC; older builds reject it."""
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
