"""
service.py — xbmc.Monitor subclass; the long-running service loop.

Responsibilities:
  • Instantiate Cache, APIClient, and PunchPlayPlayer.
  • Block with waitForAbort() so Kodi can signal a clean shutdown.
  • Periodically flush the offline scrobble queue (every 60 s when online).
  • Prune stale identifier-cache entries once per day.
  • Reload settings when the user changes them via onSettingsChanged().
  • One-click Kodi library sync (import watched items to PunchPlay).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import xbmc
import xbmcgui

from constants import (
    ACTION_PROPERTY_CLEAR_QUEUE,
    ACTION_PROPERTY_CLEAR_SUPPRESSIONS,
    ACTION_PROPERTY_EXPORT_DEBUG,
    ACTION_PROPERTY_EXPORT_VERBOSE_DEBUG,
    ACTION_PROPERTY_LOGIN,
    ACTION_PROPERTY_LOGOUT,
    ACTION_PROPERTY_PREVIEW_LIBRARY,
    ACTION_PROPERTY_PULL_SYNC,
    ACTION_PROPERTY_SHOW_STATUS,
    ACTION_PROPERTY_SYNC_LIBRARY,
    ACTION_PROPERTY_TEST_CONNECTION,
    ADDON_NAME,
    AUTO_PULL_CHECK_INTERVAL_SECS,
    FLUSH_INTERVAL_SECS,
    HOME_WINDOW_ID,
    LIBRARY_SYNC_BATCH_SIZE,
    LIBRARY_SYNC_MAX_CONSECUTIVE_FAILURES,
    NOTIFICATION_TITLE,
    PRUNE_INTERVAL_SECS,
    PULL_SYNC_INTERVAL_SECS,
    PULL_SYNC_MAX_HELD_RUNS,
    PULL_SYNC_OVERLAP_SECS,
    SCAN_SYNC_DELAY_SECS,
    SCAN_SYNC_MIN_INTERVAL_SECS,
    SCROBBLE_IMPORT_ENDPOINT,
    get_addon,
    get_profile_dir,
    kodi_datetime_to_utc_iso,
    localize,
)


class PunchPlayService(xbmc.Monitor):
    def __init__(self) -> None:
        super().__init__()

        from api import APIClient
        from cache import Cache
        from library_events import LiveWatchedSync
        from player import PunchPlayPlayer

        self._cache = Cache()
        self._api = APIClient(cache=self._cache)
        self._player = PunchPlayPlayer(api=self._api, cache=self._cache)
        self._live_sync = LiveWatchedSync()

        self._last_flush = 0.0
        self._last_prune = 0.0
        self._last_auto_pull_check = 0.0
        self._scan_sync_due_at: float | None = None
        self._last_scan_sync = 0.0

    # ------------------------------------------------------------------
    # Monitor callbacks
    # ------------------------------------------------------------------

    def onSettingsChanged(self) -> None:  # type: ignore[override]
        xbmc.log("[PunchPlay] Settings changed — will apply on next event", xbmc.LOGDEBUG)

    def onNotification(self, sender: str, method: str, data: str) -> None:  # type: ignore[override]
        # Runs on Kodi's announce thread — queue only, no I/O or dialogs.
        _ = sender
        try:
            if method == "VideoLibrary.OnScanFinished":
                self._scan_sync_due_at = time.monotonic() + SCAN_SYNC_DELAY_SECS
                xbmc.log("[PunchPlay] Library scan finished — pull sync queued", xbmc.LOGDEBUG)
                return
            if method == "VideoLibrary.OnUpdate" and self._live_sync_enabled():
                self._live_sync.push_update(data)
        except Exception as exc:
            xbmc.log(f"[PunchPlay] Notification handling error: {exc}", xbmc.LOGDEBUG)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        addon = get_addon()
        xbmc.log(
            f"[PunchPlay] Service started (v{addon.getAddonInfo('version')})",
            xbmc.LOGINFO,
        )

        # Window 10000 is the Kodi home window — its properties are globally
        # accessible, so settings action buttons can signal the service here.
        home_window = xbmcgui.Window(HOME_WINDOW_ID)

        while not self.abortRequested():
            now = time.monotonic()

            # Handle login / logout triggered from the settings screen.
            if home_window.getProperty(ACTION_PROPERTY_LOGIN):
                home_window.clearProperty(ACTION_PROPERTY_LOGIN)
                if self._api.is_authenticated():
                    xbmcgui.Dialog().notification(
                        NOTIFICATION_TITLE,
                        localize(32031),
                        xbmcgui.NOTIFICATION_INFO, 3000,
                    )
                else:
                    xbmc.log("[PunchPlay] Login triggered from settings", xbmc.LOGINFO)
                    self._api.device_code_login()

            if home_window.getProperty(ACTION_PROPERTY_LOGOUT):
                home_window.clearProperty(ACTION_PROPERTY_LOGOUT)
                if not self._api.is_authenticated():
                    xbmcgui.Dialog().notification(
                        NOTIFICATION_TITLE,
                        localize(32032),
                        xbmcgui.NOTIFICATION_INFO, 3000,
                    )
                else:
                    xbmc.log("[PunchPlay] Logout triggered from settings", xbmc.LOGINFO)
                    if self._api.logout():
                        self._player.handle_logout()

            if home_window.getProperty(ACTION_PROPERTY_TEST_CONNECTION):
                home_window.clearProperty(ACTION_PROPERTY_TEST_CONNECTION)
                xbmc.log("[PunchPlay] Connection test triggered from settings", xbmc.LOGINFO)
                result = self._api.test_connection()
                xbmcgui.Dialog().notification(
                    NOTIFICATION_TITLE,
                    result["message"],
                    xbmcgui.NOTIFICATION_INFO,
                    4000,
                )

            if home_window.getProperty(ACTION_PROPERTY_SHOW_STATUS):
                home_window.clearProperty(ACTION_PROPERTY_SHOW_STATUS)
                self._show_status()

            if home_window.getProperty(ACTION_PROPERTY_EXPORT_DEBUG):
                home_window.clearProperty(ACTION_PROPERTY_EXPORT_DEBUG)
                self._export_debug_info()

            if home_window.getProperty(ACTION_PROPERTY_EXPORT_VERBOSE_DEBUG):
                home_window.clearProperty(ACTION_PROPERTY_EXPORT_VERBOSE_DEBUG)
                self._export_debug_info(verbose=True)

            if home_window.getProperty(ACTION_PROPERTY_CLEAR_QUEUE):
                home_window.clearProperty(ACTION_PROPERTY_CLEAR_QUEUE)
                self._clear_offline_queue()

            if home_window.getProperty(ACTION_PROPERTY_CLEAR_SUPPRESSIONS):
                home_window.clearProperty(ACTION_PROPERTY_CLEAR_SUPPRESSIONS)
                self._clear_rating_suppressions()

            if home_window.getProperty(ACTION_PROPERTY_PULL_SYNC):
                home_window.clearProperty(ACTION_PROPERTY_PULL_SYNC)
                xbmc.log("[PunchPlay] Pull sync triggered from settings", xbmc.LOGINFO)
                self._pull_sync(manual=True)

            if home_window.getProperty(ACTION_PROPERTY_PREVIEW_LIBRARY):
                home_window.clearProperty(ACTION_PROPERTY_PREVIEW_LIBRARY)
                xbmc.log("[PunchPlay] Library preview triggered from settings", xbmc.LOGINFO)
                self._sync_kodi_library(dry_run=True)

            if home_window.getProperty(ACTION_PROPERTY_SYNC_LIBRARY):
                home_window.clearProperty(ACTION_PROPERTY_SYNC_LIBRARY)
                xbmc.log("[PunchPlay] Library sync triggered from settings", xbmc.LOGINFO)
                self._sync_kodi_library()

            # Flush offline queue periodically. Routed through the player's
            # post worker (not called on this thread) so it can never run
            # concurrently with a flush the worker is already doing ahead of
            # a playback start — see PunchPlayPlayer.dispatch_flush().
            if self._api.is_authenticated() and (now - self._last_flush >= FLUSH_INTERVAL_SECS):
                self._player.dispatch_flush()
                self._last_flush = now

            # Show a queued rating prompt once its delay has elapsed.  The
            # player queues these instead of blocking its callback thread.
            rating_request = self._player.pop_due_rating_prompt()
            if rating_request is not None:
                try:
                    self._player.prompt_for_rating(rating_request)
                except Exception as exc:
                    xbmc.log(f"[PunchPlay] Rating prompt error: {exc}", xbmc.LOGWARNING)

            # Push manual Kodi watched toggles to PunchPlay.
            try:
                self._push_watched_toggles()
            except Exception as exc:
                xbmc.log(f"[PunchPlay] Live watched sync error: {exc}", xbmc.LOGWARNING)

            # Library scan finished → pull sync so new items inherit
            # watched states and resume points.
            if self._scan_sync_due_at is not None and now >= self._scan_sync_due_at:
                self._scan_sync_due_at = None
                try:
                    self._maybe_scan_pull_sync(now)
                except Exception as exc:
                    xbmc.log(f"[PunchPlay] Scan pull sync error: {exc}", xbmc.LOGWARNING)

            # Periodic PunchPlay → Kodi sync when enabled.
            if now - self._last_auto_pull_check >= AUTO_PULL_CHECK_INTERVAL_SECS:
                self._last_auto_pull_check = now
                try:
                    self._maybe_auto_pull_sync()
                except Exception as exc:
                    xbmc.log(f"[PunchPlay] Auto pull sync error: {exc}", xbmc.LOGWARNING)

            # Prune stale identifier cache entries once a day.
            if now - self._last_prune >= PRUNE_INTERVAL_SECS:
                try:
                    self._cache.prune_identifier_cache()
                    xbmc.log("[PunchPlay] Identifier cache pruned", xbmc.LOGDEBUG)
                except Exception as exc:
                    xbmc.log(f"[PunchPlay] Cache prune error: {exc}", xbmc.LOGDEBUG)
                self._last_prune = now

            # Sleep 1 s so login/logout feel responsive.
            self.waitForAbort(1)

        # Kodi is shutting down — clean up the player.
        self._player.cleanup()
        xbmc.log("[PunchPlay] Service stopped", xbmc.LOGINFO)

    def _format_relative_age(self, age_secs: int | None) -> str:
        _s = localize
        if age_secs is None:
            return _s(32084)
        if age_secs < 60:
            return _s(32080)
        if age_secs < 3600:
            return _s(32081).format(max(1, age_secs // 60))
        if age_secs < 86400:
            return _s(32082).format(max(1, age_secs // 3600))
        return _s(32083).format(max(1, age_secs // 86400))

    def _format_pull_sync_status(self, snapshot: dict[str, Any]) -> str:
        last_at = snapshot.get("last_pull_sync_at")
        if not last_at:
            return localize(32070)
        age_secs = max(0, int(time.time() - int(last_at) / 1000))
        text = self._format_relative_age(age_secs)
        summary = snapshot.get("last_pull_sync_summary")
        if summary:
            text = f"{text} — {summary}"
        return text

    def _show_status(self) -> None:
        snapshot = self._api.get_status_snapshot()
        _s = localize
        status_label = _s(32079) if snapshot["connected"] else _s(32078)
        username = snapshot.get("account_username") or _s(32071)
        last_success = snapshot.get("last_successful_event_type") or _s(32070)
        if snapshot.get("last_successful_title"):
            last_success = f"{last_success} — {snapshot['last_successful_title']}"
        last_error = snapshot.get("last_error") or _s(32070)
        backend_health = _s(32098) if snapshot.get("backend_valid") else _s(32099)
        queue_summary = snapshot.get("queue_endpoints") or {}
        queue_endpoints = ", ".join(
            "{0}: {1}".format(endpoint.rsplit("/", 1)[-1], count)
            for endpoint, count in sorted(queue_summary.items())
        ) or _s(32070)
        last_identify = snapshot.get("last_identify_status") or _s(32070)
        if snapshot.get("last_identify_title"):
            last_identify = "{0} — {1}".format(last_identify, snapshot["last_identify_title"])
        rating_scope = (
            _s(32140)
            if snapshot.get("rating_prompt_scope") == "movies"
            else _s(32141)
        )

        lines = [
            _s(32060).format(status_label),
            _s(32061).format(username),
            _s(32062).format(snapshot.get("backend_url") or _s(32071)),
            _s(32100).format(backend_health),
            _s(32063).format(snapshot.get("device_id") or _s(32071)),
            _s(32064).format(snapshot.get("queue_count") or 0),
            _s(32065).format(self._format_relative_age(snapshot.get("oldest_queue_age_secs"))),
            _s(32101).format(queue_endpoints),
            _s(32102).format(snapshot.get("identifier_cache_size") or 0),
            _s(32103).format(last_identify),
            _s(32066).format(last_success),
            _s(32067).format(last_error),
            _s(32127).format(self._format_pull_sync_status(snapshot)),
            _s(32142).format(rating_scope),
            _s(32068).format(snapshot.get("addon_version") or _s(32071)),
            _s(32069).format(snapshot.get("kodi_version") or _s(32071)),
        ]
        if snapshot.get("backend_error"):
            lines.append(_s(32104).format(snapshot["backend_error"]))
        xbmcgui.Dialog().textviewer(_s(32059), "\n".join(lines))

    def _export_debug_info(self, *, verbose: bool = False) -> None:
        _s = localize
        if verbose and not xbmcgui.Dialog().yesno(ADDON_NAME, _s(32105)):
            return
        try:
            path = self._api.export_debug_info(verbose=verbose)
        except Exception as exc:
            xbmc.log(f"[PunchPlay] Debug export failed: {exc}", xbmc.LOGWARNING)
            xbmcgui.Dialog().notification(
                NOTIFICATION_TITLE,
                _s(32086).format(str(exc)[:80]),
                xbmcgui.NOTIFICATION_ERROR,
                5000,
            )
            return

        xbmcgui.Dialog().notification(
            NOTIFICATION_TITLE,
            _s(32074).format(path),
            xbmcgui.NOTIFICATION_INFO,
            5000,
        )

    def _clear_offline_queue(self) -> None:
        _s = localize
        summary = self._cache.get_queue_summary()
        count = int(summary["count"] or 0)
        if count <= 0:
            xbmcgui.Dialog().notification(
                NOTIFICATION_TITLE,
                _s(32077),
                xbmcgui.NOTIFICATION_INFO,
                3000,
            )
            return

        if not xbmcgui.Dialog().yesno(ADDON_NAME, _s(32072).format(count)):
            return

        self._api.clear_offline_queue()
        xbmcgui.Dialog().notification(
            NOTIFICATION_TITLE,
            _s(32073),
            xbmcgui.NOTIFICATION_INFO,
            3000,
        )

    def _clear_rating_suppressions(self) -> None:
        _s = localize
        cleared = self._cache.clear_rating_suppressions()
        if cleared <= 0:
            message = _s(32131)
        else:
            message = _s(32130).format(cleared)
        xbmcgui.Dialog().notification(
            NOTIFICATION_TITLE, message, xbmcgui.NOTIFICATION_INFO, 3000
        )

    # ------------------------------------------------------------------
    # Live watched sync (Kodi → PunchPlay)
    # ------------------------------------------------------------------

    def _live_sync_enabled(self) -> bool:
        return get_addon().getSettingBool("live_watched_sync")

    def _push_watched_toggles(self) -> None:
        if self._live_sync.pending_count() == 0:
            return
        if not self._api.is_authenticated():
            self._live_sync.clear()
            return

        events = self._live_sync.pop_due_events(self._player.recent_library_items())
        if not events:
            return

        from library_events import LibraryDetailLookupError, build_import_entry

        addon = get_addon()
        scrobble_settings = {
            "movie": addon.getSettingBool("scrobble_movies"),
            "episode": addon.getSettingBool("scrobble_tv"),
            "anime": addon.getSettingBool("scrobble_anime"),
        }

        entries = []
        retry_events = []
        for event in events:
            try:
                entry = build_import_entry(event)
            except LibraryDetailLookupError:
                retry_events.append(event)
                continue
            if entry is None or not entry.get("title"):
                continue
            # Anime is a separate toggle only for episodes. Movies always
            # follow the movie setting, matching PunchPlayPlayer._should_track.
            content_key = entry["media_type"]
            if content_key == "episode" and entry.get("anime"):
                content_key = "anime"
            if not scrobble_settings.get(content_key, True):
                xbmc.log(
                    f"[PunchPlay] Watched toggle skipped — {content_key} scrobbling disabled",
                    xbmc.LOGDEBUG,
                )
                continue
            entries.append(entry)

        if retry_events:
            self._live_sync.requeue_events(retry_events)
            xbmc.log(
                f"[PunchPlay] Requeued {len(retry_events)} watched toggle(s) "
                "after detail lookup failure",
                xbmc.LOGWARNING,
            )

        if not entries:
            return

        xbmc.log(
            f"[PunchPlay] Pushing {len(entries)} watched toggle(s) to PunchPlay",
            xbmc.LOGINFO,
        )
        # Routed through the player's post worker rather than posted here —
        # this runs on the service loop's own thread, which must stay free
        # for login/logout handling, dispatch_flush()'s periodic trigger, and
        # rating-prompt draining, not blocked on a network round trip.
        self._player.dispatch_import(entries)

    def _maybe_scan_pull_sync(self, now: float) -> None:
        settings = self._pull_sync_settings()
        if not settings["auto"]:
            return
        if not (settings["watched"] or settings["resume"]):
            return
        if not self._api.is_authenticated():
            return
        if now - self._last_scan_sync < SCAN_SYNC_MIN_INTERVAL_SECS:
            xbmc.log("[PunchPlay] Scan pull sync skipped (ran recently)", xbmc.LOGDEBUG)
            return
        self._last_scan_sync = now
        # Full sync, not incremental — a scan may have added files whose
        # watched history on PunchPlay is arbitrarily old.
        xbmc.log("[PunchPlay] Scan-triggered pull sync starting", xbmc.LOGINFO)
        self._pull_sync(manual=False)

    # ------------------------------------------------------------------
    # PunchPlay → Kodi sync (pull)
    # ------------------------------------------------------------------

    def _pull_sync_settings(self) -> dict[str, bool]:
        addon = get_addon()
        return {
            "watched": addon.getSettingBool("pull_watched"),
            "resume": addon.getSettingBool("pull_resume"),
            "auto": addon.getSettingBool("pull_sync_auto"),
        }

    def _pull_sync_context(self, settings: dict[str, bool]) -> str:
        """Stable key for the enabled halves of automatic pull sync."""
        return "watched={0};resume={1}".format(
            int(settings["watched"]),
            int(settings["resume"]),
        )

    def _maybe_auto_pull_sync(self) -> None:
        settings = self._pull_sync_settings()
        if not settings["auto"]:
            return
        if not (settings["watched"] or settings["resume"]):
            return
        if not self._api.is_authenticated():
            return
        self._cache.ensure_pull_sync_context(self._pull_sync_context(settings))
        last_ms = self._cache.get_runtime_status().get("last_pull_sync_at") or 0
        now_ms = int(time.time() * 1000)
        if now_ms - int(last_ms) < PULL_SYNC_INTERVAL_SECS * 1000:
            return
        since_ms = None
        if last_ms:
            since_ms = max(0, int(last_ms) - PULL_SYNC_OVERLAP_SECS * 1000)
        xbmc.log("[PunchPlay] Auto pull sync starting", xbmc.LOGINFO)
        self._pull_sync(manual=False, since_ms=since_ms)

    def _pull_sync(self, *, manual: bool, since_ms: int | None = None) -> None:
        _s = localize

        if not self._api.is_authenticated():
            if manual:
                xbmcgui.Dialog().notification(
                    NOTIFICATION_TITLE, _s(32032), xbmcgui.NOTIFICATION_WARNING, 4000
                )
            return

        settings = self._pull_sync_settings()
        if not (settings["watched"] or settings["resume"]):
            if manual:
                xbmcgui.Dialog().notification(
                    NOTIFICATION_TITLE, _s(32132), xbmcgui.NOTIFICATION_WARNING, 4000
                )
            return
        self._cache.ensure_pull_sync_context(self._pull_sync_context(settings))

        from pull_sync import run_pull_sync

        progress = None
        if manual:
            progress = xbmcgui.DialogProgress()
            progress.create(_s(32121), _s(32122))

        def _progress_callback(done: int, total: int) -> bool:
            if progress is None:
                return not self.abortRequested()
            if progress.iscanceled():
                return False
            progress.update(
                int(100 * done / max(total, 1)),
                _s(32123).format(done, total),
            )
            return True

        failed_items: set[str] = set()
        try:
            summary = run_pull_sync(
                self._api,
                apply_watched=settings["watched"],
                apply_resume=settings["resume"],
                since_ms=since_ms,
                progress_callback=_progress_callback,
                applied_callback=lambda item: self._live_sync.record_pull_applied({item}),
                failed_out=failed_items,
            )
        except Exception as exc:
            if progress is not None:
                progress.close()
            if since_ms is None:
                # A manual/scan-triggered full pull may have been needed to
                # apply history older than the previous incremental cursor.
                # Keep the next automatic run full too instead of silently
                # falling back to that stale cursor after this failure.
                self._cache.clear_pull_sync_checkpoint()
            xbmc.log(f"[PunchPlay] Pull sync failed: {exc}", xbmc.LOGWARNING)
            if manual:
                xbmcgui.Dialog().notification(
                    NOTIFICATION_TITLE, _s(32126).format(str(exc)[:80]),
                    xbmcgui.NOTIFICATION_ERROR, 5000
                )
            return

        if progress is not None:
            progress.close()

        marked = summary["movies_marked"] + summary["episodes_marked"]
        apply_failed = summary.get("apply_failed") or 0
        summary_text = _s(32138).format(
            marked,
            summary["resume_set"],
            summary["unmatched"],
            apply_failed,
        )

        if summary.get("cancelled"):
            # Don't record a cancelled run — the next auto-sync must not
            # treat the unfinished remainder as already synced.
            xbmc.log(
                f"[PunchPlay] Pull sync cancelled after: {summary_text}",
                xbmc.LOGINFO,
            )
            if manual:
                xbmcgui.Dialog().notification(
                    NOTIFICATION_TITLE, _s(32133), xbmcgui.NOTIFICATION_INFO, 4000
                )
            return

        if apply_failed:
            # Some items failed to write to the Kodi library — hold back the
            # incremental checkpoint so they're retried next time, rather
            # than letting the next sync's `since` filter treat them as
            # already covered. But a persistently-failing item must not
            # block the checkpoint (and every newer item behind it) forever.
            # Retry counts are tracked per failed item, so only advance once
            # every item failing on this run has exhausted its own allowance;
            # a new or unrelated failure always starts at run one.
            held_runs = self._cache.record_pull_sync_held(failed_items)
            if held_runs < PULL_SYNC_MAX_HELD_RUNS:
                if since_ms is None:
                    # A failed item in a full pull can predate the previous
                    # incremental checkpoint. Clearing it ensures the next
                    # automatic run fetches that item again.
                    self._cache.clear_pull_sync_checkpoint()
                xbmc.log(
                    f"[PunchPlay] Pull sync finished with {apply_failed} apply "
                    f"failure(s) ({held_runs}/{PULL_SYNC_MAX_HELD_RUNS}), "
                    f"checkpoint not advanced: {summary_text}",
                    xbmc.LOGWARNING,
                )
            else:
                xbmc.log(
                    f"[PunchPlay] Pull sync still has {apply_failed} apply "
                    f"failure(s) after {held_runs} held run(s) — advancing "
                    f"checkpoint anyway so future syncs aren't blocked: "
                    f"{summary_text}",
                    xbmc.LOGWARNING,
                )
                self._cache.record_pull_sync(summary_text)
        else:
            self._cache.record_pull_sync(summary_text)
            xbmc.log(f"[PunchPlay] Pull sync finished: {summary_text}", xbmc.LOGINFO)

        changed = marked + summary["resume_set"]
        if manual:
            if apply_failed:
                message = _s(32137).format(changed, apply_failed)
                icon = xbmcgui.NOTIFICATION_WARNING
            elif changed:
                message = _s(32124).format(marked, summary["resume_set"])
                icon = xbmcgui.NOTIFICATION_INFO
            else:
                message = _s(32125)
                icon = xbmcgui.NOTIFICATION_INFO
            xbmcgui.Dialog().notification(NOTIFICATION_TITLE, message, icon, 5000)
        elif changed and get_addon().getSettingBool("show_notifications"):
            xbmcgui.Dialog().notification(
                NOTIFICATION_TITLE,
                _s(32124).format(marked, summary["resume_set"]),
                xbmcgui.NOTIFICATION_INFO,
                5000,
            )

    def _write_library_diagnostics(
        self,
        filename: str,
        payload: dict[str, Any],
    ) -> str | None:
        try:
            path = os.path.join(get_profile_dir(), filename)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
            return path
        except Exception as exc:
            xbmc.log(f"[PunchPlay] Could not write library diagnostics: {exc}", xbmc.LOGDEBUG)
            return None

    # ------------------------------------------------------------------
    # Kodi library sync
    # ------------------------------------------------------------------

    def _post_library_batches(
        self,
        entries: list[dict[str, Any]],
        *,
        endpoint: str,
        dry_run: bool,
        progress: Any,
        progress_base: int,
        progress_span: int,
        message_id: int,
        totals: dict[str, int],
        diagnostics: list[dict[str, Any]],
    ) -> str:
        """
        POST *entries* in batches, accumulating counts into *totals*.

        Returns "done", "cancelled", or "failed".  A failed batch is counted
        and retried on the next run rather than silently forgotten; after
        LIBRARY_SYNC_MAX_CONSECUTIVE_FAILURES in a row we stop, because the
        rest of the run would only pile up more of the same error.
        """
        _s = localize
        total = len(entries)
        consecutive_failures = 0

        for start in range(0, total, LIBRARY_SYNC_BATCH_SIZE):
            if progress.iscanceled():
                return "cancelled"

            batch = entries[start : start + LIBRARY_SYNC_BATCH_SIZE]
            done = min(start + LIBRARY_SYNC_BATCH_SIZE, total)
            progress.update(
                progress_base + int(progress_span * done / max(total, 1)),
                _s(message_id).format(done, total),
            )

            try:
                resp = self._api.post_immediate(
                    endpoint,
                    {"entries": batch},
                    timeout=55,
                )
            except Exception as exc:
                # A preview exists to surface problems — fail loudly.
                if dry_run:
                    raise RuntimeError(_s(32116).format(str(exc)[:80])) from exc
                consecutive_failures += 1
                totals["failed_batches"] += 1
                totals["not_sent"] += len(batch)
                xbmc.log(
                    f"[PunchPlay] Library batch failed "
                    f"({consecutive_failures}/{LIBRARY_SYNC_MAX_CONSECUTIVE_FAILURES}): {exc}",
                    xbmc.LOGWARNING,
                )
                if consecutive_failures >= LIBRARY_SYNC_MAX_CONSECUTIVE_FAILURES:
                    totals["not_sent"] += total - done
                    xbmc.log(
                        "[PunchPlay] Library sync aborted after repeated batch failures",
                        xbmc.LOGWARNING,
                    )
                    return "failed"
                continue

            consecutive_failures = 0
            totals["imported"] += resp.get("would_import", resp.get("imported", 0))
            totals["skipped_duplicates"] += resp.get("skipped_duplicates", 0)
            totals["unmatched"] += resp.get("unmatched", 0)
            totals["rejected_items"] += resp.get("failed", 0)
            diagnostics.extend(resp.get("items", []) or [])

        return "done"

    def _sync_kodi_library(self, dry_run: bool = False) -> None:
        """Import all watched items from the Kodi library into PunchPlay."""
        _s = localize

        if not self._api.is_authenticated():
            xbmcgui.Dialog().notification(
                NOTIFICATION_TITLE, _s(32032), xbmcgui.NOTIFICATION_WARNING, 4000
            )
            return

        progress = xbmcgui.DialogProgress()
        progress.create(
            _s(32106) if dry_run else _s(32023),
            _s(32025).format(0, "?"),
        )

        try:
            movies = self._get_watched_movies()
            episodes = self._get_watched_episodes()

            if not movies and not episodes:
                progress.close()
                xbmcgui.Dialog().notification(
                    NOTIFICATION_TITLE, _s(32029), xbmcgui.NOTIFICATION_INFO, 4000
                )
                return

            totals = {
                "imported": 0,
                "skipped_duplicates": 0,
                "unmatched": 0,
                "rejected_items": 0,
                "failed_batches": 0,
                "not_sent": 0,
            }
            diagnostics: list[dict[str, Any]] = []
            endpoint = (
                SCROBBLE_IMPORT_ENDPOINT + "?dry_run=true"
                if dry_run
                else SCROBBLE_IMPORT_ENDPOINT
            )

            outcome = self._post_library_batches(
                movies,
                endpoint=endpoint,
                dry_run=dry_run,
                progress=progress,
                progress_base=0,
                progress_span=50,
                message_id=32025,
                totals=totals,
                diagnostics=diagnostics,
            )
            if outcome == "done":
                outcome = self._post_library_batches(
                    episodes,
                    endpoint=endpoint,
                    dry_run=dry_run,
                    progress=progress,
                    progress_base=50,
                    progress_span=50,
                    message_id=32026,
                    totals=totals,
                    diagnostics=diagnostics,
                )
            elif outcome == "failed":
                totals["not_sent"] += len(episodes)

            progress.close()
            if outcome == "cancelled":
                xbmc.log(
                    f"[PunchPlay] Library sync cancelled after importing "
                    f"{totals['imported']} item(s).",
                    xbmc.LOGINFO,
                )
            else:
                diagnostics_path = None
                if diagnostics:
                    diagnostics_path = self._write_library_diagnostics(
                        "library-import-preview.json" if dry_run else "library-import-diagnostics.json",
                        {
                            "dry_run": dry_run,
                            "movies": len(movies),
                            "episodes": len(episodes),
                            "would_import" if dry_run else "imported": totals["imported"],
                            "skipped_duplicates": totals["skipped_duplicates"],
                            "unmatched": totals["unmatched"],
                            "failed": totals["rejected_items"],
                            "failed_batches": totals["failed_batches"],
                            "not_sent": totals["not_sent"],
                            "items": diagnostics,
                        },
                    )

                if dry_run:
                    msg = _s(32107).format(
                        totals["imported"],
                        totals["skipped_duplicates"],
                        totals["unmatched"],
                    )
                    icon = xbmcgui.NOTIFICATION_INFO
                elif totals["not_sent"]:
                    # Some entries never reached the backend — say so rather
                    # than reporting a total that quietly excludes them.
                    msg = _s(32135).format(totals["imported"], totals["not_sent"])
                    icon = xbmcgui.NOTIFICATION_WARNING
                else:
                    msg = _s(32027).format(
                        totals["imported"],
                        totals["skipped_duplicates"],
                        totals["unmatched"],
                    )
                    icon = xbmcgui.NOTIFICATION_INFO

                if totals["rejected_items"]:
                    xbmc.log(
                        f"[PunchPlay] Library sync: backend rejected "
                        f"{totals['rejected_items']} item(s)",
                        xbmc.LOGWARNING,
                    )
                xbmcgui.Dialog().notification(NOTIFICATION_TITLE, msg, icon, 6000)
                xbmc.log(f"[PunchPlay] Library sync: {msg}", xbmc.LOGINFO)
                if diagnostics_path:
                    xbmc.log(
                        f"[PunchPlay] Library diagnostics written to {diagnostics_path}",
                        xbmc.LOGINFO,
                    )
                if dry_run and totals["imported"] > 0:
                    if xbmcgui.Dialog().yesno(ADDON_NAME, _s(32108)):
                        self._sync_kodi_library(dry_run=False)

        except Exception as exc:
            try:
                progress.close()
            except Exception:
                pass
            xbmc.log(f"[PunchPlay] Library sync failed: {exc}", xbmc.LOGWARNING)
            xbmcgui.Dialog().notification(
                NOTIFICATION_TITLE, _s(32028).format(str(exc)[:80]),
                xbmcgui.NOTIFICATION_ERROR, 5000
            )

    def _get_watched_movies(self) -> list[dict[str, Any]]:
        """Query Kodi's JSON-RPC for all watched movies."""
        raw = xbmc.executeJSONRPC(json.dumps({
            "jsonrpc": "2.0",
            "method": "VideoLibrary.GetMovies",
            "params": {
                "filter": {
                    "field": "playcount",
                    "operator": "greaterthan",
                    "value": "0",
                },
                "properties": [
                    "title", "year", "imdbnumber", "uniqueid",
                    "lastplayed", "playcount",
                ],
            },
            "id": 1,
        }))
        data = json.loads(raw)
        results: list[dict[str, Any]] = []
        for movie in data.get("result", {}).get("movies", []):
            entry: dict[str, Any] = {
                "media_type": "movie",
                "title": movie.get("title", ""),
                "year": movie.get("year"),
            }
            # Extract IDs from uniqueid dict or imdbnumber field.
            unique_ids = movie.get("uniqueid", {})
            imdb = unique_ids.get("imdb") or movie.get("imdbnumber") or None
            tmdb = unique_ids.get("tmdb")
            if imdb:
                entry["imdb_id"] = imdb
            if tmdb:
                try:
                    entry["tmdb_id"] = int(tmdb)
                except (ValueError, TypeError):
                    pass
            watched_at = kodi_datetime_to_utc_iso(movie.get("lastplayed", ""))
            if watched_at:
                entry["watched_at"] = watched_at
            playcount = int(movie.get("playcount") or 0)
            if playcount > 0:
                entry["playcount"] = playcount
            results.append(entry)
        return results

    def _get_watched_episodes(self) -> list[dict[str, Any]]:
        """Query Kodi's JSON-RPC for all watched episodes."""
        raw = xbmc.executeJSONRPC(json.dumps({
            "jsonrpc": "2.0",
            "method": "VideoLibrary.GetEpisodes",
            "params": {
                "filter": {
                    "field": "playcount",
                    "operator": "greaterthan",
                    "value": "0",
                },
                "properties": [
                    "showtitle", "season", "episode", "uniqueid",
                    "lastplayed", "playcount",
                ],
            },
            "id": 2,
        }))
        data = json.loads(raw)
        results: list[dict[str, Any]] = []
        for ep in data.get("result", {}).get("episodes", []):
            entry: dict[str, Any] = {
                "media_type": "episode",
                "title": ep.get("showtitle", ""),
                "season": ep.get("season"),
                "episode": ep.get("episode"),
            }
            unique_ids = ep.get("uniqueid", {})
            imdb = unique_ids.get("imdb")
            tmdb = unique_ids.get("tmdb")
            if imdb:
                entry["imdb_id"] = imdb
            if tmdb:
                try:
                    entry["tmdb_id"] = int(tmdb)
                except (ValueError, TypeError):
                    pass
            watched_at = kodi_datetime_to_utc_iso(ep.get("lastplayed", ""))
            if watched_at:
                entry["watched_at"] = watched_at
            playcount = int(ep.get("playcount") or 0)
            if playcount > 0:
                entry["playcount"] = playcount
            results.append(entry)
        return results
