"""
Kodi's video sources and the folders they cover, and the 1.1 sources.json
(per-folder languages) that the conversion to libraries reads.

Logging:
    Logger: 'sources'
    Key events:
        - sources.load (INFO): Source config loaded
        - sources.discover (INFO): Video sources discovered from Kodi
        - sources.content (ERROR): a library's content type could not be read
"""
from __future__ import annotations

import json
import os
from collections import Counter
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote

import xbmc

from resources.lib.providers.languages import tmdb_language
from resources.lib.utils import get_logger, log_timing

if TYPE_CHECKING:
    from resources.lib.data.libraries import LibraryConfig

log = get_logger('sources')


_MULTIPATH = "multipath://"

# Used when Kodi does not report a usable UI language.
_FALLBACK_UI_LANGUAGE = "en-US"


def _default_config() -> dict[str, Any]:
    """Return a fresh default config (no shared mutable state). It sets no
    default_language: without one, a folder no source entry covers has no
    known language (see the scan's fill-only rule)."""
    return {"sources": []}


def kodi_ui_language() -> str:
    """Kodi's interface language with its region (e.g. "nl-NL"), the best
    guess for a folder whose language is not configured. Kodi answers "en-"
    when no region is set, so a missing region becomes TMDB's primary one
    for the language. "en-US" when Kodi reports nothing usable."""
    try:
        code = xbmc.getLanguage(xbmc.ISO_639_1, region=True)
    except Exception:
        log.exception("Failed to read Kodi's UI language", event="sources.ui_language")
        return _FALLBACK_UI_LANGUAGE
    if not isinstance(code, str) or not code.strip():
        return _FALLBACK_UI_LANGUAGE
    return tmdb_language(code) or _FALLBACK_UI_LANGUAGE


def load_source_config(config_path: str) -> dict[str, Any]:
    """Load source configuration from a JSON file.

    Args:
        config_path: Absolute path to the sources.json file.

    Returns:
        The parsed config dict. If the file does not exist or cannot
        be read, returns a default config with an empty sources list and
        no default language.
    """
    if not os.path.exists(config_path):
        log.info(
            "No source config found, using defaults",
            event="sources.load",
            path=config_path,
        )
        return _default_config()

    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            config = json.load(fh)
    except (json.JSONDecodeError, IOError, OSError):
        log.exception(
            "Failed to read source config, using defaults",
            event="sources.load",
            path=config_path,
        )
        return _default_config()

    log.info(
        "Source config loaded",
        event="sources.load",
        path=config_path,
        source_count=len(config.get("sources", [])),
    )
    return config


def source_paths(path: str) -> list[str]:
    """The folders a Kodi source covers. A source with several folders is
    reported by Files.GetSources as one `multipath://` URL of URL-encoded
    folders separated by "/"; a file path never starts with it, so each
    folder needs its own sources.json entry."""
    if not path.startswith(_MULTIPATH):
        return [path]
    return [unquote(part) for part in path[len(_MULTIPATH):].split("/") if part]


# Paths that are no folder of files: nothing in the library lies under them.
_NOT_FOLDERS = ("addons://", "plugin://", "videodb://", "http://", "https://")


def discover_sources() -> list[dict[str, str]] | None:
    """Kodi's video sources ("path" and "label" each), from
    Files.GetSources, without the ones that are no folder: Kodi 22 lists
    its Video add-ons node there even when the user has no sources. []
    when Kodi has none; None when the query failed, which must not be
    taken for "no sources": the caller would then fall back to
    library-derived folders and store them as libraries."""
    query = {
        "jsonrpc": "2.0",
        "method": "Files.GetSources",
        "params": {"media": "video"},
        "id": 1,
    }

    try:
        with log_timing(log, "discover_sources"):
            raw = xbmc.executeJSONRPC(json.dumps(query))
            data = json.loads(raw)
        sources = data["result"].get("sources", [])
        discovered = [
            {"path": s.get("file", ""), "label": s.get("label", "")}
            for s in sources
            if not s.get("file", "").startswith(_NOT_FOLDERS)
        ]
    except Exception:
        log.exception(
            "Failed to discover video sources",
            event="sources.discover",
        )
        return None

    log.info(
        "Video sources discovered",
        event="sources.discover",
        count=len(discovered),
    )

    return discovered


def _parent(path: str) -> str | None:
    """The folder holding ``path`` (a file, or a folder with or without its
    trailing separator), ending in that folder's own separator, or None
    when there is none. Kodi paths use "/" or, on Windows, "\\"."""
    stripped = path.rstrip("/\\")
    cut = max(stripped.rfind("/"), stripped.rfind("\\"))
    return stripped[:cut + 1] if cut > 0 else None


def _folder_label(path: str) -> str:
    """The last two parts of a folder path, e.g. "TVSeries/EN": enough to
    tell library folders apart without the server name."""
    bare = path.split("://", 1)[-1]
    parts = [p for p in bare.replace("\\", "/").split("/") if p]
    return "/".join(parts[-2:])


