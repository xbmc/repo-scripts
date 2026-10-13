# -*- coding: utf-8 -*-
"""Downloading a manual next to its game."""

import time

import xbmc
import xbmcvfs

from . import manuals
from .main import ADDON_ID, PROFILE_MANUALS, budget_bytes, downloads, log

CHUNK = 256 * 1024


def writable(folder):
    """Whether a file can be written in a folder, making the folder if needed.

    Tried rather than asked: Kodi answers whether a folder exists from its
    listing of the folder above, which can predate the folder being made.
    """
    xbmcvfs.mkdirs(folder)
    probe = manuals.join(folder, ".%s.part" % ADDON_ID)
    f = xbmcvfs.File(probe, "w")
    try:
        written = f.write(b"-")
    finally:
        f.close()
    xbmcvfs.delete(probe)
    return bool(written)


def target_for(game, extension):
    """Beside the game if that can be written to, otherwise in the profile."""
    folder = manuals.folder_of(game)
    existing = set(xbmcvfs.listdir(folder)[0]) if xbmcvfs.exists(folder) else set()
    beside = manuals.download_target(game, existing, extension)
    if beside:
        folder = manuals.folder_of(beside)
        if writable(folder):
            return beside
        log("\"%s\" can't be written to; keeping the manual in the profile" % folder)
    xbmcvfs.mkdirs(PROFILE_MANUALS)
    return manuals.join(PROFILE_MANUALS, manuals.profile_name(game, extension))


def download(url, game, progress):
    """Fetch a manual for a game; its path, or "" if it could not be fetched.

    progress(share) is told how far it has got, from 0 to 1. The file is
    written under another name until it is whole, so a failed download never
    leaves something that looks like a manual. Nothing bigger than the space
    chosen for downloaded manuals is kept, whatever size the server gave.
    """
    target = target_for(game, manuals.fetched_extension(url))
    partial = target + ".part"
    limit = budget_bytes()
    copied = 0
    done = False
    try:
        source = xbmcvfs.File(url)
        size = source.size()
        if size > limit:
            source.close()
            log("The manual is %d MB, more than the space for downloaded manuals" % (size // (1024 * 1024)),
                xbmc.LOGERROR)
            return ""
        with xbmcvfs.File(partial, "w") as out:
            while copied <= limit:
                data = source.readBytes(CHUNK)
                if not data:
                    break
                out.write(data)
                copied += len(data)
                if size > 0:
                    progress(float(copied) / size)
        source.close()
        done = (0 < copied <= limit and (size <= 0 or copied == size)
                and xbmcvfs.rename(partial, target))
    except Exception as error:
        log("Fetching the manual failed: %s" % error, xbmc.LOGERROR)
    if not done:
        xbmcvfs.delete(partial)
        return ""
    downloads().add(target, copied, time.time())
    log("Fetched a manual to \"%s\"" % target)
    return target
