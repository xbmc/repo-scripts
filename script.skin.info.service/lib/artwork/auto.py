"""Auto-apply missing artwork from queue.

Processes queue items and automatically applies artwork based on language policies.
"""
from __future__ import annotations

import xbmc
from lib.infrastructure.dialogs import show_ok, show_textviewer
import xbmcgui
from typing import Optional, List, Sequence

from lib.data import database as db
from lib.data.database.queue import QueueEntry
from lib.kodi.client import request, get_item_details, KODI_SET_DETAILS_METHODS
from lib.kodi.settings import KodiSettings
from lib.kodi.utilities import get_preferred_language_code, normalize_language_tag
from lib.artwork.utilities import compare_art_quality, sort_artwork_by_popularity
from lib.data.api.tmdb import ApiTmdb
from lib.data.api.fanarttv import ApiFanarttv
from lib.artwork.config import AUTO_LANG_REQUIRED_TYPES, AUTO_NO_LANGUAGE_TYPES
from lib.data.api.artwork import ApiArtworkFetcher
from lib.infrastructure.dialogs import ProgressDialog
from lib.kodi.client import log, ADDON

DEFAULT_BATCH_SIZE = 100


class ArtworkAuto:
    """Process queue and apply artwork automatically."""

    def __init__(
        self,
        use_background: bool = False,
        mode: str = 'full',
        source_fetcher: Optional[ApiArtworkFetcher] = None,
        enable_download: bool = False,
        abort_flag=None,
        task_context=None,
    ):
        self.progress = ProgressDialog(
            use_background=use_background, heading=ADDON.getLocalizedString(32072))
        self.progress.enable_throttling()
        self.cancelled = False
        self.total_items = 0  # Track original total
        self.mode = mode if mode in ('full', 'missing_only') else 'full'
        self.media_filter: Optional[Sequence[str]] = None
        self.preferred_language = get_preferred_language_code()
        self.enable_download = enable_download
        self._abort_flag = abort_flag
        self._task_context = task_context
        self.stats = {
            'processed': 0,
            'auto_applied': 0,
            'skipped': 0,
            'errors': 0
        }
        self.applied_items = []
        self.skipped_items = []
        # One downloader for the whole run: a per-item instance resets the provider and
        # file-write error counters, so the blocking they exist for could never engage.
        self._downloader = None
        self.savewith_basefilename = ADDON.getSettingBool('download.savewith_basefilename')

        if source_fetcher:
            self.source_fetcher = source_fetcher
        else:
            from lib.data.api.artwork import create_default_fetcher
            self.source_fetcher = create_default_fetcher()

    def _is_cancelled(self) -> bool:
        """True if the progress dialog was cancelled or the owning task aborted."""
        if self._abort_flag is not None and self._abort_flag.is_requested():
            return True
        return self.progress.is_cancelled()

    def _filter_candidates_for_mode(self, art_type: str, candidates: List[dict]) -> List[dict]:
        """Filter candidates by preferred language when running in missing-only mode."""
        if self.mode != 'missing_only' or not candidates:
            return candidates

        normalized_candidates = []

        if art_type in AUTO_NO_LANGUAGE_TYPES:
            normalized_candidates = [
                art for art in candidates
                if not normalize_language_tag(art.get('language'))
            ]
        elif art_type in AUTO_LANG_REQUIRED_TYPES:
            target_lang = self.preferred_language
            if target_lang:
                normalized_candidates = [
                    art for art in candidates
                    if normalize_language_tag(art.get('language')) == target_lang
                ]
            else:
                normalized_candidates = candidates
        else:
            normalized_candidates = candidates

        return normalized_candidates

    def _select_best_candidate(self, art_type: str, candidates: List[dict]) -> Optional[dict]:
        """Choose best candidate using quality/popularity sort."""
        if not candidates:
            return None

        sorted_candidates = sort_artwork_by_popularity(candidates, art_type)
        if not sorted_candidates:
            return None

        return sorted_candidates[0]

    def process_queue(self, *, media_types: Optional[Sequence[str]] = None) -> None:
        """Process pending queue items."""
        self.media_filter = tuple(media_types) if media_types else None
        batch_size = DEFAULT_BATCH_SIZE

        initial_stats = db.get_queue_stats(media_types=self.media_filter)
        self.total_items = initial_stats.get('pending', 0)

        scope_hint = f", scope={','.join(self.media_filter)}" if self.media_filter else ""
        log("Artwork",
            f"Processing queue: {self.total_items} pending items, mode={self.mode}{scope_hint}")

        self.progress.create(ADDON.getLocalizedString(32278))

        try:
            while True:
                batch = db.get_next_batch(batch_size, media_types=self.media_filter)
                if not batch:
                    break

                for item in batch:
                    if self._is_cancelled():
                        self.cancelled = True
                        break

                    self._process_item(item)
                    self._update_progress()
                    if self._task_context is not None:
                        self._task_context.mark_progress()

                if self.cancelled:
                    break

            self._update_progress(force=True)
        finally:
            self.progress.close()
            if self._downloader is not None:
                self._downloader.close()
                self._downloader = None

        self._show_summary()

        if self.applied_items:
            self._reconcile_slideshow_pool()

    def _reconcile_slideshow_pool(self) -> None:
        """One batched slideshow-pool reconcile after a bulk run (per-item refresh was deferred)."""
        pool_types = ('movie', 'tvshow', 'artist')
        scope = tuple(t for t in pool_types
                      if self.media_filter is None or t in self.media_filter)
        if not scope:
            return
        try:
            from lib.service.slideshow import reconcile_pool
            reconcile_pool(scope)
        except Exception as e:
            log("Artwork", f"Slideshow pool reconcile failed: {str(e)}", xbmc.LOGWARNING)

    def _process_item(self, queue_item: QueueEntry) -> None:
        """Process single queue item."""
        try:
            media_type = queue_item.media_type
            dbid = queue_item.dbid
            title = queue_item.title

            art_items = db.get_art_items_for_queue(queue_item.id)

            all_available_art = self.source_fetcher.fetch_all(media_type, dbid)

            applied_any = False
            no_art_available = False
            blocked_by_policy = False

            for art_item in art_items:
                art_type = art_item.art_type
                review_mode = art_item.review_mode or db.ARTITEM_REVIEW_MISSING

                # auto-process must never overwrite existing artwork
                if review_mode != db.ARTITEM_REVIEW_MISSING:
                    continue

                available = all_available_art.get(art_type, [])

                if not available:
                    no_art_available = True
                    continue

                filtered_candidates = self._filter_candidates_for_mode(art_type, available)
                if self.mode == 'missing_only' and not filtered_candidates:
                    blocked_by_policy = True
                    continue

                if self.mode == 'missing_only':
                    best = self._select_best_candidate(art_type, filtered_candidates)
                else:
                    best = compare_art_quality(filtered_candidates)

                if best:
                    self._apply_art(media_type, dbid, {art_type: best['url']}, title=title,
                                    artwork_type=art_type, defer_pool_refresh=True)
                    db.update_art_item(art_item.id, best['url'], auto_applied=True)
                    applied_any = True
                    self.stats['auto_applied'] += 1
                    self.applied_items.append((title, art_type, best['url']))

            if applied_any:
                db.update_queue_status(queue_item.id, 'completed')
            else:
                db.update_queue_status(queue_item.id, 'skipped')
                if no_art_available:
                    self.skipped_items.append((title, ADDON.getLocalizedString(32009)))
                elif blocked_by_policy:
                    self.skipped_items.append((title, ADDON.getLocalizedString(32010)))
                else:
                    self.skipped_items.append((title, ADDON.getLocalizedString(32011)))

            self.stats['processed'] += 1
            if not applied_any:
                self.stats['skipped'] += 1

        except Exception as e:
            log("Artwork", f"Error processing item: {str(e)}", xbmc.LOGERROR)
            self.stats['errors'] += 1
            db.update_queue_status(queue_item.id, 'error')

    def _apply_art(self, media_type: str, dbid: int, art_dict: dict, title: str = "",
                   artwork_type: str = "", defer_pool_refresh: bool = False) -> bool:
        """Apply artwork to library item and optionally download to filesystem.

        `defer_pool_refresh` skips the per-item slideshow-pool update (the bulk auto-apply path
        does one batched reconcile at the end instead).
        """
        if media_type not in KODI_SET_DETAILS_METHODS:
            return False

        method, id_key = KODI_SET_DETAILS_METHODS[media_type]

        try:
            resp = request(method, {
                id_key: dbid,
                'art': art_dict
            })

            if resp is None:
                return False

            if self.enable_download and artwork_type and art_dict.get(artwork_type):
                url = art_dict[artwork_type]
                if url.startswith('http'):
                    self._download_artwork(media_type, dbid, artwork_type, url, title)

            if (not defer_pool_refresh and 'fanart' in art_dict
                    and media_type in ('movie', 'tvshow', 'artist')):
                from lib.service.slideshow import refresh_pool_item
                refresh_pool_item(media_type, dbid)

            return True

        except Exception as e:
            log("Artwork", f"Error applying art: {str(e)}", xbmc.LOGERROR)
            return False

    def _download_artwork(self, media_type: str, dbid: int, artwork_type: str, url: str,
                          title: str) -> None:
        """Download artwork to filesystem after applying to library."""
        try:
            from lib.kodi.client import KODI_GET_DETAILS_METHODS
            from lib.download.artwork import DownloadArtwork
            from lib.infrastructure.paths import PathBuilder, use_basename_for

            if media_type not in KODI_GET_DETAILS_METHODS:
                return

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

            if not media_file and media_type not in ('season', 'tvshow', 'set', 'artist', 'album'):
                log("Artwork", f"No file path for {media_type} '{title}', skipping download")
                return

            path_builder = PathBuilder()
            use_basename = use_basename_for(media_type, self.savewith_basefilename)
            local_path = path_builder.build_path(
                media_type=media_type,
                media_file=media_file,
                artwork_type=artwork_type,
                season_number=season,
                use_basename=use_basename
            )

            # Art saved under the opposite naming convention still counts as present,
            # otherwise flipping the setting re-downloads beside the old files.
            alternate_path = None
            if media_type in ('movie', 'musicvideo'):
                alternate_path = path_builder.build_path(
                    media_type=media_type,
                    media_file=media_file,
                    artwork_type=artwork_type,
                    season_number=season,
                    use_basename=not use_basename
                )

            if not local_path:
                log("Artwork",
                    f"Could not build download path for {media_type} '{title}' {artwork_type}")
                return

            existing_file_mode_setting = KodiSettings.existing_file_mode()
            existing_file_mode_int = (
                int(existing_file_mode_setting) if existing_file_mode_setting else 0)
            existing_file_mode = ['skip', 'overwrite'][existing_file_mode_int]

            if self._downloader is None:
                self._downloader = DownloadArtwork()

            success, error, bytes_downloaded, _ = self._downloader.download_artwork(
                url=url,
                local_path=local_path,
                existing_file_mode=existing_file_mode,
                alternate_path=alternate_path
            )

            if success:
                log("Artwork",
                    f"Downloaded {artwork_type} for '{title}': {local_path} "
                    f"({bytes_downloaded} bytes)")
            elif error:
                log("Artwork", f"Failed to download {artwork_type} for '{title}': {error}")

        except Exception as e:
            log("Artwork", f"Error downloading artwork: {str(e)}", xbmc.LOGWARNING)

    def _update_progress(self, force: bool = False) -> None:
        """Update progress dialog (throttled for performance)."""
        if self.total_items > 0:
            percent = int((self.stats['processed'] / self.total_items) * 100)
        else:
            percent = 0

        message = (
            f"Processed: {self.stats['processed']}/{self.total_items}[CR]"
            f"Auto-applied: {self.stats['auto_applied']}[CR]"
            f"Skipped: {self.stats['skipped']}")

        self.progress.update(percent, message, force=force)

    def _show_summary(self) -> None:
        """Show processing summary."""
        message = (
            f"{ADDON.getLocalizedString(32032 if self.cancelled else 32279)}[CR][CR]"
            f"{ADDON.getLocalizedString(32284).format(self.stats['processed'])}[CR]"
            f"{ADDON.getLocalizedString(32285).format(self.stats['auto_applied'])}[CR]"
            f"{ADDON.getLocalizedString(32286).format(self.stats['skipped'])}"
        )

        if self.stats['errors'] > 0:
            message += f"[CR]{ADDON.getLocalizedString(32287).format(self.stats['errors'])}"

        message += f"[CR][CR][I]{ApiTmdb.get_attribution()}[/I]"
        message += f"[CR][I]{ApiFanarttv.get_attribution()}[/I]"

        if self.stats['processed'] > 0 and (self.applied_items or self.skipped_items):
            dialog = xbmcgui.Dialog()
            choice = dialog.yesno(
                ADDON.getLocalizedString(32033 if self.cancelled else 32281),
                message,
                yeslabel=ADDON.getLocalizedString(32282),
                nolabel=xbmc.getLocalizedString(15067)
            )

            if choice:
                self._show_detailed_report()
        else:
            show_ok(ADDON.getLocalizedString(32280), message)

    def _show_detailed_report(self) -> None:
        """Show detailed report of applied and skipped items."""
        dialog = xbmcgui.Dialog()

        options = []

        if self.applied_items:
            options.append(f"[B]Auto-Applied ({len(self.applied_items)} items)[/B]")

        if self.skipped_items:
            options.append(f"[B]Skipped ({len(self.skipped_items)} items)[/B]")

        if not options:
            dialog.ok(ADDON.getLocalizedString(32190), ADDON.getLocalizedString(32171))
            return

        selected = dialog.select(ADDON.getLocalizedString(32191), options)

        if selected == -1:
            return

        if selected == 0 and self.applied_items:
            self._show_applied_report()
        elif ((selected == 1 and self.skipped_items)
              or (selected == 0 and not self.applied_items and self.skipped_items)):
            self._show_skipped_report()

    def _show_applied_report(self) -> None:
        """Show report of auto-applied items."""
        lines = ["[B]Auto-Applied Artwork:[/B]", ""]

        current_title = None
        for title, art_type, _ in self.applied_items:
            if title != current_title:
                if current_title:
                    lines.append("")  # Blank line between items
                lines.append(f"[B]{title}[/B]")
                current_title = title
            lines.append(f"  • {art_type}")

        text = "[CR]".join(lines)
        show_textviewer(ADDON.getLocalizedString(32550), text)

    def _show_skipped_report(self) -> None:
        """Show report of skipped items."""
        lines = ["[B]Skipped Items:[/B]", ""]

        for title, reason in self.skipped_items:
            lines.append(f"• {title}")
            lines.append(f"  Reason: {reason}")
            lines.append("")

        text = "[CR]".join(lines)
        show_textviewer(ADDON.getLocalizedString(32551), text)
