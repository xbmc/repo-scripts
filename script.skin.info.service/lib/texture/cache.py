"""User-facing artwork orchestrators: precache, precache+download, and orphaned-texture cleanup."""
from __future__ import annotations

import time
from typing import Optional, List, Dict, Any

import xbmc
import xbmcgui

from lib.kodi.client import get_library_items, log, ADDON, decode_image_url, LibraryScanAborted
from lib.kodi.settings import KodiSettings
from lib.infrastructure.dialogs import ProgressDialog
from lib.infrastructure.paths import (
    PathBuilder,
    get_album_folders,
    get_tvshow_paths,
    resolve_media_file,
)
from lib.infrastructure.workers import STALL_TIMEOUT_SECONDS
from lib.texture.utilities import should_precache_url, is_library_artwork_url
from lib.texture.queues import TextureCache, TextureCacheDownload
from lib.texture.library import (
    DEFAULT_TEXTURE_MEDIA_TYPES,
    get_all_library_artwork_urls,
    get_library_scan_data,
    load_cached_urls_once,
    clear_cached_urls_cache,
    remove_texture,
)

_PRECACHE_PROPERTIES = {
    'movie': ['art', 'title', 'file'],
    'tvshow': ['art', 'title', 'file', 'season', 'episode'],
    'episode': ['art', 'title', 'file', 'season', 'episode', 'tvshowid'],
    'musicvideo': ['art', 'title', 'file'],
    'set': ['art', 'title'],
    'season': ['art', 'title', 'season', 'episode', 'tvshowid'],
    'artist': ['art', 'musicbrainzartistid'],
    'album': ['art', 'title'],
}


def precache_library_artwork(media_types: Optional[List[str]] = None,
                             progress_dialog: Optional[ProgressDialog] = None,
                             task_context=None) -> Dict[str, Any]:
    """Pre-cache library artwork URLs not already in the texture cache.

    Returns stats: `total_urls, already_cached, needed_caching, successfully_cached, failed`.
    """
    stats = {
        'total_urls': 0,
        'already_cached': 0,
        'needed_caching': 0,
        'successfully_cached': 0,
        'failed': 0,
        'cancelled': False
    }

    monitor = xbmc.Monitor()

    try:
        if media_types is None:
            media_types = list(DEFAULT_TEXTURE_MEDIA_TYPES)

        if progress_dialog:
            progress_dialog.update(0, "Scanning library for artwork URLs...")

        def progress_callback(type_index: int, type_count: int, media_type: str,
                              done: int, total: int):
            if progress_dialog:
                frac = (type_index - 1 + (done / total if total else 1)) / type_count
                progress_dialog.update(int(frac * 10),
                                       f"Scanning {media_type}: {done:,} / {total:,}")

        library_urls = get_all_library_artwork_urls(
            media_types, progress_callback=progress_callback
        )

        log("Artwork",f"Pre-cache: found {len(library_urls)} total library artwork URLs")

        if progress_dialog:
            progress_dialog.update(10, "Loading texture cache...")

        cached_urls_set = load_cached_urls_once()

        if progress_dialog:
            progress_dialog.update(20, "Identifying uncached artwork...")

        precacheable_urls = []
        urls_to_cache = []

        for url in library_urls:
            if not should_precache_url(url):
                continue

            precacheable_urls.append(url)
            decoded_url = decode_image_url(url)

            if decoded_url not in cached_urls_set:
                urls_to_cache.append(url)

        stats['total_urls'] = len(precacheable_urls)
        stats['already_cached'] = len(precacheable_urls) - len(urls_to_cache)
        stats['needed_caching'] = len(urls_to_cache)

        skipped_count = len(library_urls) - len(precacheable_urls)

        log("Artwork",
            f"Pre-cache: {stats['already_cached']} already cached, "
            f"{stats['needed_caching']} need caching, "
            f"{skipped_count} skipped (system/addon files)"
        )

        if stats['needed_caching'] == 0:
            log("Artwork", "Pre-cache: all URLs already cached, nothing to do")
            return stats

        if progress_dialog:
            progress_dialog.update(25, f"Pre-caching {len(urls_to_cache)} images...")

        cache_queue = TextureCache(
            check_cached=False,
            abort_flag=task_context.abort_flag if task_context else None,
            task_context=task_context
        )
        cache_queue.start()

        try:
            queued = cache_queue.bulk_add_urls(urls_to_cache)
            log("Artwork",f"Pre-cache: queued {queued} URLs for background processing")

            last_update_time = time.time()
            last_percent = -1

            while not cache_queue.queue.empty() or cache_queue.processing_set:
                if (
                    monitor.abortRequested()
                    or (task_context and task_context.abort_flag.is_requested())
                    or (progress_dialog and progress_dialog.is_cancelled())
                ):
                    stats['cancelled'] = True
                    break

                if progress_dialog:
                    progress = cache_queue.get_progress()
                    percent = 25 + int(progress['percent'] * 0.75) if progress['total'] > 0 else 100
                    completed = progress['completed']
                    total = progress['total']
                    remaining = total - completed

                    current_time = time.time()
                    time_since_update = current_time - last_update_time
                    percent_changed = abs(percent - last_percent) >= 1

                    if time_since_update >= 0.5 or percent_changed:
                        if progress_dialog.use_background:
                            progress_dialog.update(
                                percent, f"Cached: {completed}/{total} ({remaining} remaining)"
                            )
                        else:
                            progress_dialog.update(
                                percent,
                                f"Cached: {completed} of {total}[CR]Remaining: {remaining}",
                            )
                        last_update_time = current_time
                        last_percent = percent

                monitor.waitForAbort(0.2)

            queue_stats = cache_queue.get_stats()
            stats['successfully_cached'] = queue_stats['successful']
            stats['failed'] = queue_stats['failed']
            stats['failed_urls'] = [
                r['url'] for r in queue_stats['results']
                if not r.get('success', False) and 'url' in r
            ]

            status = "cancelled" if stats['cancelled'] else "complete"
            log("Artwork",
                f"Pre-cache {status}: {stats['successfully_cached']} cached, "
                f"{stats['failed']} failed"
            )

        finally:
            cache_queue.stop(wait=False)
            clear_cached_urls_cache()

    except Exception as e:
        log("Texture",f"Pre-cache failed: {str(e)}", xbmc.LOGERROR)
        stats['failed'] = stats['needed_caching']
        clear_cached_urls_cache()

    return stats


