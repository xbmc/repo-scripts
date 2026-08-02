"""Bulk artwork download workflow coordinators."""
from __future__ import annotations

import time
from datetime import datetime
import xbmc
from lib.infrastructure.dialogs import show_ok, show_textviewer, DialogProgress
import xbmcgui
import xbmcvfs
from typing import Optional, List, Dict, Tuple, Any

from lib.kodi.client import KODI_GET_LIBRARY_METHODS, get_library_items
from lib.download.queue import DownloadQueue
from lib.infrastructure.paths import (
    DirectoryListing, PathBuilder, get_album_folders, resolve_media_file, use_basename_for
)
from lib.infrastructure.tasks import TaskContext
from lib.infrastructure.workers import STALL_TIMEOUT_SECONDS
from lib.artwork.config import REVIEW_MEDIA_FILTERS, REVIEW_SCOPE_LABELS
from lib.kodi.client import log, ADDON, is_inherited_art
from lib.data import database as db

# Log file paths
LOG_DIR = xbmcvfs.translatePath('special://profile/addon_data/script.skin.info.service/')
LOG_FILE = LOG_DIR + 'artwork_download.log'
LOG_FILE_PREVIOUS = LOG_DIR + 'artwork_download_previous.log'
MAX_LOG_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

ART_EXTENSIONS = ('jpg', 'png', 'gif', 'webp')

ERROR_CATEGORY_LABELS = {
    'network': "Network errors (timeouts / connection failures)",
    'provider_blocked': "Source blocked after repeated failures (one server kept erroring)",
    'storage_blocked': (
        "Writing stopped after repeated file errors (check disk space / permissions)"
    ),
    'directory': "Could not create destination folder (check permissions)",
    'bad_content': "Server returned a non-image response",
    'input': "Missing URL or destination path",
    'unexpected': "Unexpected errors (see debug log)",
}

# Valid properties per media type from Kodi JSON-RPC introspect
DOWNLOAD_PROPERTIES = {
    'movie': ['art', 'title', 'file'],
    'tvshow': ['art', 'title', 'file', 'season', 'episode'],
    'episode': ['art', 'title', 'file', 'season', 'episode', 'tvshowid'],
    'musicvideo': ['art', 'title', 'file'],
    'set': ['art', 'title'],
    'season': ['art', 'title', 'season', 'episode', 'tvshowid'],
    'artist': ['art', 'musicbrainzartistid'],
    'album': ['art', 'title'],
}


def _ensure_log_directory() -> None:
    """Create log directory if it doesn't exist."""
    if not xbmcvfs.exists(LOG_DIR):
        xbmcvfs.mkdirs(LOG_DIR)


def _rotate_log_files() -> None:
    """Rotate log files: current -> previous, delete old previous."""
    if xbmcvfs.exists(LOG_FILE):
        if xbmcvfs.exists(LOG_FILE_PREVIOUS):
            xbmcvfs.delete(LOG_FILE_PREVIOUS)
        xbmcvfs.rename(LOG_FILE, LOG_FILE_PREVIOUS)


