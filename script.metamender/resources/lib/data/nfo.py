"""NFO detection for library items.

Mirrors Kodi's own lookup, ``CVideoTagLoaderNFO::FindNFO`` in
``xbmc/video/tags/VideoTagLoaderNFO.cpp`` (Omega), so metamender treats an item
as NFO-managed exactly when Kodi would have read an NFO for it. Everything goes
through ``xbmcvfs`` so SMB, NFS and other VFS paths work.

Logging:
    Logger: 'nfo'
    Key events:
        - nfo.listdir_failed / nfo.exists_failed (ERROR): a VFS call failed;
          the item is reported UNREACHABLE
"""
from __future__ import annotations

import re
from typing import List, Tuple
from urllib.parse import unquote

import xbmcvfs

from resources.lib.utils import get_logger

log = get_logger('nfo')

NFO = "nfo"
NO_NFO = "no_nfo"
UNREACHABLE = "unreachable"

_STACK_PREFIX = "stack://"
_STACK_SEPARATOR = " , "
_ARCHIVE_PREFIXES = ("rar://", "zip://")

# Folder names whose containing movie folder carries the NFO. Kodi's
# GetLocalMetadataPath steps out of these for disc images.
_DISC_FOLDERS = ("video_ts", "bdmv")
_DISC_FILES = (
    "video_ts.ifo", "index.bdmv", "index.bdm", "movieobject.bdmv",
    "movieobject.bdm",
)

# Kodi's default video stack markers (cd1, dvd2, part3, disc 4, ...): the
# stacked title is the first file's name without the marker.
_STACK_MARKER = re.compile(
    r"^(.*?)[ _.-]*(?:cd|dvd|p(?:ar)?t|dis[ck])[ _.-]*[0-9a-d]+(.*?)(\.[^.]*)?$",
    re.IGNORECASE,
)


def _sep(path: str) -> str:
    return "\\" if "\\" in path and "/" not in path else "/"


def _split(path: str) -> Tuple[str, str]:
    """Return (folder without trailing separator, file name)."""
    sep = _sep(path)
    stripped = path.rstrip(sep) if path.endswith(sep) and len(path) > 1 else path
    head, _, tail = stripped.rpartition(sep)
    return head, tail


def _join(folder: str, name: str) -> str:
    sep = _sep(folder)
    return folder.rstrip(sep) + sep + name


def _replace_ext(path: str, ext: str) -> str:
    folder, name = _split(path)
    stem, dot, _ = name.rpartition(".")
    if not dot:
        stem = name
    new = stem + ext
    return _join(folder, new) if folder else new


class _VfsError(Exception):
    """A VFS call failed, so nothing can be concluded about the NFO."""


def _exists(path: str) -> bool:
    try:
        return bool(path) and bool(xbmcvfs.exists(path))
    except Exception as exc:
        log.exception("VFS exists check failed", event="nfo.exists_failed", path=path)
        raise _VfsError(path) from exc


def _nfo_files(folder: str) -> List[str]:
    try:
        _dirs, files = xbmcvfs.listdir(folder)
    except Exception as exc:
        log.exception("Could not list folder", event="nfo.listdir_failed", folder=folder)
        raise _VfsError(folder) from exc
    return [f for f in files if f.lower().endswith(".nfo")]


def _unique_nfo(folder: str) -> str:
    """The only .nfo in the folder, or "" when there are none or several."""
    found = _nfo_files(folder)
    return _join(folder, found[0]) if len(found) == 1 else ""


def _is_optical(path: str) -> bool:
    return _split(path)[1].lower() in _DISC_FILES


def _local_metadata_folder(path: str) -> str:
    """Folder holding the metadata of a disc image (parent of VIDEO_TS/BDMV)."""
    folder, _ = _split(path)
    parent, name = _split(folder)
    if name.lower() in _DISC_FOLDERS:
        return parent
    return folder


def _stacked_parts(path: str) -> List[str]:
    return path[len(_STACK_PREFIX):].split(_STACK_SEPARATOR)


def _stacked_title_path(first_file: str) -> str:
    folder, name = _split(first_file)
    m = _STACK_MARKER.match(name)
    if not m:
        return first_file
    title = m.group(1) + m.group(2) + (m.group(3) or "")
    return _join(folder, title)


def _archive_outer_path(path: str) -> str:
    """Path next to the archive for an item inside rar:// or zip://.

    The URL host part is the percent-encoded archive path; the item sits next
    to the archive under the inner file's name.
    """
    rest = path[len("rar://"):]
    encoded, _, inner = rest.partition("/")
    archive = unquote(encoded)
    folder, _ = _split(archive)
    return _join(folder, _split(inner)[1])


def _find_file_nfo(path: str, movie_folder: bool) -> str:
    """Kodi's FindNFO for a non-folder item; "" when none."""
    nfo_file = ""
    if path.lower().startswith(_ARCHIVE_PREFIXES):
        return _find_file_nfo(_archive_outer_path(path), movie_folder)

    is_stack = path.startswith(_STACK_PREFIX)
    str_path = _split(_stacked_parts(path)[0])[0] if is_stack else _split(path)[0]

    if movie_folder and not is_stack:
        candidate = _join(str_path, "movie.nfo")
        if _exists(candidate):
            return candidate

    if is_stack:
        first = _stacked_parts(path)[0]
        nfo_file = _find_file_nfo(first, movie_folder)
        if not nfo_file:
            nfo_file = _find_file_nfo(_stacked_title_path(first), movie_folder)
    elif path.lower().endswith(".nfo"):
        nfo_file = path
    else:
        nfo_file = _replace_ext(path, ".nfo")

    if nfo_file and not _exists(nfo_file):
        nfo_file = ""

    # Movie parts in a "cd1" subfolder share the NFO of the parent folder.
    if not nfo_file and str_path.lower().endswith("cd1"):
        return _find_file_nfo(_join(str_path[:-3], _split(path)[1]), movie_folder)

    optical = _is_optical(path)
    if not nfo_file and optical:
        nfo_file = _unique_nfo(_local_metadata_folder(path))

    if optical or (movie_folder and not nfo_file):
        unique = _unique_nfo(str_path)
        if unique:
            return unique
    return nfo_file


def _first_media_path(file_path: str) -> str:
    """The path whose existence proves the media is reachable."""
    if file_path.startswith(_STACK_PREFIX):
        return _stacked_parts(file_path)[0]
    if file_path.lower().startswith(_ARCHIVE_PREFIXES):
        rest = file_path[len("rar://"):]
        return unquote(rest.partition("/")[0])
    return file_path


def nfo_state(media_type_name: str, file_path: str) -> str:
    """Classify an item as ``NFO``, ``NO_NFO`` or ``UNREACHABLE``.

    ``file_path`` is the media file for movies and episodes (stack://, rar://,
    zip:// and disc images included) and the show folder for TV shows.
    ``UNREACHABLE`` means the media (or show folder) cannot be found, for
    instance because a share is offline, so the caller must not conclude that
    there is no NFO.
    """
    try:
        if not file_path or not _exists(_first_media_path(file_path)):
            return UNREACHABLE

        if media_type_name == "tvshow":
            found = _join(file_path, "tvshow.nfo")
            return NFO if _exists(found) else NO_NFO

        found = _find_file_nfo(file_path, media_type_name == "movie")
    except _VfsError:
        # A share dropping mid-check must not read as "no NFO": that would
        # unlock writes onto a possibly NFO-managed item.
        return UNREACHABLE
    return NFO if found else NO_NFO
