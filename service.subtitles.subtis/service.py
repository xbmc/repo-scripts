"""
Subtis subtitle service addon for Kodi.

This addon integrates with the subt.is API to search and download Spanish subtitles
for movies. It registers as a subtitle provider in Kodi's subtitle menu.

Actions:
    search: Searches for subtitles based on the currently playing file's name and size.
    download: Downloads a subtitle file from the provided link.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, TypedDict

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

__addon__ = xbmcaddon.Addon()
__scriptid__ = __addon__.getAddonInfo("id")
__version__ = __addon__.getAddonInfo("version")

__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo("profile"))
__temp__ = xbmcvfs.translatePath(os.path.join(__profile__, "temp", ""))

USER_AGENT = f"Kodi Subtis Addon/{__version__}"
LANGUAGE_CODE = "es"
NOTIFICATION_DURATION_MS = 10000
REQUEST_TIMEOUT_SEC = 10
DOWNLOAD_TIMEOUT_SEC = 30
SUBTIS_API_BASE = "https://api.subt.is/v1"
UNSUPPORTED_MEDIA_TYPES = {"episode", "tvshow"}


class SubtitleData(TypedDict, total=False):
    subtitle_link: str
    subtitle_file_name: str


class TitleData(TypedDict, total=False):
    title_name: str
    year: str


class MediaItem(TypedDict):
    file_name: str
    file_size: int


def log(message: str) -> None:
    xbmc.log(f"### SUBTIS ### {message}", level=xbmc.LOGINFO)


def notify(message: str, level: int = xbmcgui.NOTIFICATION_INFO) -> None:
    xbmcgui.Dialog().notification("Subtis", message, level, NOTIFICATION_DURATION_MS)


def fetch_json(url: str) -> tuple[dict[str, Any] | None, int]:
    """Fetches JSON from a URL and returns the parsed data with status code."""
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", USER_AGENT)

        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC) as response:
            data = response.read()
            status_code = response.getcode()
            return json.loads(data.decode("utf-8")), status_code

    except urllib.error.HTTPError as exc:
        log(f"HTTP error {exc.code} for {url}")
        return None, exc.code

    except urllib.error.URLError as exc:
        log(f"URL error for {url}: {exc.reason}")
        return None, 0

    except Exception as exc:
        log(f"Unexpected error requesting {url}: {exc}")
        return None, 0


def build_subtitle_result(
    response_data: dict[str, Any],
    is_synced: bool = True,
) -> tuple[str, xbmcgui.ListItem] | None:
    """Builds a Kodi ListItem from API response data."""
    subtitle_data = response_data.get("subtitle", {})
    title_data = response_data.get("title", {})

    subtitle_link = subtitle_data.get("subtitle_link")
    subtitle_file_name = subtitle_data.get("subtitle_file_name")

    if not subtitle_link or not subtitle_file_name:
        log("ERROR: Missing subtitle_link or subtitle_file_name in response")
        return None

    title_name = title_data.get("title_name", "Unknown")
    year = title_data.get("year", "")
    display_label = f"{title_name} ({year})" if year else title_name

    listitem = xbmcgui.ListItem(label=LANGUAGE_CODE, label2=display_label)
    # Icon "5" represents the subtitle sync/quality rating (1-5 scale in Kodi's subtitle API)
    listitem.setArt({"icon": "5", "thumb": LANGUAGE_CODE})
    listitem.setProperty("sync", "true" if is_synced else "false")
    listitem.setProperty("hearing_imp", "false")

    url = (
        f"plugin://{__scriptid__}/?action=download"
        f"&link={urllib.parse.quote(subtitle_link)}"
        f"&filename={urllib.parse.quote(subtitle_file_name)}"
    )

    return url, listitem


def fetch_primary_subtitle(
    file_name: str,
    file_size: int,
) -> tuple[str, xbmcgui.ListItem] | None:
    """Fetches subtitle by exact file name and size match."""
    encoded_filename = urllib.parse.quote(file_name)
    search_url = f"{SUBTIS_API_BASE}/subtitle/file/name/{file_size}/{encoded_filename}"
    response_data, status_code = fetch_json(search_url)

    if not response_data or status_code != 200:
        log(f"Primary search: no match (status: {status_code})")
        return None

    return build_subtitle_result(response_data, is_synced=True)


def fetch_alternative_subtitle(file_name: str) -> tuple[str, xbmcgui.ListItem] | None:
    """Fetches alternative subtitle by file name only (fuzzy match)."""
    encoded_filename = urllib.parse.quote(file_name)
    search_url = f"{SUBTIS_API_BASE}/subtitle/file/alternative/{encoded_filename}"
    response_data, status_code = fetch_json(search_url)

    if not response_data or status_code != 200:
        log(f"Alternative search: no match (status: {status_code})")
        return None

    return build_subtitle_result(response_data, is_synced=False)


def search_subtitles(item: MediaItem) -> tuple[str, xbmcgui.ListItem] | None:
    """Searches for subtitles, trying primary then alternative endpoints."""
    file_name = item.get("file_name", "")
    file_size = item.get("file_size", 0)

    if not file_name:
        log("ERROR: File name missing")
        return None

    # Try primary search (exact match by size + name)
    if file_size:
        result = fetch_primary_subtitle(file_name, file_size)
        if result:
            return result

    # Fallback to alternative search (fuzzy match by name only)
    return fetch_alternative_subtitle(file_name)


def download_subtitle(subtitle_link: str, subtitle_file_name: str) -> str | None:
    """Downloads a subtitle file and saves it to the temp directory."""
    if not xbmcvfs.exists(__temp__):
        xbmcvfs.mkdirs(__temp__)

    try:
        req = urllib.request.Request(subtitle_link)
        req.add_header("User-Agent", USER_AGENT)

        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT_SEC) as response:
            subtitle_content = response.read().decode("utf-8")

        subtitle_path = os.path.join(__temp__, subtitle_file_name)

        file_handle = xbmcvfs.File(subtitle_path, "w")
        try:
            file_handle.write(subtitle_content)
        finally:
            file_handle.close()

        return subtitle_path

    except urllib.error.HTTPError as exc:
        log(f"ERROR downloading subtitle: HTTP {exc.code}")
        return None

    except urllib.error.URLError as exc:
        log(f"ERROR downloading subtitle: {exc.reason}")
        return None

    except Exception as exc:
        log(f"ERROR downloading subtitle: {exc}")
        return None


def get_params() -> dict[str, str]:
    return dict(urllib.parse.parse_qsl(sys.argv[2].lstrip("?")))


def handle_search(handle: int, player: xbmc.Player) -> None:
    """Handles the search action: finds subtitles for the currently playing media."""
    if not player.isPlaying():
        log("Search requested but no media is playing")
        notify("No hay reproducción activa.")
        return

    video_info = player.getVideoInfoTag()
    media_type = video_info.getMediaType()

    if media_type in UNSUPPORTED_MEDIA_TYPES:
        log(f"Content type '{media_type}' is not supported (TV shows are not supported)")
        notify("Soporte para series proximamente", xbmcgui.NOTIFICATION_WARNING)
        return

    playing_file = player.getPlayingFile()
    file_name = os.path.basename(playing_file)
    file_size = 0

    try:
        if xbmcvfs.exists(playing_file):
            stat = xbmcvfs.Stat(playing_file)
            file_size = stat.st_size()
    except Exception as exc:
        log(f"Could not get file size: {exc}")

    item: MediaItem = {"file_name": file_name, "file_size": file_size}
    result = search_subtitles(item)

    if result is None:
        log("Movie not found in Subtis database")
        notify("Película no encontrada. Estamos trabajando para agregarla pronto.")
    else:
        url, listitem = result
        xbmcplugin.addDirectoryItem(
            handle=handle,
            url=url,
            listitem=listitem,
            isFolder=False,
        )


def handle_download(handle: int, params: dict[str, str]) -> None:
    """Handles the download action: downloads and registers a subtitle file."""
    subtitle_link = params.get("link")
    subtitle_file_name = params.get("filename")

    if not subtitle_link or not subtitle_file_name:
        log("ERROR: Missing link or filename in download params")
        return

    subtitle_link = urllib.parse.unquote(subtitle_link)
    subtitle_file_name = urllib.parse.unquote(subtitle_file_name)
    subtitle_path = download_subtitle(subtitle_link, subtitle_file_name)

    if subtitle_path:
        listitem = xbmcgui.ListItem(label=subtitle_path)
        xbmcplugin.addDirectoryItem(
            handle=handle,
            url=subtitle_path,
            listitem=listitem,
            isFolder=False,
        )


def main() -> None:
    params = get_params()
    handle = int(sys.argv[1])
    action = params.get("action")

    if action == "search":
        player = xbmc.Player()
        handle_search(handle, player)
    elif action == "download":
        handle_download(handle, params)

    xbmcplugin.endOfDirectory(handle)


if __name__ == "__main__":
    main()
