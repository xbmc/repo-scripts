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

import threading
import time
from typing import Any

import xbmc
import xbmcaddon
import xbmcgui

_ADDON_ID = "script.punchplay"
_VERSION = "1.0.0"


class PunchPlayPlayer(xbmc.Player):
    def __init__(self, api, cache) -> None:
        super().__init__()
        self._api = api
        self._cache = cache

        # State for the currently tracked item.
        self._metadata: dict[str, Any] | None = None
        self._is_playing: bool = False

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
        addon = xbmcaddon.Addon(_ADDON_ID)
        return {
            "watched_threshold": addon.getSettingInt("watched_threshold") / 100.0,
            "min_length_secs": addon.getSettingInt("min_length") * 60,
            "heartbeat_interval": addon.getSettingInt("heartbeat_interval"),
            "scrobble_movies": addon.getSettingBool("scrobble_movies"),
            "scrobble_tv": addon.getSettingBool("scrobble_tv"),
            "scrobble_anime": addon.getSettingBool("scrobble_anime"),
            "show_notifications": addon.getSettingBool("show_notifications"),
            "notify_during_playback": addon.getSettingBool("notify_during_playback"),
        }

    def _notify(self, message: str, settings: dict[str, Any]) -> None:
        """Show a Kodi notification, respecting the user's notification settings."""
        if not settings["show_notifications"]:
            return
        if not settings["notify_during_playback"] and self.isPlayingVideo():
            return
        xbmcgui.Dialog().notification(
            "PunchPlay",
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
            "media_type": metadata.get("media_type", "movie"),
            "title": metadata.get("title", ""),
            "progress": progress,
            "duration_seconds": int(duration),
            "position_seconds": int(position),
            "device_id": self._api.device_id,
            "client_version": _VERSION,
        }
        for field in ("year", "imdb_id", "tmdb_id", "tvdb_id", "season", "episode", "raw_filename"):
            val = metadata.get(field)
            if val is not None:
                payload[field] = val
        return payload

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
                time.sleep(0.5)
                slept += 0.5

            if not self._is_playing or self._metadata is None:
                continue

            try:
                position = self.getTime()
                duration = self.getTotalTime()
                self._last_position = position
                self._last_duration = duration
                settings = self._settings()  # re-read in case changed

                if duration < settings["min_length_secs"]:
                    continue

                payload = self._build_payload(self._metadata, position, duration)
                xbmc.log(
                    f"[PunchPlay] Heartbeat — {payload['progress']:.1%} "
                    f"({payload['position_seconds']}s / {payload['duration_seconds']}s)",
                    xbmc.LOGDEBUG,
                )
                self._api.post("/api/scrobble/progress", payload)

            except Exception as exc:
                xbmc.log(f"[PunchPlay] Heartbeat error: {exc}", xbmc.LOGWARNING)
                # If the player is no longer valid, stop the heartbeat loop
                # rather than spinning silently.
                if not self.isPlayingVideo():
                    xbmc.log("[PunchPlay] Heartbeat stopping — player no longer active", xbmc.LOGINFO)
                    return

    # ------------------------------------------------------------------
    # Playback events
    # ------------------------------------------------------------------

    def onAVStarted(self) -> None:  # type: ignore[override]
        try:
            if not self.isPlayingVideo():
                return

            settings = self._settings()

            # If something was already tracked (e.g. immediate next play),
            # close the previous session cleanly.
            if self._metadata is not None:
                self._emit_stop(settings)

            path = self.getPlayingFile()
            info_tag = self.getVideoInfoTag()

            # Identify the media.
            from identifier import identify, is_anime

            metadata = identify(
                list_item_path=path,
                info_tag=info_tag,
                cache=self._cache,
            )

            if not metadata or not metadata.get("title"):
                xbmc.log("[PunchPlay] Could not identify media — skipping", xbmc.LOGINFO)
                return

            # Duration filter.
            duration = self.getTotalTime()
            if duration < settings["min_length_secs"]:
                xbmc.log(
                    f"[PunchPlay] File too short ({duration:.0f}s < "
                    f"{settings['min_length_secs']}s) — skipping",
                    xbmc.LOGDEBUG,
                )
                return

            # Content-type filter.
            anime = is_anime(info_tag)
            if not self._should_track(metadata, settings, anime=anime):
                xbmc.log(
                    f"[PunchPlay] Scrobbling disabled for "
                    f"{'anime' if anime else metadata.get('media_type')} — skipping",
                    xbmc.LOGDEBUG,
                )
                return

            self._metadata = metadata
            self._is_playing = True

            position = self.getTime()
            payload = self._build_payload(metadata, position, duration)

            xbmc.log(
                f"[PunchPlay] Started: {metadata.get('title')!r} "
                f"(type={metadata.get('media_type')})",
                xbmc.LOGINFO,
            )

            # Attempt to flush any offline queue before the new event.
            self._api.flush_queue()
            self._api.post("/api/scrobble/start", payload)
            self._start_heartbeat()

        except Exception as exc:
            xbmc.log(f"[PunchPlay] onAVStarted error: {exc}", xbmc.LOGWARNING)

    def onPlayBackPaused(self) -> None:  # type: ignore[override]
        if self._metadata is None or not self._is_playing:
            return
        try:
            self._is_playing = False
            self._stop_heartbeat()
            position = self.getTime()
            duration = self.getTotalTime()
            self._last_position = position
            self._last_duration = duration
            payload = self._build_payload(self._metadata, position, duration)
            xbmc.log(f"[PunchPlay] Paused at {position:.0f}s", xbmc.LOGDEBUG)
            self._api.post("/api/scrobble/pause", payload)
        except Exception as exc:
            xbmc.log(f"[PunchPlay] onPlayBackPaused error: {exc}", xbmc.LOGDEBUG)

    def onPlayBackResumed(self) -> None:  # type: ignore[override]
        if self._metadata is None:
            return
        try:
            self._is_playing = True
            position = self.getTime()
            duration = self.getTotalTime()
            payload = self._build_payload(self._metadata, position, duration)
            xbmc.log(f"[PunchPlay] Resumed at {position:.0f}s", xbmc.LOGDEBUG)
            self._api.post("/api/scrobble/resume", payload)
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
            try:
                position = self.getTime()
                duration = self.getTotalTime()
                self._last_position = position
                self._last_duration = duration
            except Exception:
                # Player already closed — use last cached values.
                position = self._last_position
                duration = self._last_duration
            payload = self._build_payload(self._metadata, position, duration)
            watched = duration > 0 and payload["progress"] >= settings["watched_threshold"]
            if watched:
                payload["watched"] = True
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
            self._api.post("/api/scrobble/stop", payload)
            if watched:
                _s = xbmcaddon.Addon(_ADDON_ID).getLocalizedString
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
        except Exception as exc:
            xbmc.log(f"[PunchPlay] Stop emit error: {exc}", xbmc.LOGDEBUG)

    def _handle_stop(self) -> None:
        if self._metadata is None:
            return
        try:
            self._is_playing = False
            self._stop_heartbeat()
            self._emit_stop(self._settings())
        finally:
            self._metadata = None

    # ------------------------------------------------------------------
    # Cleanup (called on service shutdown)
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        self._is_playing = False
        self._stop_heartbeat()
        self._metadata = None