def library_folders(
    movie_files: Iterable[str], show_folders: Iterable[str],
) -> list[dict[str, str]]:
    """The library's top folders, derived from item paths, in the shape of
    ``discover_sources``: a show's folder sits in a library folder; a movie
    file sits in a library folder when other movies share its folder, else
    in a folder of its own one level down. Folders inside another listed
    folder are dropped, since a source entry covers everything below it."""
    movie_dirs: Counter[str] = Counter()
    for file in movie_files:
        if file.startswith("stack://"):
            file = file[len("stack://"):].split(" , ")[0]
        if file and not file.startswith(_NOT_FOLDERS):
            folder = _parent(file)
            if folder:
                movie_dirs[folder] += 1
    roots = set()
    for folder, count in movie_dirs.items():
        root = folder if count > 1 else _parent(folder)
        if root:
            roots.add(root)
    for show in show_folders:
        if show and not show.startswith(_NOT_FOLDERS):
            root = _parent(show)
            if root:
                roots.add(root)
    top = sorted(r for r in roots if not any(o != r and r.startswith(o) for o in roots))
    return [{"path": r, "label": _folder_label(r)} for r in top]


def _query_library_files(method: str, key: str) -> list[str] | None:
    """The file of every item ``method`` lists; None when the query failed."""
    query = {"jsonrpc": "2.0", "method": method,
             "params": {"properties": ["file"]}, "id": 1}
    try:
        data = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
        items = data["result"].get(key, [])
        return [item.get("file", "") for item in items]
    except Exception:
        log.exception("Failed to read library paths", event="sources.library", method=method)
        return None


def _library_files(method: str, key: str) -> list[str]:
    return _query_library_files(method, key) or []


def discover_folders() -> list[dict[str, str]] | None:
    """The folders the setup screens offer: Kodi's video sources, or, when
    Kodi lists none (a client sharing another machine's library database
    has no sources of its own), the folders derived from the library.
    None when a query failed: what was found then is incomplete and must
    not be stored."""
    sources = discover_sources()
    if sources is None:
        return None
    if sources:
        return sources
    with log_timing(log, "library_folders"):
        movies = _query_library_files("VideoLibrary.GetMovies", "movies")
        shows = _query_library_files("VideoLibrary.GetTVShows", "tvshows")
        if movies is None or shows is None:
            return None
        folders = library_folders(movies, shows)
    log.info("Library folders derived", event="sources.library", count=len(folders))
    return folders


def library_folders_in_use(libraries: LibraryConfig) -> list[str]:
    """The folders worth watching for being offline: every folder of the
    included libraries (a multipath library split into its folders) that
    holds library items and is not an excluded subfolder. A library without
    library items (a USB stick, a downloads folder) is left out: it being
    gone says nothing about the library."""
    files = (_library_files("VideoLibrary.GetMovies", "movies")
             + _library_files("VideoLibrary.GetTVShows", "tvshows"))
    folders: list[str] = []
    for lib in libraries.libraries:
        if not lib.included:
            continue
        for folder in source_paths(lib.path):
            if (folder and folder not in folders
                    and libraries.folder_settings(folder, lib)[0]
                    and any(_path_matches(f, folder) for f in files)):
                folders.append(folder)
    return folders


# What a library holds, as library_content tells it.
CONTENT_MOVIES = "movies"
CONTENT_TVSHOWS = "tvshows"
CONTENT_MIXED = "mixed"
CONTENT_UNKNOWN = ""


def _has_items_under(method: str, folder: str) -> bool | None:
    """Whether ``method`` lists any item under ``folder``; None when the
    query failed. Kodi's source and derived folders end in a separator,
    so "startswith" stays on a folder boundary."""
    query = {"jsonrpc": "2.0", "method": method, "id": 1, "params": {
        "filter": {"field": "path", "operator": "startswith", "value": folder},
        "limits": {"end": 1}}}
    try:
        data = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
        return int(data["result"]["limits"]["total"]) > 0
    except Exception:
        log.exception("Failed to read a library's content", event="sources.content",
                      method=method)
        return None


def library_content(path: str) -> str:
    """Whether the library at ``path`` holds movies, TV shows, both, or
    nothing Kodi has scanned yet (CONTENT_UNKNOWN, also when a query
    failed). Kodi keeps each source's content type in its video database
    but offers it to add-ons through neither JSON-RPC nor Python, so the
    items under the library's folders stand in for it."""
    found = set()
    for folder in source_paths(path):
        if not folder:
            continue
        for method, content in (("VideoLibrary.GetMovies", CONTENT_MOVIES),
                                ("VideoLibrary.GetTVShows", CONTENT_TVSHOWS)):
            has = _has_items_under(method, folder)
            if has is None:
                return CONTENT_UNKNOWN
            if has:
                found.add(content)
    if len(found) > 1:
        return CONTENT_MIXED
    return found.pop() if found else CONTENT_UNKNOWN


def _path_matches(file_path: str, source_path: str) -> bool:
    """Whether file_path lies under source_path, on a path boundary.

    A plain ``startswith`` would let source ``/media/movies`` match
    ``/media/movies_extra/...``. Require either an exact match or that the
    character after the prefix is a separator (either "/" or "\\", since Kodi
    paths may be POSIX, Windows, smb://, or nfs://).
    """
    if not source_path:
        return False
    if file_path == source_path:
        return True
    if not file_path.startswith(source_path):
        return False
    return source_path[-1] in "/\\" or file_path[len(source_path)] in "/\\"
