"""
Per-source configuration for MetaMender.

Manages which Kodi video sources are enabled for backfill
and what metadata language to use for each.

Logging:
    Logger: 'sources'
    Key events:
        - sources.load (INFO): Source config loaded
        - sources.discover (INFO): Video sources discovered from Kodi
        - sources.save (INFO): Source config saved
        - sources.match (DEBUG): Item matched to a source
"""
from __future__ import annotations

import copy
import json
import os
from collections import Counter
from collections.abc import Iterable
from typing import Any
from urllib.parse import unquote

import xbmc

from resources.lib.providers.languages import tmdb_language
from resources.lib.utils import get_logger, log_timing

log = get_logger('sources')


_MULTIPATH = "multipath://"

# Used when Kodi does not report a usable UI language.
_FALLBACK_UI_LANGUAGE = "en-US"


def _default_config() -> dict[str, Any]:
    """Return a fresh default config (no shared mutable state). It sets no
    default_language: without one, a folder no source entry covers has no
    known language (see the scan's fill-only rule)."""
    return {"sources": []}


def _default_match() -> dict[str, Any]:
    """Return a fresh default match result: enabled, with no language."""
    return {"enabled": True}


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


def save_source_config(config_path: str, config: dict[str, Any]) -> bool:
    """Write source configuration to a JSON file, creating parent
    directories as needed. False when the file could not be written."""
    try:
        parent = os.path.dirname(config_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=2)
    except OSError:
        log.exception(
            "Failed to save source config",
            event="sources.save_fail",
            path=config_path,
        )
        return False

    log.info(
        "Source config saved",
        event="sources.save",
        path=config_path,
    )
    return True


def source_paths(path: str) -> list[str]:
    """The folders a Kodi source covers. A source with several folders is
    reported by Files.GetSources as one `multipath://` URL of URL-encoded
    folders separated by "/"; a file path never starts with it, so each
    folder needs its own sources.json entry."""
    if not path.startswith(_MULTIPATH):
        return [path]
    return [unquote(part) for part in path[len(_MULTIPATH):].split("/") if part]


