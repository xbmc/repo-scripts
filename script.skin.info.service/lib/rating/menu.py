"""Ratings menu entry points, mode selection, and report display."""
from __future__ import annotations

from typing import List, Optional, Tuple
import xbmc
import xbmcgui

from lib.kodi.client import request, get_api_key, log, KODI_GET_DETAILS_METHODS, ADDON
from lib.data.api.tmdb import ApiTmdb as TMDBRatingsSource
from lib.data.api.mdblist import ApiMdblist as MDBListRatingsSource
from lib.data.api.omdb import ApiOmdb as OMDbRatingsSource
from lib.data.api.trakt import ApiTrakt as TraktRatingsSource
from lib.data.api.imdb import get_imdb_dataset
from lib.infrastructure.dialogs import (
    show_ok, show_textviewer, show_notification, BackgroundNotice, ProgressDialog)
from lib.infrastructure.menus import Menu, MenuItem
from lib.infrastructure import tasks as task_manager
from lib.data.database import workflow as db
from lib.data.database._infrastructure import init_database
from lib.rating.updater import (
    update_library_ratings,
    update_tvshow_episodes,
)
from lib.rating.single import update_single_item


_RATINGS_HEADING_ID = 32300

_SCOPE_LABELS = {
    "movie": "Movies",
    "tvshow": "TV Shows",
    "episode": "Episodes",
}

_SOURCE_MODE_LABELS = {
    "imdb": "IMDb Dataset",
    "tmdb": "TMDB",
    "trakt": "Trakt",
    "aggregators": "Aggregators (MDBList, OMDB)",
    "multi_source": "All Sources",
}


def _notify(message_id: int, level: str = xbmcgui.NOTIFICATION_INFO,
            duration: int = 3000, *args) -> None:
    """Show a notification under the standard ratings heading."""
    message = ADDON.getLocalizedString(message_id)
    if args:
        message = message.format(*args)
    show_notification(ADDON.getLocalizedString(_RATINGS_HEADING_ID), message, level, duration)


def initialize_sources() -> List:
    """Initialize available rating sources, in priority order (TMDB, then MDBList/OMDb if keyed,
    then Trakt) for multi_source updates."""
    sources = []
    sources.append(TMDBRatingsSource())
    if get_api_key("mdblist_api_key"):
        sources.append(MDBListRatingsSource())
    if get_api_key("omdb_api_key"):
        sources.append(OMDbRatingsSource())
    sources.append(TraktRatingsSource())
    return sources


def run_ratings_menu() -> None:
    """Show ratings updater menu."""
    init_database()

    items = [
        MenuItem(ADDON.getLocalizedString(32406), lambda: _run_update("movie")),
        MenuItem(ADDON.getLocalizedString(32407), lambda: _run_update("tvshow")),
        MenuItem(ADDON.getLocalizedString(32408), lambda: _run_update("episode")),
        MenuItem(ADDON.getLocalizedString(32409), _run_update_all),
    ]

    if db.get_last_operation_stats('ratings_update'):
        items.append(MenuItem(ADDON.getLocalizedString(32086), show_ratings_report, loop=True))

    menu = Menu(ADDON.getLocalizedString(32300), items)
    menu.show()


def _run_update(media_type: str) -> None:
    """Run ratings update for a media type."""
    _select_mode_and_run([media_type], initialize_sources(), "multi_source")


def _run_update_all() -> None:
    """Run ratings update for all media types."""
    _select_mode_and_run(["movie", "tvshow", "episode"], initialize_sources(), "multi_source")


def _select_mode_and_run(media_types: List[str], sources: List, source_mode: str) -> None:
    """Show foreground/background picker, then run `update_library_ratings` per media type."""
    from lib.infrastructure.menus import run_with_mode_choice

    def run(use_background: bool) -> None:
        for media_type in media_types:
            update_library_ratings(
                media_type, sources, use_background=use_background, source_mode=source_mode)

    run_with_mode_choice("Update Library Ratings", run)


def _resolve_single_item_target(
        dbid: Optional[str], dbtype: Optional[str]) -> Optional[Tuple[str, str]]:
    """Validate and resolve `(dbid, media_type)` for a single-item update; notifies and returns
    None on failure."""
    if not dbid:
        dbid = xbmc.getInfoLabel("ListItem.DBID")
    if not dbtype:
        dbtype = xbmc.getInfoLabel("ListItem.DBType")

    if not dbid or dbid == "-1" or not dbtype:
        _notify(32259, xbmcgui.NOTIFICATION_WARNING)
        return None

    media_type = dbtype.lower()
    if media_type not in ("movie", "tvshow", "episode", "set"):
        _notify(32263, xbmcgui.NOTIFICATION_WARNING, 3000, media_type)
        return None

    return dbid, media_type


