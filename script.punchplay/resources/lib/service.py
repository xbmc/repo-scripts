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
    ACTION_PROPERTY_EXPORT_DEBUG,
    ACTION_PROPERTY_EXPORT_VERBOSE_DEBUG,
    ACTION_PROPERTY_LOGIN,
    ACTION_PROPERTY_LOGOUT,
    ACTION_PROPERTY_PREVIEW_LIBRARY,
    ACTION_PROPERTY_SHOW_STATUS,
    ACTION_PROPERTY_SYNC_LIBRARY,
    ACTION_PROPERTY_TEST_CONNECTION,
    ADDON_NAME,
    FLUSH_INTERVAL_SECS,
    HOME_WINDOW_ID,
    LIBRARY_SYNC_BATCH_SIZE,
    NOTIFICATION_TITLE,
    PRUNE_INTERVAL_SECS,
    SCROBBLE_IMPORT_ENDPOINT,
    get_addon,
    get_profile_dir,
    localize,
)


class PunchPlayService(xbmc.Monitor):
    def __init__(self) -> None:
        super().__init__()

        from api import APIClient
        from cache import Cache
        from player import PunchPlayPlayer

        self._cache = Cache()
        self._api = APIClient(cache=self._cache)
        self._player = PunchPlayPlayer(api=self._api, cache=self._cache)

        self._last_flush = 0.0
        self._last_prune = 0.0

    # ------------------------------------------------------------------
    # Monitor callbacks
    # ------------------------------------------------------------------

    def onSettingsChanged(self) -> None:  # type: ignore[override]
        xbmc.log("[PunchPlay] Settings changed — will apply on next event", xbmc.LOGDEBUG)

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
                    self._api.logout()

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

            if home_window.getProperty(ACTION_PROPERTY_PREVIEW_LIBRARY):
                home_window.clearProperty(ACTION_PROPERTY_PREVIEW_LIBRARY)
                xbmc.log("[PunchPlay] Library preview triggered from settings", xbmc.LOGINFO)
                self._sync_kodi_library(dry_run=True)

            if home_window.getProperty(ACTION_PROPERTY_SYNC_LIBRARY):
                home_window.clearProperty(ACTION_PROPERTY_SYNC_LIBRARY)
                xbmc.log("[PunchPlay] Library sync triggered from settings", xbmc.LOGINFO)
                self._sync_kodi_library()

            # Flush offline queue periodically.
            if self._api.is_authenticated() and (now - self._last_flush >= FLUSH_INTERVAL_SECS):
                try:
                    self._api.flush_queue()
                except Exception as exc:
                    xbmc.log(f"[PunchPlay] Queue flush error: {exc}", xbmc.LOGWARNING)
                else:
                    self._last_flush = now

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

            total_movies = len(movies)
            total_episodes = len(episodes)
            importable_movies = 0
            importable_episodes = 0
            skipped_duplicates = 0
            unmatched = 0
            failed = 0
            diagnostics: list[dict[str, Any]] = []
            endpoint = (
                SCROBBLE_IMPORT_ENDPOINT + "?dry_run=true"
                if dry_run
                else SCROBBLE_IMPORT_ENDPOINT
            )

            # ── Sync movies in batches of 50 ────────────────────────────
            cancelled = False
            for i in range(0, total_movies, LIBRARY_SYNC_BATCH_SIZE):
                if progress.iscanceled():
                    cancelled = True
                    break
                batch = movies[i : i + LIBRARY_SYNC_BATCH_SIZE]
                progress.update(
                    int(50 * min(i + LIBRARY_SYNC_BATCH_SIZE, total_movies) / max(total_movies, 1)),
                    _s(32025).format(
                        min(i + LIBRARY_SYNC_BATCH_SIZE, total_movies), total_movies
                    ),
                )
                try:
                    resp = self._api.post_immediate(
                        endpoint,
                        {"entries": batch},
                        timeout=55,
                    )
                    importable_movies += resp.get("would_import", resp.get("imported", 0))
                    skipped_duplicates += resp.get("skipped_duplicates", 0)
                    unmatched += resp.get("unmatched", 0)
                    failed += resp.get("failed", 0)
                    diagnostics.extend(resp.get("items", []) or [])
                except Exception as exc:
                    if dry_run:
                        raise RuntimeError(_s(32116).format(str(exc)[:80])) from exc
                    xbmc.log(f"[PunchPlay] Movie batch error: {exc}", xbmc.LOGWARNING)

            # ── Sync episodes in batches of 50 ──────────────────────────
            if not cancelled:
                for i in range(0, total_episodes, LIBRARY_SYNC_BATCH_SIZE):
                    if progress.iscanceled():
                        cancelled = True
                        break
                    batch = episodes[i : i + LIBRARY_SYNC_BATCH_SIZE]
                    pct = 50 + int(
                        50
                        * min(i + LIBRARY_SYNC_BATCH_SIZE, total_episodes)
                        / max(total_episodes, 1)
                    )
                    progress.update(
                        pct,
                        _s(32026).format(
                            min(i + LIBRARY_SYNC_BATCH_SIZE, total_episodes),
                            total_episodes,
                        ),
                    )
                    try:
                        resp = self._api.post_immediate(
                            endpoint,
                            {"entries": batch},
                            timeout=55,
                        )
                        importable_episodes += resp.get("would_import", resp.get("imported", 0))
                        skipped_duplicates += resp.get("skipped_duplicates", 0)
                        unmatched += resp.get("unmatched", 0)
                        failed += resp.get("failed", 0)
                        diagnostics.extend(resp.get("items", []) or [])
                    except Exception as exc:
                        if dry_run:
                            raise RuntimeError(_s(32116).format(str(exc)[:80])) from exc
                        xbmc.log(f"[PunchPlay] Episode batch error: {exc}", xbmc.LOGWARNING)

            progress.close()
            if cancelled:
                xbmc.log(
                    f"[PunchPlay] Library sync cancelled. "
                    f"Processed {importable_movies} movies, {importable_episodes} episodes before cancel.",
                    xbmc.LOGINFO,
                )
            else:
                diagnostics_path = None
                if diagnostics:
                    diagnostics_path = self._write_library_diagnostics(
                        "library-import-preview.json" if dry_run else "library-import-diagnostics.json",
                        {
                            "dry_run": dry_run,
                            "movies": total_movies,
                            "episodes": total_episodes,
                            "would_import" if dry_run else "imported": (
                                importable_movies + importable_episodes
                            ),
                            "skipped_duplicates": skipped_duplicates,
                            "unmatched": unmatched,
                            "failed": failed,
                            "items": diagnostics,
                        },
                    )

                if dry_run:
                    msg = _s(32107).format(
                        importable_movies + importable_episodes,
                        skipped_duplicates,
                        unmatched,
                    )
                else:
                    msg = _s(32027).format(
                        importable_movies + importable_episodes,
                        skipped_duplicates,
                        unmatched,
                    )
                if failed:
                    xbmc.log(
                        f"[PunchPlay] Library sync finished with {failed} failed item(s)",
                        xbmc.LOGWARNING,
                    )
                xbmcgui.Dialog().notification(
                    NOTIFICATION_TITLE, msg, xbmcgui.NOTIFICATION_INFO, 6000
                )
                xbmc.log(f"[PunchPlay] Library sync: {msg}", xbmc.LOGINFO)
                if diagnostics_path:
                    xbmc.log(
                        f"[PunchPlay] Library diagnostics written to {diagnostics_path}",
                        xbmc.LOGINFO,
                    )
                if dry_run and (importable_movies + importable_episodes) > 0:
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
            last_played = movie.get("lastplayed", "")
            if last_played:
                entry["watched_at"] = last_played
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
            last_played = ep.get("lastplayed", "")
            if last_played:
                entry["watched_at"] = last_played
            results.append(entry)
        return results