def write_download_log(report_text: str, scope: str, stats: Dict) -> Optional[str]:
    """Write the download report to disk with 2-file rotation. Returns log path on success."""
    try:
        _ensure_log_directory()
        _rotate_log_files()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scope_label = REVIEW_SCOPE_LABELS.get(scope, scope.title())

        header = "=" * 80 + "\n"
        header += f"Artwork Download Report - {timestamp}\n"
        header += f"Scope: {scope_label}\n"
        header += "=" * 80 + "\n\n"

        full_text = header + report_text

        estimated_size = len(full_text.encode('utf-8'))

        if estimated_size > MAX_LOG_SIZE_BYTES:
            folder_stats = stats.get('folder_counts', {})
            if folder_stats:
                max_folders = int((MAX_LOG_SIZE_BYTES * 0.8) / 265)

                sorted_folders = sorted(folder_stats.items(), key=lambda x: x[0])
                truncated_count = len(sorted_folders) - max_folders

                if truncated_count > 0:
                    truncated_text = (
                        f"\n(Truncated {truncated_count} folders to fit 5MB size limit)\n"
                    )

                    folder_lines = [
                        f"{count} files - {path}"
                        for path, count in sorted_folders[:max_folders]
                    ]

                    report_parts = report_text.split("[B]Downloaded Files by Folder[/B]")
                    if len(report_parts) == 2:
                        before_folders = report_parts[0] + "[B]Downloaded Files by Folder[/B]\n\n"
                        after_folders = ""

                        if "[B]Filename Pattern Mismatches" in report_parts[1]:
                            _, mismatch_part = report_parts[1].split(
                                "[B]Filename Pattern Mismatches", 1
                            )
                            after_folders = (
                                "\n\n[B]Filename Pattern Mismatches" + mismatch_part
                            )

                        report_text = (
                            before_folders + truncated_text
                            + "\n".join(folder_lines) + after_folders
                        )
                        full_text = header + report_text

        with xbmcvfs.File(LOG_FILE, 'w') as f:
            f.write(full_text.encode('utf-8'))

        return LOG_FILE

    except Exception as e:
        log("Download", f"Error writing download log: {str(e)}", xbmc.LOGERROR)
        return None


def get_library_items_for_download(media_types: List[str]) -> List[Dict[str, Any]]:
    """Query Kodi library, return items with artwork as `{dbid, media_type, title, file, art}`."""
    def has_artwork(item: Dict[str, Any]) -> bool:
        art = item.get('art', {})
        return bool(art and isinstance(art, dict))

    try:
        log("Artwork", f"Querying library for media types: {', '.join(media_types)}", xbmc.LOGDEBUG)
        all_items: List[Dict[str, Any]] = []

        for media_type in media_types:
            if media_type not in KODI_GET_LIBRARY_METHODS:
                continue

            properties = DOWNLOAD_PROPERTIES.get(media_type, ['art', 'title'])

            include_seasons = media_type == 'tvshow'
            season_props = DOWNLOAD_PROPERTIES.get('season', ['art', 'title', 'season'])

            items = get_library_items(
                media_types=[media_type],
                properties=properties,
                decode_urls=True,
                include_nested_seasons=include_seasons,
                season_properties=season_props,
                filter_func=has_artwork
            )

            all_items.extend(items)

        album_ids = [item['dbid'] for item in all_items
                     if item.get('media_type') == 'album' and item.get('dbid')]
        album_folders = get_album_folders(album_ids)

        for item in all_items:
            item['file'] = resolve_media_file(item, album_folders=album_folders)

            if 'title' not in item:
                item['title'] = item.get('label', 'Unknown')

        log("Artwork", f"Retrieved {len(all_items)} library items with artwork", xbmc.LOGDEBUG)
        return all_items

    except Exception as e:
        log("Download", f"Error querying library for download: {str(e)}", xbmc.LOGERROR)
        return []


