import json
import re
import sys
import threading
import time

import os

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_PATH = ADDON.getAddonInfo("path")
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))

KINDS = ("video", "music", "pictures")
# Kodi only has a video and a music library. Pictures have none: their files are counted instead
LIBRARY_KINDS = ("video", "music")
PICTURES_FILE = os.path.join(PROFILE, "pictures.json")

SCANNING_FLAG = {
    "video": "Library.IsScanningVideo",
    "music": "Library.IsScanningMusic",
}

LIBRARY_LABEL = {"video": 30045, "music": 30046, "pictures": 30047}

LIBRARIES = {
    "video": [
        (30030, "VideoLibrary.GetMovies", "movies"),
        (30031, "VideoLibrary.GetTVShows", "tvshows"),
        (30032, "VideoLibrary.GetEpisodes", "episodes"),
        (30035, "VideoLibrary.GetMusicVideos", "musicvideos"),
    ],
    "music": [
        (30036, "AudioLibrary.GetArtists", "artists"),
        (30033, "AudioLibrary.GetAlbums", "albums"),
        (30034, "AudioLibrary.GetSongs", "songs"),
    ],
}

REPORT_MODES = ("dialog", "notification", "none")

# Scanning only adds: what is no longer on disk stays in the library until it is cleaned
CLEAN_METHOD = {"video": "VideoLibrary.Clean", "music": "AudioLibrary.Clean"}

GREEN = "FF7FD36E"
RED = "FFE06C6C"
GREY = "FFAAAAAA"

SCAN_START_TIMEOUT = 3.0
POLL_INTERVAL = 0.5

# Home window property set while a scan runs, so a second launch does not start another one
RUNNING_PROPERTY = "%s.running" % ADDON_ID
HOME_WINDOW = 10000

# Actions that close the summary
CLOSE_ACTIONS = (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_STOP)
# Moving around stops the countdown so the summary can be read. Only these: Kodi also sends the
# window actions nobody pressed (screenshots, for example)
STOP_COUNTDOWN_ACTIONS = (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_MOVE_UP,
                          xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_PAGE_UP, xbmcgui.ACTION_PAGE_DOWN)


def _(string_id):
    return ADDON.getLocalizedString(string_id)


def fmt(string_id, value):
    """A translated string with its number. Kodi keeps an add-on's strings in memory until it restarts,
    so right after an update a new string can be empty: the number is still shown."""
    text = _(string_id)
    return text % value if "%d" in text else str(value)


def log(message, level=xbmc.LOGINFO):
    xbmc.log("[%s] %s" % (ADDON_ID, message), level)


def parse_args(argv):
    """Options passed by RunScript(script.program.quicksync,key=value,...) or JSON-RPC Addons.ExecuteAddon.

    report=dialog|notification|none  how to show the result (default: the add-on settings)
    library=video|music|pictures|all libraries to scan (default: the add-on settings)
    clean=true|false                  remove what is no longer available (default: the add-on settings)
    """
    options = {}
    for arg in argv:
        key, sep, value = arg.partition("=")
        if sep:
            options[key.strip().lower()] = value.strip().lower()
    return options


def library_total(method):
    payload = {
        "jsonrpc": "2.0",
        "id": "quicksync",
        "method": method,
        "params": {"limits": {"start": 0, "end": 0}},
    }
    result = json.loads(xbmc.executeJSONRPC(json.dumps(payload)))
    return result.get("result", {}).get("limits", {}).get("total", 0)


def snapshot(kinds):
    return {method: library_total(method) for kind in kinds if kind in LIBRARIES for _, method, _ in LIBRARIES[kind]}


def picture_sources():
    payload = {"jsonrpc": "2.0", "id": "quicksync", "method": "Files.GetSources", "params": {"media": "pictures"}}
    result = json.loads(xbmc.executeJSONRPC(json.dumps(payload)))
    return [source["file"] for source in result.get("result", {}).get("sources", [])]


