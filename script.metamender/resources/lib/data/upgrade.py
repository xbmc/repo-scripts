"""
Conversion of 1.1 global settings to per-library settings.

The pure parts live here; the service reads Kodi's settings file, writes
sources.json and only then removes the moved ids from Kodi's settings.

Logging:
    Logger: 'upgrade'
    Key events:
        - upgrade.copy_written (INFO): the moved settings were saved aside
        - upgrade.copy_fail (ERROR): the safe copy could not be written
        - upgrade.copy_unreadable (WARNING): the safe copy is damaged and is
          treated as absent
        - upgrade.dropped_entry (WARNING): an old source entry matches no library
"""
from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET
from typing import Any, Optional

from resources.lib.data.libraries import (
    FIELD_TOGGLES,
    Library,
    LibraryConfig,
    library_from_legacy_settings,
)
from resources.lib.data.presets import country_for_setting
from resources.lib.data.sources import _path_matches, source_paths
from resources.lib.utils import get_logger

log = get_logger('upgrade')

COPY_FILE_NAME = "legacy-settings.json"

MOVED_IDS: tuple[str, ...] = (
    "rating_source", "text_source_order", "fallback_order",
    "enable_ratings", "enable_plots", "enable_episode_titles",
    "enable_main_titles", "enable_certifications", "enable_credits",
    "enable_trailers", "enable_taglines", "enable_details",
    "country", "override_prefix", "rating_prefix", "replace_incorrect",
    "enable_fallback", "fallback_rating",
)

# The 1.1 defaults, used for an id Kodi did not write to the settings file.
_DEFAULT_TEXT = {"rating_prefix": "", "fallback_rating": "NR"}
_DEFAULT_INT = {"rating_source": 4, "text_source_order": 2, "fallback_order": 0, "country": 0}
_DEFAULT_BOOL = {
    "enable_ratings": True, "enable_plots": True, "enable_episode_titles": False,
    "enable_main_titles": False, "enable_certifications": True,
    "enable_credits": False, "enable_trailers": False, "enable_taglines": False,
    "enable_details": False, "override_prefix": False, "replace_incorrect": True,
    "enable_fallback": False,
    # Toggles 1.1 never had: absent from its settings, so they convert as off.
    "enable_posters": False, "enable_episode_thumbs": False,
    "enable_fanart": False, "enable_other_art": False, "enable_movie_sets": False,
}


def read_user_settings(path: str) -> dict[str, str]:
    """Setting id to text from Kodi's userdata settings.xml; {} when the
    file is missing or unreadable."""
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return {}
    return {
        str(node.get("id")): node.text or ""
        for node in root.iter("setting") if node.get("id")
    }