def apply_folder_languages(
    config: dict[str, Any],
    discovered: list[dict[str, str]],
    default_language: str,
    fallback_language: str,
    exceptions: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    """A copy of ``config`` with the wizard's languages applied.

    ``exceptions`` maps a discovered source's path (possibly multipath) to
    (language, fallback language, "" for none). Every folder of a discovered
    source loses its language unless the source is an exception, in which
    case each of its folders gets one; `enabled: false` is kept. Entries for
    folders no discovered source names exactly (hand-written subfolders,
    removed sources) are left as they are.
    """
    out = copy.deepcopy(config)
    out["default_language"] = default_language
    if fallback_language:
        out["fallback_language"] = fallback_language
    else:
        out.pop("fallback_language", None)

    wanted: dict[str, tuple[str, str] | None] = {}
    for source in discovered:
        raw = source.get("path", "")
        for folder in source_paths(raw):
            wanted[folder] = exceptions.get(raw)

    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in out.get("sources") or []:
        path = entry.get("path", "")
        if path not in wanted:
            entries.append(entry)
            continue
        seen.add(path)
        updated = _with_languages(entry, wanted[path])
        if updated is not None:
            entries.append(updated)
    for folder, langs in wanted.items():
        if folder not in seen and langs is not None:
            new_entry = _with_languages({"path": folder}, langs)
            if new_entry is not None:
                entries.append(new_entry)
    out["sources"] = entries
    return out


def folder_exceptions(
    config: dict[str, Any], discovered: list[dict[str, str]],
) -> dict[str, tuple[str, str]]:
    """The exceptions apply_folder_languages would need to reproduce
    ``config``: a discovered source whose folders have an entry with a
    language, mapped to the first such entry's languages."""
    by_path = {e.get("path"): e for e in config.get("sources") or []}
    result: dict[str, tuple[str, str]] = {}
    for source in discovered:
        raw = source.get("path", "")
        for folder in source_paths(raw):
            entry = by_path.get(folder)
            if entry and entry.get("language"):
                result[raw] = (entry["language"], entry.get("fallback_language", ""))
                break
    return result


def _with_languages(
    entry: dict[str, Any], langs: tuple[str, str] | None,
) -> dict[str, Any] | None:
    """``entry`` with its languages set from ``langs`` (cleared when None),
    or None when nothing worth keeping is left: only a disabled flag or a
    language changes how a folder is scanned."""
    kept: dict[str, Any] = {"path": entry["path"]}
    if entry.get("enabled") is False:
        kept["enabled"] = False
    if langs is not None:
        language, fallback = langs
        kept["language"] = language
        if fallback:
            kept["fallback_language"] = fallback
    return kept if len(kept) > 1 else None


def discover_sources() -> list[dict[str, str]]:
    """Discover video sources from Kodi via JSON-RPC.

    Calls Files.GetSources with media="video" and returns a list of
    dicts with "path" and "label" keys.

    Returns:
        List of source dicts, or empty list on failure.
    """
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
    except Exception:
        log.exception(
            "Failed to discover video sources",
            event="sources.discover",
        )
        return []

    result = data.get("result", {})
    sources = result.get("sources", [])

    discovered = [
        {"path": s.get("file", ""), "label": s.get("label", "")}
        for s in sources
    ]

    log.info(
        "Video sources discovered",
        event="sources.discover",
        count=len(discovered),
    )

    return discovered


_NOT_FOLDERS = ("plugin://", "videodb://", "http://", "https://")


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


def _library_files(method: str, key: str) -> list[str]:
    query = {"jsonrpc": "2.0", "method": method,
             "params": {"properties": ["file"]}, "id": 1}
    try:
        data = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
    except Exception:
        log.exception("Failed to read library paths", event="sources.library", method=method)
        return []
    items = data.get("result", {}).get(key, [])
    return [item.get("file", "") for item in items]


def discover_folders() -> list[dict[str, str]]:
    """The folders the setup screens offer: Kodi's video sources, or, when
    Kodi lists none (a client sharing another machine's library database
    has no sources of its own), the folders derived from the library."""
    sources = discover_sources()
    if sources:
        return sources
    with log_timing(log, "library_folders"):
        folders = library_folders(
            _library_files("VideoLibrary.GetMovies", "movies"),
            _library_files("VideoLibrary.GetTVShows", "tvshows"),
        )
    log.info("Library folders derived", event="sources.library", count=len(folders))
    return folders


def library_folders_in_use(sources: list[dict[str, Any]]) -> list[str]:
    """The folders worth watching for being offline: every folder of the
    video sources (a multipath source split into its folders) that holds
    library items and that sources.json does not disable. A source without
    library items (a USB stick, a downloads folder) is left out: it being
    gone says nothing about the library."""
    files = (_library_files("VideoLibrary.GetMovies", "movies")
             + _library_files("VideoLibrary.GetTVShows", "tvshows"))
    folders: list[str] = []
    for source in discover_folders():
        for folder in source_paths(source.get("path", "")):
            if (folder and folder not in folders
                    and match_source(folder, sources).get("enabled", True)
                    and any(_path_matches(f, folder) for f in files)):
                folders.append(folder)
    return folders


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


def match_source(
    file_path: str,
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    """Match a file path to the most specific configured source.

    Uses longest-prefix matching: the source whose path is the longest
    prefix of file_path wins.

    Args:
        file_path: The Kodi file path for a library item.
        sources: List of source config dicts with at least "path" key.

    Returns:
        The matching source config dict, or a default dict with
        enabled=True and no language if no source matches.
    """
    best_match: Any = None
    best_length = 0

    for source in sources:
        source_path = source.get("path", "")
        if _path_matches(file_path, source_path) and len(source_path) > best_length:
            best_match = source
            best_length = len(source_path)

    if best_match is not None:
        log.debug(
            "Item matched to source",
            event="sources.match",
            file_path=file_path,
            source_path=best_match.get("path", ""),
            language=best_match.get("language", ""),
        )
        return best_match

    log.debug(
        "No source match, using defaults",
        event="sources.match",
        file_path=file_path,
    )
    return _default_match()