def precache_and_download_artwork(media_types: Optional[List[str]] = None,
                                  progress_dialog: Optional[ProgressDialog] = None,
                                  task_context=None) -> Dict[str, Any]:
    """Pre-cache + download artwork in one pass via `TextureCacheDownload`.

    Returns stats: `total_items, cached, downloaded, skipped, failed, cancelled, stalled`.
    """
    stats = {
        'total_items': 0,
        'total_urls': 0,
        'cached': 0,
        'cache_failed': 0,
        'downloaded': 0,
        'download_skipped': 0,
        'download_failed': 0,
        'bytes_downloaded': 0,
        'cancelled': False,
        'stalled': False
    }

    if media_types is None:
        media_types = list(DEFAULT_TEXTURE_MEDIA_TYPES)

    monitor = xbmc.Monitor()

    try:
        if progress_dialog:
            progress_dialog.update(5, "Scanning library...")

        def has_artwork(item: Dict[str, Any]) -> bool:
            art = item.get('art', {})
            return bool(art and isinstance(art, dict))

        items: List[Dict[str, Any]] = []
        try:
            tvshow_paths = get_tvshow_paths() if 'season' in media_types else {}

            for media_type in media_types:
                properties = _PRECACHE_PROPERTIES.get(media_type, ['art', 'title'])
                type_items = get_library_items(
                    media_types=[media_type],
                    properties=properties,
                    decode_urls=True,
                    filter_func=has_artwork
                )
                for item in type_items:
                    if 'title' not in item:
                        item['title'] = "Unknown"
                items.extend(type_items)

            album_ids = [item['dbid'] for item in items
                         if item.get('media_type') == 'album' and item.get('dbid')]
            album_folders = get_album_folders(album_ids)

            for item in items:
                item['file'] = resolve_media_file(
                    item, album_folders=album_folders, tvshow_paths=tvshow_paths
                )

        except Exception as e:
            log("Texture",
                f"SkinInfo: Error querying library for precache+download: {str(e)}",
                xbmc.LOGERROR
            )
            items = []

        stats['total_items'] = len(items)

        if not items:
            log("Artwork", "No items found for precache+download")
            return stats

        if progress_dialog:
            progress_dialog.update(15, f"Processing {len(items)} items...")

        existing_file_mode_setting = KodiSettings.existing_file_mode()
        existing_file_mode_int = (
            int(existing_file_mode_setting) if existing_file_mode_setting else 0
        )
        existing_file_mode = ['skip', 'overwrite', 'use_existing'][existing_file_mode_int]

        PathBuilder.prepare_named_item_folders(media_types)

        queue = TextureCacheDownload(
            existing_file_mode=existing_file_mode,
            abort_flag=task_context.abort_flag if task_context else None,
            task_context=task_context
        )
        queue.start()

        try:
            queued = 0
            for item in items:
                for art_type, url in item['art'].items():
                    if not url or not should_precache_url(url):
                        continue

                    mbid = None
                    if item['media_type'] == 'artist':
                        mbid = item.get('musicbrainzartistid', '')
                        if isinstance(mbid, list):
                            mbid = mbid[0] if mbid else ''

                    queue.add_cache_and_download(
                        url=url,
                        media_type=item['media_type'],
                        media_file=item['file'],
                        artwork_type=art_type,
                        title=item['title'],
                        season=item.get('season'),
                        episode=item.get('episode'),
                        mbid=mbid
                    )
                    queued += 1

            stats['total_urls'] = queued
            log("Artwork",f"Pre-cache+download: queued {queued} URLs for processing")

            last_update_time = time.time()
            last_percent = -1
            last_completed = -1
            last_activity = -1
            last_progress_time = time.time()

            while not queue.queue.empty() or queue.processing_set:
                if (
                    monitor.abortRequested()
                    or (task_context and task_context.abort_flag.is_requested())
                    or (progress_dialog and progress_dialog.is_cancelled())
                ):
                    stats['cancelled'] = True
                    break

                current_time = time.time()
                queue_stats = queue.get_stats()
                completed = queue_stats['completed']
                total = queue_stats['total_queued']
                activity = queue_stats['activity']

                if completed > last_completed or activity > last_activity:
                    last_completed = completed
                    last_activity = activity
                    last_progress_time = current_time
                elif current_time - last_progress_time > STALL_TIMEOUT_SECONDS:
                    stats['stalled'] = True
                    log("Artwork",
                        f"Pre-cache+download stalled - no progress for "
                        f"{STALL_TIMEOUT_SECONDS}s at {completed}/{total}, forcing exit",
                        xbmc.LOGWARNING)
                    break

                if progress_dialog:
                    percent = 25 + int((completed / total) * 75) if total > 0 else 100

                    time_since_update = current_time - last_update_time
                    percent_changed = abs(percent - last_percent) >= 1

                    if time_since_update >= 0.5 or percent_changed:
                        remaining = total - completed
                        cached = queue_stats['cached']
                        downloaded = queue_stats['downloaded']

                        if progress_dialog.use_background:
                            progress_dialog.update(
                                percent,
                                f"Processed: {completed}/{total} ({remaining} remaining)",
                            )
                        else:
                            progress_dialog.update(
                                percent,
                                f"Processed: {completed} of {total}[CR]"
                                f"Remaining: {remaining}[CR]"
                                f"Cached: {cached} | Downloaded: {downloaded}",
                            )
                        last_update_time = current_time
                        last_percent = percent

                monitor.waitForAbort(0.2)

            queue_stats = queue.get_stats()
            stats['cached'] = queue_stats['cached']
            stats['cache_failed'] = queue_stats['cache_failed']
            stats['downloaded'] = queue_stats['downloaded']
            stats['download_skipped'] = queue_stats['download_skipped']
            stats['download_failed'] = queue_stats['download_failed']
            stats['bytes_downloaded'] = queue_stats['bytes_downloaded']

            if stats['stalled']:
                status = "stalled"
            else:
                status = "cancelled" if stats['cancelled'] else "complete"
            log("Artwork",
                f"Pre-cache+download {status}: {stats['cached']} cached, "
                f"{stats['downloaded']} downloaded"
            )

        finally:
            queue.stop(wait=False)
            clear_cached_urls_cache()

    except Exception as e:
        log("Texture",f"Pre-cache+download failed: {str(e)}", xbmc.LOGERROR)
        clear_cached_urls_cache()

    return stats