def build_download_jobs(
    items: List[Dict[str, Any]]
) -> Tuple[List[Tuple[str, str, str, str, Optional[str], str]], Dict[str, int]]:
    """Build download jobs and per-type mismatch counters.

    Jobs are `(url, local_path, art_type, title, alternate_path, media_type)` tuples.
    Mismatch keys: `{movie,mvid}_{basename,folder}_to_{other}`. Each increments when
    an existing file under the opposite naming convention is detected.
    """
    log("Artwork", f"Building download jobs from {len(items)} library items", xbmc.LOGDEBUG)
    jobs = []
    path_builder = PathBuilder()
    listing = DirectoryListing()

    savewith_basefilename = ADDON.getSettingBool('download.savewith_basefilename')

    mismatch_counts = {'movie_basename_to_folder': 0, 'movie_folder_to_basename': 0,
                       'mvid_basename_to_folder': 0, 'mvid_folder_to_basename': 0}

    skipped_no_path = 0
    failed_build_path = 0

    for item in items:
        media_type = item['media_type']
        title = item['title']
        art = item['art']
        file_path = item.get('file', '')

        if not file_path and media_type not in ('season', 'tvshow', 'set', 'artist', 'album'):
            skipped_no_path += 1
            continue

        use_basename = use_basename_for(media_type, savewith_basefilename)

        for art_type, url in art.items():
            if not url or not url.startswith('http'):
                continue

            if is_inherited_art(media_type, art_type):
                continue

            mbid = None
            if media_type == 'artist':
                mbid = item.get('musicbrainzartistid', '')
                if isinstance(mbid, list):
                    mbid = mbid[0] if mbid else ''

            local_path = path_builder.build_path(
                media_type=media_type,
                media_file=file_path,
                artwork_type=art_type,
                season_number=item.get('season'),
                use_basename=use_basename,
                mbid=mbid
            )

            if not local_path:
                failed_build_path += 1
                log(
                    "Download",
                    f"Failed to build path for {media_type} '{title}' "
                    f"art:{art_type} file:{file_path}",
                    xbmc.LOGWARNING,
                )
                continue

            alternate_path = None
            if media_type in ('movie', 'musicvideo'):
                alternate_path = path_builder.build_path(
                    media_type=media_type,
                    media_file=file_path,
                    artwork_type=art_type,
                    season_number=item.get('season'),
                    use_basename=not use_basename
                )

                if alternate_path and listing.find_with_extension(alternate_path, ART_EXTENSIONS):
                    if media_type == 'movie':
                        if use_basename:
                            mismatch_counts['movie_folder_to_basename'] += 1
                        else:
                            mismatch_counts['movie_basename_to_folder'] += 1
                    else:
                        if use_basename:
                            mismatch_counts['mvid_folder_to_basename'] += 1
                        else:
                            mismatch_counts['mvid_basename_to_folder'] += 1

            jobs.append((url, local_path, art_type, title, alternate_path, media_type))

    total_mismatches = sum(mismatch_counts.values())
    log("Artwork", f"Built {len(jobs)} download jobs from {len(items)} items "
        f"(skipped: {skipped_no_path} no path, {failed_build_path} path build failed, "
        f"{total_mismatches} mismatches)")
    return jobs, mismatch_counts


