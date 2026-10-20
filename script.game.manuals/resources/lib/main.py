# -*- coding: utf-8 -*-
"""Show a game's manual, finding one first if the game has none."""

import json
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from . import budget, manuals, pages, positions

# An Addon object kept past the script's end is reported as a leak by Kodi
ADDON_ID = xbmcaddon.Addon().getAddonInfo("id")
ADDON_PATH = xbmcaddon.Addon().getAddonInfo("path")
#: Where a manual goes when there is nowhere beside the game to put it
PROFILE_MANUALS = "special://profile/addon_data/%s/manuals/" % ADDON_ID
POSITIONS = "special://profile/addon_data/%s/positions.json" % ADDON_ID
DOWNLOADED = "special://profile/addon_data/%s/downloaded.json" % ADDON_ID
#: What a player is told when the add-on that reads a kind of manual can't be had
READER_MISSING = {"vfs.pdf": 32038, "vfs.rar": 32040}


def localize(string_id):
    return xbmcaddon.Addon().getLocalizedString(string_id)


def log(message, level=xbmc.LOGINFO):
    xbmc.log("[%s] %s" % (ADDON_ID, message), level)


def jsonrpc(method, params):
    """A JSON-RPC call's result, or None if Kodi answered with an error."""
    answer = json.loads(xbmc.executeJSONRPC(json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params})))
    if "error" in answer:
        log("%s failed: %s" % (method, answer["error"]), xbmc.LOGERROR)
        return None
    return answer.get("result") or {}


def files_in(folder):
    # Asking for a folder that isn't there logs an error, and most games have
    # no manuals folder
    if not xbmcvfs.exists(folder):
        return []
    return xbmcvfs.listdir(folder)[1]


def read_text(path):
    if not xbmcvfs.exists(path):
        return None
    with xbmcvfs.File(path) as f:
        return f.read()


def write_text(path, text):
    xbmcvfs.mkdirs(manuals.folder_of(xbmcvfs.translatePath(path)))
    with xbmcvfs.File(path, "w") as f:
        f.write(text)


def downloads():
    return budget.Budget(DOWNLOADED, read_text, write_text)


def budget_bytes():
    """The space chosen for downloaded manuals."""
    return xbmcaddon.Addon().getSettingInt("budget") * budget.MEGABYTE


def keep_within_budget(store, keep):
    """Delete downloaded manuals, least recently read first, down to the chosen space."""
    for manual in store.enforce(budget_bytes(), keep, xbmcvfs.exists, xbmcvfs.delete):
        log("Deleted \"%s\" to stay within the space for downloaded manuals" % manual)


def locate(game):
    """The game's manual on disk, or ""."""
    found = manuals.find(game, xbmcvfs.exists, files_in)
    if found:
        return found
    for extension in manuals.EXTENSIONS:
        kept = manuals.join(PROFILE_MANUALS, manuals.profile_name(game, extension))
        if xbmcvfs.exists(kept):
            return kept
    return ""


def page_paths(manual):
    """Every page picture of a manual, in reading order."""
    folder = pages.pages_folder(manual)
    if not folder:
        return []
    names = []
    pending = [""]
    while pending:
        sub = pending.pop()
        dirs, files = xbmcvfs.listdir(folder + sub)
        names += [sub + f for f in files]
        pending += [sub + d + "/" for d in dirs]
    return [folder + name for name in pages.ordered_pictures(names)]


def reader_ready(manual):
    """Whether the add-on that reads this kind of manual is enabled, offering to
    install or enable it when it isn't."""
    addon_id = pages.reader_addon(manual)
    enabled = "System.AddonIsEnabled(%s)" % addon_id
    if not addon_id or xbmc.getCondVisibility(enabled):
        return True
    if xbmc.getCondVisibility("System.HasAddon(%s)" % addon_id):
        xbmc.executebuiltin("EnableAddon(%s)" % addon_id, True)
    else:
        xbmc.executebuiltin("InstallAddon(%s)" % addon_id, True)
    if xbmc.getCondVisibility(enabled):
        return True
    xbmcgui.Dialog().notification(localize(32000), localize(READER_MISSING[addon_id]),
                                  xbmcgui.NOTIFICATION_ERROR)
    return False


def fetch_with_progress(url, game):
    from . import fetch

    progress = xbmcgui.DialogProgressBG()
    progress.create(localize(32000), localize(32007))
    try:
        return fetch.download(url, game, lambda share: progress.update(int(share * 100)))
    finally:
        progress.close()


def run(args):
    from .finder import Finder, offer_disabled_provider
    from .viewer import Viewer

    arguments = manuals.parse_args(args)
    game, manual = arguments["game"], arguments["manual"]
    title = manuals.title_for(game, arguments["title"])
    # A library may know a manual only by where to fetch it. One already on
    # disk is read instead, so it is fetched once rather than on every visit.
    address = ""
    if manual.lower().startswith(("http://", "https://")):
        address, manual = manual, ""
    if not manual and game:
        manual = locate(game)
    if not manual and address:
        manual = fetch_with_progress(address, game)
        if not manual:
            xbmcgui.Dialog().notification(localize(32000), localize(32008), xbmcgui.NOTIFICATION_ERROR)
            return

    if not manual:
        if not game:
            return
        offer_disabled_provider()
        finder = Finder("script-game-manuals-finder.xml", ADDON_PATH, "Default", "1080i", game=game,
                        title=title)
        finder.doModal()
        manual = finder.downloaded
        del finder
        if not manual:
            return

    if not reader_ready(manual):
        return

    paths = page_paths(manual)
    if not paths:
        log("No pages in \"%s\"" % manual, xbmc.LOGERROR)
        xbmcgui.Dialog().notification(localize(32000), localize(32011), xbmcgui.NOTIFICATION_ERROR)
        return

    downloaded = downloads()
    downloaded.opened(manual, time.time())
    keep_within_budget(downloaded, manual)

    store = positions.Positions(POSITIONS, read_text, write_text)
    viewer = Viewer("script-game-manuals-viewer.xml", ADDON_PATH, "Default", "1080i",
                    manual=manual, title=title, pages=paths, positions=store)
    viewer.doModal()
    del viewer
