"""Smart playlist (.xsp) generation, turning a source shortcut into a library view."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote
from xml.sax.saxutils import escape

import xbmc
import xbmcvfs

from .log import get_logger

log = get_logger("playlists")

DATA_DIR = "special://profile/addon_data/script.skinshortcuts/"
PLAYLISTS_SUBDIR = "playlists"
FILENAME_PREFIX = "source-"
DEFAULT_PLAYLISTS_PATH = "special://profile/playlists/"


def _playlist_dir() -> str:
    """Per-skin folder for generated source playlists; addon_data itself is shared."""
    return f"{DATA_DIR}{PLAYLISTS_SUBDIR}/{xbmc.getSkinDir()}/"


def playlists_base_path() -> str:
    """Folder Kodi keeps the user's playlists in, trailing slash included."""
    request = {
        "jsonrpc": "2.0",
        "method": "Settings.GetSettingValue",
        "params": {"setting": "system.playlistspath"},
        "id": 1,
    }
    try:
        response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    except (ValueError, TypeError):
        return DEFAULT_PLAYLISTS_PATH
    if "error" in response:
        log.warning(f"JSON-RPC error for {request['method']}: {response['error']}")
    base = (response.get("result") or {}).get("value") or ""
    if not base:
        return DEFAULT_PLAYLISTS_PATH
    return base if base.endswith("/") else f"{base}/"

_PROBE_METHODS: dict[str, str] = {
    "movies": "VideoLibrary.GetMovies",
    "tvshows": "VideoLibrary.GetTVShows",
    "episodes": "VideoLibrary.GetEpisodes",
    "musicvideos": "VideoLibrary.GetMusicVideos",
    "albums": "AudioLibrary.GetAlbums",
    "songs": "AudioLibrary.GetSongs",
    "artists": "AudioLibrary.GetArtists",
}

@dataclass(frozen=True)
class DisplayOption:
    """A choice in the source "Display..." dialog."""

    label_id: int
    core: bool  # label_id is a Kodi core string, else an add-on one
    media_type: str  # empty = Files view, no playlist
    exclude: bool = False  # flips the path rule


@dataclass(frozen=True)
class SortOption:
    """A choice in the sort dialog, all labels being Kodi core strings."""

    label_id: int
    field: str  # empty = no <order>, so the library default
    direction: str = ""  # empty for random or default


FILES_VIEW = DisplayOption(32079, False, "")

# Episodes is a second view of a tvshows source; Songs/Albums/Artists are views of a
# music source, which has no single configured content type.
DOMAIN_VIEWS: dict[str, list[DisplayOption]] = {
    "movies": [
        DisplayOption(32015, False, "movies"),
        DisplayOption(32081, False, "movies", exclude=True),
    ],
    "tvshows": [
        DisplayOption(32016, False, "tvshows"),
        DisplayOption(20360, True, "episodes"),
        DisplayOption(32082, False, "tvshows", exclude=True),
        DisplayOption(32204, False, "episodes", exclude=True),
    ],
    "musicvideos": [
        DisplayOption(32018, False, "musicvideos"),
        DisplayOption(32083, False, "musicvideos", exclude=True),
    ],
    "music": [
        DisplayOption(134, True, "songs"),
        DisplayOption(132, True, "albums"),
        DisplayOption(133, True, "artists"),
        DisplayOption(32084, False, "songs", exclude=True),
        DisplayOption(32085, False, "albums", exclude=True),
        DisplayOption(32206, False, "artists", exclude=True),
    ],
}

# source media -> [(domain, library type to probe)]. A video source is one content type,
# so the first probe with rows wins; music is one domain probed via songs (albums and
# artists derive from them).
_DOMAIN_DETECT: dict[str, list[tuple[str, str]]] = {
    "video": [("movies", "movies"), ("tvshows", "tvshows"), ("musicvideos", "musicvideos")],
    "music": [("music", "songs")],
}

SORT_OPTIONS: list[SortOption] = [
    SortOption(571, ""),
    SortOption(556, "title", "ascending"),
    SortOption(562, "year", "descending"),
    SortOption(570, "dateadded", "descending"),
    SortOption(590, "random"),
]


def unpack_multipath(path: str) -> list[str]:
    """Expand a multipath:// source into the real folders a path rule can match."""
    prefix = "multipath://"
    if not path.startswith(prefix):
        return [path]
    return [unquote(part) for part in path[len(prefix):].split("/") if part]


