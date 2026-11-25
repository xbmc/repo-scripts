"""Station logos: the translucent 'bug' in a corner during programmes, and the
logo in the channel banner.

A channel's logo is the image picked for it in the channel editor, or else a
file in the logo folder (Settings > Channels) named after the channel's name,
call letters or number - 'Comedy Channel.png', 'CC.png' or '5.png'.
stations.brand() decides which logo a channel shows at a moment (and says where
it came from); everything on screen asks it, never this module directly.
CableBox ships no logos (real network logos are trademarks); they're the
viewer's own images.  Kodi can't show SVG, so PNG (with transparency) is best.
"""
import os
import re
import time

import xbmcvfs

from . import kodiutil as K

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
CORNERS = ("tl", "tr", "bl", "br")
OPACITY = (30, 50, 70, 100)
_FOLDER_CACHE = {}
_CACHE_TTL = 120


def _key(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def _folder_index(folder):
    """{normalised file name: full path} for the images in the logo folder."""
    hit = _FOLDER_CACHE.get(folder)
    if hit and time.time() - hit[0] < _CACHE_TTL:
        return hit[1]
    idx = {}
    try:
        _dirs, files = xbmcvfs.listdir(folder)
        sep = "" if folder.endswith(("/", "\\")) else "/"
        for f in files:
            stem, ext = os.path.splitext(f)
            if ext.lower() in IMAGE_EXT:
                idx.setdefault(_key(stem), folder + sep + f)
    except Exception as exc:
        K.log("logo folder %s: %s" % (folder, exc))
    _FOLDER_CACHE[folder] = (time.time(), idx)
    return idx


def logo_for(ch):
    """Path of the channel's logo image, or ''."""
    if not ch:
        return ""
    own = ch.get("logo") or ""
    if own == "none":
        return ""
    if own:
        return own
    return folder_logo(ch.get("name"), ch.get("callsign"), str(ch.get("number", "")))


def folder_logo(*names):
    """The logo folder's image named like the first of `names` that has one, or ''."""
    folder = K.setting("logo_folder", "")
    if not folder:
        return ""
    idx = _folder_index(folder)
    for cand in names:
        k = _key(cand)
        if k and k in idx:
            return idx[k]
    return ""


def bug_settings():
    """(on, corner, opacity) from Settings > On screen."""
    on = K.setting_bool("logo_bug", True)
    corner = CORNERS[max(0, min(3, K.setting_int("logo_corner", 3)))]
    opacity = OPACITY[max(0, min(3, K.setting_int("logo_opacity", 1)))]
    return on, corner, opacity


def clear_cache():
    _FOLDER_CACHE.clear()