def _fetch_single_item(dbid: str, media_type: str) -> Optional[dict]:
    """Fetch a single Kodi item with the properties needed for rating update; notify on failure."""
    if media_type == "episode":
        properties = ["title", "season", "episode", "tvshowid", "uniqueid", "ratings"]
    else:
        properties = ["title", "year", "uniqueid", "ratings"]

    method_info = KODI_GET_DETAILS_METHODS.get(media_type)
    if not method_info:
        _notify(32263, xbmcgui.NOTIFICATION_WARNING, 3000, media_type)
        return None

    method_name, id_key, result_key = method_info
    response = request(method_name, {id_key: int(dbid), "properties": properties})
    if not response or result_key not in response.get("result", {}):
        _notify(32401, xbmcgui.NOTIFICATION_WARNING, 3000, media_type.title())
        return None

    return response["result"][result_key]


def _report_single_item_result(success: Optional[bool], item_stats: Optional[dict],
                               title: str, episodes_updated: int) -> None:
    """Notify the user of single-item update outcome and refresh the container if updated."""
    if success is False:
        _notify(32405, xbmcgui.NOTIFICATION_ERROR)
        return
    if success is None:
        _notify(32404, xbmcgui.NOTIFICATION_WARNING)
        return

    total_added = item_stats.get('added_details', []) if item_stats else []
    total_updated = item_stats.get('updated_details', []) if item_stats else []

    if total_added or total_updated or episodes_updated > 0:
        message_lines = []
        if total_added:
            message_lines.append(f"[B]Added:[/B] {', '.join(total_added)}")
        if total_updated:
            message_lines.append(f"[B]Updated:[/B] {', '.join(total_updated)}")
        if episodes_updated > 0:
            message_lines.append(f"[B]Episodes:[/B] {episodes_updated} updated")
        show_ok(ADDON.getLocalizedString(32316).format(title), "[CR]".join(message_lines))
        xbmc.executebuiltin("Container.Refresh")
    else:
        _notify(32403)


def _update_movieset_ratings(setid: int, sources: List) -> None:
    """Update ratings for every movie in a set, then report the aggregate."""
    response = request("VideoLibrary.GetMovieSetDetails", {
        "setid": setid,
        "movies": {"properties": ["title", "year", "uniqueid", "ratings"]},
    })
    setdetails = response.get("result", {}).get("setdetails") if response else None
    movies = setdetails.get("movies") if setdetails else None
    if not setdetails or not movies:
        _notify(32401, xbmcgui.NOTIFICATION_WARNING, 3000, "Set")
        return

    abort_flag = task_manager.ShutdownAbortFlag()
    updated_titles: List[str] = []
    total = len(movies)
    progress = ProgressDialog(heading=ADDON.getLocalizedString(_RATINGS_HEADING_ID))
    progress.create(ADDON.getLocalizedString(32402))
    try:
        for idx, movie in enumerate(movies):
            if progress.is_cancelled():
                abort_flag.request()
                break
            progress.update(int(idx / total * 100), movie.get("title") or movie.get("label", ""))
            success, item_stats = update_single_item(movie, "movie", sources, abort_flag)
            if success and item_stats and (
                    item_stats.get("added_details") or item_stats.get("updated_details")):
                updated_titles.append(movie.get("title", "Unknown"))
    finally:
        progress.close()

    if updated_titles:
        message = (f"[B]Movies updated ({len(updated_titles)}/{len(movies)}):[/B][CR]"
                   f"{', '.join(updated_titles)}")
        show_ok(ADDON.getLocalizedString(32316).format(setdetails.get("label", "Set")), message)
        xbmc.executebuiltin("Container.Refresh")
    else:
        _notify(32403)


