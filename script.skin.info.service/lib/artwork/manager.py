"""Artwork management workflows for interactive selection and auto-processing.

Contains:
- ArtworkSelection: Interactive artwork selection workflow
- ArtworkManager: Workflow coordinator

Core functionality is in the artwork package (scanner, processor, api_integration).
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any

import xbmc
import xbmcgui

from lib.data import database as db
from lib.data.database.queue import QueueEntry, ArtItemEntry
from lib.kodi.client import (
    request, extract_result, get_item_details, decode_image_url, KODI_GET_DETAILS_METHODS,
)
from lib.artwork.dialogs.select import show_artwork_selection_dialog
from lib.kodi.client import log, ADDON
from lib.kodi.settings import KodiSettings
from lib.infrastructure.menus import Menu, MenuItem
from lib.infrastructure.dialogs import (
    show_ok, show_yesno, show_textviewer, show_select, show_notification, DialogProgress)
from lib.actor.downloader import download_actor_images

# Import from new artwork package
from lib.artwork.config import (
    REVIEW_SCOPE_OPTIONS,
    REVIEW_SCOPE_LABELS,
    REVIEW_MEDIA_FILTERS,
    REVIEW_MODE_MISSING,
    SESSION_DETAIL_KEYS,
    default_session_stats as _default_session_stats,
    serialise_session_stats as _serialise_session_stats,
)
from lib.artwork.scanner import ArtworkScanner

MAX_REVIEW_LOG_ITEMS = 100


def _scan_scope(scope: str, use_background: bool = False,
                abort_flag=None, task_context=None) -> Optional[ArtworkScanner]:
    """Run artwork scanner for the selected scope and return the scanner on success."""

    scanner = ArtworkScanner(
        use_background=use_background, abort_flag=abort_flag, task_context=task_context)
    log("Artwork", f"Running scan for scope '{scope}'")
    result = scanner.scan(scope)
    if not result:
        show_ok(ADDON.getLocalizedString(32273), ADDON.getLocalizedString(32274))
        return None
    return scanner


def _show_session_report(session_row) -> None:
    """Display a report for a review session."""
    stats = json.loads(session_row['stats']) if session_row['stats'] else {}
    applied = int(stats.get('applied', 0) or 0)
    skipped = int(stats.get('skipped', 0) or 0)
    auto = int(stats.get('auto', 0) or 0)
    remaining = stats.get('remaining')
    details = stats.get('details')
    if not isinstance(details, dict):
        details = {}
    auto_runs = stats.get('auto_runs')
    if not isinstance(auto_runs, list):
        auto_runs = []

    started = session_row['started']
    last_activity = session_row['last_activity']
    status = session_row['status']
    completed = session_row['completed']

    def _shorten(value: Optional[str], max_len: int = 80) -> str:
        if not value:
            return ''
        if len(value) <= max_len:
            return value
        return value[:max_len - 3] + "..."

    def _append_detail_section(
        lines: List[str],
        header: str,
        entries: List[Dict[str, Any]],
        formatter,
        *,
        indent: str = "    ",
        max_items: int = 20
    ) -> None:
        valid_entries = [entry for entry in entries if isinstance(entry, dict)]
        if not valid_entries:
            return
        lines.append(header)
        to_show = min(max_items, len(valid_entries))
        for entry in valid_entries[:to_show]:
            lines.append(f"{indent}• {formatter(entry)}")
        if len(valid_entries) > max_items:
            lines.append(f"{indent}… {len(valid_entries) - max_items} more")
        lines.append("")

    def _format_entry(
        entry: Dict[str, Any],
        *,
        include_art_type: bool = True,
        include_source: bool = False,
        include_url: bool = False,
        include_reason: bool = False
    ) -> str:
        title = entry.get('title', 'Unknown')
        parts = [title]

        if include_art_type:
            art_type = entry.get('art_type', '?')
            parts[0] = f"{title} – {art_type}"

        if include_source:
            source = entry.get('source')
            if source:
                parts.append(f"[{source}]")

        if include_url:
            url = entry.get('url', '')
            if url:
                parts.append(_shorten(url, 70))

        if include_reason:
            reason = entry.get('reason', 'skipped')
            parts.append(f"({reason})")

        return " ".join(parts)

    def _format_manual_applied(entry: Dict[str, Any]) -> str:
        return _format_entry(entry, include_art_type=True, include_source=True, include_url=True)

    def _format_manual_skipped(entry: Dict[str, Any]) -> str:
        return _format_entry(entry, include_art_type=True, include_reason=True)

    def _format_auto_run_applied(entry: Dict[str, Any]) -> str:
        return _format_entry(entry, include_art_type=True, include_url=True)

    def _format_auto_run_skipped(entry: Dict[str, Any]) -> str:
        return _format_entry(entry, include_art_type=False, include_reason=True)

    session_id = session_row['id']
    session_art_types = db.get_session_art_types(session_id)
    session_media_types = db.get_session_media_types(session_id)
    missing_count = db.count_pending_missing_art(session_media_types) if session_media_types else 0

    art_types_str = ', '.join(session_art_types) if session_art_types else 'all'

    lines = []
    lines.append("=" * 50)
    lines.append("ARTWORK REVIEW SESSION REPORT")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Status: {status.upper()}")
    lines.append(f"Started: {started}")
    lines.append(f"Last Activity: {last_activity}")
    if status == 'completed' and completed:
        lines.append(f"Completed: {completed}")
    elif status == 'cancelled':
        lines.append(f"Cancelled: {last_activity}")
    lines.append(f"Art Types: {art_types_str}")
    lines.append("")
    lines.append("Statistics:")
    lines.append(f"  Manual Reviewed: {applied + skipped}")
    lines.append(f"    Applied: {applied}")
    lines.append(f"    Skipped: {skipped}")
    lines.append(f"  Auto-Skipped: {auto}")
    if remaining is not None:
        if missing_count > 0:
            lines.append(f"  Remaining Pending: {remaining} ({missing_count} missing artwork)")
        else:
            lines.append(f"  Remaining Pending: {remaining}")
    lines.append("")

    manual_applied = details.get('manual_applied', [])
    manual_skipped = details.get('manual_skipped', [])
    manual_auto = details.get('manual_auto', [])
    stale_entries = details.get('stale', [])

    _append_detail_section(
        lines,
        "Manual Applied:",
        manual_applied,
        _format_manual_applied
    )
    _append_detail_section(
        lines,
        "Manual Skipped:",
        manual_skipped,
        _format_manual_skipped
    )
    _append_detail_section(
        lines,
        "Auto-Skipped During Review:",
        manual_auto,
        _format_manual_skipped
    )
    _append_detail_section(
        lines,
        "Stale Items (baseline changed during review):",
        stale_entries,
        _format_manual_skipped
    )

    if auto_runs:
        lines.append("Auto Fetch Runs:")
        for idx, run in enumerate(auto_runs, start=1):
            timestamp = run.get('timestamp')
            if isinstance(timestamp, str):
                ts_display = timestamp.replace('T', ' ')
            else:
                ts_display = "unknown"
            counts = run.get('counts', {})
            processed = counts.get('processed', 0)
            auto_applied = counts.get('auto_applied', 0)
            skipped_auto = counts.get('skipped', 0)
            errors = counts.get('errors', 0)
            pending_after = run.get('pending_after', 'n/a')
            lines.append(f"  Run #{idx} ({ts_display})")
            lines.append(
                f"    Processed: {processed} | Applied: {auto_applied} | "
                f"Skipped: {skipped_auto} | Errors: {errors}"
            )
            lines.append(f"    Remaining after run: {pending_after}")
            _append_detail_section(
                lines,
                "    Applied:",
                run.get('applied', []),
                _format_auto_run_applied,
                indent="      ",
                max_items=15
            )
            _append_detail_section(
                lines,
                "    Skipped:",
                run.get('skipped', []),
                _format_auto_run_skipped,
                indent="      ",
                max_items=15
            )
        lines.append("")

    lines.append("=" * 50)

    text = "\n".join(lines)
    show_textviewer(ADDON.getLocalizedString(32500), text, use_mono=True)


def _download_selected_artwork(
    media_type: str,
    dbid: int,
    title: str,
    art_updates: Dict[str, str],
    force_overwrite: bool = False
) -> None:
    """Download selected artwork to filesystem."""
    from lib.download.artwork import DownloadArtwork
    from lib.infrastructure.paths import PathBuilder, use_basename_for

    if media_type not in KODI_GET_DETAILS_METHODS:
        return

    mbid: Optional[str] = None
    season: Optional[int] = None

    if media_type == 'set':
        media_file = title
    elif media_type == 'artist':
        media_file = title
        artist_details = get_item_details(media_type, dbid, ["musicbrainzartistid"])
        if isinstance(artist_details, dict):
            mbid = artist_details.get("musicbrainzartistid", "")
            if isinstance(mbid, list):
                mbid = mbid[0] if mbid else ""
    elif media_type == 'album':
        songs_resp = request("AudioLibrary.GetSongs", {
            "filter": {"albumid": dbid},
            "properties": ["file"],
            "limits": {"start": 0, "end": 1}
        })
        songs = extract_result(songs_resp, "songs", [])
        if songs and songs[0].get("file"):
            from lib.infrastructure.paths import vfs_dirname
            media_file = vfs_dirname(songs[0]["file"])
        else:
            media_file = ""
    else:
        properties = []
        if media_type in ('movie', 'tvshow', 'episode', 'musicvideo'):
            properties.append("file")
        if media_type == 'season':
            properties.extend(["season", "tvshowid"])
        elif media_type == 'episode':
            properties.extend(["season", "episode"])

        if not properties:
            return

        item = get_item_details(media_type, dbid, properties)
        if not isinstance(item, dict):
            return

        media_file = item.get("file", "")
        season = item.get("season")

        if media_type == 'season' and not media_file:
            tvshowid = item.get("tvshowid")
            if tvshowid:
                tvshow = get_item_details("tvshow", tvshowid, ["file"])
                if isinstance(tvshow, dict):
                    media_file = tvshow.get("file", "")

    if not media_file and media_type not in ('tvshow', 'set', 'artist'):
        log("Artwork", f"No file path for {media_type} '{title}', skipping download")
        return

    if force_overwrite:
        existing_file_mode = 'overwrite'
    else:
        existing_file_mode_setting = KodiSettings.existing_file_mode()
        existing_file_mode_int = (
            int(existing_file_mode_setting) if existing_file_mode_setting else 0
        )
        existing_file_mode = ['skip', 'overwrite'][existing_file_mode_int]

    savewith_basefilename = ADDON.getSettingBool('download.savewith_basefilename')

    use_basename = use_basename_for(media_type, savewith_basefilename)

    path_builder = PathBuilder()
    downloader = DownloadArtwork()

    for artwork_type, url in art_updates.items():
        if not url or not url.startswith('http'):
            continue

        local_path = path_builder.build_path(
            media_type=media_type,
            media_file=media_file,
            artwork_type=artwork_type,
            season_number=season,
            use_basename=use_basename,
            mbid=mbid
        )

        if not local_path:
            log(
                "Artwork",
                f"Could not build download path for {media_type} '{title}' {artwork_type}",
            )
            continue

        success, error, bytes_downloaded, _ = downloader.download_artwork(
            url=url,
            local_path=local_path,
            existing_file_mode=existing_file_mode
        )

        if success:
            log(
                "Artwork",
                f"Downloaded {artwork_type} for '{title}': {local_path} ({bytes_downloaded} bytes)",
            )
        elif error:
            log("Artwork", f"Failed to download {artwork_type} for '{title}': {error}")


def _extract_downloadable_art(
    art_dict: Dict[str, str],
    skip_prefixes: Optional[List[str]] = None
) -> Dict[str, str]:
    """Extract HTTP URLs from art dict, optionally filtering by prefix."""
    downloadable = {}
    for art_type, url in art_dict.items():
        if not url:
            continue
        if skip_prefixes:
            if any(art_type.startswith(prefix) for prefix in skip_prefixes):
                continue
        decoded_url = decode_image_url(url)
        if decoded_url.startswith('http'):
            downloadable[art_type] = decoded_url
    return downloadable


def download_item_artwork(dbid: Optional[str], dbtype: Optional[str]) -> None:
    """Download existing library artwork to filesystem for a single item.

    For TV shows, downloads show + all seasons + all episodes.
    Falls back to ListItem.DBID/DBType if args are None.
    """
    if not dbid:
        dbid = xbmc.getInfoLabel("ListItem.DBID")
    if not dbtype:
        dbtype = xbmc.getInfoLabel("ListItem.DBType")

    if not dbid or dbid == "-1" or not dbtype:
        show_notification(
            ADDON.getLocalizedString(32290),
            ADDON.getLocalizedString(32259),
            xbmcgui.NOTIFICATION_WARNING,
            3000
        )
        return

    db.init_database()

    media_type = dbtype.lower()
    dbid_int = int(dbid)

    method_info = KODI_GET_DETAILS_METHODS.get(media_type)
    if not method_info:
        show_notification(
            ADDON.getLocalizedString(32290),
            ADDON.getLocalizedString(32263).format(media_type),
            xbmcgui.NOTIFICATION_WARNING,
            3000
        )
        return

    method_name, id_key, result_key = method_info

    progress = DialogProgress()
    progress.create(ADDON.getLocalizedString(32290), ADDON.getLocalizedString(32297))

    try:
        if media_type == 'artist':
            detail_properties = ["art"]
        elif media_type in ('album', 'set'):
            detail_properties = ["title", "art"]
        else:
            detail_properties = ["title", "art", "file"]

        details = extract_result(
            request(method_name, {id_key: dbid_int, "properties": detail_properties}),
            result_key
        )

        if not details or not isinstance(details, dict):
            progress.close()
            show_notification(
                ADDON.getLocalizedString(32290),
                ADDON.getLocalizedString(32262),
                xbmcgui.NOTIFICATION_WARNING,
                3000
            )
            return

        if media_type == 'artist':
            title = details.get("artist", details.get("label", "Unknown"))
        else:
            title = details.get("title", details.get("label", "Unknown"))
        current_art = details.get("art", {})

        skip_prefixes = None
        if media_type == 'episode':
            skip_prefixes = ["tvshow.", "season."]
        elif media_type == 'season':
            skip_prefixes = ["tvshow."]
        elif media_type == 'movie':
            skip_prefixes = ["set."]

        downloadable_art = _extract_downloadable_art(current_art, skip_prefixes=skip_prefixes)

        art_count = 0
        season_count = 0
        episode_count = 0
        actor_count = 0

        existing_file_mode_setting = KodiSettings.existing_file_mode()
        existing_file_mode_int = (
            int(existing_file_mode_setting) if existing_file_mode_setting else 0
        )
        existing_file_mode = ['skip', 'overwrite'][existing_file_mode_int]

        if progress.iscanceled():
            progress.close()
            return

        if downloadable_art:
            progress.update(5, f"{title}\n{ADDON.getLocalizedString(32298)}")
            _download_selected_artwork(media_type, dbid_int, title, downloadable_art)
            art_count += len(downloadable_art)

        if media_type == 'tvshow':
            if progress.iscanceled():
                progress.close()
                return

            progress.update(10, f"{title}\n{ADDON.getLocalizedString(32299)}")

            seasons_resp = request("VideoLibrary.GetSeasons", {
                "tvshowid": dbid_int,
                "properties": ["art", "season", "title"]
            })
            seasons = extract_result(seasons_resp, "seasons", [])

            include_episode_thumbs = ADDON.getSettingBool("download.include_episode_thumbs")
            episodes = []
            if include_episode_thumbs:
                episodes_resp = request("VideoLibrary.GetEpisodes", {
                    "tvshowid": dbid_int,
                    "properties": ["art", "season", "episode", "title", "file"]
                })
                episodes = extract_result(episodes_resp, "episodes", [])

            total_items = len(seasons) + len(episodes)
            processed = 0

            for season in seasons:
                if progress.iscanceled():
                    progress.close()
                    return

                if not isinstance(season, dict):
                    processed += 1
                    continue

                season_art = season.get("art", {})
                season_downloadable = _extract_downloadable_art(
                    season_art, skip_prefixes=["tvshow."]
                )

                if season_downloadable:
                    season_id = season.get("seasonid")
                    season_title = season.get("title", f"Season {season.get('season', '?')}")

                    if season_id:
                        pct = 10 + int((processed / max(total_items, 1)) * 85)
                        progress.update(pct, f"{title}\n{season_title}")
                        _download_selected_artwork(
                            "season", season_id, f"{title} - {season_title}", season_downloadable
                        )
                        art_count += len(season_downloadable)
                        season_count += 1

                processed += 1

            for episode in episodes:
                if progress.iscanceled():
                    progress.close()
                    return

                if not isinstance(episode, dict):
                    processed += 1
                    continue

                episode_art = episode.get("art", {})
                episode_downloadable = _extract_downloadable_art(
                    episode_art, skip_prefixes=["tvshow.", "season."]
                )

                if episode_downloadable:
                    episode_id = episode.get("episodeid")
                    ep_title = episode.get("title", "")
                    ep_num = f"S{episode.get('season', 0):02d}E{episode.get('episode', 0):02d}"

                    if episode_id:
                        pct = 10 + int((processed / max(total_items, 1)) * 85)
                        progress.update(pct, f"{title}\n{ep_num} {ep_title}")
                        _download_selected_artwork(
                            "episode", episode_id, f"{title} - {ep_num} {ep_title}",
                            episode_downloadable,
                        )
                        art_count += len(episode_downloadable)
                        episode_count += 1

                processed += 1

        if progress.iscanceled():
            progress.close()
            return

        if media_type in ('movie', 'tvshow'):
            progress.update(95, f"{title}\n{ADDON.getLocalizedString(32981)}")
            file_path = details.get("file", "")
            downloaded, _, _ = download_actor_images(
                media_type=media_type,
                dbid=dbid_int,
                file_path=file_path,
                existing_file_mode=existing_file_mode
            )
            actor_count = downloaded

        progress.close()

    except Exception as e:
        progress.close()
        log("Artwork", f"Error downloading artwork: {e}", xbmc.LOGERROR)
        show_notification(
            ADDON.getLocalizedString(32290),
            str(e),
            xbmcgui.NOTIFICATION_ERROR,
            3000
        )
        return

    total_count = art_count + actor_count
    log(
        "Artwork",
        f"Download counts - art: {art_count}, actors: {actor_count}, total: {total_count}",
        xbmc.LOGDEBUG,
    )
    if total_count == 0:
        show_notification(
            ADDON.getLocalizedString(32290),
            ADDON.getLocalizedString(32296),
            xbmcgui.NOTIFICATION_INFO,
            3000
        )
    else:
        if media_type == 'tvshow':
            parts = [ADDON.getLocalizedString(32014).format(art_count)]
            if season_count > 0:
                parts.append(ADDON.getLocalizedString(32016).format(season_count))
            if episode_count > 0:
                parts.append(ADDON.getLocalizedString(32017).format(episode_count))
            if actor_count > 0:
                parts.append(ADDON.getLocalizedString(32982).format(actor_count))
            message = ADDON.getLocalizedString(32045) + " " + ", ".join(parts)
        else:
            if actor_count > 0:
                message = (
                    ADDON.getLocalizedString(32013).format(art_count) + ", "
                    + ADDON.getLocalizedString(32982).format(actor_count)
                )
            else:
                message = ADDON.getLocalizedString(32013).format(art_count)

        show_notification(
            ADDON.getLocalizedString(32290),
            message,
            xbmcgui.NOTIFICATION_INFO,
            3000
        )


def run_art_fetcher_single(dbid: Optional[str], dbtype: Optional[str]) -> None:
    """Open artwork selection dialog for a single item.

    Falls back to ListItem.DBID/DBType if args are None.
    """
    if not dbid:
        dbid = xbmc.getInfoLabel("ListItem.DBID")
    if not dbtype:
        dbtype = xbmc.getInfoLabel("ListItem.DBType")

    if not dbid or dbid == "-1" or not dbtype:
        show_notification(
            "Artwork",
            "No valid item selected",
            xbmcgui.NOTIFICATION_WARNING,
            3000
        )
        return

    db.init_database()

    dbtype_lower = dbtype.lower()
    dbid_int = int(dbid)

    art_type_options = {
        'movie': [
            'poster', 'fanart', 'clearlogo', 'clearart', 'banner', 'landscape', 'discart', 'keyart'
        ],
        'tvshow': [
            'poster', 'fanart', 'clearlogo', 'clearart', 'banner', 'landscape', 'characterart',
            'keyart',
        ],
        'season': ['poster', 'banner', 'landscape', 'fanart'],
        'episode': ['thumb'],
        'musicvideo': ['thumb', 'fanart'],
        'set': [
            'poster', 'fanart', 'clearlogo', 'clearart', 'banner', 'landscape', 'discart', 'keyart'
        ],
        'artist': ['thumb', 'fanart', 'clearlogo', 'clearart', 'banner', 'landscape', 'cutout'],
        'album': ['thumb', 'discart', 'back', 'spine', '3dcase', '3dflat', '3dface', '3dthumb'],
    }

    art_types = art_type_options.get(dbtype_lower)
    method_info = KODI_GET_DETAILS_METHODS.get(dbtype_lower)

    if not art_types or not method_info:
        show_notification(
            "Artwork",
            f"Unsupported media type: {dbtype}",
            xbmcgui.NOTIFICATION_WARNING,
            3000
        )
        return

    method_name, id_key, result_key = method_info

    properties = ["art"]
    if dbtype_lower == 'album':
        properties.extend(
            ["title", "year", "musicbrainzalbumartistid", "musicbrainzreleasegroupid"]
        )
    elif dbtype_lower == 'artist':
        properties.append("musicbrainzartistid")
    else:
        properties.append("title")
        if dbtype_lower in ('movie', 'tvshow', 'musicvideo'):
            properties.append("year")

    details = extract_result(
        request(method_name, {id_key: dbid_int, "properties": properties}),
        result_key
    )

    if not details or not isinstance(details, dict):
        show_notification(
            "Artwork",
            f"{dbtype.title()} not found",
            xbmcgui.NOTIFICATION_WARNING,
            3000
        )
        return

    title = details.get("artist") or details.get("title") or "Unknown"
    year = details.get("year", "")
    current_art = details.get("art", {})

    if dbtype_lower == 'artist':
        mbid = details.get('musicbrainzartistid')
        if isinstance(mbid, list):
            mbid = mbid[0] if mbid else None
        if not mbid:
            show_notification(
                "Artwork",
                "No MusicBrainz ID for this artist",
                xbmcgui.NOTIFICATION_WARNING,
                4000
            )
            return
    elif dbtype_lower == 'album':
        artist_mbid = details.get('musicbrainzalbumartistid')
        if isinstance(artist_mbid, list):
            artist_mbid = artist_mbid[0] if artist_mbid else None
        release_group_id = details.get('musicbrainzreleasegroupid')
        if not artist_mbid or not release_group_id:
            missing = []
            if not artist_mbid:
                missing.append("artist")
            if not release_group_id:
                missing.append("release group")
            show_notification(
                "Artwork",
                f"Missing MusicBrainz {' & '.join(missing)} ID",
                xbmcgui.NOTIFICATION_WARNING,
                4000
            )
            return

    from lib.data.api.artwork import create_default_fetcher
    from lib.artwork.auto import ArtworkAuto

    fetcher = create_default_fetcher()
    processor = ArtworkAuto(source_fetcher=fetcher, use_background=False)

    show_notification(
        "Artwork",
        "Fetching artwork...",
        xbmcgui.NOTIFICATION_INFO,
        2000
    )

    try:
        all_artwork = fetcher.fetch_all(dbtype_lower, dbid_int, bypass_cache=True)
    except Exception as e:
        log("Artwork", f"Error fetching artwork: {str(e)}", xbmc.LOGERROR)
        show_notification(
            "Artwork",
            "Failed to fetch artwork",
            xbmcgui.NOTIFICATION_ERROR,
            3000
        )
        return

    available_by_type = {
        art_type: all_artwork.get(art_type, [])
        for art_type in art_types
        if all_artwork.get(art_type)
    }

    if not available_by_type:
        show_notification(
            "Artwork",
            "No artwork found",
            xbmcgui.NOTIFICATION_INFO,
            3000
        )
        return

    available_art_types = [art_type for art_type in art_types if art_type in available_by_type]
    art_type_labels = [f"{art_type.capitalize()} ({len(available_by_type[art_type])})"
                       for art_type in available_art_types]

    from lib.artwork.utilities import filter_artwork_by_language

    last_selected = 0
    while True:
        selected = show_select(
            ADDON.getLocalizedString(32555).format(title), art_type_labels, preselect=last_selected
        )

        if selected < 0:
            return

        last_selected = selected

        selected_art_type = available_art_types[selected]
        full_artwork_list = available_by_type[selected_art_type]

        filtered_art = filter_artwork_by_language(full_artwork_list, art_type=selected_art_type)

        current_url = current_art.get(selected_art_type, "")

        action, selected_art, queued_multiart = show_artwork_selection_dialog(
            title=title,
            art_type=selected_art_type,
            available_art=filtered_art,
            full_artwork_list=full_artwork_list,
            media_type=dbtype_lower,
            year=str(year) if year else "",
            current_url=current_url,
            dbid=dbid_int
        )

        art_updates = {}

        if queued_multiart:
            art_updates.update(queued_multiart)

        if action == "selected" and selected_art:
            art_updates[selected_art_type] = selected_art.get("url")

        if art_updates:
            processor._apply_art(dbtype_lower, dbid_int, art_updates)
            xbmc.executebuiltin("Container.Refresh")
            show_notification(
                "Artwork",
                "Artwork updated",
                xbmcgui.NOTIFICATION_INFO,
                2000
            )
            if KodiSettings.download_after_manage_artwork():
                _download_selected_artwork(
                    dbtype_lower, dbid_int, title, art_updates, force_overwrite=True
                )
            refreshed_details = extract_result(
                request(method_name, {id_key: dbid_int, "properties": ["art"]}),
                result_key
            )
            if refreshed_details and isinstance(refreshed_details, dict):
                current_art = refreshed_details.get("art", {})

        if action == "cancel":
            if not queued_multiart:
                continue
            return

        elif action == "skip":
            return


class ArtworkSelection:
    """Interactive artwork selection workflow for queue items."""

    def __init__(
        self,
        session_id: Optional[int] = None,
        media_filter: Optional[List[str]] = None,
        enable_download: bool = False,
    ):

        from lib.data.api.artwork import create_default_fetcher
        from lib.infrastructure.dialogs import ProgressDialog
        from lib.artwork.auto import ArtworkAuto

        fetcher = create_default_fetcher()
        self.auto = ArtworkAuto(source_fetcher=fetcher, enable_download=enable_download)
        self.session_id = session_id  # Resume existing session or None for new
        self.stats = {'applied': 0, 'skipped': 0, 'auto': 0}
        self.media_filter = media_filter or None
        self.review_mode = REVIEW_MODE_MISSING
        self.review_log: Dict[str, List[Dict[str, Any]]] = {key: [] for key in SESSION_DETAIL_KEYS}
        self.remaining_pending: int = 0
        self.loading_progress = ProgressDialog(
            use_background=False, heading=ADDON.getLocalizedString(32273)
        )
        self.enable_download = enable_download
        self._current_art_cache: Dict[Tuple[str, int], Dict[str, Any]] = {}
        self._session_base_stats: Dict[str, Any] = {}

    def _build_stats_payload(self) -> Dict[str, Any]:
        """Return a JSON-serializable snapshot of review statistics and details."""
        payload = _default_session_stats()

        payload.update(self._session_base_stats)

        payload['applied'] = self.stats['applied']
        payload['skipped'] = self.stats['skipped']
        payload['auto'] = self.stats['auto']
        payload['remaining'] = self.remaining_pending
        payload['review_mode'] = self.review_mode
        payload['details'] = {
            key: [dict(entry) for entry in self.review_log.get(key, [])]
            for key in SESSION_DETAIL_KEYS
        }
        return payload

    def review_queue(self) -> Optional[Dict[str, Any]]:
        """Review pending queue items with visual artwork selection.

        Processes the queue in batches, validating each item before prompting.

        Returns:
            Dict with keys: status, cancelled, session_id, remaining, stats.
            None if queue is empty.
        """
        pending_check = db.get_next_batch(
            batch_size=1,
            status='pending',
            media_types=self.media_filter,
        )

        if not pending_check:
            return

        enable_debug = KodiSettings.debug_enabled()
        if enable_debug:
            pending_count = len(
                db.get_next_batch(batch_size=1000, status='pending', media_types=self.media_filter)
            )
            log(
                "Artwork",
                f"Manual review starting: {pending_count} pending items, "
                f"media_filter={self.media_filter}",
            )

        self._initialize_session()
        assert self.session_id is not None

        cancelled = False
        self.loading_progress.create(ADDON.getLocalizedString(32275))

        try:
            while not cancelled:
                if self.loading_progress.is_cancelled():
                    cancelled = True
                    break

                self._current_art_cache.clear()

                queue_batch = db.get_next_batch(
                    batch_size=25,
                    status='pending',
                    media_types=self.media_filter,
                )

                if not queue_batch:
                    break

                queue_ids = [entry.id for entry in queue_batch]
                art_items_by_queue = db.get_art_items_for_queue_batch(queue_ids)

                for queue_entry in queue_batch:
                    if self.loading_progress.is_cancelled():
                        cancelled = True
                        break

                    art_items = art_items_by_queue.get(queue_entry.id, [])
                    pending_art, current_art = self._collect_pending_art_items(
                        queue_entry, art_items
                    )
                    if not pending_art:
                        continue

                    result = self._review_single_item(queue_entry, pending_art, current_art)

                    if result == 'cancel':
                        cancelled = True
                        break
                    elif result == 'applied':
                        self.stats['applied'] += 1
                    elif result == 'skipped':
                        self.stats['skipped'] += 1
                    elif result == 'auto':
                        self.stats['auto'] += 1

                    db.update_session_stats(
                        self.session_id,
                        _serialise_session_stats(self._build_stats_payload()),
                    )
        finally:
            self.loading_progress.close()

        enable_debug = KodiSettings.debug_enabled()
        if enable_debug:
            status = "cancelled" if cancelled else "complete"
            log("Artwork",
                f"Manual review {status}: applied={self.stats['applied']}, "
                f"skipped={self.stats['skipped']}, "
                f"auto={self.stats.get('auto', 0)}, session={self.session_id}"
            )

        applied_count = self.stats['applied']
        skipped_count = self.stats['skipped']
        auto_count = self.stats.get('auto', 0)
        manual_total = applied_count + skipped_count
        remaining = db.count_queue_items(
            status='pending',
            media_types=self.media_filter,
        )
        self.remaining_pending = remaining

        if cancelled:
            db.update_session_stats(
                self.session_id, _serialise_session_stats(self._build_stats_payload())
            )
            db.cancel_session(self.session_id)
            heading = (
                f"Cancelled: manual {manual_total} "
                f"(applied {applied_count}, skipped {skipped_count})"
            )
            message = f"Auto-skipped: {auto_count}"
            show_notification(heading, message, xbmcgui.NOTIFICATION_INFO, 5000)
        else:
            db.update_session_stats(
                self.session_id, _serialise_session_stats(self._build_stats_payload())
            )
            db.complete_session(self.session_id)
            heading = (
                f"Complete: manual {manual_total} "
                f"(applied {applied_count}, skipped {skipped_count})"
            )
            message = f"Auto-skipped: {auto_count}"
            show_notification(heading, message, xbmcgui.NOTIFICATION_INFO, 5000)

        outcome = {
            'status': 'cancelled' if cancelled else 'completed',
            'cancelled': cancelled,
            'session_id': self.session_id,
            'remaining': remaining,
            'stats': self._build_stats_payload()
        }

        return outcome

    def _initialize_session(self) -> None:
        """Create the manual review session."""
        if not self.session_id:
            self.session_id = db.create_scan_session(
                scan_type='manual_review',
                media_types=self.media_filter or [],
                art_types=[]
            )
            log("Artwork", f"Created review session {self.session_id}", xbmc.LOGDEBUG)

    def _collect_pending_art_items(
        self,
        queue_entry: QueueEntry,
        art_items: Optional[List[ArtItemEntry]] = None
    ) -> Tuple[List[ArtItemEntry], Dict[str, Any]]:
        """Return pending art items plus current artwork state for validation."""
        if art_items is None:
            art_items = db.get_art_items_for_queue(queue_entry.id)
        current_art = self._get_current_artwork(queue_entry.media_type, queue_entry.dbid)

        pending_items: List[ArtItemEntry] = []
        stale_reasons: List[Tuple[str, str]] = []

        for art_item in art_items:
            if art_item.status not in ('pending', None):
                continue

            if current_art.get(art_item.art_type):
                db.update_art_item_status(art_item.id, 'stale')
                stale_reasons.append((art_item.art_type, "Artwork already set"))
                continue

            pending_items.append(art_item)

        if not pending_items:
            if stale_reasons:
                db.update_queue_status(queue_entry.id, 'completed')
            return [], current_art

        return pending_items, current_art

    def _get_current_artwork(self, media_type: str, dbid: int) -> Dict[str, Any]:
        """Fetch current artwork from Kodi (with per-item caching)."""
        cache_key = (media_type, dbid)

        if cache_key in self._current_art_cache:
            return self._current_art_cache[cache_key]

        if media_type not in KODI_GET_DETAILS_METHODS:
            return {}

        try:
            details = get_item_details(media_type, dbid, ['art'])
        except Exception as e:
            log(
                "Artwork",
                f"Failed to get current artwork for {media_type}:{dbid}: {e}",
                xbmc.LOGERROR,
            )
            return {}

        if not isinstance(details, dict):
            return {}

        current_art = details.get('art', {}) or {}

        self._current_art_cache[cache_key] = current_art

        return current_art


    def _load_available_artwork(
        self, media_type: str, dbid: int, title: str
    ) -> Dict[str, List[Any]]:
        """Load all available artwork for a media item, bypassing cache for manual review."""
        self.loading_progress.update(10, ADDON.getLocalizedString(32276).format(title))
        try:
            all_available_art = self.auto.source_fetcher.fetch_all(
                media_type, dbid, bypass_cache=True
            )
        except Exception as exc:
            log("Artwork", f"Failed to load artwork for {title}: {exc}", xbmc.LOGERROR)
            all_available_art = {}
        return all_available_art

    def _log_review_event(self, category: str, entry_data: Dict[str, Any]) -> None:
        entry_data['timestamp'] = datetime.now().isoformat()
        log = self.review_log[category]
        log.append(entry_data)

        if len(log) > MAX_REVIEW_LOG_ITEMS:
            log.pop(0)

    def _handle_user_cancel(self, queue_entry: QueueEntry, applied_any: bool) -> str:
        """Handle user cancellation during review."""
        if applied_any:
            db.update_queue_status(queue_entry.id, 'completed')
            return 'applied'
        else:
            db.update_queue_status(queue_entry.id, 'pending')
            return 'cancel'

    def _apply_selected_artwork(
        self,
        queue_entry: QueueEntry,
        art_item: ArtItemEntry,
        selected_art: Dict[str, Any]
    ) -> bool:
        """Apply selected artwork and log the action. Returns True if applied."""
        media_type = queue_entry.media_type
        dbid = queue_entry.dbid
        art_type = art_item.art_type

        latest_art = self._get_current_artwork(queue_entry.media_type, queue_entry.dbid)
        if latest_art.get(art_type):
            db.update_art_item_status(art_item.id, 'stale')
            self._log_review_event('stale', {
                'title': queue_entry.title,
                'art_type': art_type,
                'media_type': media_type,
                'dbid': dbid,
                'guid': queue_entry.guid,
                'reason': 'artwork_no_longer_missing',
            })
            return False

        self.auto._apply_art(media_type, dbid, {art_type: selected_art['url']})

        cache_key = (media_type, dbid)
        if cache_key in self._current_art_cache:
            del self._current_art_cache[cache_key]

        db.update_art_item(art_item.id, selected_art['url'], auto_applied=False)
        self._log_review_event('manual_applied', {
            'title': queue_entry.title,
            'art_type': art_type,
            'media_type': media_type,
            'dbid': dbid,
            'guid': queue_entry.guid,
            'url': selected_art.get('url', ''),
            'source': selected_art.get('source', ''),
        })
        return True

    def _log_no_options(self, queue_entry: QueueEntry, art_type: str) -> None:
        """Log when no artwork options are available for an item."""
        self._log_review_event('manual_auto', {
            'title': queue_entry.title,
            'art_type': art_type,
            'media_type': queue_entry.media_type,
            'dbid': queue_entry.dbid,
            'guid': queue_entry.guid,
            'reason': 'no_options',
        })

    def _process_dialog_action(
        self,
        action: str,
        selected_art: Optional[Dict[str, Any]],
        queue_entry: QueueEntry,
        art_item: ArtItemEntry,
        applied_any: bool
    ) -> Tuple[str, bool]:
        """Process user action from artwork selection dialog.

        Returns:
            (flow_control, applied_any) where flow_control is 'cancel', 'continue', or 'applied'.
        """
        if action == 'cancel':
            return ('cancel', applied_any)

        if action == 'skip':
            db.update_art_item_status(art_item.id, 'skipped')
            self._log_review_event('manual_skipped', {
                'title': queue_entry.title,
                'art_type': art_item.art_type,
                'media_type': queue_entry.media_type,
                'dbid': queue_entry.dbid,
                'guid': queue_entry.guid,
                'reason': 'user_skip',
            })
            return ('continue', applied_any)

        if action == 'selected' and selected_art:
            if self._apply_selected_artwork(queue_entry, art_item, selected_art):
                return ('applied', True)

        return ('continue', applied_any)

    def _finalize_review_status(
        self,
        queue_entry: QueueEntry,
        art_items: List[ArtItemEntry],
        applied_any: bool,
        had_options: bool,
        auto_logged: bool
    ) -> str:
        """Finalize queue status and return result after reviewing all art items."""
        if applied_any:
            db.update_queue_status(queue_entry.id, 'completed')
            return 'applied'

        db.update_queue_status(queue_entry.id, 'skipped')
        if not had_options and not auto_logged:
            for art_item in art_items:
                self._log_review_event('manual_auto', {
                    'title': queue_entry.title,
                    'art_type': art_item.art_type,
                    'media_type': queue_entry.media_type,
                    'dbid': queue_entry.dbid,
                    'guid': queue_entry.guid,
                    'reason': 'all_art_types_missing',
                })
        return 'skipped' if had_options else 'auto'

    def _review_single_item(
        self, queue_entry: QueueEntry, art_items: List[ArtItemEntry],
        current_art: Dict[str, Any],
    ) -> str:
        """Review a single queue item with visual artwork selection."""
        from lib.artwork.utilities import filter_artwork_by_language

        enable_debug = KodiSettings.debug_enabled()
        if enable_debug:
            art_types = [item.art_type for item in art_items]
            log(
                "Artwork",
                f"Reviewing item: '{queue_entry.title}' "
                f"({len(art_items)} art types: {', '.join(art_types)})",
            )

        art_priority = {
            'poster': 1, 'fanart': 2, 'clearlogo': 3, 'clearart': 4,
            'banner': 5, 'landscape': 6, 'characterart': 7, 'discart': 8, 'keyart': 9,
        }
        sorted_items = sorted(art_items, key=lambda item: art_priority.get(item.art_type, 99))

        all_available_art = self._load_available_artwork(
            queue_entry.media_type, queue_entry.dbid, queue_entry.title
        )

        applied_any = False
        had_options = False
        auto_logged = False

        for art_item in sorted_items:
            full_available = all_available_art.get(art_item.art_type, [])
            filtered_available = filter_artwork_by_language(
                full_available, art_type=art_item.art_type
            )

            if not filtered_available:
                self._log_no_options(queue_entry, art_item.art_type)
                auto_logged = True
                continue

            had_options = True
            action, selected_art, queued_multiart = show_artwork_selection_dialog(
                queue_entry.title, art_item.art_type, filtered_available,
                full_artwork_list=full_available,
                media_type=queue_entry.media_type, year=queue_entry.year or '',
                current_url=current_art.get(art_item.art_type, ''),
                dbid=queue_entry.dbid, review_mode=art_item.review_mode
            )

            if queued_multiart:
                self.auto._apply_art(queue_entry.media_type, queue_entry.dbid, queued_multiart)

            flow_control, applied_any = self._process_dialog_action(
                action, selected_art, queue_entry, art_item, applied_any
            )

            if flow_control == 'cancel':
                return self._handle_user_cancel(queue_entry, applied_any)
            elif flow_control == 'applied':
                applied_any = True

        result = self._finalize_review_status(
            queue_entry, art_items, applied_any, had_options, auto_logged
        )

        enable_debug = KodiSettings.debug_enabled()
        if enable_debug:
            log("Artwork", f"Item review complete: '{queue_entry.title}', result={result}")

        return result


class ArtworkManager:
    """Coordinates artwork management workflows."""

    def __init__(self, scope_arg: Optional[str] = None):
        self.scope_arg = scope_arg.lower().strip() if scope_arg else None
        self.scope: Optional[str] = None
        self.media_filter: Optional[List[str]] = None
        self.session_id: Optional[int] = None
        self.review_mode: str = REVIEW_MODE_MISSING

    def run(self) -> None:
        db.init_database()
        db.cleanup_old_queue_items()

        if self.scope_arg:
            if not self._handle_scope_arg():
                return
            self.scope_arg = None

        self._select_intent()

    def _handle_scope_arg(self) -> bool:
        """Handle pre-selected scope from argument."""
        valid_scopes = {scope for scope, _ in REVIEW_SCOPE_OPTIONS}

        if self.scope_arg not in valid_scopes:
            show_notification(
                "Missing Artwork",
                f"Unknown scope '{self.scope_arg}'.",
                xbmcgui.NOTIFICATION_WARNING,
                4000
            )
            return False

        self.scope = self.scope_arg
        self.media_filter = (
            None if self.scope == 'all' else REVIEW_MEDIA_FILTERS.get(self.scope, None)
        )
        self.session_id = None

        scope_label = REVIEW_SCOPE_LABELS.get(self.scope, self.scope.title())

        items = []

        items.append(
            MenuItem(
                ADDON.getLocalizedString(32502),
                lambda: self._handle_manual_review(enable_download=False),
            )
        )

        if KodiSettings.enable_combo_workflows():
            items.append(
                MenuItem(
                    ADDON.getLocalizedString(32503),
                    lambda: self._handle_manual_review(enable_download=True),
                )
            )

        items.append(
            MenuItem(
                ADDON.getLocalizedString(32504), lambda: self._run_auto_apply_and_return_false()
            )
        )
        items.append(
            MenuItem(
                ADDON.getLocalizedString(32086),
                lambda: self._view_scope_report(scope_label),
                loop=True,
            )
        )

        menu = Menu(f"{scope_label} - Select Action", items)
        result = menu.show()
        return result if isinstance(result, bool) else False

    def _run_auto_apply_and_return_false(self) -> bool:
        """Run auto-apply and return False to exit workflow."""
        self._run_auto_apply_mode()
        return False

    def _view_scope_report(self, scope_label: str) -> None:
        """View report for current scope."""
        last_session = db.get_last_manual_review_session(self.media_filter)
        if last_session and last_session['stats']:
            _show_session_report(last_session)
        else:
            show_notification(
                "View Report",
                f"No report available for {scope_label}.",
                xbmcgui.NOTIFICATION_INFO,
                3000
            )

    def _select_intent(self):
        """Show the artwork review main menu."""
        items = []

        items.append(
            MenuItem(ADDON.getLocalizedString(32502), self._handle_manual_review_flow, loop=True)
        )

        if KodiSettings.enable_combo_workflows():
            items.append(
                MenuItem(
                    ADDON.getLocalizedString(32503),
                    self._handle_manual_review_download_flow,
                    loop=True,
                )
            )

        items.extend([
            MenuItem(ADDON.getLocalizedString(32504), self._handle_auto_apply_flow, loop=True),
            MenuItem(ADDON.getLocalizedString(32505), self._handle_view_reports_flow, loop=True),
        ])

        menu = Menu(ADDON.getLocalizedString(32273), items)
        return menu.show()

    def _handle_manual_review_flow(self):
        """Handle 'Browse & Choose Artwork' flow with scope selection."""
        items = []

        for scope, label in REVIEW_SCOPE_OPTIONS:
            items.append(
                MenuItem(
                    label, lambda s=scope: self._start_scan_for_scope(s, enable_download=False)
                )
            )

        menu = Menu(ADDON.getLocalizedString(32507), items)
        return menu.show()

    def _handle_manual_review_download_flow(self):
        """Handle 'Browse & Choose + Download' flow with scope selection."""
        items = []

        for scope, label in REVIEW_SCOPE_OPTIONS:
            items.append(
                MenuItem(label, lambda s=scope: self._start_scan_for_scope(s, enable_download=True))
            )

        menu = Menu(ADDON.getLocalizedString(32508), items)
        return menu.show()

    def _start_scan_for_scope(self, scope: str, enable_download: bool = False) -> bool:
        """Start scan workflow for selected scope."""
        self.scope = scope
        self.media_filter = None if scope == 'all' else REVIEW_MEDIA_FILTERS.get(scope, None)
        self.session_id = None
        return self._handle_manual_review(enable_download=enable_download)

    def _handle_auto_apply_flow(self):
        """Handle 'Auto-Fill Missing Artwork' flow with scope selection."""
        items = [MenuItem(xbmc.getLocalizedString(593), lambda: self._run_auto_apply('all'))]

        for scope, label in REVIEW_SCOPE_OPTIONS:
            if scope != 'all':
                items.append(MenuItem(label, lambda s=scope: self._run_auto_apply(s)))

        menu = Menu(ADDON.getLocalizedString(32509), items)
        return menu.show()

    def _run_auto_apply_mode(self) -> None:
        """Foreground/background picker, then auto-apply for the current scope."""
        from lib.infrastructure.menus import run_with_mode_choice

        run_with_mode_choice(
            ADDON.getLocalizedString(32072),
            lambda bg: self._handle_auto_apply_missing(use_background=bg),
        )

    def _run_auto_apply(self, scope: str) -> None:
        """Execute auto-apply for selected scope."""
        scope_label = REVIEW_SCOPE_LABELS.get(scope, scope.title())

        message = (
            "Automatically applies missing artwork without review.[CR]"
            "Only fills in missing artwork, won't replace existing.[CR]"
            "View results afterwards in Session History.[CR][CR]"
            "Continue?"
        )

        confirmed = show_yesno(
            f"Auto-Fill {scope_label}",
            message,
            nolabel=xbmc.getLocalizedString(222),
            yeslabel=ADDON.getLocalizedString(32567)
        )

        if not confirmed:
            return

        self.scope = scope
        self.media_filter = None if scope == 'all' else REVIEW_MEDIA_FILTERS.get(scope, None)
        self.session_id = None
        self._run_auto_apply_mode()

    def _handle_view_reports_flow(self):
        """Handle 'View Session History' flow with scope selection."""
        items = [
            MenuItem(ADDON.getLocalizedString(32510), self._view_last_report_any_scope, loop=True)
        ]

        for scope, label in REVIEW_SCOPE_OPTIONS:
            if scope != 'all':
                items.append(
                    MenuItem(label, lambda s=scope: self._view_report_for_scope(s), loop=True)
                )

        menu = Menu(ADDON.getLocalizedString(32512), items)
        return menu.show()

    def _view_last_report_any_scope(self) -> None:
        """View the last report from any scope."""
        last_session = db.get_last_manual_review_session(None)
        if last_session and last_session['stats']:
            _show_session_report(last_session)
        else:
            show_notification(
                "View Reports",
                "No reports available.",
                xbmcgui.NOTIFICATION_INFO,
                3000
            )

    def _view_report_for_scope(self, scope: str) -> None:
        """View report for a specific scope."""
        self.scope = scope
        self.media_filter = None if scope == 'all' else REVIEW_MEDIA_FILTERS.get(scope, None)

        last_session = db.get_last_manual_review_session(self.media_filter)

        if last_session and last_session['stats']:
            _show_session_report(last_session)
        else:
            show_notification(
                "View Reports",
                f"No report available for {REVIEW_SCOPE_LABELS.get(scope, scope)}.",
                xbmcgui.NOTIFICATION_INFO,
                3000
            )

    def _clear_scope_queue(self) -> None:
        if self.media_filter:
            db.clear_queue_for_media(self.media_filter)
        else:
            db.clear_queue_and_sessions()
        log("Artwork", "Cleared queue for scope")

    def _handle_auto_apply_missing(self, use_background: bool = False) -> None:
        from lib.artwork.auto import ArtworkAuto
        from lib.infrastructure import tasks as task_manager

        if not self.scope:
            return

        try:
            with task_manager.TaskContext(ADDON.getLocalizedString(32072)) as ctx:
                scanner = _scan_scope(
                    self.scope, use_background=use_background,
                    abort_flag=ctx.abort_flag, task_context=ctx)
                if not scanner or scanner.cancelled:
                    return

                processor = ArtworkAuto(
                    use_background=use_background, mode=REVIEW_MODE_MISSING,
                    abort_flag=ctx.abort_flag, task_context=ctx)
                processor.process_queue(media_types=self.media_filter)
        except Exception as e:
            log("Artwork", f"Auto-apply failed: {str(e)}", xbmc.LOGERROR)
            show_notification(
                ADDON.getLocalizedString(32072),
                ADDON.getLocalizedString(32274),
                xbmcgui.NOTIFICATION_ERROR,
                4000,
            )

    def _handle_manual_review(self, enable_download: bool = False) -> bool:
        if not self.scope:
            return False

        self.review_mode = REVIEW_MODE_MISSING
        self._clear_scope_queue()
        self.session_id = None

        scanner = _scan_scope(self.scope)
        if not scanner:
            return False
        if scanner.cancelled:
            return True

        pending_total = db.count_queue_items(status='pending', media_types=self.media_filter)

        if pending_total == 0:
            show_ok(
                ADDON.getLocalizedString(32273),
                ADDON.getLocalizedString(32295)
            )
            return False

        reviewer = ArtworkSelection(
            session_id=self.session_id,
            media_filter=self.media_filter,
            enable_download=enable_download,
        )
        review_outcome = reviewer.review_queue()
        if not review_outcome:
            return False

        return True

def run_artwork_manager(scope: Optional[str] = None) -> None:
    normalized = scope.lower().strip() if scope else None

    valid_scopes = {s for s, _ in REVIEW_SCOPE_OPTIONS}
    if normalized:
        if normalized == 'single':
            run_art_fetcher_single(None, None)
            return
        if normalized in valid_scopes:
            manager = ArtworkManager(normalized)
            manager.run()
            return
        show_notification(
            "Missing Artwork",
            f"Unknown scope '{normalized}'.",
            xbmcgui.NOTIFICATION_WARNING,
            4000
        )
        return

    manager = ArtworkManager()
    manager.run()