def cleanup_orphaned_textures(media_types: Optional[List[str]] = None,
                              progress_dialog: Optional[ProgressDialog] = None,
                              task_context=None) -> Dict[str, int]:
    """Remove cached textures whose URL no longer appears in the library.

    Returns stats: `total_cached, total_library, orphaned_found, removed, failed, cancelled`.
    """
    stats = {
        'total_cached': 0,
        'total_library': 0,
        'orphaned_found': 0,
        'removed': 0,
        'failed': 0,
        'cancelled': False
    }

    monitor = xbmc.Monitor()

    try:
        log("Artwork",f"Starting orphaned texture cleanup for media types: {media_types}")

        def aborted() -> bool:
            return bool(
                monitor.abortRequested()
                or (task_context and task_context.abort_flag.is_requested())
                or (progress_dialog is not None and progress_dialog.is_cancelled())
            )

        scan_data = get_library_scan_data(
            media_types, progress_dialog, include_cast=True, abort_check=aborted
        )

        library_urls = scan_data['library_urls']
        cached_textures = scan_data['cached_textures']

        stats['total_library'] = scan_data['stats']['total_library']
        stats['total_cached'] = scan_data['stats']['total_cached']

        if progress_dialog:
            progress_dialog.update(50, "Finding orphaned textures...")

        orphaned = []
        for texture in cached_textures:
            url = texture.get('url', '')
            decoded_cache_url = decode_image_url(url)
            if is_library_artwork_url(url) and decoded_cache_url not in library_urls:
                orphaned.append(texture)

        stats['orphaned_found'] = len(orphaned)

        log("Artwork",f"Found {stats['orphaned_found']} orphaned textures")

        if stats['orphaned_found'] > 0:
            dialog = xbmcgui.Dialog()

            while True:
                result = dialog.yesnocustom(
                    "Confirm Cleanup",
                    f"Found {stats['orphaned_found']} orphaned textures to remove.[CR][CR]"
                    f"Continue with removal?",
                    customlabel="View Report"
                )

                if result == 2:
                    report_lines = [
                        "ORPHANED TEXTURES REPORT",
                        "",
                        f"Total orphaned: {stats['orphaned_found']}",
                        f"Total cached: {stats['total_cached']}",
                        f"Total library: {stats['total_library']}",
                        "",
                        "URLs to be removed:",
                        ""
                    ]
                    for i, texture in enumerate(orphaned, 1):
                        url = texture.get('url', '')
                        report_lines.append(f"{i}. {url}")

                    dialog.textviewer(ADDON.getLocalizedString(32183), "\n".join(report_lines))
                elif result == 1:
                    break
                else:
                    return stats

        if progress_dialog:
            progress_dialog.update(60, f"Removing {stats['orphaned_found']} orphaned textures...")

        for idx, texture in enumerate(orphaned):
            if (
                monitor.abortRequested()
                or (task_context and task_context.abort_flag.is_requested())
            ):
                stats['cancelled'] = True
                break

            texture_id = texture.get('textureid')
            url = texture.get('url', '')

            if texture_id:
                success = remove_texture(texture_id)
                if success:
                    stats['removed'] += 1
                else:
                    stats['failed'] += 1

            if progress_dialog:
                percent = 60 + int(((idx + 1) / len(orphaned)) * 40) if orphaned else 100
                progress_dialog.update(percent, f"Removed {idx + 1} / {stats['orphaned_found']}")

        status = "cancelled" if stats['cancelled'] else "complete"
        log("Artwork",f"Cleanup {status}: {stats['removed']} removed, {stats['failed']} failed")

    except LibraryScanAborted:
        stats['cancelled'] = True
        log("Artwork", "Orphaned cleanup cancelled during library scan")

    except Exception as e:
        log("Texture",f"Orphaned cleanup failed: {str(e)}", xbmc.LOGERROR)

    return stats


