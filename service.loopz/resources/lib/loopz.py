# -*- coding: utf-8 -*-
"""
Loopz for Kodi.

When an episode or a movie finishes here, Loopz asks the member "did you watch it?".
Nothing is marked watched from Kodi: the answer is given in the app.

Linking: the app shows a 6-digit code; the member types it in this add-on's
settings, and the add-on exchanges it for its own private link.
"""
import json
import os
import threading
import urllib.error
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON_ID = "service.loopz"
PAIR_URL = "https://loopztv.com/api/v1/home-server/kodi/pair"
FINISHED_AT = 0.9  # the same 90% Plex uses
MIN_LENGTH = 120  # trailers and samples are not watches

S_LINKED = 30010
S_NOT_LINKED = 30011
S_BAD_CODE = 30012
S_OFFLINE = 30013
S_BUSY = 30014


def addon():
    # a fresh instance reads the settings as they are now
    return xbmcaddon.Addon(ADDON_ID)


def tr(string_id):
    return addon().getLocalizedString(string_id)


def log(msg):
    xbmc.log("[%s] %s" % (ADDON_ID, msg), xbmc.LOGDEBUG)


def notify(string_id, error=False):
    # the add-on's own icon (the Loopz logo) on confirmations; errors keep Kodi's red icon so they read as errors
    icon = xbmcgui.NOTIFICATION_ERROR if error else addon().getAddonInfo("icon")
    xbmcgui.Dialog().notification("Loopz", tr(string_id), icon, 5000)


def version():
    return addon().getAddonInfo("version")


def link_file():
    folder = xbmcvfs.translatePath("special://profile/addon_data/%s" % ADDON_ID)
    return os.path.join(folder, "link.json")


def read_link():
    try:
        with open(link_file(), "r", encoding="utf-8") as f:
            url = json.load(f).get("webhook_url", "")
    except (OSError, ValueError, AttributeError):
        return ""
    return url if isinstance(url, str) and url.startswith("https://") else ""


def write_link(url):
    path = link_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"webhook_url": url}, f)


def show_status():
    addon().setSetting("status", tr(S_LINKED if read_link() else S_NOT_LINKED))


def post(url, payload):
    """POST JSON -> (status, body). Network failure -> (0, {})."""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "Loopz-Kodi/%s" % version()},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode("utf-8")
            status = r.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        status = e.code
    except (urllib.error.URLError, OSError, ValueError) as e:
        log("network: %s" % e)
        return 0, {}
    try:
        body = json.loads(raw or "{}")
    except ValueError:
        body = {}
    return status, body if isinstance(body, dict) else {}


# ---------------------------------------------------------------- linking

_pairing = threading.Lock()


def pair_from_settings():
    code = "".join(ch for ch in addon().getSetting("code") if ch.isdigit())
    if not code:
        return
    if not _pairing.acquire(blocking=False):
        return
    try:
        # the code is used once: clear it before anything else
        addon().setSetting("code", "")
        if len(code) != 6:
            notify(S_BAD_CODE, error=True)
            return
        device = xbmc.getInfoLabel("System.FriendlyName") or "Kodi"
        status, body = post(PAIR_URL, {"code": code, "device": device})
        url = body.get("webhook_url") if status == 200 and body.get("ok") else None
        if isinstance(url, str) and url.startswith("https://"):
            write_link(url)
            notify(S_LINKED)
        elif status == 0:
            notify(S_OFFLINE, error=True)
        elif status == 429:
            notify(S_BUSY, error=True)
        else:
            notify(S_BAD_CODE, error=True)
        show_status()
    finally:
        _pairing.release()


# ---------------------------------------------------------------- what is playing

def rpc(method, params):
    req = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        res = json.loads(xbmc.executeJSONRPC(json.dumps(req)))
    except ValueError:
        return {}
    out = res.get("result") if isinstance(res, dict) else None
    return out if isinstance(out, dict) else {}


def ids_of(uniqueid):
    """Kodi "uniqueid" {"tmdb": "1396", "imdb": "tt0903747", "tvdb": "81189"} -> what Loopz reads."""
    out = {}
    if not isinstance(uniqueid, dict):
        return out
    for key in ("tmdb", "tvdb"):
        v = str(uniqueid.get(key) or "").strip()
        if v.isdigit() and int(v) > 0:
            out[key] = int(v)
    imdb = str(uniqueid.get("imdb") or "").strip()
    if imdb.startswith("tt") and imdb[2:].isdigit():
        out["imdb"] = imdb
    return out


