"""The Kodi side: read the player, draw the list, save the file.

service.py puts this directory on the path and calls main(); Kodi's checker wants
the entry point itself kept to a few lines. Everything that can be decided without
Kodi is in logic.py and is tested there. What is left here is the part only a media
centre can run.
"""


import json
import os
import sys

try:
    from urllib.parse import parse_qsl, unquote, urlencode
except ImportError:  # pragma: no cover - Kodi 18 and older
    from urllib import unquote, urlencode  # type: ignore[attr-defined,no-redef]

    from urlparse import parse_qsl  # type: ignore[import-not-found,no-redef]

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
PROFILE = ADDON.getAddonInfo("profile")

import logic  # noqa: E402
from subtitledb import SubtitleDbError, per_language  # noqa: E402

HANDLE = int(sys.argv[1])


def log(message, level=xbmc.LOGDEBUG):
    xbmc.log("[%s] %s" % (ADDON_ID, message), level)


def notify(message):
    xbmcgui.Dialog().notification(
        ADDON.getAddonInfo("name"), message, xbmcgui.NOTIFICATION_INFO, 4000
    )


def temp_dir():
    """A directory of our own under the addon profile, emptied on each download.

    Kodi keeps playing whatever it was handed, so clearing this at download time
    rather than at exit leaves nothing behind between films and never pulls a file
    out from under the player.
    """
    path = xbmcvfs.translatePath(os.path.join(PROFILE, "subs"))
    if xbmcvfs.exists(path):
        _dirs, files = xbmcvfs.listdir(path)
        for name in files:
            xbmcvfs.delete(os.path.join(path, name))
    else:
        xbmcvfs.mkdirs(path)
    return path


def playing_file():
    """The file Kodi is playing, or "" once playback has stopped.

    Kodi raises rather than answering "nothing", and playback can stop between the
    dialog opening and the search running.
    """
    try:
        return xbmc.Player().getPlayingFile()
    except RuntimeError:
        return ""


def show_imdb():
    """The IMDb id of the show the playing episode belongs to, from Kodi's library.

    An episode scraped from TVDB or TMDB often has no IMDb id of its own, and its
    show nearly always has one.
    """
    show = xbmc.getInfoLabel("VideoPlayer.TvShowDBID")
    if not show.isdigit():
        return ""
    request = {"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.GetTVShowDetails",
               "params": {"tvshowid": int(show), "properties": ["uniqueid"]}}
    try:
        reply = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    except (TypeError, ValueError):
        return ""
    details = (reply.get("result") or {}).get("tvshowdetails") or {}
    return (details.get("uniqueid") or {}).get("imdb") or ""


def player_info():
    """What Kodi believes it is playing.

    IMDBNumber is the item's default id, which Kodi's own TMDB and TVDB scrapers
    make theirs, so the IMDb and TMDB ids are read by name as well.
    """
    return {
        "path": playing_file(),
        "title": xbmc.getInfoLabel("VideoPlayer.Title"),
        "original_title": xbmc.getInfoLabel("VideoPlayer.OriginalTitle"),
        "year": xbmc.getInfoLabel("VideoPlayer.Year"),
        "tvshow": xbmc.getInfoLabel("VideoPlayer.TVshowtitle"),
        "season": xbmc.getInfoLabel("VideoPlayer.Season"),
        "episode": xbmc.getInfoLabel("VideoPlayer.Episode"),
        "imdb": xbmc.getInfoLabel("VideoPlayer.UniqueID(imdb)"),
        "imdb_number": xbmc.getInfoLabel("VideoPlayer.IMDBNumber"),
        "tmdb": xbmc.getInfoLabel("VideoPlayer.UniqueID(tmdb)"),
        "tvshow_imdb": show_imdb(),
    }


def draw(items):
    lines = ADDON.getLocalizedString(32013)
    for item in items:
        entry = xbmcgui.ListItem(label=item["language_name"], label2=logic.describe(item, lines))
        entry.setArt({"icon": str(item["rating"]), "thumb": item["language_code"]})
        entry.setProperty("sync", "true" if item["sync"] else "false")
        entry.setProperty("hearing_imp", "true" if item["hearing_impaired"] else "false")
        url = "plugin://%s/?%s" % (
            ADDON_ID,
            urlencode({"action": "download", "id": item["id"], "format": item["format"],
                       "url": item["download_url"]}),
        )
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=entry, isFolder=False)


def do_search(params):
    languages = [unquote(x) for x in (params.get("languages") or "").split(",") if x]
    if params.get("action") == "manualsearch" and params.get("searchstring"):
        info = {"title": params["searchstring"], "path": playing_file()}
    else:
        info = player_info()
        if not info["path"]:
            # The labels keep the last thing played, so with no file they describe
            # something that is no longer on screen.
            log("nothing is playing")
            return

    log("searching for %s" % logic.hint_from(info))
    client = logic.make_client(ADDON.getSetting("api_base") or None)
    try:
        items = logic.search(client, info, languages,
                             limit=per_language(ADDON.getSetting("per_language")), log=log)
    except SubtitleDbError as err:
        log("search failed: %s" % err, xbmc.LOGERROR)
        notify(ADDON.getLocalizedString(32011))
        return
    log("%d subtitles for %s" % (len(items), info.get("path")))
    draw(items)


def do_download(params):
    item = {"id": int(params.get("id") or 0), "format": params.get("format") or "srt"}
    client = logic.make_client(ADDON.getSetting("api_base") or None)
    try:
        content = client.download(params.get("url") or "")
    except SubtitleDbError as err:
        log("download failed: %s" % err, xbmc.LOGERROR)
        notify(ADDON.getLocalizedString(32012))
        return

    path = os.path.join(temp_dir(), logic.filename_for(item))
    handle = xbmcvfs.File(path, "wb")
    try:
        handle.write(bytearray(content))
    finally:
        handle.close()

    entry = xbmcgui.ListItem(label=path)
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=path, listitem=entry, isFolder=False)


def main():
    params = dict(parse_qsl(sys.argv[2].lstrip("?")))
    action = params.get("action")
    if action in ("search", "manualsearch"):
        do_search(params)
    elif action == "download":
        do_download(params)
    xbmcplugin.endOfDirectory(HANDLE)


if __name__ == "__main__":
    main()
