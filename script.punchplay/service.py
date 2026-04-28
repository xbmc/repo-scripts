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
import time
from typing import Any

import xbmc
import xbmcaddon
import xbmcgui

_ADDON_ID = "script.punchplay"

# Flush the offline queue this often when network is available (seconds).
_FLUSH_INTERVAL = 60

# Prune the identifier cache this often (seconds).  24 h.
_PRUNE_INTERVAL = 86_400


class PunchPlayService(xbmc.Monitor):
    def __init__(self) -> None:
        super().__init__()

        from cache import Cache
        from api import APIClient
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
        addon = xbmcaddon.Addon(_ADDON_ID)
        xbmc.log(
            f"[PunchPlay] Service started (v{addon.getAddonInfo('version')})",
            xbmc.LOGINFO,
        )

        # Window 10000 is the Kodi home window — its properties are globally
        # accessible, so settings action buttons can signal the service here.
        _home = xbmcgui.Window(10000)

        while not self.abortRequested():
            now = time.monotonic()

            # Handle login / logout triggered from the settings screen.
            if _home.getProperty("punchplay_login"):
                _home.clearProperty("punchplay_login")
                if self._api.is_authenticated():
                    xbmcgui.Dialog().notification(
                        "PunchPlay",
                        xbmcaddon.Addon(_ADDON_ID).getLocalizedString(32031),
                        xbmcgui.NOTIFICATION_INFO, 3000,
                    )
                else:
                    xbmc.log("[PunchPlay] Login triggered from settings", xbmc.LOGINFO)
                    self._api.device_code_login()

            if _home.getProperty("punchplay_logout"):
                _home.clearProperty("punchplay_logout")
                if not self._api.is_authenticated():
                    xbmcgui.Dialog().notification(
                        "PunchPlay",
                        xbmcaddon.Addon(_ADDON_ID).getLocalizedString(32032),
                        xbmcgui.NOTIFICATION_INFO, 3000,
                    )
                else:
                    xbmc.log("[PunchPlay] Logout triggered from settings", xbmc.LOGINFO)
                    self._api.logout()

            if _home.getProperty("punchplay_sync_library"):
                _home.clearProperty("punchplay_sync_library")
                xbmc.log("[PunchPlay] Library sync triggered from settings", xbmc.LOGINFO)
                self._sync_kodi_library()

            # Flush offline queue periodically.
            if self._api.is_authenticated() and (now - self._last_flush >= _FLUSH_INTERVAL):
                try:
                    self._api.flush_queue()
                except Exception as exc:
                    xbmc.log(f"[PunchPlay] Queue flush error: {exc}", xbmc.LOGWARNING)
                else:
                    self._last_flush = now

            # Prune stale identifier cache entries once a day.
            if now - self._last_prune >= _PRUNE_INTERVAL:
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

    # ------------------------------------------------------------------
    # Kodi library sync
    # ------------------------------------------------------------------

    def _sync_kodi_library(self) -> None:
        """Import all watched items from the Kodi library into PunchPlay."""
        _s = xbmcaddon.Addon(_ADDON_ID).getLocalizedString

        if not self._api.is_authenticated():
            xbmcgui.Dialog().notification(
                "PunchPlay", "Not logged in.", xbmcgui.NOTIFICATION_WARNING, 4000
            )
            return

        progress = xbmcgui.DialogProgress()
        progress.create(_s(32023), _s(32025).format(0, "?"))

        try:
            movies = self._get_watched_movies()
            episodes = self._get_watched_episodes()

            if not movies and not episodes:
                progress.close()
                xbmcgui.Dialog().notification(
                    "PunchPlay", _s(32029), xbmcgui.NOTIFICATION_INFO, 4000
                )
                return

            total_movies = len(movies)
            total_episodes = len(episodes)
            imported_movies = 0
            imported_episodes = 0

            # ── Sync movies in batches of 50 ────────────────────────────
            cancelled = False
            batch_size = 50
            for i in range(0, total_movies, batch_size):
                if progress.iscanceled():
                    cancelled = True
                    break
                batch = movies[i : i + batch_size]
                progress.update(
                    int(50 * min(i + batch_size, total_movies) / max(total_movies, 1)),
                    _s(32025).format(min(i + batch_size, total_movies), total_movies),
                )
                try:
                    resp = self._api.post_immediate(
                        "/api/scrobble/import", {"entries": batch}, timeout=55
                    )
                    imported_movies += resp.get("imported", 0)
                except Exception as exc:
                    xbmc.log(f"[PunchPlay] Movie batch error: {exc}", xbmc.LOGWARNING)

            # ── Sync episodes in batches of 50 ──────────────────────────
            if not cancelled:
                for i in range(0, total_episodes, batch_size):
                    if progress.iscanceled():
                        cancelled = True
                        break
                    batch = episodes[i : i + batch_size]
                    pct = 50 + int(50 * min(i + batch_size, total_episodes) / max(total_episodes, 1))
                    progress.update(
                        pct,
                        _s(32026).format(min(i + batch_size, total_episodes), total_episodes),
                    )
                    try:
                        resp = self._api.post_immediate(
                            "/api/scrobble/import", {"entries": batch}, timeout=55
                        )
                        imported_episodes += resp.get("imported", 0)
                    except Exception as exc:
                        xbmc.log(f"[PunchPlay] Episode batch error: {exc}", xbmc.LOGWARNING)

            progress.close()
            if cancelled:
                xbmc.log(
                    f"[PunchPlay] Library sync cancelled. "
                    f"Imported {imported_movies} movies, {imported_episodes} episodes before cancel.",
                    xbmc.LOGINFO,
                )
            else:
                msg = _s(32027).format(imported_movies, imported_episodes)
                xbmcgui.Dialog().notification("PunchPlay", msg, xbmcgui.NOTIFICATION_INFO, 6000)
                xbmc.log(f"[PunchPlay] Library sync: {msg}", xbmc.LOGINFO)

        except Exception as exc:
            try:
                progress.close()
            except Exception:
                pass
            xbmc.log(f"[PunchPlay] Library sync failed: {exc}", xbmc.LOGWARNING)
            xbmcgui.Dialog().notification(
                "PunchPlay", _s(32028).format(str(exc)[:80]),
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