def parse_smart_playlist(path: str) -> tuple[str, str]:
    """Parse a smart playlist (.xsp file) for name and type; empty strings when unreadable."""
    import xml.etree.ElementTree as ET

    try:
        f = xbmcvfs.File(path)
        try:
            content = f.read()
        finally:
            f.close()
        root = ET.fromstring(content)
    except Exception as e:
        log.debug(f"Unreadable playlist {path}: {e}")
        return "", ""
    return root.findtext("name") or "", root.get("type") or ""


def build_smartplaylist_xml(
    media_type: str,
    name: str,
    paths: list[str],
    *,
    exclude: bool = False,
    sort_field: str = "",
    sort_order: str = "ascending",
) -> str:
    """Build a path-filtered smart playlist as an .xsp XML string, over real folders."""
    # no <group> written, so movie set grouping follows the user's Kodi setting
    operator = "doesnotcontain" if exclude else "startswith"
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<smartplaylist type="{media_type}">',
        f"\t<name>{escape(name)}</name>",
        f"\t<match>{'all' if exclude else 'one'}</match>",
    ]
    for path in paths:
        lines.append(f'\t<rule field="path" operator="{operator}">')
        lines.append(f"\t\t<value>{escape(path)}</value>")
        lines.append("\t</rule>")
    if sort_field == "random":
        lines.append("\t<order>random</order>")
    elif sort_field:
        lines.append(f'\t<order direction="{sort_order}">{sort_field}</order>')
    lines.append("</smartplaylist>")
    return "\n".join(lines) + "\n"


def playlist_filename(menu: str, item: str) -> str:
    """Stable per-item .xsp filename; non-word chars collapsed so it stays path-safe."""
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", f"{menu}-{item}")
    return f"{FILENAME_PREFIX}{safe}.xsp"


def save_playlist(menu: str, item: str, xml: str) -> str:
    """Save the .xsp to addon_data, returning the special:// path a shortcut action takes."""
    path = _playlist_dir() + playlist_filename(menu, item)
    real = xbmcvfs.translatePath(path)
    Path(real).parent.mkdir(parents=True, exist_ok=True)
    with open(real, "w", encoding="utf-8") as f:
        f.write(xml)
    return path


def _probe_total(method: str, filt: dict) -> int:
    """Rows a filtered library query would return; 0 if the query fails."""
    request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": {"filter": filt, "limits": {"end": 1}},
        "id": 1,
    }
    try:
        response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    except (ValueError, TypeError):
        return 0
    if "error" in response:
        log.warning(f"JSON-RPC error for {method}: {response['error']}")
    return (response.get("result") or {}).get("limits", {}).get("total", 0)


def path_has_content(media_type: str, paths: list[str], *, exclude: bool = False) -> bool:
    """Whether the library holds rows the playlist would show, as a fail-fast for the picker."""
    # filter can match wider than the playlist, so a populated source never reads as empty
    method = _PROBE_METHODS.get(media_type)
    if not method:
        return False
    if exclude:
        rules = [{"field": "path", "operator": "doesnotcontain", "value": p} for p in paths]
        filt: dict = rules[0] if len(rules) == 1 else {"and": rules}
        return _probe_total(method, filt) > 0
    return any(
        _probe_total(method, {"field": "path", "operator": "startswith", "value": p}) > 0
        for p in paths
    )


def cleanup_orphan_playlists(actions: list[str]) -> None:
    """Delete source-*.xsp files in addon_data that no current action references."""
    plist_dir = _playlist_dir()
    try:
        _, files = xbmcvfs.listdir(plist_dir)
    except OSError:
        return
    referenced = "\n".join(actions)
    for name in files:
        if name.startswith(FILENAME_PREFIX) and name.endswith(".xsp") and name not in referenced:
            xbmcvfs.delete(plist_dir + name)


def detect_domain(source_media: str, paths: list[str]) -> str | None:
    """The library domain a source belongs to, or None when it has no scanned content."""
    for domain, probe_type in _DOMAIN_DETECT.get(source_media, []):
        if path_has_content(probe_type, paths):
            return domain
    return None


def display_options(source_media: str, paths: list[str]) -> list[DisplayOption]:
    """The "Display..." choices for a source: Files view, then any detected domain's views."""
    domain = detect_domain(source_media, paths)
    return [FILES_VIEW, *DOMAIN_VIEWS[domain]] if domain else [FILES_VIEW]