def _read_copy(copy_path: str) -> Optional[dict[str, str]]:
    """The saved copy; None when there is none or it cannot be read (a
    damaged copy is then replaced from Kodi's file, if that still has the
    ids)."""
    try:
        with open(copy_path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        log.warning("Settings copy unreadable", event="upgrade.copy_unreadable",
                    path=copy_path)
        return None
    if not isinstance(raw, dict):
        log.warning("Settings copy unreadable", event="upgrade.copy_unreadable",
                    path=copy_path)
        return None
    return {str(k): str(v) for k, v in raw.items()}


def ensure_copy(user_settings_path: str, copy_path: str) -> Optional[dict[str, str]]:
    """The moved settings, kept in a file of our own. An existing copy wins:
    after a partial run Kodi's file may already lack the ids. None when
    neither source has any moved id (a fresh install, or Kodi dropped the
    ids before a copy was made) or the copy cannot be written (the old
    settings then stay where they are).

    The copy is written beside its place and swapped in, so a copy that
    exists is always whole."""
    existing = _read_copy(copy_path)
    if existing is not None:
        return existing
    user = read_user_settings(user_settings_path)
    moved = {key: user[key] for key in MOVED_IDS if key in user}
    if not moved:
        return None
    temp = copy_path + ".tmp"
    try:
        parent = os.path.dirname(copy_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(temp, "w", encoding="utf-8") as fh:
            json.dump(moved, fh, indent=2)
        os.replace(temp, copy_path)
    except OSError:
        log.exception("Failed to write the settings copy", event="upgrade.copy_fail",
                      path=copy_path)
        try:
            os.remove(temp)
        except OSError:
            pass
        return None
    log.info("Settings copy written", event="upgrade.copy_written", path=copy_path,
             setting_count=len(moved))
    return moved


def _int(legacy: dict[str, str], key: str) -> int:
    try:
        return int(float(legacy[key]))
    except (KeyError, ValueError, TypeError):
        return _DEFAULT_INT[key]


def _bool(legacy: dict[str, str], key: str) -> bool:
    if key not in legacy:
        return _DEFAULT_BOOL[key]
    return legacy[key] == "true"


def _text(legacy: dict[str, str], key: str) -> str:
    return legacy.get(key, _DEFAULT_TEXT[key])


def _scan_shaped(legacy: dict[str, str], ui_language: str) -> dict[str, Any]:
    """The 1.1 values in the shape daemon._load_settings produced, so the
    mapping to a library is the one the scan adapter uses."""
    enabled: set[str] = set()
    for name, field_names in FIELD_TOGGLES.items():
        if _bool(legacy, "enable_" + name):
            enabled.update(field_names)
    return {
        "enabled_fields": frozenset(enabled),
        "rating_source": _int(legacy, "rating_source"),
        "text_source_order": _int(legacy, "text_source_order"),
        "fallback_order": _int(legacy, "fallback_order"),
        "cert_country": country_for_setting(_int(legacy, "country"), ui_language),
        "cert_prefix_override": (
            _text(legacy, "rating_prefix") if _bool(legacy, "override_prefix") else None
        ),
        "cert_replace_foreign": _bool(legacy, "replace_incorrect"),
        "cert_not_found": (
            _text(legacy, "fallback_rating").strip() or None
            if _bool(legacy, "enable_fallback") else None
        ),
    }


def _norm(path: str) -> str:
    return path.rstrip("/\\")


def _folders(path: str) -> list[str]:
    return [_norm(f) for f in source_paths(path)]


def _owner(entry_path: str, discovered: list[dict[str, str]]) -> tuple[Optional[int], bool]:
    """(index of the library the old entry belongs to, whether the entry is
    one of that library's own folders). An exact folder match beats
    containment; among containing folders the longest wins."""
    target = _norm(entry_path)
    for i, src in enumerate(discovered):
        if target in _folders(src["path"]):
            return i, True
    best: Optional[int] = None
    best_len = -1
    for i, src in enumerate(discovered):
        for folder in _folders(src["path"]):
            if _path_matches(target, folder) and len(folder) > best_len:
                best, best_len = i, len(folder)
    return best, False


def _inherited_entries(entries: list[dict[str, Any]],
                       discovered: list[dict[str, str]]) -> tuple[list[dict[str, Any]], set[int]]:
    """An entry of its own for every library folder that has none but lies
    inside a 1.1 entry, taken from the longest such entry, as 1.1 matched a
    file to the longest configured prefix. Also the ids of the entries used
    that way."""
    exact = {_norm(str(e["path"])) for e in entries}
    inherited: list[dict[str, Any]] = []
    used: set[int] = set()
    for src in discovered:
        for folder in source_paths(src["path"]):
            target = _norm(folder)
            if target in exact:
                continue
            parent: Optional[dict[str, Any]] = None
            for entry in entries:
                path = _norm(str(entry["path"]))
                if (_path_matches(target, path)
                        and (parent is None or len(path) > len(_norm(str(parent["path"]))))):
                    parent = entry
            if parent is not None:
                inherited.append({**parent, "path": folder})
                used.add(id(parent))
    return inherited, used


def convert(legacy: Optional[dict[str, str]], old_sources: dict[str, Any],
            discovered: list[dict[str, str]], ui_language: str) -> LibraryConfig:
    """One library per discovered source, each carrying the 1.1 global
    settings. A library the old config disabled is left out but keeps them.
    Hand-written entries inside a library's folder survive as subfolders,
    and an entry above a library's folder gives it that entry's language
    and enabled state.

    ``legacy`` None means the 1.1 values are lost (Kodi dropped the ids
    before a copy was made): the libraries are then set up as 1.1 scanned
    them, with their languages, but with nothing switched on, since
    guessing the 1.1 defaults could start writing what the user had off."""
    settings = None if legacy is None else _scan_shaped(legacy, ui_language)
    default_language = str(old_sources.get("default_language") or ui_language)
    default_fallback = str(old_sources.get("fallback_language") or "")

    entries = [e for e in old_sources.get("sources") or [] if str(e.get("path") or "")]
    inherited, used = _inherited_entries(entries, discovered)

    own: dict[int, dict[str, Any]] = {}
    subs: dict[int, list[dict[str, Any]]] = {i: [] for i in range(len(discovered))}
    folder_entries: dict[int, list[dict[str, Any]]] = {}
    for entry in entries + inherited:
        path = str(entry["path"])
        idx, is_own = _owner(path, discovered)
        if idx is None:
            if id(entry) not in used:
                log.warning("Old source entry matches no library",
                            event="upgrade.dropped_entry", path=path)
        elif is_own and len(_folders(discovered[idx]["path"])) == 1:
            own.setdefault(idx, entry)
        else:
            sub = dict(entry)
            if sub.get("language") and "fallback_language" not in sub:
                sub["fallback_language"] = default_fallback
            if is_own:
                # A multipath library has one 1.1 entry per folder; each
                # stays a subfolder entry so the folders keep their own
                # language and enabled state.
                sub["path"] = next(f for f in source_paths(discovered[idx]["path"])
                                   if _norm(f) == _norm(path))
                folder_entries.setdefault(idx, []).append(sub)
            subs[idx].append(sub)

    libraries = []
    for i, src in enumerate(discovered):
        entry = own.get(i, {})
        # Included unless 1.1 disabled every folder of a multipath library.
        multi = folder_entries.get(i, [])
        all_off = (len(multi) == len(_folders(src["path"]))
                   and all(e.get("enabled", True) is False for e in multi))
        included = entry.get("enabled", True) is not False and not all_off
        language = str(entry.get("language") or default_language)
        fallback = str(entry.get("fallback_language", default_fallback) or "")
        if settings is None:
            libraries.append(Library(
                path=src["path"], label=src.get("label", ""), included=included,
                language=language, fallback_language=fallback, toggles=frozenset(),
                subfolders=tuple(subs[i])))
            continue
        libraries.append(library_from_legacy_settings(
            settings,
            path=src["path"],
            label=src.get("label", ""),
            included=included,
            language=language,
            fallback_language=fallback,
            subfolders=tuple(subs[i]),
        ))
    return LibraryConfig(libraries)