def tag_ids(tag):
    """Items from streaming add-ons are not in the library: read what they set on the tag."""
    raw = {}
    for key in ("tmdb", "imdb", "tvdb"):
        try:
            raw[key] = tag.getUniqueID(key)
        except (AttributeError, RuntimeError):
            pass
    if not raw.get("imdb"):
        try:
            raw["imdb"] = tag.getIMDBNumber()
        except (AttributeError, RuntimeError):
            pass
    return ids_of(raw)


def describe(tag):
    """The finished item as Loopz reads it, or None for what is not an episode or a movie."""
    kind = tag.getMediaType()
    dbid = tag.getDbId()
    if kind == "movie":
        item = {"type": "movie", "title": tag.getTitle(), "year": tag.getYear() or None, "ids": tag_ids(tag)}
        if dbid and dbid > 0:
            d = rpc("VideoLibrary.GetMovieDetails", {"movieid": dbid, "properties": ["uniqueid", "year", "title"]})
            d = d.get("moviedetails") or {}
            item["ids"] = ids_of(d.get("uniqueid")) or item["ids"]
            item["title"] = d.get("title") or item["title"]
            item["year"] = d.get("year") or item["year"]
        return item if item["title"] or item["ids"] else None
    if kind != "episode":
        return None
    item = {
        "type": "episode",
        "title": tag.getTVShowTitle(),
        "season": tag.getSeason(),
        "episode": tag.getEpisode(),
        "ids": tag_ids(tag),
    }
    if dbid and dbid > 0:
        d = rpc(
            "VideoLibrary.GetEpisodeDetails",
            {"episodeid": dbid, "properties": ["tvshowid", "season", "episode", "showtitle", "uniqueid"]},
        )
        d = d.get("episodedetails") or {}
        item["ids"] = ids_of(d.get("uniqueid")) or item["ids"]
        item["title"] = d.get("showtitle") or item["title"]
        if isinstance(d.get("season"), int):
            item["season"] = d["season"]
        if isinstance(d.get("episode"), int):
            item["episode"] = d["episode"]
        show_id = d.get("tvshowid")
        if isinstance(show_id, int) and show_id > 0:
            s = rpc("VideoLibrary.GetTVShowDetails", {"tvshowid": show_id, "properties": ["uniqueid"]})
            show = ids_of((s.get("tvshowdetails") or {}).get("uniqueid"))
            if show:
                item["show"] = show
    if not isinstance(item["season"], int) or item["season"] < 0:
        return None
    if not isinstance(item["episode"], int) or item["episode"] < 1:
        return None
    return item


def send(item):
    url = read_link()
    if not url:
        return
    payload = dict(item, server="kodi", event="finished")
    for attempt in range(2):
        status, _ = post(url, payload)
        if status:
            return
        if attempt == 0:
            xbmc.Monitor().waitForAbort(30)
    log("could not reach Loopz")


class Player(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.item = None
        self.pos = 0.0
        self.total = 0.0

    def onAVStarted(self):
        self.finish()  # a playlist moving on: the previous item ended here
        if not self.isPlayingVideo() or not read_link():
            return
        try:
            self.item = describe(self.getVideoInfoTag())
        except RuntimeError as e:
            log("describe: %s" % e)
            self.item = None
        self.pos, self.total = 0.0, 0.0

    def tick(self):
        if self.item is None:
            return
        try:
            if self.isPlayingVideo():
                self.pos, self.total = self.getTime(), self.getTotalTime()
        except RuntimeError:
            return
        # past 90% counts now, while it still plays: Back only hides the video, and quitting Kodi may not
        # leave time to send — finish() clears the item, so it is sent once
        if self.total >= MIN_LENGTH and self.pos / self.total >= FINISHED_AT:
            self.finish()

    def finish(self):
        item, pos, total = self.item, self.pos, self.total
        self.item = None
        # the last position seen decides, ended or stopped: 90% and a real length
        if item is None or total < MIN_LENGTH or pos / total < FINISHED_AT:
            return
        threading.Thread(target=send, args=(item,), daemon=True).start()

    def onPlayBackEnded(self):
        self.finish()

    def onPlayBackStopped(self):
        self.finish()

    def onPlayBackError(self):
        self.item = None


class Monitor(xbmc.Monitor):
    def onSettingsChanged(self):
        threading.Thread(target=pair_from_settings, daemon=True).start()


def main():
    monitor = Monitor()
    player = Player()
    show_status()
    pair_from_settings()  # a code typed while Kodi was closing
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break
        player.tick()