def download_scope_artwork(scope: str, media_filter: Optional[List[str]] = None,
                           use_background: bool = False) -> None:
    """Download every artwork URL for a scope, wrapped in a TaskContext.

    `use_background=True` uses `DialogProgressBG`; False uses a foreground `DialogProgress`.
    """
    from lib.infrastructure.dialogs import show_yesno

    monitor = xbmc.Monitor()

    if media_filter is None:
        media_filter = REVIEW_MEDIA_FILTERS.get(scope, ['movie', 'tvshow', 'episode'])

    if not ADDON.getSettingBool('download.include_episode_thumbs'):
        media_filter = [mt for mt in media_filter if mt != 'episode']

    media_filter = [mt for mt in media_filter if mt in KODI_GET_LIBRARY_METHODS]

    if not media_filter:
        show_ok(
            ADDON.getLocalizedString(32290),
            ADDON.getLocalizedString(32043)
        )
        return

    if use_background:
        progress = xbmcgui.DialogProgressBG()
        progress.create(ADDON.getLocalizedString(32290), ADDON.getLocalizedString(32291))
    else:
        progress = DialogProgress()
        progress.create(ADDON.getLocalizedString(32290), ADDON.getLocalizedString(32291))

    try:
        if use_background:
            progress.update(5, message=ADDON.getLocalizedString(32292))
        else:
            progress.update(5, ADDON.getLocalizedString(32292))
        items = get_library_items_for_download(media_filter)

        if not items:
            progress.close()
            show_ok(
                ADDON.getLocalizedString(32290),
                ADDON.getLocalizedString(32171)
            )
            return

        if monitor.abortRequested() or (
            isinstance(progress, xbmcgui.DialogProgress) and progress.iscanceled()
        ):
            progress.close()
            return

        if use_background:
            progress.update(15, message=ADDON.getLocalizedString(32293).format(len(items)))
        else:
            progress.update(15, ADDON.getLocalizedString(32293).format(len(items)))

        existing_file_mode_setting = ADDON.getSetting('download.existing_file_mode')
        existing_file_mode_int = (
            int(existing_file_mode_setting) if existing_file_mode_setting else 0
        )
        existing_file_mode = ['skip', 'overwrite'][existing_file_mode_int]

        jobs, mismatch_counts = build_download_jobs(items)

        if existing_file_mode == 'overwrite' and sum(mismatch_counts.values()) > 0:
            progress.close()

            total_mismatches = sum(mismatch_counts.values())
            savewith_basefilename = ADDON.getSettingBool('download.savewith_basefilename')

            pattern_desc = []
            if (mismatch_counts.get('movie_folder_to_basename', 0) > 0
                    or mismatch_counts.get('movie_basename_to_folder', 0) > 0):
                pattern_desc.append(
                    f"Movies: {'basename' if savewith_basefilename else 'folder'} mode"
                )
            if (mismatch_counts.get('mvid_folder_to_basename', 0) > 0
                    or mismatch_counts.get('mvid_basename_to_folder', 0) > 0):
                pattern_desc.append("Music videos: basename mode")

            pattern_text = ", ".join(pattern_desc)

            confirmed = show_yesno(
                ADDON.getLocalizedString(32119),
                f"[B]Overwrite mode is enabled[/B][CR][CR]"
                f"Filename pattern: {pattern_text}[CR]"
                f"Mismatches detected: {total_mismatches} files[CR][CR]"
                f"Original artwork will be [B]deleted[/B] after successful download.[CR][CR]",
                nolabel=xbmc.getLocalizedString(222),
                yeslabel=ADDON.getLocalizedString(32566)
            )

            if not confirmed:
                return

            if use_background:
                progress = xbmcgui.DialogProgressBG()
                progress.create(ADDON.getLocalizedString(32290), ADDON.getLocalizedString(32291))
            else:
                progress = DialogProgress()
                progress.create(ADDON.getLocalizedString(32290), ADDON.getLocalizedString(32291))

        if not jobs:
            progress.close()
            show_ok(
                ADDON.getLocalizedString(32290),
                ADDON.getLocalizedString(32118).format(len(items))
            )
            return

        if monitor.abortRequested() or (
            isinstance(progress, xbmcgui.DialogProgress) and progress.iscanceled()
        ):
            progress.close()
            return

        if use_background:
            progress.update(25, message=ADDON.getLocalizedString(32294).format(len(jobs)))
        else:
            progress.update(25, ADDON.getLocalizedString(32294).format(len(jobs)))

        with TaskContext("Download Artwork") as ctx:
            queue = DownloadQueue(
                existing_file_mode=existing_file_mode,
                abort_flag=ctx.abort_flag,
                task_context=ctx
            )
            queue.start()

            try:
                for job in jobs:
                    url, local_path, artwork_type, title, alternate_path, media_type = job
                    queue.add_download(
                        url, local_path, artwork_type, title, alternate_path, media_type
                    )

                log(
                    "Artwork",
                    f"Queued {len(jobs)} download jobs to "
                    f"{queue.num_workers} worker threads",
                )
                last_update_time = time.time()
                last_progress_time = time.time()
                last_completed = 0
                last_activity = 0
                stalled = False

                while not queue.queue.empty() or queue.processing_set:
                    if monitor.abortRequested() or ctx.abort_flag.is_requested() or (
                        isinstance(progress, xbmcgui.DialogProgress)
                        and progress.iscanceled()
                    ):
                        abort_reason = (
                            "monitor" if monitor.abortRequested()
                            else "ctx.abort_flag" if ctx.abort_flag.is_requested()
                            else "progress.iscanceled"
                        )
                        log("Artwork", f"Download cancelled by user ({abort_reason})")
                        queue.stop(wait=False)
                        break

                    current_time = time.time()
                    if current_time - last_update_time >= 0.5:
                        stats = queue.get_stats()
                        total = stats.get('total_queued', 0)
                        completed = stats.get('completed', 0)
                        activity = stats.get('activity', 0)
                        downloaded = stats.get('downloaded', 0)
                        skipped = stats.get('skipped', 0)
                        failed = stats.get('failed', 0)

                        if completed > last_completed or activity > last_activity:
                            last_completed = completed
                            last_activity = activity
                            last_progress_time = current_time
                        elif current_time - last_progress_time > STALL_TIMEOUT_SECONDS:
                            stalled = True
                            log("Artwork",
                                f"Download stalled - no progress for "
                                f"{STALL_TIMEOUT_SECONDS}s at "
                                f"{completed}/{total}, forcing exit", xbmc.LOGWARNING)
                            queue.stop(wait=False)
                            break

                        if total > 0:
                            percent = 25 + int((completed / total) * 75)
                        else:
                            percent = 100

                        bytes_downloaded = stats.get('bytes_downloaded', 0)
                        mb = bytes_downloaded / (1024 * 1024) if bytes_downloaded > 0 else 0

                        if use_background:
                            message = f"Downloaded {downloaded} of {total} ({mb:.2f} MB)"
                            progress.update(percent, message=message)
                        else:
                            message = (
                                f"Progress: {completed} / {total}[CR]"
                                f"Downloaded: {downloaded} | Skipped: {skipped} | "
                                f"Failed: {failed}[CR]"
                                f"Size: {mb:.2f} MB"
                            )
                            progress.update(percent, message)
                        last_update_time = current_time

                    monitor.waitForAbort(0.2)

                final_stats = queue.get_stats()

                # stop() raises the abort flag itself, so a stall would otherwise read as a cancel.
                cancelled = not stalled and (
                    monitor.abortRequested() or
                    ctx.abort_flag.is_requested() or
                    (isinstance(progress, xbmcgui.DialogProgress) and progress.iscanceled())
                )

                progress.close()

                log("Artwork", f"Download finished: downloaded={final_stats.get('downloaded', 0)} "
                    f"skipped={final_stats.get('skipped', 0)} "
                    f"failed={final_stats.get('failed', 0)} "
                    f"of {len(jobs)} jobs (cancelled={cancelled}, stalled={stalled}) "
                    f"errors={final_stats.get('error_categories', {})}")

                db.save_operation_stats('artwork_download', {
                    'total_jobs': len(jobs),
                    'total_items': len(items),
                    'downloaded': final_stats.get('downloaded', 0),
                    'skipped': final_stats.get('skipped', 0),
                    'failed': final_stats.get('failed', 0),
                    'bytes_downloaded': final_stats.get('bytes_downloaded', 0),
                    'cancelled': cancelled,
                    'stalled': stalled,
                    'mismatch_counts': mismatch_counts,
                    'folder_counts': final_stats.get('folder_counts', {}),
                    'error_categories': final_stats.get('error_categories', {})
                }, scope=scope)

                _show_download_report(
                    final_stats, len(jobs), scope=scope, use_background=use_background,
                    mismatch_counts=mismatch_counts, stalled=stalled)

            finally:
                queue.stop(wait=False)

    except Exception as e:
        if progress:
            try:
                progress.close()
            except Exception:
                pass
        import traceback
        log("Download",
            f"Download artwork failed: {str(e)}\n{traceback.format_exc()}",
            xbmc.LOGERROR)