def update_single_item_ratings(dbid: Optional[str], dbtype: Optional[str]) -> None:
    """Update ratings for a single item by DBID. Three-phase: validate, fetch+update, report."""
    target = _resolve_single_item_target(dbid, dbtype)
    if target is None:
        return
    dbid, media_type = target

    log("Ratings", f"Updating ratings for single item - dbid={dbid}, dbtype={media_type}",
        xbmc.LOGINFO)

    init_database()
    notice = BackgroundNotice(
        ADDON.getLocalizedString(_RATINGS_HEADING_ID), ADDON.getLocalizedString(32305))
    try:
        get_imdb_dataset().refresh_if_stale(on_download_start=notice.start)
    finally:
        notice.close()

    sources = initialize_sources()
    if not sources:
        show_ok(ADDON.getLocalizedString(_RATINGS_HEADING_ID), ADDON.getLocalizedString(32400))
        return

    if media_type == "set":
        _update_movieset_ratings(int(dbid), sources)
        return

    item = _fetch_single_item(dbid, media_type)
    if item is None:
        return

    title = item.get("title", "Unknown")
    _notify(32402, xbmcgui.NOTIFICATION_INFO, 2000)

    success, item_stats = update_single_item(item, media_type, sources)
    episodes_updated = 0
    if media_type == "tvshow" and success:
        episodes_updated = update_tvshow_episodes(int(dbid), sources)

    _report_single_item_result(success, item_stats, title, episodes_updated)


def show_ratings_report() -> None:
    """Show the last ratings update report from operation history."""
    last_report = db.get_last_operation_stats('ratings_update')

    if not last_report:
        show_ok(
            ADDON.getLocalizedString(32430),
            ADDON.getLocalizedString(32424)
        )
        return

    stats = last_report['stats']
    scope = last_report.get('scope', 'unknown')
    timestamp = last_report['timestamp']

    scope_label = _SCOPE_LABELS.get(scope, scope.title())

    updated = stats.get('updated', 0)
    failed = stats.get('failed', 0)
    skipped = stats.get('skipped', 0)
    total_items = stats.get('total_items', 0)
    elapsed_time = stats.get('elapsed_time', 0)
    cancelled = stats.get('cancelled', False)
    source_stats = stats.get('source_stats', {})
    item_details = stats.get('item_details', [])
    source_mode = stats.get('source_mode', 'multi_source')

    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

    status = "Cancelled" if cancelled else "Complete"

    source_label = _SOURCE_MODE_LABELS.get(source_mode, source_mode)

    lines = [
        f"[B]Ratings Update Report - {status}[/B]",
        "",
        f"Source: {source_label}",
        f"Scope: {scope_label}",
        f"Timestamp: {timestamp}",
        f"Duration: {time_str}",
        "",
        "[B]Summary[/B]",
        f"Total items found: {total_items}",
        f"Successfully updated: {updated}",
        f"Failed: {failed}",
        f"Skipped (no rating data): {skipped}",
        ""
    ]

    if source_stats:
        lines.extend([
            "[B]Source Statistics[/B]",
            ""
        ])

        sorted_sources = sorted(source_stats.items(), key=lambda x: x[0])
        for source_name, source_data in sorted_sources:
            fetched = source_data.get('fetched', 0)
            lines.append(f"{source_name.upper()}: {fetched} items fetched")

        lines.append("")

    total_ratings_added = stats.get('total_ratings_added', 0)
    total_ratings_updated = stats.get('total_ratings_updated', 0)
    imdb_ids_added = stats.get('imdb_ids_added', 0)
    imdb_ids_corrected = stats.get('imdb_ids_corrected', 0)

    if (total_ratings_added > 0 or total_ratings_updated > 0 or imdb_ids_added > 0
            or imdb_ids_corrected > 0):
        lines.extend([
            "[B]Rating Changes[/B]",
            f"Total ratings added: {total_ratings_added}",
            f"Total ratings updated: {total_ratings_updated}",
        ])
        if imdb_ids_added > 0:
            lines.append(f"IMDb IDs added to library: {imdb_ids_added}")
        if imdb_ids_corrected > 0:
            lines.append(f"IMDb IDs corrected (redirects): {imdb_ids_corrected}")
        lines.append("")

    if item_details and len(item_details) <= 20:
        lines.extend([
            "[B]Detailed Changes[/B]",
            ""
        ])

        for item in item_details:
            if item.get('ratings_added', 0) > 0 or item.get('ratings_updated', 0) > 0:
                title = item.get('title', 'Unknown')
                year = item.get('year', '')
                year_str = f" ({year})" if year else ""

                lines.append(f"{title}{year_str}:")

                added = item.get('added_details', [])
                if added:
                    lines.append(f"  Added: {', '.join(added)}")

                updated_details = item.get('updated_details', [])
                if updated_details:
                    lines.append(f"  Updated: {', '.join(updated_details)}")

                lines.append("")

    text = "\n".join(lines)

    show_textviewer(ADDON.getLocalizedString(32430), text)
