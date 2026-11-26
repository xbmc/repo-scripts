"""Kodi's movie set information folder: where a set's own artwork and
set.nfo live, one subfolder per set named after the set.

Kodi derives the subfolder name with ``CUtil::MakeLegalFileName`` using
``LEGAL_WIN32_COMPAT`` (xbmc/Util.cpp), so a set called "Star Wars: Saga" is
looked up as "Star Wars_ Saga". Everything goes through ``xbmcvfs`` so SMB,
NFS and other VFS paths work.

Logging:
    Logger: 'setfolder'
    Key events:
        - setfolder.exists_failed (ERROR, with the trace): a VFS call
          failed; no folder is reported
"""
from __future__ import annotations

from typing import Iterable, Optional

import xbmcvfs

from resources.lib.utils import get_logger

log = get_logger('setfolder')

_ILLEGAL = '/\\?:*"<>|'
_TABLE = {ord(c): "_" for c in _ILLEGAL}


def legal_name(title: str) -> str:
    """The folder name Kodi uses for a set title."""
    return title.translate(_TABLE).rstrip(". ")


def folder_for(root: str, names: Iterable[str]) -> Optional[str]:
    """The first of ``names``, in the order given, whose folder
    ``root/<legal_name>/`` exists; None for an empty root, no match or a VFS
    error (the caller treats all of those as "no folder"). A local Windows
    root (``D:\\Sets\\``: backslashes and no slash) is joined with
    backslashes; any other root with slashes."""
    if not root:
        return None
    sep = "\\" if "\\" in root and "/" not in root else "/"
    base = root.rstrip(sep)
    try:
        for name in names:
            if xbmcvfs.exists("{0}{1}{2}{1}".format(base, sep, legal_name(name))):
                return name
    except Exception:
        log.exception("Set folder lookup failed", event="setfolder.exists_failed",
                      root=root)
    return None
