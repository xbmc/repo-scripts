"""Small helpers around the Kodi Python API."""
import contextlib
import json
import os
import random
import threading
import time

try:
    import fcntl                  # Linux / CoreELEC / Android / macOS
except ImportError:
    fcntl = None
try:
    import msvcrt                 # Windows
except ImportError:
    msvcrt = None

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
    """Write data to a temp file of this writer's own, then replace path in one step.
    A temp name per process, thread and call: with one shared name ('state.json.tmp')
    two writers at once could interleave in it and leave a broken file."""
    ensure_dirs()
    tmp = "%s.%d.%x.%06x.tmp" % (path, os.getpid(), threading.get_ident() & 0xffffff,
                                  random.getrandbits(24))
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))
        for i in range(10):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:       # Windows: a reader has path open for a moment
                if i == 9:
                    raise
                time.sleep(0.02)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# ---------------------------------------------------------------- state.json
# Written by the TV, its captions thread, the menus and the service, often in different
# Python interpreters of the same Kodi process.  Every write goes through update_state():
# a lock (a thread lock here, flock / msvcrt on state.json.lock across interpreters and
# processes), a fresh read, only the given keys changed, an atomic replace.  A file that
# can't be read is never written over.
DELETE = object()                         # update_state({key: DELETE}) removes the key
_STATE_THREAD_LOCK = threading.Lock()


class StateUnreadable(Exception):
    pass


@contextlib.contextmanager
def _file_lock(path, timeout=5.0):
    """Hold path + '.lock' exclusively (blocks up to `timeout` s, then goes on unlocked
    rather than lose the change: the atomic replace still keeps the file whole)."""
    with _STATE_THREAD_LOCK:
        ensure_dirs()
        fd = None
        held = False
        try:
            fd = os.open(path + ".lock", os.O_RDWR | os.O_CREAT, 0o644)
            end = time.time() + timeout
            while True:
                try:
                    if fcntl is not None:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    elif msvcrt is not None:
                        os.lseek(fd, 0, 0)
                        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    held = True
                    break
                except OSError:
                    if time.time() > end:
                        log_err("%s: lock busy for %.0f s, saving without it" % (os.path.basename(path), timeout))
                        break
                    time.sleep(0.005 + random.random() * 0.01)
        except OSError as exc:
            log_err("%s: no lock file (%s)" % (os.path.basename(path), exc))
        try:
            yield
        finally:
            if fd is not None:
                try:
                    if held and fcntl is not None:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    elif held and msvcrt is not None:
                        os.lseek(fd, 0, 0)
                        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
                os.close(fd)


def _read_state(path, tries=8):
    """The state as a dict: {} when there is no file yet; StateUnreadable when the file
    is there but won't read or parse after a few tries over ~0.4 s."""
    err = None
    for i in range(tries):
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            err = "not an object"
        except (IOError, OSError, ValueError) as exc:
            err = exc
        time.sleep(0.05)
    raise StateUnreadable(str(err))


def load_state():
    """state.json for reading (no lock needed: writes replace the file in one step).
    {} when it's missing or still unreadable after the retries (logged)."""
    try:
        return _read_state(STATE_FILE)
    except StateUnreadable as exc:
        log_err("state.json unreadable: %s" % exc)
        return {}


def update_state(changes=None, fn=None, path=None):
    """Change only the given keys of state.json, under the lock, on a fresh read.
    `changes`: {key: value or DELETE}.  `fn(st)`: changes the fresh dict in place;
    returning False skips the save.  Returns the saved dict, or None when nothing was
    saved (fn said no, or the file couldn't be read: then it's logged and left alone)."""
    path = path or STATE_FILE
    with _file_lock(path):
        try:
            st = _read_state(path)
        except StateUnreadable as exc:
            log_err("state.json unreadable (%s): not saved over; change skipped: %s"
                    % (exc, sorted((changes or {}).keys()) or getattr(fn, "__name__", "fn")))
            return None
        before = dict(st)
        for k, v in (changes or {}).items():
            if v is DELETE:
                st.pop(k, None)
            else:
                st[k] = v
        if fn is not None and fn(st) is False:
            return None
        if st != before:
            save_json(path, st)
        return st


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
        "skip_short": setting_int("skip_short", 2),
        "chapter_breaks": setting_bool("chapter_breaks", True),
        "seasons": seasons_cfg(),
        "reruns": setting_int("summer_reruns", 1),
        "rerun_today": setting("rerun_today", ""),     # hidden: a date for testing reruns
        "specials_today": setting("specials_today", ""),   # hidden: today's date for testing specials
        "promos": setting_bool("promos_on", True),
        "promo_every": setting_int("promo_every", 1),
        "promo_target": setting_int("promo_target", 2),
        "promo_extras": setting_bool("promo_extras", True),
        "house_breaks": setting_int("house_breaks", 1),
        # Retro ads: the promo style they follow (era ads), "" when off
        "retro_ads": (("modern" if setting_int("promo_style", 0) == 1 else "90s")
                      if setting_bool("retro_ads", True) else ""),
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
        if name == "halloween" and (out[name]["genres"] or "").replace(" ", "").lower() == "horror,mystery":
            out[name]["genres"] = "Horror"     # the old default (~all9 and before): plain Mystery was too broad
    from . import seasons                  # seasons.json: the editor's changes and the viewer's own seasons
    seasons.apply_file(out, load_json(seasons.path(), None))
    today = setting("seasons_today", "")   # hidden: a date for testing seasons (YYYY-MM-DD)
    if today:
        try:
            import time
            y, m, d = [int(x) for x in today.split("-")]
            lt = time.localtime()
            out["shift"] = (time.mktime((y, m, d, 0, 0, 0, 0, 0, -1))
                            - time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1)))
        except (ValueError, OverflowError):
            pass
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
