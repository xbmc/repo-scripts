"""
player.py — xbmc.Player subclass that intercepts playback events.

Events handled:
  onAVStarted        → POST /scrobble/start
  onPlayBackPaused   → POST /scrobble/pause
  onPlayBackResumed  → POST /scrobble/resume
  onPlayBackStopped  → POST /scrobble/stop  (+ watched flag if threshold met)
  onPlayBackEnded    → POST /scrobble/stop  (+ watched flag)

A heartbeat thread fires every N seconds during active playback and POSTs
/scrobble/progress.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from typing import Any

import xbmc
import xbmcgui

from constants import (
    HEARTBEAT_INTERVAL_SECS,
    NOTIFICATION_TITLE,
    SCROBBLE_PAUSE_ENDPOINT,
    SCROBBLE_PROGRESS_ENDPOINT,
    SCROBBLE_RATE_ENDPOINT,
    SCROBBLE_RESUME_ENDPOINT,
    SCROBBLE_START_ENDPOINT,
    SCROBBLE_STOP_ENDPOINT,
    STOP_COMPLETE_GRACE_SECS,
    get_addon,
    get_addon_path,
    get_addon_version,
    localize,
)


def _normalise_key_part(value: Any) -> str:
    return str(value or "").strip().lower()


def build_rating_suppression_keys(metadata: dict[str, Any]) -> dict[str, str]:
    media_type = metadata.get("media_type", "movie")
    canonical_id = (
        metadata.get("punchplay_id")
        or metadata.get("tmdb_id")
        or metadata.get("tvdb_id")
        or metadata.get("imdb_id")
    )
    title = _normalise_key_part(metadata.get("title"))
    year = _normalise_key_part(metadata.get("year"))
    season = _normalise_key_part(metadata.get("season"))
    episode = _normalise_key_part(metadata.get("episode"))
    absolute_episode = _normalise_key_part(metadata.get("absolute_episode"))

    keys = {
        "title": "title:{0}:{1}:{2}:{3}:{4}".format(
            media_type,
            canonical_id or title,
            year,
            season,
            episode or absolute_episode,
        )
    }
    if media_type == "episode":
        keys["show"] = "show:{0}:{1}:{2}".format(
            canonical_id or title,
            title,
            year,
        )
    return keys


def has_reliable_rating_identity(metadata: dict[str, Any]) -> bool:
    return any(metadata.get(key) for key in ("punchplay_id", "tmdb_id", "tvdb_id", "imdb_id"))


class PunchPlayPlayer(xbmc.Player):
    def __init__(self, api, cache) -> None:
        super().__init__()
        self._api = api
        self._cache = cache
        self._client_version = get_addon_version()

        # State for the currently tracked item.
        self._metadata: dict[str, Any] | None = None
        self._is_playing: bool = False
        self._playback_session_id: str | None = None
        self._stop_emitted: bool = False

        # Last known playback position — used as fallback in _emit_stop when
        # getTime()/getTotalTime() throw because the player has already closed.
        self._last_position: float = 0.0
        self._last_duration: float = 0.0

        # Heartbeat thread management.
        self._hb_thread: threading.Thread | None = None
        self._hb_stop = threading.Event()

    # ------------------------------------------------------------------
    # Settings helpers
    # ------------------------------------------------------------------

    def _settings(self) -> dict[str, Any]:
        addon = get_addon()
        anime_setting = addon.getSetting("anime_episode_format") or "0"
        anime_format_map = {
            "0": "auto",
            "1": "season_episode",
            "2": "absolute",
            "auto": "auto",
            "season_episode": "season_episode",
            "absolute": "absolute",
        }
        return {
            "watched_threshold": addon.getSettingInt("watched_threshold") / 100.0,
            "min_length_secs": addon.getSettingInt("min_length") * 60,
            "heartbeat_interval": HEARTBEAT_INTERVAL_SECS,
            "anime_episode_format": anime_format_map.get(anime_setting, "auto"),
            "scrobble_movies": addon.getSettingBool("scrobble_movies"),
            "scrobble_tv": addon.getSettingBool("scrobble_tv"),
            "scrobble_anime": addon.getSettingBool("scrobble_anime"),
            "show_notifications": addon.getSettingBool("show_notifications"),
            "notify_during_playback": addon.getSettingBool("notify_during_playback"),
            "rate_after_watching": addon.getSettingBool("rate_after_watching"),
            "rating_prompt_delay": addon.getSettingInt("rating_prompt_delay"),
        }

    def _notify(self, message: str, settings: dict[str, Any]) -> None:
        """Show a Kodi notification, respecting the user's notification settings."""
        if not settings["show_notifications"]:
            return
        if not settings["notify_during_playback"] and self.isPlayingVideo():
            return
        xbmcgui.Dialog().notification(
            NOTIFICATION_TITLE,
            message,
            xbmcgui.NOTIFICATION_INFO,
            4000,
        )

    def _should_track(
        self,
        metadata: dict[str, Any],
        settings: dict[str, Any],
        anime: bool = False,
    ) -> bool:
        media_type = metadata.get("media_type", "")
        if media_type == "movie" and not settings["scrobble_movies"]:
            return False
        if media_type == "episode":
            if anime and not settings["scrobble_anime"]:
                return False
            if not anime and not settings["scrobble_tv"]:
                return False
        return True

    # ------------------------------------------------------------------
    # Payload builder
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        metadata: dict[str, Any],
        position: float,
        duration: float,
    ) -> dict[str, Any]:
        progress = round(position / duration, 4) if duration > 0 else 0.0
        payload: dict[str, Any] = {
            "event_id": str(uuid.uuid4()),
            "media_type": metadata.get("media_type", "movie"),
            "title": metadata.get("title", ""),
            "progress": progress,
            "duration_seconds": int(duration),
            "position_seconds": int(position),
            "device_id": self._api.device_id,
            "playback_session_id": self._playback_session_id,
            "event_created_at": int(time.time() * 1000),
            "client_version": self._client_version,
        }
        for field in (
            "year",
            "imdb_id",
            "tmdb_id",
            "tvdb_id",
            "punchplay_id",
            "season",
            "episode",
            "episode_end",
            "absolute_episode",
            "episode_title",
            "raw_filename",
            "identify_source",
            "identify_confidence",
        ):
            val = metadata.get(field)
            if val is not None:
                payload[field] = val
        if metadata.get("multi_episode"):
            payload["multi_episode"] = True
        if metadata.get("anime"):
            payload["anime"] = True
        return payload

    def _capture_position(self) -> tuple[float, float] | None:
        """Read and cache the current Kodi playback position."""
        try:
            position = self.getTime()
            duration = self.getTotalTime()
        except Exception:
            return None
        self._last_position = position
        self._last_duration = duration
        return position, duration

    # ------------------------------------------------------------------
    # Heartbeat thread
    # ------------------------------------------------------------------

    def _start_heartbeat(self) -> None:
        self._stop_heartbeat()
        self._hb_stop.clear()
        self._hb_thread = threading.Thread(
            target=self._heartbeat_loop, name="PunchPlayHeartbeat", daemon=True
        )
        self._hb_thread.start()

    def _stop_heartbeat(self) -> None:
        self._hb_stop.set()
        if self._hb_thread and self._hb_thread.is_alive():
            self._hb_thread.join(timeout=3)
        self._hb_thread = None

    def _heartbeat_loop(self) -> None:
        while not self._hb_stop.is_set():
            settings = self._settings()
            interval = max(1, settings["heartbeat_interval"])

            # Sleep in short slices so we can react to stop quickly.
            slept = 0.0
            while slept < interval:
                if self._hb_stop.is_set():
                    return
                if self._is_playing and self._metadata is not None:
                    self._capture_position()
                time.sleep(0.5)
                slept += 0.5

            if not self._is_playing or self._metadata is None:
                continue

            try:
                captured = self._capture_position()
                if captured is None:
                    continue
                position, duration = captured
                settings = self._settings()  # re-read in case changed

                if duration < settings["min_length_secs"]:
                    continue

                payload = self._build_payload(self._metadata, position, duration)
                xbmc.log(
                    f"[PunchPlay] Heartbeat — {payload['progress']:.1%} "
                    f"({payload['position_seconds']}s / {payload['duration_seconds']}s)",
                    xbmc.LOGDEBUG,
                )
                self._api.post(SCROBBLE_PROGRESS_ENDPOINT, payload)

            except Exception as exc:
                xbmc.log(f"[PunchPlay] Heartbeat error: {exc}", xbmc.LOGWARNING)
                # Always stop the heartbeat on any unhandled error — avoids
                # the thread spinning silently if the player enters a bad state.
                self._hb_stop.set()
                xbmc.log("[PunchPlay] Heartbeat stopping due to error", xbmc.LOGINFO)
                return

    # ------------------------------------------------------------------
    # Playback events
    # ------------------------------------------------------------------

    def onAVStarted(self) -> None:  # type: ignore[override]
        try:
            if not self.isPlayingVideo():
                return

            if not self._api.is_authenticated():
                return

            settings = self._settings()

            # If something was already tracked (e.g. immediate next play),
            # close the previous session cleanly.
            if self._metadata is not None:
                self._handle_stop()

            path = self.getPlayingFile()
            info_tag = self.getVideoInfoTag()
            duration = self.getTotalTime()

            # Identify the media.
            from identifier import identify, is_anime

            metadata = identify(
                list_item_path=path,
                info_tag=info_tag,
                cache=self._cache,
                api_client=self._api,
                duration_seconds=int(duration),
                anime_preference=settings["anime_episode_format"],
            )

            if not metadata or not metadata.get("title"):
                xbmc.log("[PunchPlay] Could not identify media — skipping", xbmc.LOGINFO)
                return

            # Duration filter.
            if duration < settings["min_length_secs"]:
                xbmc.log(
                    f"[PunchPlay] File too short ({duration:.0f}s < "
                    f"{settings['min_length_secs']}s) — skipping",
                    xbmc.LOGDEBUG,
                )
                return

            # Content-type filter.
            anime = bool(metadata.get("anime")) or is_anime(info_tag, path=path, metadata=metadata)
            if not self._should_track(metadata, settings, anime=anime):
                xbmc.log(
                    f"[PunchPlay] Scrobbling disabled for "
                    f"{'anime' if anime else metadata.get('media_type')} — skipping",
                    xbmc.LOGDEBUG,
                )
                return

            self._metadata = metadata
            self._is_playing = True
            self._playback_session_id = str(uuid.uuid4())
            self._stop_emitted = False
            self._last_position = 0.0
            self._last_duration = 0.0

            captured = self._capture_position()
            position = captured[0] if captured else 0.0
            payload = self._build_payload(metadata, position, duration)

            xbmc.log(
                f"[PunchPlay] Started: {metadata.get('title')!r} "
                f"(type={metadata.get('media_type')})",
                xbmc.LOGINFO,
            )

            # Attempt to flush any offline queue before the new event.
            self._api.flush_queue()
            self._api.post(SCROBBLE_START_ENDPOINT, payload)
            self._start_heartbeat()

        except Exception as exc:
            xbmc.log(f"[PunchPlay] onAVStarted error: {exc}", xbmc.LOGWARNING)

    def onPlayBackPaused(self) -> None:  # type: ignore[override]
        if self._metadata is None or not self._is_playing:
            return
        try:
            self._is_playing = False
            self._stop_heartbeat()
            captured = self._capture_position()
            if captured is None:
                position = self._last_position
                duration = self._last_duration
            else:
                position, duration = captured
            payload = self._build_payload(self._metadata, position, duration)
            xbmc.log(f"[PunchPlay] Paused at {position:.0f}s", xbmc.LOGDEBUG)
            self._api.post(SCROBBLE_PAUSE_ENDPOINT, payload)
        except Exception as exc:
            xbmc.log(f"[PunchPlay] onPlayBackPaused error: {exc}", xbmc.LOGDEBUG)

    def onPlayBackResumed(self) -> None:  # type: ignore[override]
        if self._metadata is None:
            return
        try:
            self._is_playing = True
            captured = self._capture_position()
            if captured is None:
                position = self._last_position
                duration = self._last_duration
            else:
                position, duration = captured
            payload = self._build_payload(self._metadata, position, duration)
            xbmc.log(f"[PunchPlay] Resumed at {position:.0f}s", xbmc.LOGDEBUG)
            self._api.post(SCROBBLE_RESUME_ENDPOINT, payload)
            self._start_heartbeat()
        except Exception as exc:
            xbmc.log(f"[PunchPlay] onPlayBackResumed error: {exc}", xbmc.LOGDEBUG)

    def onPlayBackStopped(self) -> None:  # type: ignore[override]
        self._handle_stop()

    def onPlayBackEnded(self) -> None:  # type: ignore[override]
        self._handle_stop()

    # ------------------------------------------------------------------
    # Internal stop logic
    # ------------------------------------------------------------------

    def _emit_stop(self, settings: dict[str, Any]) -> None:
        """Post a stop event for the current item (without clearing state)."""
        if self._metadata is None:
            return
        try:
            captured = self._capture_position()
            if captured is None:
                # Player already closed — use last cached values.
                position = self._last_position
                duration = self._last_duration
            else:
                position, duration = captured
            if duration > 0 and position + STOP_COMPLETE_GRACE_SECS >= duration:
                position = duration
            payload = self._build_payload(self._metadata, position, duration)
            payload["watched_threshold"] = settings["watched_threshold"]
            watched = duration > 0 and payload["progress"] >= settings["watched_threshold"]
            payload["watched"] = watched
            if watched:
                xbmc.log(
                    f"[PunchPlay] Watched threshold met "
                    f"({payload['progress']:.0%} >= {settings['watched_threshold']:.0%})",
                    xbmc.LOGINFO,
                )
            xbmc.log(
                f"[PunchPlay] Stop: {self._metadata.get('title')!r} "
                f"pos={payload['position_seconds']}s",
                xbmc.LOGINFO,
            )
            if self._playback_session_id and self._cache is not None:
                self._cache.delete_pending_scrobbles_for_session(self._playback_session_id)
            stop_resp = self._api.post(SCROBBLE_STOP_ENDPOINT, payload)
            if watched:
                _s = localize
                title = self._metadata.get("title", "")
                media_type = self._metadata.get("media_type", "movie")
                if media_type == "episode":
                    season = self._metadata.get("season")
                    episode = self._metadata.get("episode")
                    if isinstance(season, int) and isinstance(episode, int):
                        msg = _s(32014).format(title, f"{season:02d}", f"{episode:02d}")
                    else:
                        msg = _s(32013).format(title)
                else:
                    msg = _s(32013).format(title)
                self._notify(msg, settings)

                # Offer the rating dialog if enabled and not already playing
                # something else (e.g. immediate next episode).
                if not settings["rate_after_watching"]:
                    xbmc.log("[PunchPlay] Rating disabled in settings", xbmc.LOGINFO)
                else:
                    merged_metadata = dict(self._metadata)
                    if stop_resp and isinstance(stop_resp, dict):
                        for key in ("tmdb_id", "tvdb_id", "imdb_id", "punchplay_id"):
                            if stop_resp.get(key) is not None:
                                merged_metadata[key] = stop_resp[key]
                    self._maybe_prompt_for_rating(merged_metadata, settings, stop_resp=stop_resp)
        except Exception as exc:
            xbmc.log(f"[PunchPlay] Stop emit error: {exc}", xbmc.LOGDEBUG)

    # ------------------------------------------------------------------
    # Rating dialog
    # ------------------------------------------------------------------

    def _maybe_prompt_for_rating(
        self,
        metadata: dict[str, Any],
        settings: dict[str, Any],
        *,
        stop_resp: dict[str, Any] | None,
    ) -> None:
        if self.isPlayingVideo():
            xbmc.log("[PunchPlay] Skipping rating — another video is playing", xbmc.LOGINFO)
            return
        if stop_resp is None and not has_reliable_rating_identity(metadata):
            xbmc.log("[PunchPlay] Skipping rating — no reliable canonical ID", xbmc.LOGINFO)
            return

        suppression_keys = build_rating_suppression_keys(metadata)
        if self._cache is not None:
            if self._cache.has_rating_suppression(suppression_keys["title"]):
                xbmc.log("[PunchPlay] Rating suppressed for title", xbmc.LOGINFO)
                return
            show_key = suppression_keys.get("show")
            if show_key and self._cache.has_rating_suppression(show_key):
                xbmc.log("[PunchPlay] Rating suppressed for show", xbmc.LOGINFO)
                return

        delay_secs = max(0, int(settings.get("rating_prompt_delay") or 0))
        if delay_secs:
            monitor = xbmc.Monitor()
            deadline = time.monotonic() + delay_secs
            while time.monotonic() < deadline:
                if monitor.abortRequested():
                    xbmc.log("[PunchPlay] Skipping rating — Kodi is shutting down", xbmc.LOGINFO)
                    return
                if self.isPlayingVideo():
                    xbmc.log("[PunchPlay] Skipping rating — autoplay resumed", xbmc.LOGINFO)
                    return
                monitor.waitForAbort(0.25)

        title = metadata.get("title", "")
        _s = localize
        options = [
            _s(32093),
            _s(32094),
            _s(32095),
        ]
        option_map = ["rate_now", "later", "never_title"]
        if metadata.get("media_type") == "episode":
            options.append(_s(32096))
            option_map.append("never_show")
        options.append(_s(32097))
        option_map.append("disable")

        choice = xbmcgui.Dialog().select(
            _s(32092).format(title),
            options,
        )
        if choice < 0:
            return
        action = option_map[choice]
        if action == "later":
            return
        if action == "never_title":
            if self._cache is not None:
                self._cache.set_rating_suppression(suppression_keys["title"], "title")
            return
        if action == "never_show":
            if self._cache is not None and suppression_keys.get("show"):
                self._cache.set_rating_suppression(suppression_keys["show"], "show")
            return
        if action == "disable":
            get_addon().setSettingBool("rate_after_watching", False)
            return

        self._show_rating_dialog(metadata)

    def _show_rating_dialog(self, metadata: dict[str, Any]) -> None:
        """Show a 1–10 rating dialog after a completed scrobble."""
        try:
            _s = localize
            media_type = metadata.get("media_type", "movie")
            title = metadata.get("title", "")

            # Build heading: "Rate Inception" or "Rate Breaking Bad S01E02"
            if media_type == "episode":
                season = metadata.get("season")
                episode = metadata.get("episode")
                if isinstance(season, int) and isinstance(episode, int):
                    heading = _s(32022).format(title, f"{season:02d}", f"{episode:02d}")
                else:
                    heading = _s(32021).format(title)
            else:
                    heading = _s(32021).format(title)

            from rating_dialog import RatingDialog

            bg_path = os.path.join(get_addon_path(), "resources", "media", "background.png")
            rate_dlg = RatingDialog(
                bg_path=bg_path,
                heading=heading,
                initial=5,
            )
            rate_dlg.doModal()

            if not rate_dlg.confirmed:
                del rate_dlg
                return

            rating = rate_dlg.rating
            del rate_dlg

            rate_payload: dict[str, Any] = {
                "media_type": media_type,
                "rating": rating,
                "event_id": str(uuid.uuid4()),
                "client_version": self._client_version,
            }
            for key in (
                "tmdb_id",
                "tvdb_id",
                "imdb_id",
                "punchplay_id",
                "season",
                "episode",
                "absolute_episode",
            ):
                if metadata.get(key) is not None:
                    rate_payload[key] = metadata[key]

            self._api.post_immediate(SCROBBLE_RATE_ENDPOINT, rate_payload)
            xbmc.log(
                f"[PunchPlay] Rated {title!r} {rating}/10",
                xbmc.LOGINFO,
            )
        except Exception as exc:
            xbmc.log(f"[PunchPlay] Rating dialog error: {exc}", xbmc.LOGDEBUG)

    def _handle_stop(self) -> None:
        if self._metadata is None or self._stop_emitted:
            return
        try:
            self._stop_emitted = True
            self._is_playing = False
            self._stop_heartbeat()
            self._emit_stop(self._settings())
        finally:
            self._metadata = None
            self._playback_session_id = None
            self._stop_emitted = False

    # ------------------------------------------------------------------
    # Cleanup (called on service shutdown)
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        self._is_playing = False
        self._stop_heartbeat()
        self._metadata = None
        self._playback_session_id = None
        self._stop_emitted = False