def format_folder_section(folder_stats: Optional[Dict[str, int]]) -> List[str]:
    """Format the per-folder download breakdown. Returns empty list when no folder data."""
    if not folder_stats:
        return []
    lines = ["", "[B]Downloaded Files by Folder[/B]", ""]
    for folder_path, count in sorted(folder_stats.items(), key=lambda x: x[0]):
        lines.append(f"{count} files - {folder_path}")
    return lines


_MISMATCH_LABELS: List[Tuple[str, str, str]] = [
    ('movie_folder_to_basename',
     "{} movie artwork files saved as 'poster.jpg' in movie folder",
     "  Setting 'Use Movie Filename Prefix' is ON (expects 'MovieTitle-poster.jpg')"),
    ('movie_basename_to_folder',
     "{} movie artwork files saved as 'MovieTitle-poster.jpg'",
     "  Setting 'Use Movie Filename Prefix' is OFF (expects 'poster.jpg')"),
    ('mvid_folder_to_basename',
     "{} music video artwork files saved as 'poster.jpg' in video folder",
     "  Setting 'Use Music Video Filename Prefix' is ON (expects 'VideoTitle-poster.jpg')"),
    ('mvid_basename_to_folder',
     "{} music video artwork files saved as 'VideoTitle-poster.jpg'",
     "  Setting 'Use Music Video Filename Prefix' is OFF (expects 'poster.jpg')"),
]


