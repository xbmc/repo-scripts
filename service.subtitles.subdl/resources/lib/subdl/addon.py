"""The Kodi side: read the player, list SubDL's subtitles, save the one chosen.

service.py puts resources/lib on the path and calls run(); the settings button runs
check_key.py, which calls check_key(). Everything that can be decided without Kodi
lives in the other modules of this package and is tested there.

Logging rule: no API key, address, title, file name or search text ever reaches
Kodi's log, which viewers paste into public forum threads. Only the kind of request,
HTTP status and counts are logged.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
import traceback
import uuid
from datetime import datetime, timezone
from typing import Callable, List, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from . import api, archive, languages, query, releases, results
from .api import SubDLError

ADDON_ID = "service.subtitles.subdl"
HOME_WINDOW = 10000
TEMP_MAX_AGE_S = 3600
_PLATFORMS = (
    ("Android", "System.Platform.Android"),
    ("Xbox", "System.Platform.UWP"),
    ("Windows", "System.Platform.Windows"),
    ("tvOS", "System.Platform.TVOS"),
    ("iOS", "System.Platform.IOS"),
    ("macOS", "System.Platform.OSX"),
    ("webOS", "System.Platform.WebOS"),
    ("Linux", "System.Platform.Linux"),
)
_VARIANT_LABELS = {"simplified": 32231, "traditional": 32230, "cyrillic": 32232, "canada": 32233}


def log(message: str) -> None:
    """Kodi's add-on rules ask for the debug level only."""
    xbmc.log("[%s] %s" % (ADDON_ID, message), xbmc.LOGDEBUG)


# ---- entry points ---------------------------------------------------------------


def run(argv: Sequence[str]) -> None:
    """Called by Kodi's subtitle dialog with action=search, manualsearch or download."""
    handle = int(argv[1]) if len(argv) > 1 and str(argv[1]).lstrip("-").isdigit() else -1
    params = dict(parse_qsl(str(argv[2]).lstrip("?"))) if len(argv) > 2 else {}
    action = params.get("action", "")
    addon = xbmcaddon.Addon(ADDON_ID)
    try:
        if action in ("search", "manualsearch"):
            search(addon, handle, params)
        elif action == "download":
            download(addon, handle, params)
    except SubDLError as error:
        report(addon, error, action)
    except Exception as error:  # noqa: BLE001 - Kodi's dialog must always get its answer
        log("%s failed: %s at %s" % (action, type(error).__name__, _where(error)))
        notify(addon, 32212 if action == "download" else 32216)
    finally:
        if handle >= 0:
            xbmcplugin.endOfDirectory(handle)


def check_key() -> None:
    """The settings button: does the key work, and how much of today is used.

    Kodi runs the button's script outside the add-on's context, where Addon() without
    an id raises, so the id is always given.
    """
    addon = xbmcaddon.Addon(ADDON_ID)
    try:
        body = client(addon).account()
    except SubDLError as error:
        report(addon, error, "check", always_dialog=True)
        return
    except Exception as error:  # noqa: BLE001
        log("check failed: %s at %s" % (type(error).__name__, _where(error)))
        notify(addon, 32216)
        return
    # Kodi's OK dialog shows four lines, so the verdict goes in its title.
    xbmcgui.Dialog().ok(addon.getLocalizedString(32220), "[CR]".join(account_lines(addon, body)))


# ---- search ---------------------------------------------------------------------


def search(addon, handle: int, params: dict) -> None:
    subdl = client(addon)  # raises SubDLError when the key is missing
    wanted = wanted_languages(params)
    if not wanted:
        notify(addon, 32211)
        return
    item = playing_item()
    if params.get("action") == "manualsearch":
        plan = query.build_manual_plan(params.get("searchstring", ""), item)
    else:
        plan = query.build_plan(item)
    if not plan:
        log("search: nothing known about the video to search with")
        return
    hearing = _int(addon.getSetting("hearing_impaired")) or results.HI_ALL
    packs = addon.getSetting("season_packs") != "false"
    entries, target = find(subdl, plan, wanted, item.filename, hearing, packs)
    stacked = params.get("stack") == "1"
    for entry in entries:
        add_row(addon, handle, entry, target, stacked)