def count_pictures(monitor):
    """Pictures in Kodi's picture sources, with the extensions Kodi shows. None when there is no source."""
    sources = picture_sources()
    if not sources:
        return None
    extensions = tuple(ext for ext in xbmc.getSupportedMedia("picture").lower().split("|") if ext)
    total = 0
    pending = list(sources)
    seen = set()
    while pending:
        if monitor.abortRequested():
            break
        folder = pending.pop()
        if folder in seen:  # A source inside another one, or a link back up
            continue
        seen.add(folder)
        try:
            dirs, files = xbmcvfs.listdir(folder)
        except Exception as error:  # Unreachable network share: counted as empty
            log("Cannot read %s: %s" % (folder, error), xbmc.LOGWARNING)
            continue
        sep = "\\" if "\\" in folder and "/" not in folder else "/"
        base = folder if folder.endswith(("/", "\\")) else folder + sep
        total += sum(1 for name in files if name.lower().endswith(extensions))
        pending.extend(base + name + sep for name in dirs if not name.startswith("."))
    log("Pictures in %d source(s): %d" % (len(sources), total))
    return total


def previous_pictures():
    try:
        with open(PICTURES_FILE, encoding="utf-8") as handle:
            return int(json.load(handle)["total"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def save_pictures(total):
    try:
        os.makedirs(PROFILE, exist_ok=True)
        with open(PICTURES_FILE, "w", encoding="utf-8") as handle:
            json.dump({"total": total, "at": int(time.time())}, handle)
    except OSError as error:
        log("Cannot save the picture count: %s" % error, xbmc.LOGWARNING)


def is_scanning(kind):
    return xbmc.getCondVisibility(SCANNING_FLAG[kind])


def wait_for_job(kind, monitor):
    """Waits for the scan or clean just requested. Returns False when Kodi did not start it.

    Library.IsScanningVideo/Music is also true while the library is being cleaned.
    """
    # waitForAbort() returns True as soon as Kodi asks add-ons to stop
    deadline = time.monotonic() + SCAN_START_TIMEOUT
    while time.monotonic() < deadline:
        if is_scanning(kind):
            while is_scanning(kind):
                if monitor.waitForAbort(POLL_INTERVAL):
                    return True
            return True
        if monitor.waitForAbort(0.25):
            return True
    return False


def run_scan(kind, monitor):
    """Returns False when Kodi did not start the scan (no source with a content type, for example)."""
    log("Triggering UpdateLibrary(%s)" % kind)
    xbmc.executebuiltin("UpdateLibrary(%s)" % kind)
    if wait_for_job(kind, monitor):
        log("Scan of %s finished" % kind)
        return True
    log("Kodi did not start the %s scan (nothing to update)" % kind)
    return False


def run_clean(kind, monitor):
    """Removes from the library the items whose files are gone. Kodi keeps the items of a source it
    cannot reach (a network share that is off), so they are not lost.

    JSON-RPC with showdialogs=false: the CleanLibrary() builtin opens a modal progress dialog.
    """
    log("Cleaning the %s library" % kind)
    payload = {"jsonrpc": "2.0", "id": "quicksync", "method": CLEAN_METHOD[kind],
               "params": {"showdialogs": False}}
    xbmc.executeJSONRPC(json.dumps(payload))
    # A clean with nothing to do can be over before it is seen: the counts tell what it did anyway
    wait_for_job(kind, monitor)
    log("Clean of %s finished" % kind)


def enabled_in_settings(kind):
    return ADDON.getSetting("scan_" + kind) == "true"


def clean_enabled(options):
    value = options.get("clean")
    if value in ("true", "false"):
        return value == "true"
    return ADDON.getSetting("clean_library") != "false"


def count_line(label, total, added, removed):
    line = "%s: %d" % (label, total)
    if added > 0:
        line += "  [COLOR %s](+%d)[/COLOR]" % (GREEN, added)
    if removed > 0:
        line += "  [COLOR %s](-%d)[/COLOR]" % (RED, removed)
    return line


def build_report(kinds, before, scanned, after, started, pictures=None, cleaned=False):
    """Summary of every library: the scanned ones with their totals, what is new and what was removed,
    the others with why not.

    before/scanned/after are the totals before the scan, after the scan and after the clean: the scan
    only adds and the clean only removes, so a movie replaced by another one shows up in both.

    Returns (text with Kodi formatting tags, plain text, new items, added per type, removed items,
    removed per type).
    """
    lines = []
    added = {}
    removed = {}
    for kind in KINDS:
        if lines:
            lines.append("")
        lines.append("[B]%s[/B]" % _(LIBRARY_LABEL[kind]))
        if kind not in kinds:
            # 30042: off in the settings; 30043: on, but this launch asked for other libraries
            lines.append("[COLOR %s]%s[/COLOR]" % (GREY, _(30043 if enabled_in_settings(kind) else 30042)))
            continue
        if kind == "pictures":
            total, previous = pictures or (None, None)
            if total is None:
                lines.append("[COLOR %s]%s[/COLOR]" % (GREY, _(30048)))
            elif previous is None:
                lines.append("%s: %d" % (_(30050), total))
                lines.append("[COLOR %s]%s[/COLOR]" % (GREY, _(30049)))
            else:
                # Only the total is known: a picture replaced by another one is not seen
                delta = total - previous
                added["pictures"] = max(delta, 0)
                removed["pictures"] = max(-delta, 0)
                lines.append(count_line(_(30050), total, delta, -delta))
            continue
        if not started.get(kind, True):
            lines.append("[COLOR %s]%s[/COLOR]" % (GREY, _(30044)))
        for label_id, method, key in LIBRARIES[kind]:
            added[key] = max(scanned[method] - before[method], 0)
            removed[key] = max(scanned[method] - after[method], 0)
            lines.append(count_line(_(label_id), after[method], added[key], removed[key]))
    new_items = sum(added.values())
    removed_items = sum(removed.values())
    lines.append("")
    lines.append("[B]%s[/B]" % (fmt(30022, new_items) if new_items else _(30024)))
    if removed_items:
        lines.append("[B]%s[/B]" % fmt(30025, removed_items))
    elif cleaned:
        lines.append("[COLOR %s]%s[/COLOR]" % (GREY, _(30026)))
    text = "\n".join(lines)
    plain = re.sub(r"\[/?(B|COLOR[^\]]*)\]", "", text)
    return text, plain, new_items, added, removed_items, removed


def selected_kinds(options):
    library = options.get("library")
    if library in KINDS:
        return [library]
    if library == "all":
        return list(KINDS)
    return [kind for kind in KINDS if enabled_in_settings(kind)]


def report_mode(options):
    mode = options.get("report")
    if mode in REPORT_MODES:
        return mode
    return "dialog" if ADDON.getSetting("show_report") == "true" else "notification"


def report_timeout():
    """Seconds before the summary closes by itself, or 0 when automatic closing is off."""
    if ADDON.getSetting("auto_close") != "true":
        return 0
    try:
        return max(1, int(float(ADDON.getSetting("report_timeout") or 15)))
    except ValueError:
        return 15


def notify_all(message, data):
    """JSON-RPC clients and service add-ons receive it as Other.<message>, sent by this add-on.

    JSONRPC.NotifyAll rather than the NotifyAll() builtin: builtin parameters are split on commas.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": "quicksync",
        "method": "JSONRPC.NotifyAll",
        "params": {"sender": ADDON_ID, "message": message, "data": data},
    }
    xbmc.executeJSONRPC(json.dumps(payload))


class SummaryDialog(xbmcgui.WindowXMLDialog):
    """Taller than Dialog().ok() and with a countdown. Pressing up or down stops the countdown."""

    HEADING, TEXT, COUNTDOWN, OK_BUTTON = 2, 3, 4, 10

    def setup(self, heading, text, timeout, monitor):
        self.heading = heading
        self.text = text
        self.timeout = timeout
        self.monitor = monitor
        self.stopped = threading.Event()

    def onInit(self):
        self.getControl(self.HEADING).setLabel(self.heading)
        self.getControl(self.TEXT).setText(self.text)
        self.getControl(self.COUNTDOWN).setLabel("")
        if self.timeout:
            threading.Thread(target=self.countdown, daemon=True).start()

    def countdown(self):
        for remaining in range(self.timeout, 0, -1):
            if self.stopped.is_set():
                return
            self.getControl(self.COUNTDOWN).setLabel(fmt(30040, remaining))
            if self.monitor.waitForAbort(1) or self.stopped.is_set():
                return
        self.stopped.set()
        self.close()

    def stop_countdown(self):
        if self.timeout and not self.stopped.is_set():
            self.stopped.set()
            self.getControl(self.COUNTDOWN).setLabel(_(30041))

    def finish(self):
        self.stopped.set()
        self.close()

    def onClick(self, control_id):
        if control_id == self.OK_BUTTON:
            self.finish()

    def onAction(self, action):
        if action.getId() in CLOSE_ACTIONS:
            self.finish()
        elif action.getId() in STOP_COUNTDOWN_ACTIONS:
            self.stop_countdown()


def show_dialog(report, plain, timeout, monitor):
    try:
        dialog = SummaryDialog("script-quicksync-summary.xml", ADDON_PATH, "default", "1080i")
    except RuntimeError as error:  # Skin files missing or unreadable: Kodi's own dialog, without countdown
        log("Summary dialog not available (%s), using the OK dialog" % error, xbmc.LOGWARNING)
        xbmcgui.Dialog().ok(ADDON_NAME, plain)
        return
    dialog.setup(ADDON_NAME, report, timeout, monitor)
    dialog.doModal()
    del dialog


def main(argv=None):
    options = parse_args(sys.argv[1:] if argv is None else argv)
    monitor = xbmc.Monitor()
    mode = report_mode(options)
    home = xbmcgui.Window(HOME_WINDOW)

    kinds = selected_kinds(options)
    if not kinds:
        if mode != "none":
            xbmcgui.Dialog().ok(ADDON_NAME, _(30020))
        notify_all("OnScanFinished", {"status": "nothing-selected"})
        return

    if home.getProperty(RUNNING_PROPERTY) or any(is_scanning(kind) for kind in kinds if kind in LIBRARY_KINDS):
        if mode != "none":
            xbmcgui.Dialog().notification(ADDON_NAME, _(30021), xbmcgui.NOTIFICATION_INFO, 4000)
        log("A scan is already running, not starting another one")
        return

    home.setProperty(RUNNING_PROPERTY, "true")
    try:
        clean = clean_enabled(options)
        log("Starting (libraries: %s, report: %s, clean: %s)" % (", ".join(kinds), mode, clean))
        notify_all("OnScanStarted", {"libraries": kinds})
        before = snapshot(kinds)
        started = {}
        pictures = None
        for kind in kinds:
            if kind == "pictures":
                previous = previous_pictures()
                total = count_pictures(monitor)
                if total is not None:
                    save_pictures(total)
                pictures = (total, previous)
            else:
                started[kind] = run_scan(kind, monitor)
            if monitor.abortRequested():
                log("Kodi is shutting down, skipping the summary")
                return

        scanned = snapshot(kinds)
        cleaned = False
        if clean:
            for kind in kinds:
                if kind in CLEAN_METHOD:
                    run_clean(kind, monitor)
                    cleaned = True
                    if monitor.abortRequested():
                        log("Kodi is shutting down, skipping the summary")
                        return
        after = snapshot(kinds) if cleaned else scanned

        report, plain, new_items, added, removed_items, removed = build_report(
            kinds, before, scanned, after, started, pictures, cleaned)
        log(plain.replace("\n", " | "))
        skipped = [kind for kind in KINDS if kind not in kinds]
        notify_all("OnScanFinished", {"status": "done", "libraries": kinds, "skipped": skipped,
                                      "new": new_items, "added": added, "cleaned": cleaned,
                                      "removed_total": removed_items, "removed": removed})
    finally:
        # Cleared before the summary: a dialog left open must not block the next scan
        home.clearProperty(RUNNING_PROPERTY)

    if mode == "dialog":
        show_dialog(report, plain, report_timeout(), monitor)
    elif mode == "notification":
        if new_items > 0 or removed_items > 0:
            parts = [fmt(30022, new_items) if new_items else _(30023)]
            if removed_items:
                parts.append(fmt(30027, removed_items))
            xbmcgui.Dialog().notification(ADDON_NAME, ", ".join(parts), xbmcgui.NOTIFICATION_INFO, 5000)
        else:
            xbmcgui.Dialog().notification(ADDON_NAME, _(30023), xbmcgui.NOTIFICATION_INFO, 4000)


if __name__ == "__main__":
    main()
