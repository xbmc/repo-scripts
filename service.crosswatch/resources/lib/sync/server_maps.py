# SPDX-License-Identifier: GPL-2.0-only
"""The library rows a media server add-on manages through direct paths.

With direct paths (PlexKodiConnect) or native mode (Jellyfin for Kodi) such a row holds the
server's own file path, the same kind of smb:// or local path a file Kodi scanned itself
has, and its ids and tags are ordinary too. Only the add-on's own map from server items to
Kodi ids tells them apart, so it is read here:
- PlexKodiConnect: special://database/plex.db, tables movie and episode with kodi_id
  (plex_db/common.py);
- Jellyfin for Kodi: special://database/jellyfin.db, table jellyfin with media_type and
  kodi_id (database/__init__.py).

Both add-ons write Kodi's SQLite file in that folder by name (MyVideosNN.db), never a MySQL
library, so a map counts only when Kodi's library is that file. A map counts only while its
add-on is installed: Kodi reuses ids, and a map left behind by an uninstalled add-on names
rows that may be the household's own by now. A disabled add-on still counts; enabled again,
it takes its rows back.

Maps are opened read-only: another add-on owns and writes them. Both keep them in WAL mode,
so a read sees the last committed state while that add-on writes, and leaves the -wal and
-shm files SQLite keeps beside such a database, as any reader does.

Log events: sync.server_map.unreadable (map, error_type).
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from urllib.parse import quote

from resources.lib.kodi import KodiApi, KodiRpcError
from resources.lib.log import get_logger
from resources.lib.sync.items import ItemKind
from resources.lib.sync.library_id import default_sqlite_folder

_log = get_logger("sync")

PKC_ADDON = "plugin.video.plexkodiconnect"
JELLYFIN_ADDON = "plugin.video.jellyfin"

_MAPS: tuple[tuple[str, str, str], ...] = (
    (
        PKC_ADDON,
        "plex.db",
        "SELECT 'movies', kodi_id FROM movie WHERE kodi_id IS NOT NULL"
        " UNION ALL SELECT 'episodes', kodi_id FROM episode WHERE kodi_id IS NOT NULL",
    ),
    (
        JELLYFIN_ADDON,
        "jellyfin.db",
        "SELECT CASE media_type WHEN 'movie' THEN 'movies' ELSE 'episodes' END, kodi_id FROM jellyfin"
        " WHERE media_type IN ('movie', 'episode') AND kodi_id IS NOT NULL",
    ),
)
# Another add-on may be writing its map; a short wait rides out its transaction, a longer
# lock makes the read fail and come back later.
_BUSY_TIMEOUT_SECONDS = 2.0


@dataclass(frozen=True)
class ServerRows:
    rows: frozenset[tuple[ItemKind, int]]
    # The maps that exist but could not be read; their rows are unknown.
    unreadable: tuple[str, ...] = ()


def _installed(kodi: KodiApi, addon_id: str) -> bool | None:
    """None when Kodi couldn't be asked: whether the map counts is then unknown."""
    try:
        details = kodi.jsonrpc("Addons.GetAddonDetails", {"addonid": addon_id})
    except KodiRpcError:
        # Kodi's answer for an add-on it doesn't have.
        return False
    except Exception:
        return None
    return isinstance(details.get("addon"), dict)


def _read(path: str, query: str) -> set[tuple[ItemKind, int]]:
    con = sqlite3.connect(f"file:{quote(path)}?mode=ro", uri=True, timeout=_BUSY_TIMEOUT_SECONDS)
    try:
        return {("movies" if kind == "movies" else "episodes", int(kodi_id)) for kind, kodi_id in con.execute(query)}
    finally:
        con.close()


def read_server_rows(kodi: KodiApi) -> ServerRows:
    folder = default_sqlite_folder(kodi)
    if folder is None:
        return ServerRows(frozenset())
    rows: set[tuple[ItemKind, int]] = set()
    unreadable: list[str] = []
    for addon_id, name, query in _MAPS:
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        installed = _installed(kodi, addon_id)
        if installed is None:
            _log.warning("sync.server_map.unreadable", map=name, error_type="install_check")
            unreadable.append(name)
            continue
        if not installed:
            continue
        try:
            rows |= _read(path, query)
        except (sqlite3.Error, OSError, ValueError) as exc:
            _log.warning("sync.server_map.unreadable", map=name, error_type=type(exc).__name__)
            unreadable.append(name)
    return ServerRows(frozenset(rows), tuple(unreadable))
