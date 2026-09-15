
import os
import re
import sys
import unicodedata

import xbmc
import xbmcaddon
import xbmcgui

from urllib.parse import parse_qsl

__addon__ = xbmcaddon.Addon("service.subtitles.opensubtitles-com")
__addon_name__ = __addon__.getAddonInfo("name")
__language__ = __addon__.getLocalizedString


# Temp files younger than this are considered possibly in use by an
# overlapping invocation. Shared by the downloader's temp cleanup and the
# Clear Cache script so the two can never disagree on what "active" means.
TEMP_MAX_AGE_SECONDS = 3600


def get_user_agent():
    """The ONE User-Agent for every outbound request (API, guessit, GitHub).

    Policy: a single identity everywhere - "Opensubtitles.com Kodi plugin v<version>".
    tests/test_utilities.py fails the suite if any file hardcodes its own.
    """
    return f"Opensubtitles.com Kodi plugin v{__addon__.getAddonInfo('version')}"


def _fully_unquote(s):
    """Percent-decode until nothing changes, or None to FAIL CLOSED.

    One unquote pass leaves an n-times-encoded delimiter ('%253F' ->
    '%3F') still hidden; decoding to fixpoint surfaces every layer so the
    strip that follows sees a literal '?'/'#'. A value still changing
    after 20 layers is adversarial by construction - return None so the
    caller drops the value entirely instead of passing residue through.
    """
    from urllib.parse import unquote
    for _ in range(20):
        decoded = unquote(s)
        if decoded == s:
            return s
        s = decoded
    return None


def redact_path(path):
    """A playback path safe for the debug log.

    Streaming and plugin URLs routinely carry access tokens in the query
    string or credentials in the userinfo part - and debug logs are exactly
    what users paste on public forums. Local paths pass through untouched;
    anything with a scheme loses query, fragment and userinfo.
    """
    try:
        s = str(path)
        if "://" not in s:
            return s
        from urllib.parse import urlsplit
        parts = urlsplit(s)
        # userinfo can hide behind percent-encoding ('user%3Apass%40host') -
        # decode the authority to fixpoint BEFORE splitting the credentials off
        netloc = _fully_unquote(parts.netloc)
        if netloc is None:
            return f"{parts.scheme}://[host redacted]"
        had_userinfo = "@" in netloc
        host = netloc.rsplit("@", 1)[-1]            # drop user:pass@
        # a percent-encoded '?token=' ('%3Ftoken%3D...', or nested
        # '%253F...') hides INSIDE the path component - decode to fixpoint
        # so every encoding layer surfaces, then strip
        clean_path = _fully_unquote(parts.path)
        if clean_path is None:
            # never emit residue we could not fully decode
            return f"{parts.scheme}://{host}/[path redacted]"
        encoded_smuggle = "?" in clean_path or "#" in clean_path
        clean_path = clean_path.split("?", 1)[0].split("#", 1)[0]
        redacted = f"{parts.scheme}://{host}{clean_path}"
        if parts.query or parts.fragment or encoded_smuggle or had_userinfo:
            redacted += "  [query/credentials redacted]"
        return redacted
    except Exception:
        return "[unloggable path]"


def safe_media_filename(path):
    """Filename derived from a playback path with NO credential residue.

    Order matters: strip the query at the URL layer, decode percent-encoding
    TO FIXPOINT, then strip again - '/video%3Ftoken%3DX' (or nested
    '%253F...') decodes into a fresh '?token=X' that fewer decode passes
    would leave inside the basename.
    """
    try:
        s = str(path)
        if "://" in s:
            from urllib.parse import urlsplit
            s = _fully_unquote(urlsplit(s).path)
            if s is None:
                # never let undecodable residue reach a search query
                return ""
            s = s.split("?", 1)[0].split("#", 1)[0]
        return os.path.basename(s)
    except Exception:
        return ""


# Keys whose values are the user's viewing history (titles, filenames,
# queries) - they must never appear verbatim in a shared debug log.
_HISTORY_KEYS = {"query", "tv_show_title", "original_title", "basename",
                 "filename", "file_path", "file_original_path",
                 "video_filename", "release"}