def find(subdl: api.SubDLClient, plan: List[query.Attempt], wanted: List[str], video: str,
         hearing: int, packs: bool) -> Tuple[List[results.Entry], Optional[tuple]]:
    """Run the plan until one attempt finds a title; that title's rows, best first."""
    for attempt in plan:
        params = dict(attempt.params, languages=",".join(wanted), subs_per_page=str(api.PAGE_SIZE), releases="1")
        if attempt.episode is not None and packs:
            params["unpack"] = "1"
        if hearing == results.HI_HIDE:
            params["hi"] = "0"
        elif hearing == results.HI_ONLY:
            params["hi"] = "1"
        body = subdl.search(params)
        if api.is_title_miss(body):
            log("search by %s: no title" % attempt.kind)
            continue
        if not year_matches(body, attempt.expect_year):
            log("search by %s: found a title from another year" % attempt.kind)
            continue
        rows = list(body.get("subtitles") or [])
        entries = results.build_entries(rows, wanted, video, attempt.episode, packs, hearing)
        if video and not results.has_sync(entries) and results.page_count(body) > 1:
            # Results come newest first; the release being played may be older.
            try:
                more = subdl.search(dict(params, page="2"))
            except SubDLError as error:  # keep the first page whatever happens here
                log("search page 2: %s" % error.kind)
                more = {}
            if more.get("status") is True:
                rows += list(more.get("subtitles") or [])
                entries = results.build_entries(rows, wanted, video, attempt.episode, packs, hearing)
        log("search by %s: %d results, %d listed" % (attempt.kind, len(rows), len(entries)))
        return entries, attempt.episode
    return [], None


def year_matches(body: dict, expected: Optional[int]) -> bool:
    """A title found by name must be from the expected year, give or take one."""
    if not expected:
        return True
    found = (body.get("results") or [{}])[0]
    year = _int(str(found.get("year") or "")) if isinstance(found, dict) else None
    return year is None or abs(year - expected) <= 1


def add_row(addon, handle: int, entry: results.Entry, target: Optional[tuple], stacked: bool) -> None:
    extras = []
    variant = languages.VARIANTS.get(entry.language)
    if variant:
        extras.append(addon.getLocalizedString(_VARIANT_LABELS[variant]))
    if entry.secondary:
        extras.append("+ " + language_name(entry.secondary))
    if entry.pack or entry.pack_file:
        extras.append(addon.getLocalizedString(32217))
    label2 = entry.release or language_name(entry.language)
    if extras:
        label2 = "%s  [%s]" % (label2, ", ".join(extras))

    row = xbmcgui.ListItem(label=language_name(entry.language), label2=label2)
    row.setArt({"icon": str(entry.rating), "thumb": languages.iso_for(entry.language)})
    row.setProperty("sync", "true" if entry.sync else "false")
    row.setProperty("hearing_imp", "true" if entry.hearing_impaired else "false")

    link = {"action": "download", "path": entry.path, "lang": entry.language}
    if entry.format:
        link["format"] = entry.format
    if entry.pack:
        link["pack"] = "1"
    if target is not None:
        link["season"] = "" if target[0] is None else str(target[0])
        link["episode"] = str(target[1])
    if stacked:
        link["stack"] = "1"
    url = "plugin://%s/?%s" % (ADDON_ID, urlencode(link))
    xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=row, isFolder=False)


# ---- download -------------------------------------------------------------------


def download(addon, handle: int, params: dict) -> None:
    subdl = client(addon)
    path = params.get("path", "")
    if not api.is_download_path(path):
        log("download: not a SubDL download path")
        notify(addon, 32212)
        return
    data, name = subdl.download(path)
    try:
        files = archive.files_in(data, name, params.get("format", ""))
    except archive.ArchiveError as error:
        log("download: %s" % error)
        notify(addon, 32214)
        return

    if not files:
        log("download: no subtitle file inside")
        notify(addon, 32214)
        return
    episode = _int(params.get("episode", ""))
    target = (_int(params.get("season", "")), episode) if episode is not None else None
    if target is not None and not archive.for_episode(files, target[0], target[1]):
        log("download: no file for the episode (%d in the download)" % len(files))
        notify(addon, 32213 if params.get("pack") == "1" else 32214)
        return
    video = releases.name_from_path(playing_file())
    chosen = archive.choose(files, video, target, params.get("stack") == "1", ask=ask_file(addon))
    if not chosen:
        log("download: the viewer chose no file")
        return
    folder = fresh_folder(addon)
    for subtitle in chosen:
        saved = archive.write(subtitle, folder, params.get("lang", ""))
        xbmcplugin.addDirectoryItem(handle=handle, url=saved, listitem=xbmcgui.ListItem(label=saved),
                                    isFolder=False)
    log("download: %d file(s) handed to Kodi" % len(chosen))


def ask_file(addon) -> Callable[[List[str]], int]:
    def ask(names: List[str]) -> int:
        return xbmcgui.Dialog().select(addon.getLocalizedString(32215), names)
    return ask


