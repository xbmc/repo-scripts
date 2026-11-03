import json
import time

import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_NAME = ADDON.getAddonInfo("name")

SCANNING_FLAG = {
    "video": "Library.IsScanningVideo",
    "music": "Library.IsScanningMusic",
}

LIBRARIES = {
    "video": [
        (30030, "VideoLibrary.GetMovies"),
        (30031, "VideoLibrary.GetTVShows"),
        (30032, "VideoLibrary.GetEpisodes"),
    ],
    "music": [
        (30033, "AudioLibrary.GetAlbums"),
        (30034, "AudioLibrary.GetSongs"),
    ],
}

SCAN_START_TIMEOUT = 3.0
POLL_INTERVAL = 0.5


def _(string_id):
    return ADDON.getLocalizedString(string_id)


def log(message, level=xbmc.LOGINFO):
    xbmc.log("[%s] %s" % (ADDON_ID, message), level)


def library_total(method):
    payload = {
        "jsonrpc": "2.0",
        "id": "quicksync",
        "method": method,
        "params": {"limits": {"start": 0, "end": 0}},
    }
    result = json.loads(xbmc.executeJSONRPC(json.dumps(payload)))
    return result.get("result", {}).get("limits", {}).get("total", 0)


def snapshot():
    return {method: library_total(method) for entries in LIBRARIES.values() for _, method in entries}


def is_scanning(kind):
    return xbmc.getCondVisibility(SCANNING_FLAG[kind])


def run_scan(kind, monitor):
    log("Triggering UpdateLibrary(%s)" % kind)
    xbmc.executebuiltin("UpdateLibrary(%s)" % kind)

    # waitForAbort() returns True as soon as Kodi asks add-ons to stop
    deadline = time.monotonic() + SCAN_START_TIMEOUT
    while time.monotonic() < deadline:
        if is_scanning(kind):
            while is_scanning(kind):
                if monitor.waitForAbort(POLL_INTERVAL):
                    return
            log("Scan of %s finished" % kind)
            return
        if monitor.waitForAbort(0.25):
            return

    log("Kodi did not start the %s scan (nothing to update)" % kind)


def build_report(kinds, before, after):
    lines = []
    new_items = 0
    for kind in kinds:
        for label_id, method in LIBRARIES[kind]:
            delta = after[method] - before[method]
            new_items += max(delta, 0)
            if delta > 0:
                lines.append("%s: %d  (+%d)" % (_(label_id), after[method], delta))
            else:
                lines.append("%s: %d" % (_(label_id), after[method]))
    if new_items == 0:
        lines.append("")
        lines.append(_(30024))
    return "\n".join(lines), new_items


def selected_kinds():
    return [kind for kind in ("video", "music") if ADDON.getSetting("scan_" + kind) == "true"]


def main():
    monitor = xbmc.Monitor()

    kinds = selected_kinds()
    if not kinds:
        xbmcgui.Dialog().ok(ADDON_NAME, _(30020))
        return

    if any(is_scanning(kind) for kind in kinds):
        xbmcgui.Dialog().notification(ADDON_NAME, _(30021), xbmcgui.NOTIFICATION_INFO, 4000)
        return

    before = snapshot()
    for kind in kinds:
        run_scan(kind, monitor)
        if monitor.abortRequested():
            log("Kodi is shutting down, skipping the summary")
            return

    after = snapshot()
    report, new_items = build_report(kinds, before, after)
    log(report)

    if ADDON.getSetting("show_report") == "true":
        xbmcgui.Dialog().ok(ADDON_NAME, report)
    elif new_items > 0:
        xbmcgui.Dialog().notification(
            ADDON_NAME, _(30022) % new_items, xbmcgui.NOTIFICATION_INFO, 5000)
    else:
        xbmcgui.Dialog().notification(ADDON_NAME, _(30023), xbmcgui.NOTIFICATION_INFO, 4000)


if __name__ == "__main__":
    main()
