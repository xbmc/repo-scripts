"""Hash utilities for rebuild detection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

try:
    import xbmc
    import xbmcvfs

    IN_KODI = True
except ImportError:
    IN_KODI = False

from .constants import (
    BACKGROUNDS_FILE,
    MENUS_FILE,
    PROPERTIES_FILE,
    TEMPLATES_FILE,
    VIEWS_FILE,
    WIDGETS_FILE,
)
from .log import get_logger
from .userdata import get_userdata_path

log = get_logger("Hashing")

HASH_PREFIX_LEN = 8


def get_hash_file_path() -> str:
    """Get path to hashes file for current skin."""
    if IN_KODI:
        skin_dir = xbmc.getSkinDir()
        data_path = xbmcvfs.translatePath("special://profile/addon_data/script.skinshortcuts/")
        return str(Path(data_path) / f"{skin_dir}.hashes")
    return ""


def hash_file(path: str | Path) -> str | None:
    """Generate MD5 hash for a file."""
    path = Path(path)
    if not path.exists():
        return None

    md5 = hashlib.md5()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
        return md5.hexdigest()
    except OSError:
        return None


def generate_config_hashes(shortcuts_path: str | Path) -> dict[str, str | None]:
    """Generate hashes for all config files in shortcuts folder."""
    path = Path(shortcuts_path)
    config_files = [
        MENUS_FILE,
        WIDGETS_FILE,
        BACKGROUNDS_FILE,
        PROPERTIES_FILE,
        TEMPLATES_FILE,
        VIEWS_FILE,
    ]

    hashes: dict[str, str | None] = {}
    for filename in config_files:
        file_path = path / filename
        hashes[filename] = hash_file(file_path)

    userdata_path = get_userdata_path()
    if userdata_path:
        hashes["userdata"] = hash_file(userdata_path)

    if IN_KODI:
        import xbmcaddon

        addon = xbmcaddon.Addon("script.skinshortcuts")
        hashes["script_version"] = addon.getAddonInfo("version")
        hashes["skin_dir"] = xbmc.getSkinDir()
        hashes["kodi_version"] = xbmc.getInfoLabel("System.BuildVersion").split(".")[0]

    return hashes


def read_stored_hashes() -> dict[str, str | None]:
    """Read previously stored hashes."""
    hash_file_path = get_hash_file_path()
    if not hash_file_path:
        return {}

    try:
        path = Path(hash_file_path)
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except (OSError, json.JSONDecodeError):
        pass

    return {}


def write_hashes(hashes: dict[str, str | None]) -> bool:
    """Write hashes to file."""
    hash_file_path = get_hash_file_path()
    if not hash_file_path:
        return False

    try:
        path = Path(hash_file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(hashes, f, indent=2)
        return True
    except OSError:
        return False


def needs_rebuild(shortcuts_path: str | Path, output_paths: list[str] | None = None) -> bool:
    """Check if menu needs to be rebuilt by comparing hashes."""
    stored = read_stored_hashes()

    if not stored:
        log.debug("Rebuild needed: no stored hashes")
        return True

    if output_paths:
        for out_path in output_paths:
            includes_file = Path(out_path) / "script-skinshortcuts-includes.xml"
            if not includes_file.exists():
                log.debug(f"Rebuild needed: missing {includes_file}")
                return True
            current_hash = hash_file(includes_file)
            stored_hash = stored.get(f"includes:{out_path}")
            if current_hash != stored_hash:
                log.debug(f"Rebuild needed: includes.xml at {out_path} doesn't match stored hash")
                return True

    current = generate_config_hashes(shortcuts_path)

    log.debug(f"Checking hashes for: {shortcuts_path}")
    for key, value in current.items():
        stored_val = stored.get(key)
        if stored_val != value:
            stored_prefix = stored_val[:HASH_PREFIX_LEN] if stored_val else None
            current_prefix = value[:HASH_PREFIX_LEN] if value else None
            log.info(f"Rebuild needed: {key} changed ({stored_prefix} -> {current_prefix})")
            return True
        log.debug(f"  {key}: match")

    log.info("No rebuild needed: all hashes match")
    return False
