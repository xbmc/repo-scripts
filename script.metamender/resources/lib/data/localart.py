"""Whether a local art file still exists.

A missing file is fair game to fill, so "missing" is only concluded when the
storage the file lives on is known to answer. A folder that exists is not
enough: a share mounted at a local path (fstab or systemd mounts on
LibreELEC and OSMC) leaves an empty mount point behind when it is down. So
the item's media must exist (a show folder must also hold something), and
the art must lie under the media's folder or in a folder that exists and is
not empty; an item without media needs the non-empty folder alone. Anything
else (a sleeping NAS, a share on another host that does not answer) is
``UNREACHABLE``, which the scan treats as transient. Everything goes through
``xbmcvfs`` so SMB, NFS and other VFS paths work; ``xbmcvfs.exists`` checks a
path ending in a separator as a folder and anything else as a file.

Logging:
    Logger: 'localart'
    Key events:
        - localart.exists_failed (ERROR): a VFS call failed; the art is
          reported UNREACHABLE
"""
from __future__ import annotations

import xbmcvfs

from resources.lib.data.nfo import (
    _first_media_path,
    _local_metadata_folder,
    _sep,
    _split,
)
from resources.lib.utils import get_logger

log = get_logger('localart')

EXISTS = "exists"
MISSING = "missing"
UNREACHABLE = "unreachable"


def _exists(path: str) -> bool:
    return bool(xbmcvfs.exists(path))


def _as_folder(path: str) -> str:
    sep = _sep(path)
    return path if path.endswith(sep) else path + sep


def _folder_holds_something(folder: str) -> bool:
    """The folder exists and lists at least one entry: an unmounted mount
    point is an empty folder that exists."""
    if not folder or not _exists(_as_folder(folder)):
        return False
    dirs, files = xbmcvfs.listdir(_as_folder(folder))
    return bool(dirs or files)


def _media_folder(media: str) -> str:
    """The folder whose contents belong to the media, with a trailing
    separator: a show's folder itself, the folder holding a disc image's
    VIDEO_TS or BDMV, otherwise the media file's folder."""
    if media.endswith(_sep(media)):
        return media
    folder = _local_metadata_folder(media)
    return _as_folder(folder) if folder else ""


def local_art_state(art_path: str, media_path: str) -> str:
    """Classify a local art path as ``EXISTS``, ``MISSING`` or
    ``UNREACHABLE``.

    ``media_path`` is the item's media file (stack:// and archives
    included), a show or season's show folder, or "" when the item has none;
    then only the art's own folder, holding something, can prove the file
    is gone.
    """
    try:
        if _exists(art_path):
            return EXISTS
        media = _first_media_path(media_path) if media_path else ""
        if media:
            # A show or season's media is the show folder, which always
            # holds its episodes; an empty one is an unmounted mount point.
            is_folder = media.endswith(_sep(media))
            if not (_folder_holds_something(media) if is_folder else _exists(media)):
                return UNREACHABLE
            under = _media_folder(media)
            if under and art_path.startswith(under):
                return MISSING
        if _folder_holds_something(_split(art_path)[0]):
            return MISSING
    except Exception:
        # A share dropping mid-check must not read as "missing": that would
        # replace the user's art because of a network hiccup.
        log.exception("VFS exists check failed", event="localart.exists_failed",
                      path=art_path)
    return UNREACHABLE
