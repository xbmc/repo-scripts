"""Auto-apply missing artwork from the queue, following the language policies."""
from __future__ import annotations

import xbmc
from lib.infrastructure.dialogs import show_ok, show_textviewer
import xbmcgui
from typing import Optional, List, Sequence, Final

from lib.data.database import queue as db_queue
from lib.data.database.queue import QueueEntry
from lib.kodi.client import request, KODI_SET_DETAILS_METHODS
from lib.kodi.settings import KodiSettings
from lib.kodi.utilities import get_preferred_language_code, normalize_language_tag
from lib.artwork.utilities import compare_art_quality, sort_artwork_by_popularity
from lib.data.api.tmdb import ApiTmdb
from lib.data.api.fanarttv import ApiFanarttv
from lib.artwork.config import AUTO_LANG_REQUIRED_TYPES, AUTO_NO_LANGUAGE_TYPES
from lib.download.artwork import DownloadArtwork, download_item_art
from lib.data.api.artwork import ApiArtworkFetcher
from lib.infrastructure.dialogs import ProgressDialog
from lib.kodi.client import log, ADDON

DEFAULT_BATCH_SIZE: Final = 100


class ArtworkAuto:
    """Queue processor that applies art and records what it applied and skipped."""

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
        self.total_items = 0
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
        # one downloader per run; a per-item instance resets the error counters
        self._downloader = None

        if source_fetcher:
            self.source_fetcher = source_fetcher
        else:
            from lib.data.api.artwork import create_default_fetcher
            self.source_fetcher = create_default_fetcher()

    def close(self) -> None:
        """Release the run's download connections."""
        if self._downloader is not None:
            self._downloader.close()
            self._downloader = None

    def _cancel_requested(self) -> bool:
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
        """Take the top candidate once sorted by language, popularity and resolution."""
        if not candidates:
            return None

        sorted_candidates = sort_artwork_by_popularity(candidates, art_type)
        if not sorted_candidates:
            return None

        return sorted_candidates[0]

    def process_queue(self, *, media_types: Optional[Sequence[str]] = None) -> None:
        """Process the pending queue in batches until it empties or the user cancels."""
        self.media_filter = tuple(media_types) if media_types else None
        batch_size = DEFAULT_BATCH_SIZE

        initial_stats = db_queue.get_queue_stats(media_types=self.media_filter)
        self.total_items = initial_stats.get('pending', 0)

        scope_hint = f", scope={','.join(self.media_filter)}" if self.media_filter else ""
        log("Artwork",
            f"Processing queue: {self.total_items} pending items, mode={self.mode}{scope_hint}")

        self.progress.create(ADDON.getLocalizedString(32278))

        try:
            while True:
                batch = db_queue.get_next_batch(batch_size, media_types=self.media_filter)
                if not batch:
                    break

                for item in batch:
                    if self._cancel_requested():
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
            self.close()

        self._show_summary()

        if self.applied_items:
            self._reconcile_slideshow_pool()

    def _reconcile_slideshow_pool(self) -> None:
        """Reconcile the slideshow pool once after a bulk run, in place of a refresh per item."""
        from lib.data.slideshow import POOL_MEDIA_TYPES
        scope = tuple(t for t in POOL_MEDIA_TYPES
                      if self.media_filter is None or t in self.media_filter)
        if not scope:
            return
        try:
            from lib.data.slideshow import reconcile_pool
            reconcile_pool(scope)
        except Exception as e:
            log("Artwork", f"Slideshow pool reconcile failed: {str(e)}", xbmc.LOGWARNING)

    def _process_item(self, queue_item: QueueEntry) -> None:
        """Process one item's art types, marking it completed or skipped with a reason."""
        try:
            media_type = queue_item.media_type
            dbid = queue_item.dbid
            title = queue_item.title

            art_items = db_queue.get_art_items_for_queue(media_type, dbid)

            all_available_art = self.source_fetcher.fetch_all(media_type, dbid, bulk=True)

            applied_any = False
            apply_failed = False
            no_art_available = False
            blocked_by_policy = False

            for art_item in art_items:
                art_type = art_item.art_type
                review_mode = art_item.review_mode or db_queue.ARTITEM_REVIEW_MISSING

                # auto-process must never overwrite existing artwork
                if review_mode != db_queue.ARTITEM_REVIEW_MISSING:
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
                    if not self._apply_art(media_type, dbid, {art_type: best['url']}, title=title,
                                           defer_pool_refresh=True):
                        apply_failed = True
                        continue
                    db_queue.update_art_item(media_type, dbid, art_type, best['url'])
                    applied_any = True
                    self.stats['auto_applied'] += 1
                    self.applied_items.append((title, art_type, best['url']))

            if applied_any:
                db_queue.update_queue_status(media_type, dbid, 'completed')
            elif apply_failed:
                self.stats['errors'] += 1
                db_queue.update_queue_status(media_type, dbid, 'error')
                return
            else:
                db_queue.update_queue_status(media_type, dbid, 'skipped')
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
            db_queue.update_queue_status(queue_item.media_type, queue_item.dbid, 'error')

    def _apply_art(self, media_type: str, dbid: int, art_dict: dict, title: str = "",
                   defer_pool_refresh: bool = False) -> bool:
        """Apply art to the item, with optional download and slideshow pool deferral."""
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

            if self.enable_download:
                if self._downloader is None:
                    self._downloader = DownloadArtwork()
                download_item_art(media_type, dbid, title, art_dict,
                                  KodiSettings.existing_file_mode(), self._downloader)

            if not defer_pool_refresh and 'fanart' in art_dict:
                from lib.data.slideshow import refresh_pool_item
                refresh_pool_item(media_type, dbid)

            return True

        except Exception as e:
            log("Artwork", f"Error applying art: {str(e)}", xbmc.LOGERROR)
            return False

    def _update_progress(self, force: bool = False) -> None:
        """Update the progress dialog with the running counts."""
        if self.total_items > 0:
            percent = int((self.stats['processed'] / self.total_items) * 100)
        else:
            percent = 0

        message = "[CR]".join((
            ADDON.getLocalizedString(32284).format(
                f"{self.stats['processed']}/{self.total_items}"),
            ADDON.getLocalizedString(32285).format(self.stats['auto_applied']),
            ADDON.getLocalizedString(32286).format(self.stats['skipped']),
        ))

        self.progress.update(percent, message, force=force)

    def _show_summary(self) -> None:
        """Show the run's counts, offering the detailed report when there is one."""
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
        """Offer the applied and skipped reports, each one listed only when it has entries."""
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
        """Show the applied art types, grouped by item."""
        lines = ["[B]Auto-Applied Artwork:[/B]", ""]

        current_title = None
        for title, art_type, _ in self.applied_items:
            if title != current_title:
                if current_title:
                    lines.append("")
                lines.append(f"[B]{title}[/B]")
                current_title = title
            lines.append(f"  • {art_type}")

        text = "[CR]".join(lines)
        show_textviewer(ADDON.getLocalizedString(32550), text)

    def _show_skipped_report(self) -> None:
        """Show each skipped item with its reason."""
        lines = ["[B]Skipped Items:[/B]", ""]

        for title, reason in self.skipped_items:
            lines.append(f"• {title}")
            lines.append(f"  Reason: {reason}")
            lines.append("")

        text = "[CR]".join(lines)
        show_textviewer(ADDON.getLocalizedString(32551), text)
