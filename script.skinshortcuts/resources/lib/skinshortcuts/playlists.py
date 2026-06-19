"""Smart playlist (.xsp) generation for source shortcuts.

Turns a Kodi source into a path-filtered library view (Movies, TV shows, Songs,
...) instead of a plain file listing: write a smart playlist, point the shortcut
at it.
"""

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


def _playlist_dir() -> str:
    """Per-skin folder for generated source playlists.

    addon_data is shared across skins, so playlists are namespaced by skin (like
    {skin}.userdata.json) to avoid name clashes and keep the folder organised.
    """
    return f"{DATA_DIR}{PLAYLISTS_SUBDIR}/{xbmc.getSkinDir()}/"

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
    """A choice in the source "Display..." dialog.

    label_id is a Kodi core string when core=True, else an add-on string.
    media_type empty = Files view (no playlist). exclude flips the path rule.
    """

    label_id: int
    core: bool
    media_type: str
    exclude: bool = False


@dataclass(frozen=True)
class SortOption:
    """A choice in the sort dialog (all labels are Kodi core strings).

    field empty = no <order> (library default); direction empty for random/default.
    """

    label_id: int
    field: str
    direction: str = ""


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
    """Expand a multipath:// source into its real component folders.

    A path rule matches real folders only; plain paths return as a single-item list.
    """
    prefix = "multipath://"
    if not path.startswith(prefix):
        return [path]
    return [unquote(part) for part in path[len(prefix):].split("/") if part]


def build_smartplaylist_xml(
    media_type: str,
    name: str,
    paths: list[str],
    *,
    exclude: bool = False,
    sort_field: str = "",
    sort_order: str = "ascending",
) -> str:
    """Build a path-filtered smart playlist as an .xsp XML string.

    paths are real folders (multipath already expanded). Include ORs startswith
    rules (match=one); exclude ANDs doesnotcontain rules (match=all). No <group>
    is written, so movie set grouping follows the user's Kodi setting.
    """
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
    """Write the .xsp to addon_data; return its special:// path for the shortcut action.

    The name is per-item, so editing a shortcut overwrites its own file instead of
    leaving an orphan.
    """
    path = _playlist_dir() + playlist_filename(menu, item)
    real = xbmcvfs.translatePath(path)
    Path(real).parent.mkdir(parents=True, exist_ok=True)
    with open(real, "w", encoding="utf-8") as f:
        f.write(xml)
    return path


def _probe_total(method: str, filt: dict) -> int:
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
    return (response.get("result") or {}).get("limits", {}).get("total", 0)


def path_has_content(media_type: str, paths: list[str], *, exclude: bool = False) -> bool:
    """Whether the library holds rows the playlist would show. Fail-fast for the picker.

    Mirrors the playlist filter: include = any path has rows; exclude = anything
    outside the path(s) remains. The path filter can match more than the playlist for
    show containers, so a populated source is never reported empty.
    """
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
    """Delete source-*.xsp files in addon_data that no current action references.

    Stable per-item names mean an edited shortcut overwrites its own file; this clears
    the files left behind when a shortcut is deleted or pointed away from a playlist.
    """
    plist_dir = _playlist_dir()
    try:
        _dirs, files = xbmcvfs.listdir(plist_dir)
    except OSError:
        return
    referenced = "\n".join(actions)
    for name in files:
        if name.startswith(FILENAME_PREFIX) and name.endswith(".xsp") and name not in referenced:
            xbmcvfs.delete(plist_dir + name)


def detect_domain(source_media: str, paths: list[str]) -> str | None:
    """The library domain a source belongs to, or None if it has no scanned content.

    A video source is configured as one content type, so the first probe with rows
    wins. None means the source is not in the library and only Files view applies.
    """
    for domain, probe_type in _DOMAIN_DETECT.get(source_media, []):
        if path_has_content(probe_type, paths):
            return domain
    return None


def display_options(source_media: str, paths: list[str]) -> list[DisplayOption]:
    """The "Display..." choices for a source: Files view, then the detected domain's
    views. Just Files view when the source is not in the library."""
    domain = detect_domain(source_media, paths)
    return [FILES_VIEW, *DOMAIN_VIEWS[domain]] if domain else [FILES_VIEW]
