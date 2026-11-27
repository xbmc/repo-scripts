# SPDX-License-Identifier: GPL-2.0-only
"""Which video library this Kodi has open, as the hash the sync contract calls library_id.

The contract defines it as a hash of what Kodi actually opens: the database folder and name
for SQLite, or the type, host, port and versioned database name for MySQL/MariaDB. Only the
hash leaves Kodi, because the inputs hold a host name and a home folder.

This mirrors Kodi's own choice step by step, since a library_id that disagrees with Kodi
would make two boxes on one MySQL library look separate, or one box look like two:
- advancedsettings.xml is the profile's when that file exists, else the master profile's,
  as a whole file (CProfileManager::GetUserDataItem), not element by element;
- a <videodatabase> of type mysql without host, user or pass falls back to SQLite
  (CDatabase::InitSettings);
- SQLite opens the profile's database folder (special://database, which points at the master
  folder for a profile without its own databases) unless <host> overrides it;
- the name is <name> or "MyVideos", with the schema version appended in both cases
  (CDatabase::Open).

advancedsettings.xml is parsed with the standard library for the reasons in
advanced_settings.py (no PyPI dependency; ElementTree expands no external entities).

Log events: sync.library_id.unparseable (master).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from xml.etree import ElementTree

from resources.lib.kodi import KodiApi
from resources.lib.log import get_logger

_log = get_logger("sync")

# Video database schema per Kodi major (VideoDatabase.cpp GetSchemaVersion). 22 was read off
# a live Kodi 22 test box as "testvideo149". A major missing here stands in for itself, so
# an upgrade still changes the id, which the contract accepts.
SCHEMA_BY_MAJOR = {21: 131, 22: 149}
MYSQL_DEFAULT_PORT = "3306"

_PROFILE_SETTINGS = "special://profile/advancedsettings.xml"
_MASTER_SETTINGS = "special://masterprofile/advancedsettings.xml"
_PROFILE_DATABASE = "special://database"
_MASTER_DATABASE = "special://masterprofile/Database"


@dataclass(frozen=True)
class _VideoDatabase:
    type: str = ""
    host: str = ""
    port: str = ""
    user: str = ""
    password: str = ""
    name: str = ""


def kodi_major(kodi: KodiApi) -> int:
    match = re.match(r"\s*(\d+)", kodi.info_label("System.BuildVersion"))
    return int(match.group(1)) if match else 0


def kodi_version(kodi: KodiApi) -> str:
    """major.minor, as the ping block reports it."""
    match = re.match(r"\s*(\d+)\.(\d+)", kodi.info_label("System.BuildVersion"))
    return f"{match.group(1)}.{match.group(2)}" if match else ""


def advanced_settings_text(kodi: KodiApi, master: bool = False) -> str | None:
    """The advancedsettings.xml Kodi loads: the profile's when it exists, else the master's."""
    if not master:
        text = kodi.read_text(_PROFILE_SETTINGS)
        if text is not None:
            return text
    return kodi.read_text(_MASTER_SETTINGS)


class Unparseable(Exception):
    """advancedsettings.xml can't be read the way Kodi reads it, so the library is unknown."""


# Kodi's TinyXML accepts a bare "&" (a password like "a&b"), which ElementTree rejects.
BARE_AMPERSAND = re.compile(r"&(?!(?:[A-Za-z]+|#[0-9]+|#x[0-9A-Fa-f]+);)")


def _video_database(text: str | None) -> _VideoDatabase:
    if not text:
        return _VideoDatabase()
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        try:
            root = ElementTree.fromstring(BARE_AMPERSAND.sub("&amp;", text))
        except ElementTree.ParseError as exc:
            raise Unparseable from exc
    element = root.find("videodatabase")
    if element is None:
        return _VideoDatabase()

    def field(tag: str) -> str:
        found = element.find(tag)
        return (found.text or "").strip() if found is not None else ""

    return _VideoDatabase(field("type"), field("host"), field("port"), field("user"), field("pass"), field("name"))


def library_id(kodi: KodiApi, *, master: bool = False) -> str:
    """The hash, or "" when advancedsettings.xml can't be parsed: a guessed SQLite id would
    split a MySQL library shared by several boxes, so the ping leaves the id out instead."""
    try:
        db = _video_database(advanced_settings_text(kodi, master))
    except Unparseable:
        _log.warning("sync.library_id.unparseable", master=master)
        return ""
    major = kodi_major(kodi)
    name = (db.name or "MyVideos") + str(SCHEMA_BY_MAJOR.get(major, major))
    if db.type == "mysql" and db.host and db.user and db.password:
        parts = ["mysql", db.host.lower(), db.port or MYSQL_DEFAULT_PORT, name]
    else:
        folder = db.host or (_MASTER_DATABASE if master else _PROFILE_DATABASE)
        parts = ["sqlite3", kodi.translate(folder).rstrip("/\\"), name]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def default_sqlite_folder(kodi: KodiApi) -> str | None:
    """The folder of the library Kodi opens when that library is SQLite under its default
    name in special://database, else None (MySQL, another folder or name, or settings Kodi
    would read differently)."""
    try:
        db = _video_database(advanced_settings_text(kodi))
    except Unparseable:
        return None
    # A <host> is either MySQL's server or SQLite's folder; both are not the default folder.
    if db.host or db.name not in ("", "MyVideos"):
        return None
    return kodi.translate(_PROFILE_DATABASE)


def profile_has_own_database(kodi: KodiApi) -> bool:
    """Whether this profile's library is its own, so the profile tier may decide ownership."""
    return library_id(kodi) != library_id(kodi, master=True)