def fresh_folder(addon) -> str:
    """A new folder for this download's files.

    Kodi copies the file after this script has ended, so nothing may delete it then.
    Each download gets its own folder, and only folders older than an hour are
    cleared, so two downloads close together never remove each other's file.
    """
    root = os.path.join(xbmcvfs.translatePath(addon.getAddonInfo("profile")), "temp")
    os.makedirs(root, exist_ok=True)
    now = time.time()
    for name in os.listdir(root):
        old = os.path.join(root, name)
        try:
            if now - os.path.getmtime(old) > TEMP_MAX_AGE_S:
                shutil.rmtree(old, ignore_errors=True)
        except OSError:
            pass
    folder = os.path.join(root, uuid.uuid4().hex)
    os.makedirs(folder)
    return folder


# ---- Kodi state -----------------------------------------------------------------


def client(addon) -> api.SubDLClient:
    key = (addon.getSetting("api_key") or "").strip()
    if not key:
        raise SubDLError(SubDLError.MISSING_KEY)
    return api.SubDLClient(key, user_agent(addon), log=log)


def user_agent(addon) -> str:
    """For example: SubDL-Kodi/1.0.0 (service.subtitles.subdl; Kodi/21.2; Android)

    Names the add-on, its version, Kodi's version and the kind of device, so SubDL
    can count this add-on's traffic. Nothing in it identifies the viewer.
    """
    build = re.match(r"(\d+)(?:\.\d+)?", xbmc.getInfoLabel("System.BuildVersion") or "")
    # webOS is Linux to older checks, and Kodi only knows the webOS condition from 21.
    platforms = [entry for entry in _PLATFORMS
                 if entry[0] != "webOS" or (build is not None and int(build.group(1)) >= 21)]
    platform = next((name for name, condition in platforms if xbmc.getCondVisibility(condition)), "unknown")
    return "SubDL-Kodi/%s (%s; Kodi/%s; %s)" % (
        addon.getAddonInfo("version"), ADDON_ID, build.group(0) if build else "unknown", platform)


def iso_code(name: str) -> str:
    """Kodi's ISO 639 code for a language name from the subtitle settings."""
    name = (name or "").strip()
    if not name:
        return ""
    return (xbmc.convertLanguage(name, xbmc.ISO_639_1) or xbmc.convertLanguage(name, xbmc.ISO_639_2)
            or languages.iso_for_name(name))


def wanted_languages(params: dict) -> List[str]:
    """SubDL codes for Kodi's subtitle languages, the preferred language first."""
    codes = languages.subdl_codes(iso_code(name) for name in params.get("languages", "").split(","))
    preferred = languages.subdl_codes([iso_code(params.get("preferredlanguage", ""))])
    return results.ordered_codes(codes, preferred)


def language_name(code: str) -> str:
    """The English name Kodi itself uses, so Kodi can name the saved file."""
    iso = languages.iso_for(code)
    return (xbmc.convertLanguage(iso, xbmc.ENGLISH_NAME) if iso else "") or languages.english_name(code)


def playing_file() -> str:
    try:
        return xbmc.Player().getPlayingFile()
    except RuntimeError:  # playback stopped while the dialog was open
        return ""


def playing_item() -> query.PlayingItem:
    label = xbmc.getInfoLabel
    imdb = label("VideoPlayer.UniqueID(imdb)") or label("VideoPlayer.IMDBNumber")
    item = query.PlayingItem(
        title=label("VideoPlayer.Title"),
        original_title=label("VideoPlayer.OriginalTitle"),
        year=_int(label("VideoPlayer.Year")),
        tvshow=label("VideoPlayer.TVShowTitle"),
        season=_int(label("VideoPlayer.Season")),
        episode=_int(label("VideoPlayer.Episode")),
        imdb_id=imdb,
        tmdb_id=label("VideoPlayer.UniqueID(tmdb)"),
        filename=releases.name_from_path(playing_file()),
    )
    if item.is_episode:
        add_show_details(item, label("VideoPlayer.TvShowDBID"))
    return item


def add_show_details(item: query.PlayingItem, show_id: str) -> None:
    """The show's own ids and year from Kodi's library: an episode's ids name the
    episode, and SubDL files subtitles under the show."""
    if not show_id.isdigit():
        return
    request = {"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.GetTVShowDetails",
               "params": {"tvshowid": int(show_id), "properties": ["uniqueid", "year", "originaltitle"]}}
    try:
        reply = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    except (TypeError, ValueError):
        return
    details = (reply.get("result") or {}).get("tvshowdetails") or {}
    ids = details.get("uniqueid") or {}
    item.from_library = True
    item.show_imdb_id = str(ids.get("imdb") or "")
    item.show_tmdb_id = str(ids.get("tmdb") or "")
    item.tvshow_original = str(details.get("originaltitle") or "")
    item.tvshow_year = _int(str(details.get("year") or ""))


# ---- messages -------------------------------------------------------------------