def loggable_media(mapping):
    """Mapping safe for the debug log, applied RECURSIVELY.

    URL values lose their query/credentials via redact_path; viewing-history
    values (titles, filenames, search queries) are reduced to a set/empty
    marker - presence is what debugging needs, the content is private.
    Recursion matters: fallback-attempt lists nest the same private keys."""
    def _clean(value):
        if isinstance(value, dict):
            # lstrip("_"): request objects expose the same keys as _query etc.
            return {k: ("<set>" if v else "<empty>")
                    if str(k).lstrip("_") in _HISTORY_KEYS
                    else _clean(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_clean(v) for v in value]
        if isinstance(value, str) and "://" in value:
            return redact_path(value)
        return value
    try:
        return _clean(dict(mapping))
    except Exception:
        return "[unloggable mapping]"


def log(module, msg):
    xbmc.log(f"### [{__addon_name__}:{module}] - {msg}", level=xbmc.LOGDEBUG)


_install_origin = None


def get_install_origin():
    """Repository id that installed this add-on, for the X-Kodi-Origin-Repo header.

    Kodi records the installing repository per add-on but exposes it nowhere in
    the Python API - only the addon database has it (installed.origin). Values:
    a repository id ('repository.opensubtitles-com', 'repository.xbmc.org'),
    'zip' for a manual zip install (empty origin in the DB), or 'unknown' when
    the DB cannot be read. Cached per process; read-only connection so we can
    never touch Kodi's DB state.
    """
    global _install_origin
    if _install_origin is None:
        _install_origin = "unknown"
        try:
            import glob
            import sqlite3
            import xbmcvfs
            db_dir = xbmcvfs.translatePath("special://database/")
            dbs = glob.glob(os.path.join(db_dir, "Addons*.db"))
            if dbs:
                # highest schema number = the database this Kodi actually uses
                newest = max(dbs, key=lambda p: int(re.sub(r"\D", "", os.path.basename(p)) or 0))
                con = sqlite3.connect(f"file:{newest}?mode=ro", uri=True)
                row = con.execute("SELECT origin FROM installed WHERE addonID = ?",
                                  (__addon__.getAddonInfo("id"),)).fetchone()
                con.close()
                if row is not None:
                    _install_origin = row[0] or "zip"
        except Exception:
            pass
    return _install_origin


# prints out msg to log and gives Kodi message with msg_id to user if msg_id provided
def error(module, msg_id=None, msg="", detail=""):
    if msg:
        message = msg
    elif msg_id:
        message = __language__(msg_id)
    else:
        message = "Add-on error with empty message"
    log(module, message)
    if msg_id:
        dialog_msg = f"{__language__(2103)}\n{__language__(msg_id)}"
        if detail:
            dialog_msg += f"\n\n[I]{detail}[/I]"
        xbmcgui.Dialog().ok(__addon_name__, dialog_msg)


def get_params(string=""):
    # always a dict: an empty query string used to return a LIST, and any
    # caller doing params.get(...) then crashed on the type mismatch
    param = {}
    if string == "":
        # a service invocation always carries argv[2], but RunScript and
        # crafted invocations may not - never IndexError over it
        param_string = sys.argv[2][1:] if len(sys.argv) > 2 else ""
    else:
        param_string = string

    if len(param_string) >= 2:
        param = dict(parse_qsl(param_string))

    return param


def normalize_string(str_):
    if not str_:
        return ""
    return unicodedata.normalize("NFC", str_)


def check_and_get_account_status():
    """Returns the current account status, checking 24-hour expiration."""
    verified_at = __addon__.getSetting("account_verified_at")
    status = __addon__.getSetting("account_status")

    if not status or not verified_at or verified_at == "0":
        return "Not Verified"

    try:
        import time
        age = time.time() - float(verified_at)
        if age > 86400:  # Older than 24 hours
            expired_status = "Expired (>24h)"
            __addon__.setSetting("account_status", expired_status)
            __addon__.setSetting("account_details", "Click Test Connection to re-verify")
            return expired_status
        return status
    except (ValueError, TypeError):
        return "Not Verified"

