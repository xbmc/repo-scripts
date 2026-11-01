# KarmaMole Skin Helper (script.karmamole.helper)
# Copyright (C) 2026 Omar Kamel
# SPDX-License-Identifier: GPL-2.0-or-later
"""Shared Kodi plumbing: logging, JSON-RPC, paths, Window(Home) properties, atomic file writes."""
import json
import os
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON_ID = 'script.karmamole.helper'
GROOVE = 'skin.groove'
ADDON = xbmcaddon.Addon(ADDON_ID)
PROFILE = xbmcvfs.translatePath('special://profile/addon_data/%s/' % ADDON_ID)
# Generated textures live under special://temp: Kodi treats that folder as "already cached" (TextureCache.cpp
# IsCachedImage), so they never enter Thumbnails/Textures13.db and can't be served stale from there.
TEMP_SPECIAL = 'special://temp/%s/' % ADDON_ID
TEMP = xbmcvfs.translatePath(TEMP_SPECIAL)

HOME = xbmcgui.Window(10000)

# Debug lines go to LOGDEBUG. Create an empty file "debug" in addon_data/script.karmamole.helper/ to log them at INFO.
VERBOSE = os.path.isfile(os.path.join(PROFILE, 'debug'))


def log(msg, level=xbmc.LOGDEBUG):
    if VERBOSE and level == xbmc.LOGDEBUG:
        level = xbmc.LOGINFO
    xbmc.log('[%s] %s' % (ADDON_ID, msg), level)


# English text of this add-on's strings.po, used when Kodi has no strings loaded for the add-on. Kodi loads add-on
# strings only at startup / on a language change (CLangInfo::SetLanguage) and in CAddonInstallJob (zip or repository
# install). An add-on that arrives by file copy + UpdateLocalAddons (a dev push, a manual copy) gets "" from
# getLocalizedString until Kodi restarts (device audit 2026-10-21; Kodi Omega xbmc/LangInfo.cpp,
# xbmc/addons/AddonInstaller.cpp). Keep this table in step with strings.po.
STRINGS_EN = {
    32001: 'Play a shuffled mix',
    32002: 'Only part of this folder is in the mix: it is too large to walk in full',
}


def localize(string_id):
    """ADDON.getLocalizedString with the English text as a fallback, so a label is never blank."""
    try:
        text = ADDON.getLocalizedString(string_id)
    except Exception:  # noqa: BLE001
        text = ''
    return text or STRINGS_EN.get(string_id, '')


def info(label):
    """One infolabel via xbmc.getInfoLabel. Not for ListItem.* / Container(id).ListItem.* / Player.* in a loop:
    use infos()."""
    return xbmc.getInfoLabel(label)


def infos(*labels):
    """Infolabels evaluated ON KODI'S GUI THREAD: {label: value}, {} on failure.

    xbmc.getInfoLabel runs on the calling (Python) thread and takes no GUI lock (Kodi 21 ModuleXbmc.cpp; only
    getCondVisibility locks). A ListItem.* read walks the active window's view control while the GUI thread may be
    swapping it (Container.SetViewMode, a dialog loading): Kodi 21.2 crashed with an access violation in
    CGUIControlLookup::GetControl <- CGUIViewControl::GetSelectedItem <- GetCurrentListItem <- getInfoLabel, six times
    on the PC bench in Groove (2026-10-29). JSON-RPC XBMC.GetInfoLabels hands the labels to the GUI thread
    (TMSG_GUI_INFOLABEL) and waits, so the read can never overlap a view switch."""
    res = rpc('XBMC.GetInfoLabels', {'labels': list(labels)})
    return res if isinstance(res, dict) else {}


def cond(expr):
    return xbmc.getCondVisibility(expr)


def rpc(method, params=None):
    """JSON-RPC call; returns the 'result' value or None (errors are logged)."""
    req = {'jsonrpc': '2.0', 'id': 1, 'method': method}
    if params is not None:
        req['params'] = params
    try:
        resp = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
    except Exception as e:  # noqa: BLE001
        log('rpc %s failed: %s' % (method, e), xbmc.LOGERROR)
        return None
    if 'error' in resp:
        log('rpc %s error: %s' % (method, resp['error']), xbmc.LOGWARNING)
        return None
    return resp.get('result')


def prop(name):
    return HOME.getProperty(name)


def set_prop(name, value):
    if value is None or value == '':
        HOME.clearProperty(name)
    else:
        HOME.setProperty(name, str(value))


def skin_is_groove():
    """Groove-only side effects (Skin.SetBool(Groove.SpinesReady) writes into the running skin's settings)."""
    return xbmc.getSkinDir() == GROOVE


def mkdirs(path):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def write_atomic(path, data):
    """Write bytes via a temp file + rename, so a reader (Kodi or another add-on process) never sees half a file."""
    mkdirs(os.path.dirname(path))
    # pid + thread id: every add-on call runs inside the one Kodi process, so the pid alone collides
    tmp = '%s.%d.%d.tmp' % (path, os.getpid(), threading.get_ident())
    with open(tmp, 'wb') as f:
        f.write(data)
    for attempt in range(5):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:  # Windows: a reader still has the target open
            if attempt == 4:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
                raise
            time.sleep(0.05)


def read_json(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, obj):
    write_atomic(path, json.dumps(obj, separators=(',', ':')).encode('utf-8'))


def get_pil():
    """(Image, ImageEnhance, ImageFilter) or None. PIL comes from script.module.pil (optional import)."""
    try:
        from PIL import Image, ImageEnhance, ImageFilter
        return Image, ImageEnhance, ImageFilter
    except Exception as e:  # noqa: BLE001
        log('PIL not available (script.module.pil): %s' % e, xbmc.LOGWARNING)
        return None


def parse_args(argv):
    """RunScript(script.karmamole.helper,action=x,from=2,to=1) -> {'action': 'x', 'from': '2', 'to': '1'}."""
    out = {}
    for a in argv:
        a = a.strip().strip('"')  # RunScript(...,"image=$INFO[...]") may keep the quotes
        if '=' in a:
            k, v = a.split('=', 1)
            out[k.strip().lower()] = v.strip()
    return out
