"""Small helpers around the Kodi Python API."""
import json
import os

import xbmc
import xbmcaddon
import xbmcvfs

ADDON_ID = "script.cablebox42"
ADDON = xbmcaddon.Addon(ADDON_ID)
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo("path"))
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
MEDIA = os.path.join(ADDON_PATH, "resources", "media")

CHANNELS_FILE = os.path.join(PROFILE, "channels.json")
STATE_FILE = os.path.join(PROFILE, "state.json")
DURATIONS_FILE = os.path.join(PROFILE, "durations.json")
SCHEDULE_DIR = os.path.join(PROFILE, "schedules")


def ensure_dirs():
    for d in (PROFILE, SCHEDULE_DIR):
        if not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)


def log(msg, level=xbmc.LOGDEBUG):
    xbmc.log("[%s] %s" % (ADDON_ID, msg), level)


def log_err(msg):
    log(msg, xbmc.LOGERROR)


def setting(key, default=""):
    """Read a setting fresh every time: an Addon object created earlier can keep
    returning old values after the user changes settings elsewhere in Kodi."""
    try:
        v = xbmcaddon.Addon(ADDON_ID).getSetting(key)
    except Exception:
        return default
    return v if v != "" else default


def setting_bool(key, default=False):
    v = setting(key, None)
    if v is None:
        return default
    return str(v).lower() == "true"


def setting_int(key, default=0):
    try:
        return int(float(setting(key, default)))
    except (TypeError, ValueError):
        return default


def set_setting(key, value):
    xbmcaddon.Addon(ADDON_ID).setSetting(key, str(value))


def lang(string_id):
    return ADDON.getLocalizedString(string_id)


def rpc(method, params=None):
    req = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        req["params"] = params
    raw = xbmc.executeJSONRPC(json.dumps(req))
    try:
        resp = json.loads(raw)
    except ValueError:
        log_err("Bad JSON-RPC reply for %s" % method)
        return {}
    if "error" in resp:
        log_err("JSON-RPC %s failed: %s" % (method, resp["error"]))
        return {}
    return resp.get("result", {}) or {}


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, OSError, ValueError):
        return default


def save_json(path, data):
    ensure_dirs()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    os.replace(tmp, path)


def media(name):
    return os.path.join(MEDIA, name)


def schedule_cfg():
    return {
        "commercials_path": setting("commercials_path"),
        "bumps_path": setting("bumps_path"),
        "breaks_per_slot": max(0, setting_int("breaks_per_slot", 2)),
        "horizon": max(4, setting_int("horizon_hours", 12)) * 3600,
        "low_water": 3 * 3600,
        "shorts_mode": setting_int("shorts_mode", 0),
        "seasons": seasons_cfg(),
    }


def _raw(key):
    """A text setting exactly as typed - an emptied field means 'none', not 'default'."""
    try:
        return xbmcaddon.Addon(ADDON_ID).getSetting(key)
    except Exception:
        return None


def seasons_cfg():
    out = {"on": setting_bool("seasons_on", True), "intensity": setting_int("season_intensity", 1),
           "hold": setting_bool("season_hold", True)}
    for name in ("halloween", "thanksgiving", "christmas"):
        out[name] = {"on": setting_bool("%s_on" % name, True),
                     "ads": setting("%s_commercials" % name), "bumps": setting("%s_bumps" % name),
                     "tags": _raw("%s_tags" % name), "genres": _raw("%s_genres" % name)}
    return out


# ------------------------------------------------------------------ localisation
_IDS = None


def _load_ids():
    """Map English msgid -> string id from the en_gb strings.po."""
    ids = {}
    po = os.path.join(ADDON_PATH, "resources", "language", "resource.language.en_gb", "strings.po")
    ctx = None
    try:
        with open(po, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith('msgctxt "#'):
                    ctx = int(line[10:-1])
                elif line.startswith('msgid "') and ctx is not None:
                    text = json.loads(line[6:])
                    if text:
                        ids[text] = ctx
                    ctx = None
    except (IOError, OSError, ValueError) as exc:
        xbmc.log("[%s] cannot read strings.po: %s" % (ADDON_ID, exc), xbmc.LOGERROR)
    return ids


def _(text):
    """Localised version of an English UI string (falls back to the English)."""
    global _IDS
    if _IDS is None:
        _IDS = _load_ids()
    sid = _IDS.get(text)
    if sid is None:
        return text
    return ADDON.getLocalizedString(sid) or text