def notify(addon, string_id: int, seconds: int = 5) -> None:
    xbmcgui.Dialog().notification(addon.getAddonInfo("name"), addon.getLocalizedString(string_id),
                                  addon.getAddonInfo("icon"), seconds * 1000)


def notify_panel(addon, heading_id: int) -> None:
    """A notice whose title says what is wrong and whose text is the panel link.

    Kodi's notice shows about 35 characters before it starts scrolling, so the link
    goes on a line of its own where it is readable at once. The SubDL icon beside it
    says who is talking.
    """
    xbmcgui.Dialog().notification(addon.getLocalizedString(heading_id), api.PANEL_URL,
                                  addon.getAddonInfo("icon"), 8000)


def report(addon, error: SubDLError, action: str, always_dialog: bool = False) -> None:
    """Tell the viewer what went wrong in words they can act on.

    A missing or refused key and a used-up daily limit get a dialog with the link
    to https://subdl.com/panel/api: once a day per key, so a viewer who opens the
    subtitle dialog again is not stopped every time; after that a short notice.
    """
    log("%s failed: %s%s" % (action, error.kind, " (HTTP %d)" % error.status if error.status else ""))
    text = addon.getLocalizedString
    name = addon.getAddonInfo("name")
    kind = error.kind
    if kind in (SubDLError.MISSING_KEY, SubDLError.INVALID_KEY):
        missing = kind == SubDLError.MISSING_KEY
        if always_dialog or first_notice(kind, addon):
            if xbmcgui.Dialog().yesno(name, text(32201 if missing else 32204),
                                      nolabel=text(32203), yeslabel=text(32202)):
                addon.openSettings()
        else:
            notify_panel(addon, 32207 if missing else 32219)
    elif kind in (SubDLError.DAILY_LIMIT, SubDLError.DOWNLOAD_LIMIT):
        if always_dialog or first_notice(kind, addon):
            xbmcgui.Dialog().ok(name, text(32205 if kind == SubDLError.DAILY_LIMIT else 32206))
        else:
            notify_panel(addon, 32208)
    elif kind == SubDLError.BUSY:
        notify(addon, 32209)
    elif kind == SubDLError.NETWORK:
        notify(addon, 32210)
    else:
        notify(addon, 32212 if action == "download" else 32216)


def first_notice(kind: str, addon) -> bool:
    """True the first time today this problem is met with this key.

    Kept as a property of Kodi's home window, which lives as long as Kodi runs, so
    the add-on writes nothing to disk for it.
    """
    key = (addon.getSetting("api_key") or "").strip()
    stamp = "%s|%s" % (datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                       hashlib.sha256(key.encode("utf-8")).hexdigest()[:12])
    window = xbmcgui.Window(HOME_WINDOW)
    name = "%s.notice.%s" % (ADDON_ID, kind)
    if window.getProperty(name) == stamp:
        return False
    window.setProperty(name, stamp)
    return True


def account_lines(addon, body: dict) -> List[str]:
    text = addon.getLocalizedString
    lines = []
    user = body.get("user") or {}
    if user.get("username") or user.get("name"):
        lines.append(text(32221) % (user.get("username") or user.get("name")))
    pro = body.get("pro") or {}
    plan = pro.get("plan") if isinstance(pro.get("plan"), dict) else {}
    if pro.get("isPaid"):
        lines.append(text(32222) % (plan.get("name") or plan.get("title") or text(32227)))
    else:
        lines.append(text(32222) % text(32223))
    usage = body.get("apiAccount") or {}
    searches, downloads = usage.get("requests") or {}, usage.get("downloads") or {}
    if searches.get("limit"):
        lines.append(text(32224) % (_count(searches.get("today")), _count(searches.get("limit"))))
    if downloads.get("limit"):
        lines.append(text(32226) % (_count(downloads.get("today")), _count(downloads.get("limit"))))
    else:
        # Until SubDL's fix of 2026-10-21 is live, the account endpoint reports a
        # limit of 0 for free keys, which have 50; show the count alone then.
        lines.append(text(32225) % _count(downloads.get("today")))
    return lines


# ---- helpers --------------------------------------------------------------------


def _int(value: str) -> Optional[int]:
    """A non-negative number from a Kodi label ("" and "-1" mean unknown)."""
    text = (value or "").strip()
    return int(text) if text.isdigit() else None


def _count(value) -> str:
    try:
        return "{:,}".format(int(value or 0))
    except (TypeError, ValueError):
        return "0"


def _where(error: BaseException) -> str:
    """file:line of the failure, without the exception's text, which may hold a path."""
    frames = traceback.extract_tb(error.__traceback__)
    if not frames:
        return "?"
    return "%s:%d" % (os.path.basename(frames[-1].filename), frames[-1].lineno)