def format_failure_section(error_categories: Optional[Dict[str, int]]) -> List[str]:
    """Format the per-category failure breakdown. Returns empty list when no failures."""
    if not error_categories or sum(error_categories.values()) <= 0:
        return []
    lines = ["", "[B]Failure Breakdown[/B]", ""]
    for category, count in sorted(error_categories.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            label = ERROR_CATEGORY_LABELS.get(category, category)
            lines.append(f"{count} - {label}")
    return lines


def format_mismatch_section(mismatch_counts: Optional[Dict[str, int]]) -> List[str]:
    """Format the file-handling mismatch breakdown. Returns empty list when no mismatches."""
    if not mismatch_counts or sum(mismatch_counts.values()) <= 0:
        return []
    lines = ["", "[B]File Handling Mismatches Detected[/B]", ""]
    for key, fmt, hint in _MISMATCH_LABELS:
        count = mismatch_counts.get(key, 0)
        if count > 0:
            lines.append(fmt.format(count))
            lines.append(hint)
    return lines


def _show_download_report(stats: Dict, total_jobs: int, scope: str = 'all',
                          use_background: bool = False,
                          mismatch_counts: Optional[Dict[str, int]] = None,
                          stalled: bool = False) -> None:
    """Show the post-run report: toast in background mode, textviewer in foreground."""
    from lib.infrastructure.dialogs import show_notification

    downloaded = stats.get('downloaded', 0)
    skipped = stats.get('skipped', 0)
    failed = stats.get('failed', 0)
    bytes_downloaded = stats.get('bytes_downloaded', 0)

    mb = bytes_downloaded / (1024 * 1024) if bytes_downloaded > 0 else 0

    if use_background:
        show_notification(
            ADDON.getLocalizedString(32121),
            ADDON.getLocalizedString(32099).format(downloaded, f"{mb:.2f}"),
            xbmcgui.NOTIFICATION_INFO,
            5000
        )
        return

    lines = [
        f"[B]{ADDON.getLocalizedString(32121)}[/B]",
        "",
        f"Total artwork URLs: {total_jobs}",
        f"Downloaded: {downloaded}",
        f"Skipped (already exists): {skipped}",
        f"Failed: {failed}",
        "",
        f"Total size: {mb:.2f} MB",
    ]
    if stalled:
        lines.extend([
            "",
            "[B]Stopped early: downloads stalled[/B]",
            (
                f"No progress for over {STALL_TIMEOUT_SECONDS}s. "
                f"Run the download again to finish the rest."
            ),
        ])
    lines.extend(format_folder_section(stats.get('folder_counts', {})))
    lines.extend(format_failure_section(stats.get('error_categories', {})))
    lines.extend(format_mismatch_section(mismatch_counts))

    text = "\n".join(lines)
    log_path = write_download_log(text, scope, stats)
    if log_path:
        lines.extend(["", "", f"Full report saved to: {log_path}"])
        text = "\n".join(lines)

    show_textviewer(ADDON.getLocalizedString(32520), text)
