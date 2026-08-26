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
import queue
import threading
import time
import uuid
from typing import Any, Callable, NamedTuple

import xbmc
import xbmcgui

from constants import (
    HEARTBEAT_INTERVAL_SECS,
    HEARTBEAT_MAX_CONSECUTIVE_ERRORS,
    LIVE_SYNC_ECHO_SUPPRESS_SECS,
    NOTIFICATION_TITLE,
    POST_QUEUE_MAX_ITEMS,
    POST_QUEUE_PUT_TIMEOUT_SECS,
    POST_WORKER_JOIN_TIMEOUT_SECS,
    SCROBBLE_IMPORT_ENDPOINT,
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
        # None of punchplay_id/tmdb_id/tvdb_id/imdb_id identify the show —
        # they come from Kodi's per-episode uniqueid (or the backend's
        # per-episode title record), so `canonical_id` differs from one
        # episode to the next just like the old per-episode `year` did.
        # `title` is the one field that's already show-level here: Kodi's
        # info tag reports the show's title for every episode
        # (getTVShowTitle()), not the episode's own title, so it's the only
        # value in this metadata that's actually stable across a show.
        keys["show"] = "show:{0}".format(title)
    return keys


def has_reliable_rating_identity(metadata: dict[str, Any]) -> bool:
    return any(metadata.get(key) for key in ("punchplay_id", "tmdb_id", "tvdb_id", "imdb_id"))


class _PostJob(NamedTuple):
    """A queued scrobble post. `endpoint`/`payload` describe the network
    write so a job that never got to run can still be persisted to the
    offline queue at shutdown; `run` is what the worker actually executes.

    `offline_fallback`, if set, runs instead of being silently dropped when
    the post queue is full — it must never attempt a real network call
    (it runs on whatever thread hit queue.Full, which must not block), only
    cheap local work plus persisting to the offline queue for later replay.
    """

    endpoint: str
    payload: dict[str, Any]
    auth_generation: int
    run: Callable[[], None]
    offline_fallback: Callable[[], None] | None = None


# Not a real endpoint — marks a queue-drain job (see dispatch_flush) so
# _persist_unsent_queue can recognise and skip it instead of persisting a
# bogus pending_scrobbles row with this as its "endpoint".
_FLUSH_QUEUE_SENTINEL = "__internal_flush_offline_queue__"


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
        self._playback_auth_generation: int | None = None
        self._stop_emitted: bool = False

        # Last known playback position — used as fallback in _emit_stop when
        # getTime()/getTotalTime() throw because the player has already closed.
        self._last_position: float = 0.0
        self._last_duration: float = 0.0

        # Heartbeat thread management.
        self._hb_thread: threading.Thread | None = None
        self._hb_stop = threading.Event()

        # Scrobble posts run on a single worker thread: Kodi's player
        # callbacks must never block on the network, and one consumer keeps
        # start → progress → pause → resume → stop in order.
        self._post_queue: queue.Queue = queue.Queue(maxsize=POST_QUEUE_MAX_ITEMS)
        self._post_thread: threading.Thread | None = None
        self._post_thread_lock = threading.Lock()
        self._post_state_lock = threading.Lock()
        self._active_post_job: _PostJob | None = None
        # Sessions in this set have at least one event in the durable queue.
        # Every later event for the same session must stay durable until a
        # complete flush succeeds, otherwise it could overtake the older row.
        self._deferred_sessions_lock = threading.Lock()
        self._deferred_sessions: set[str] = set()
        self._deferred_sessions_revision = 0
        # Set only after shutdown's grace period expires. It prevents the
        # worker from taking another queued job while cleanup snapshots the
        # active job and drains the backlog to SQLite.
        self._post_abandon = threading.Event()

        # Pending rating prompt — queued by the player callback thread and
        # drained by the service loop so modal dialogs never block Kodi's
        # player callbacks.
        self._rating_lock = threading.Lock()
        self._pending_rating: dict[str, Any] | None = None

        # Library items played recently, as (item_type, dbid, monotonic).
        # Kodi bumps their playcount when playback finishes; live watched
        # sync must treat those OnUpdate events as echoes of our own stop
        # scrobble, not manual toggles.
        self._library_items_lock = threading.Lock()
        self._recent_library_items: list[tuple[str, int, float]] = []
        self._current_library_item: tuple[str, int] | None = None

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
        rating_scope_setting = addon.getSetting("rating_prompt_scope") or "1"
        rating_scope_map = {
            "0": "movies",
            "1": "all",
            "movies": "movies",
            "all": "all",
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
            "rating_prompt_scope": rating_scope_map.get(
                rating_scope_setting,
                "all",
            ),
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

    def _remember_library_item(self, info_tag) -> None:
        try:
            dbid = info_tag.getDbId()
            media_type = (info_tag.getMediaType() or "").lower()
        except (AttributeError, RuntimeError):
            return
        if not isinstance(dbid, int) or dbid <= 0:
            return
        if media_type not in ("movie", "episode"):
            return
        self._current_library_item = (media_type, dbid)
        self._stamp_library_item(media_type, dbid)

    def _stamp_library_item(self, media_type: str, dbid: int) -> None:
        now = time.monotonic()
        cutoff = now - LIVE_SYNC_ECHO_SUPPRESS_SECS
        with self._library_items_lock:
            self._recent_library_items = [
                item
                for item in self._recent_library_items
                if item[2] >= cutoff and (item[0], item[1]) != (media_type, dbid)
            ]
            self._recent_library_items.append((media_type, dbid, now))

    def recent_library_items(self) -> list[tuple[str, int, float]]:
        """Recently played library items — consumed by live watched sync."""
        cutoff = time.monotonic() - LIVE_SYNC_ECHO_SUPPRESS_SECS
        with self._library_items_lock:
            self._recent_library_items = [
                item for item in self._recent_library_items if item[2] >= cutoff
            ]
            return list(self._recent_library_items)

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
    # Post worker thread
    # ------------------------------------------------------------------

    def _ensure_post_worker(self) -> None:
        with self._post_thread_lock:
            if self._post_thread is not None and self._post_thread.is_alive():
                return
            self._post_thread = threading.Thread(
                target=self._post_worker, name="PunchPlayPost", daemon=True
            )
            self._post_thread.start()

    def _post_worker(self) -> None:
        while True:
            # Hold the state lock across dequeue + active assignment. Cleanup
            # can therefore never observe a job in the tiny gap where it has
            # left the queue but is not yet recorded as in flight. The short
            # timeout bounds how long cleanup can wait when the queue is idle.
            with self._post_state_lock:
                if self._post_abandon.is_set():
                    return
                try:
                    job = self._post_queue.get(timeout=0.25)
                except queue.Empty:
                    continue
                if job is not None:
                    self._active_post_job = job
            if job is None:  # shutdown sentinel
                self._post_queue.task_done()
                return
            try:
                if job.auth_generation != self._api.auth_generation:
                    xbmc.log(
                        f"[PunchPlay] Discarding stale queued post {job.endpoint} "
                        "after logout",
                        xbmc.LOGDEBUG,
                    )
                else:
                    job.run()
            except Exception as exc:
                xbmc.log(f"[PunchPlay] Post worker error: {exc}", xbmc.LOGWARNING)
            finally:
                with self._post_state_lock:
                    if self._active_post_job is job:
                        self._active_post_job = None
                    should_abandon = self._post_abandon.is_set()
                self._post_queue.task_done()
            if should_abandon:
                return

    def _dispatch(self, job: _PostJob) -> None:
        """Hand *job* to the worker thread.  Never raises."""
        self._ensure_post_worker()
        try:
            # A short bounded wait beats a 15s network timeout on the callback
            # thread, and still lets a briefly backed-up queue drain.
            self._post_queue.put(job, timeout=POST_QUEUE_PUT_TIMEOUT_SECS)
        except queue.Full:
            if job.offline_fallback is not None:
                try:
                    job.offline_fallback()
                except Exception as exc:
                    xbmc.log(
                        f"[PunchPlay] Post queue full — offline fallback for "
                        f"{job.endpoint} failed: {exc}",
                        xbmc.LOGWARNING,
                    )
                else:
                    xbmc.log(
                        f"[PunchPlay] Post queue full — ran offline fallback for "
                        f"{job.endpoint}",
                        xbmc.LOGWARNING,
                    )
                return
            xbmc.log(
                "[PunchPlay] Post queue full — dropping event to keep playback smooth",
                xbmc.LOGWARNING,
            )

    def _mark_session_deferred(self, session_id: str | None) -> None:
        if not session_id:
            return
        with self._deferred_sessions_lock:
            self._deferred_sessions.add(session_id)
            self._deferred_sessions_revision += 1

    def _session_is_deferred(self, session_id: str | None) -> bool:
        if not session_id:
            return False
        with self._deferred_sessions_lock:
            return session_id in self._deferred_sessions

    def _clear_deferred_sessions(self) -> None:
        with self._deferred_sessions_lock:
            self._deferred_sessions.clear()
            self._deferred_sessions_revision += 1

    def _deferred_sessions_snapshot(self) -> int:
        with self._deferred_sessions_lock:
            return self._deferred_sessions_revision

    def _clear_deferred_sessions_if_unchanged(self, revision: int) -> None:
        """Clear only when no callback deferred another event mid-flush."""
        with self._deferred_sessions_lock:
            if self._deferred_sessions_revision == revision:
                self._deferred_sessions.clear()
                self._deferred_sessions_revision += 1

    def _preserve_playback_post(
        self,
        endpoint: str,
        payload: dict[str, Any],
        auth_generation: int,
        session_id: str | None,
    ) -> bool:
        """Keep a playback event behind the durable ordering barrier."""
        self._mark_session_deferred(session_id)
        return self._api.preserve_post_for_retry(
            endpoint,
            payload,
            expected_auth_generation=auth_generation,
        )

    def _flush_queue_safely(self, auth_generation: int) -> bool:
        """Return False for any failed drain so ordering callers fail shut."""
        try:
            return self._api.flush_queue(
                expected_auth_generation=auth_generation
            )
        except Exception as exc:
            xbmc.log(
                f"[PunchPlay] Offline queue flush failed: {exc}",
                xbmc.LOGWARNING,
            )
            return False

    def dispatch_flush(self) -> None:
        """Drain any offline-queued events on the post worker.

        This is the *only* code path that should call APIClient.flush_queue()
        — both the service loop's periodic 60s timer and the pre-start drain
        in onAVStarted go through this, so every flush lands on the same
        single-threaded worker as every playback post. A second, independent
        call site (e.g. the service loop calling flush_queue() directly on
        its own thread) could run concurrently with a worker-thread flush:
        both would see the same pending row via pending_scrobble_exists()
        before either deletes it, and the independent thread's request could
        land on the backend after a start the worker already sent, right
        back to the ordering bug this exists to prevent. Funnelling
        everything through the worker makes that impossible — flush and
        start jobs simply queue up and run in enqueue order, and the worker
        still executes them off Kodi's callback thread either way.
        """
        auth_generation = self._api.auth_generation

        def _run() -> None:
            revision = self._deferred_sessions_snapshot()
            if self._flush_queue_safely(auth_generation):
                self._clear_deferred_sessions_if_unchanged(revision)

        self._dispatch(
            _PostJob(
                _FLUSH_QUEUE_SENTINEL,
                {},
                auth_generation,
                _run,
            )
        )

    def dispatch_import(self, entries: list[dict[str, Any]]) -> None:
        """Push a batch of live watched-toggle entries through the post
        worker instead of blocking the caller's thread.

        The service loop used to call APIClient.post() for this directly on
        its own thread — up to REQUEST_TIMEOUT_SECS (longer after a 401
        retry) blocking that thread's login/logout handling, dispatch_flush's
        periodic trigger, and rating-prompt draining, while also writing into
        the offline queue from a thread independent of the post worker on
        failure. Routing it here keeps every network write in this addon on
        the single worker thread instead.
        """
        auth_generation = self._api.auth_generation

        def _run() -> None:
            resp = self._api.post(
                SCROBBLE_IMPORT_ENDPOINT,
                {"entries": entries},
                expected_auth_generation=auth_generation,
            )
            if resp is not None:
                xbmc.log(
                    "[PunchPlay] Watched toggle import: {0} imported, {1} "
                    "duplicate(s), {2} unmatched".format(
                        resp.get("imported", 0),
                        resp.get("skipped_duplicates", 0),
                        resp.get("unmatched", 0),
                    ),
                    xbmc.LOGINFO,
                )

        self._dispatch(
            _PostJob(
                SCROBBLE_IMPORT_ENDPOINT,
                {"entries": entries},
                auth_generation,
                _run,
                offline_fallback=lambda: self._api.preserve_post_for_retry(
                    SCROBBLE_IMPORT_ENDPOINT,
                    {"entries": entries},
                    expected_auth_generation=auth_generation,
                ),
            )
        )

    def _dispatch_start(self, payload: dict[str, Any]) -> None:
        """Drain the offline queue before allowing a new start to overtake it.

        Flush and start live in one worker job so queue saturation cannot
        split the barrier. If the job cannot be enqueued, or the drain stops
        on a transient failure, the start is persisted instead; later events
        for its session stay durable until a complete flush succeeds.
        """
        auth_generation = self._playback_auth_generation
        if auth_generation is None:
            xbmc.log(
                f"[PunchPlay] Discarding {SCROBBLE_START_ENDPOINT} without an "
                "active login session",
                xbmc.LOGDEBUG,
            )
            return
        session_id = str(payload.get("playback_session_id") or "") or None

        def _run() -> None:
            # A queue-full fallback from a later callback may already have
            # made this session durable before its start job reached the
            # worker. Persist the start too, then replay the whole session in
            # event_created_at order instead of sending the start last.
            if self._session_is_deferred(session_id):
                self._preserve_playback_post(
                    SCROBBLE_START_ENDPOINT,
                    payload,
                    auth_generation,
                    session_id,
                )
                revision = self._deferred_sessions_snapshot()
                if self._flush_queue_safely(auth_generation):
                    self._clear_deferred_sessions_if_unchanged(revision)
                return

            revision = self._deferred_sessions_snapshot()
            if not self._flush_queue_safely(auth_generation):
                # The old backlog is still live. Persist this start behind it
                # and keep every following event from overtaking either one.
                self._preserve_playback_post(
                    SCROBBLE_START_ENDPOINT,
                    payload,
                    auth_generation,
                    session_id,
                )
                return

            self._clear_deferred_sessions_if_unchanged(revision)
            response = self._api.post(
                SCROBBLE_START_ENDPOINT,
                payload,
                expected_auth_generation=auth_generation,
            )
            if response is None:
                self._mark_session_deferred(session_id)

        self._dispatch(
            _PostJob(
                SCROBBLE_START_ENDPOINT,
                payload,
                auth_generation,
                _run,
                offline_fallback=lambda: self._preserve_playback_post(
                    SCROBBLE_START_ENDPOINT,
                    payload,
                    auth_generation,
                    session_id,
                ),
            )
        )

    def _dispatch_post(self, endpoint: str, payload: dict[str, Any]) -> None:
        auth_generation = self._playback_auth_generation
        if auth_generation is None:
            xbmc.log(
                f"[PunchPlay] Discarding {endpoint} without an active login session",
                xbmc.LOGDEBUG,
            )
            return
        session_id = str(payload.get("playback_session_id") or "") or None

        def _run() -> None:
            if self._session_is_deferred(session_id):
                self._preserve_playback_post(
                    endpoint,
                    payload,
                    auth_generation,
                    session_id,
                )
                return
            response = self._api.post(
                endpoint,
                payload,
                expected_auth_generation=auth_generation,
            )
            if response is None:
                self._mark_session_deferred(session_id)

        self._dispatch(
            _PostJob(
                endpoint,
                payload,
                auth_generation,
                _run,
                offline_fallback=lambda: self._preserve_playback_post(
                    endpoint,
                    payload,
                    auth_generation,
                    session_id,
                ),
            )
        )

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
        consecutive_errors = 0
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
                self._dispatch_post(SCROBBLE_PROGRESS_ENDPOINT, payload)
                consecutive_errors = 0

            except Exception as exc:
                # Tolerate transient errors (a single bad settings read or
                # position capture) — one hiccup must not silence progress
                # updates for the rest of playback.  Only stop once the
                # player looks persistently broken.
                consecutive_errors += 1
                xbmc.log(
                    f"[PunchPlay] Heartbeat error "
                    f"({consecutive_errors}/{HEARTBEAT_MAX_CONSECUTIVE_ERRORS}): {exc}",
                    xbmc.LOGWARNING,
                )
                if consecutive_errors >= HEARTBEAT_MAX_CONSECUTIVE_ERRORS:
                    self._hb_stop.set()
                    xbmc.log(
                        "[PunchPlay] Heartbeat stopping after repeated errors",
                        xbmc.LOGINFO,
                    )
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
            auth_generation = self._api.auth_generation

            settings = self._settings()

            # If something was already tracked (e.g. immediate next play),
            # close the previous session cleanly.
            if self._metadata is not None:
                self._handle_stop()

            path = self.getPlayingFile()
            info_tag = self.getVideoInfoTag()
            duration = self.getTotalTime()

            # Remember the library dbid (if any) before content filters run,
            # so even untracked plays suppress their playcount echo.
            self._remember_library_item(info_tag)

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

            # Identification can involve network I/O. If the user logged out
            # while it was running, do not start a session for the old account.
            if (
                auth_generation != self._api.auth_generation
                or not self._api.is_authenticated()
            ):
                xbmc.log(
                    "[PunchPlay] Login changed during identification — skipping",
                    xbmc.LOGDEBUG,
                )
                return

            self._metadata = metadata
            self._is_playing = True
            self._playback_session_id = str(uuid.uuid4())
            self._playback_auth_generation = auth_generation
            self._stop_emitted = False
            self._last_position = 0.0
            self._last_duration = 0.0

            # A new tracked playback cancels any not-yet-shown rating prompt
            # (autoplay of the next episode).
            with self._rating_lock:
                self._pending_rating = None

            captured = self._capture_position()
            position = captured[0] if captured else 0.0
            payload = self._build_payload(metadata, position, duration)

            xbmc.log(
                f"[PunchPlay] Started: {metadata.get('title')!r} "
                f"(type={metadata.get('media_type')})",
                xbmc.LOGINFO,
            )

            # Drains the offline queue and posts the start as one atomic
            # worker job (see _dispatch_start) so a stale leftover event
            # can't land after this one, even under a full post queue. The
            # service loop also flushes the offline queue every 60s, through
            # dispatch_flush() on the same worker.
            self._dispatch_start(payload)
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
            self._dispatch_post(SCROBBLE_PAUSE_ENDPOINT, payload)
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
            self._dispatch_post(SCROBBLE_RESUME_ENDPOINT, payload)
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

    def _send_stop(
        self,
        *,
        payload: dict[str, Any],
        metadata: dict[str, Any],
        settings: dict[str, Any],
        session_id: str | None,
        auth_generation: int,
        watched: bool,
        attempt_network: bool = True,
    ) -> None:
        """
        Post the stop event and queue any rating prompt.  Runs on the post
        worker, so it may block on the network and on SQLite.  Shows no UI —
        the service loop drains the queued prompt and displays it.

        *attempt_network* is False when this is the offline fallback for a
        queue-full job, or when an earlier event from the same session is
        already durable. In both cases this goes straight to the offline
        queue. Everything else below (session cleanup and rating prompt)
        still needs to run, which is why the fallback comes through here.
        """
        if session_id and self._cache is not None:
            self._cache.delete_pending_scrobbles_for_session(session_id)

        if self._session_is_deferred(session_id):
            attempt_network = False

        if attempt_network:
            stop_resp = self._api.post(
                SCROBBLE_STOP_ENDPOINT,
                payload,
                expected_auth_generation=auth_generation,
            )
            if stop_resp is None:
                self._mark_session_deferred(session_id)
        else:
            self._preserve_playback_post(
                SCROBBLE_STOP_ENDPOINT,
                payload,
                auth_generation,
                session_id,
            )
            stop_resp = None

        # logout() invalidates all work from the previous account. The HTTP
        # request may already have completed, but its response must not create
        # a rating prompt that could later submit under a different login.
        if auth_generation != self._api.auth_generation:
            xbmc.log(
                "[PunchPlay] Discarding stop response after logout",
                xbmc.LOGDEBUG,
            )
            return

        if not watched:
            return
        if not settings["rate_after_watching"]:
            xbmc.log("[PunchPlay] Rating disabled in settings", xbmc.LOGINFO)
            return

        # The backend resolves canonical IDs we may not have had locally.
        merged_metadata = dict(metadata)
        if stop_resp and isinstance(stop_resp, dict):
            for key in ("tmdb_id", "tvdb_id", "imdb_id", "punchplay_id"):
                if stop_resp.get(key) is not None:
                    merged_metadata[key] = stop_resp[key]
        self._queue_rating_prompt(merged_metadata, settings, stop_resp=stop_resp)

    def _emit_stop(self, settings: dict[str, Any]) -> None:
        """Post a stop event for the current item (without clearing state)."""
        metadata = self._metadata
        auth_generation = self._playback_auth_generation
        if metadata is None or auth_generation is None:
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
            payload = self._build_payload(metadata, position, duration)
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
                f"[PunchPlay] Stop: {metadata.get('title')!r} "
                f"pos={payload['position_seconds']}s",
                xbmc.LOGINFO,
            )
            # Notify here, on the callback thread — Kodi wants UI calls off
            # background threads, and this is cheap.
            if watched:
                _s = localize
                title = metadata.get("title", "")
                media_type = metadata.get("media_type", "movie")
                if media_type == "episode":
                    season = metadata.get("season")
                    episode = metadata.get("episode")
                    if isinstance(season, int) and isinstance(episode, int):
                        msg = _s(32014).format(title, f"{season:02d}", f"{episode:02d}")
                    else:
                        msg = _s(32013).format(title)
                else:
                    msg = _s(32013).format(title)
                self._notify(msg, settings)

            # Snapshot everything the worker needs — _handle_stop clears this
            # instance state as soon as we return.
            metadata = dict(metadata)
            session_id = self._playback_session_id
            self._dispatch(
                _PostJob(
                    SCROBBLE_STOP_ENDPOINT,
                    payload,
                    auth_generation,
                    lambda: self._send_stop(
                        payload=payload,
                        metadata=metadata,
                        settings=settings,
                        session_id=session_id,
                        auth_generation=auth_generation,
                        watched=watched,
                    ),
                    offline_fallback=lambda: self._send_stop(
                        payload=payload,
                        metadata=metadata,
                        settings=settings,
                        session_id=session_id,
                        auth_generation=auth_generation,
                        watched=watched,
                        attempt_network=False,
                    ),
                )
            )
        except Exception as exc:
            xbmc.log(f"[PunchPlay] Stop emit error: {exc}", xbmc.LOGDEBUG)

    # ------------------------------------------------------------------
    # Rating dialog
    # ------------------------------------------------------------------

    def _queue_rating_prompt(
        self,
        metadata: dict[str, Any],
        settings: dict[str, Any],
        *,
        stop_resp: dict[str, Any] | None,
    ) -> None:
        """Store a pending rating request for the service loop to pick up."""
        if (
            metadata.get("media_type") == "episode"
            and settings.get("rating_prompt_scope", "all") == "movies"
        ):
            xbmc.log(
                "[PunchPlay] Skipping episode rating — prompts limited to movies",
                xbmc.LOGINFO,
            )
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
        with self._rating_lock:
            self._pending_rating = {
                "metadata": metadata,
                "suppression_keys": suppression_keys,
                "not_before": time.monotonic() + delay_secs,
            }

    def pop_due_rating_prompt(self) -> dict[str, Any] | None:
        """
        Return the pending rating request once its delay has elapsed, or None.
        Called by the service loop.  The delay lets Kodi settle so autoplay
        of the next episode cancels the prompt instead of being interrupted.
        """
        with self._rating_lock:
            pending = self._pending_rating
            if pending is None or time.monotonic() < pending["not_before"]:
                return None
            self._pending_rating = None

        if self.isPlayingVideo():
            xbmc.log("[PunchPlay] Skipping rating — another video is playing", xbmc.LOGINFO)
            return None
        return pending

    def prompt_for_rating(self, request: dict[str, Any]) -> None:
        """Show the rating option dialog.  Must be called off the player
        callback thread (the service loop)."""
        metadata = request["metadata"]
        suppression_keys = request["suppression_keys"]
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
                footer=_s(32128),
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
        # Kodi bumps the item's playcount around now — refresh the echo
        # suppression window that started when playback began. This must run
        # even when nothing was tracked (identify failed, or the play was
        # filtered by min_length_minutes): those plays only ever got the
        # start-time stamp, and without a stop-time refresh the suppression
        # window could lapse before Kodi's own echo arrives, letting a
        # filtered-out play leak into live sync as if it were a manual toggle.
        if self._current_library_item is not None:
            self._stamp_library_item(*self._current_library_item)
            self._current_library_item = None

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
            self._playback_auth_generation = None
            self._stop_emitted = False

    def handle_logout(self) -> None:
        """Cancel playback work belonging to the account just logged out.

        The API generation has already advanced when this is called. Queued
        jobs from the old generation are discarded, while an in-flight job is
        prevented by APIClient.post() from repopulating the cleared SQLite
        queue if its request later fails.
        """
        self._is_playing = False
        self._stop_heartbeat()
        self._metadata = None
        self._playback_session_id = None
        self._playback_auth_generation = None
        self._stop_emitted = False
        self._clear_deferred_sessions()
        with self._rating_lock:
            self._pending_rating = None

        discarded = 0
        with self._post_state_lock:
            while True:
                try:
                    job = self._post_queue.get_nowait()
                except queue.Empty:
                    break
                if job is not None:
                    discarded += 1
                self._post_queue.task_done()
        if discarded:
            xbmc.log(
                f"[PunchPlay] Discarded {discarded} queued post(s) on logout",
                xbmc.LOGINFO,
            )

    # ------------------------------------------------------------------
    # Cleanup (called on service shutdown)
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        # If something is still playing when Kodi quits, onPlayBackStopped/
        # onPlayBackEnded never fire — they only cover playback ending while
        # Kodi keeps running. Without this, the item is silently left in
        # "now playing" state on the backend forever: _handle_stop is the
        # only code path that actually emits the stop event, so shutdown
        # must go through it instead of just clearing local state.
        self._handle_stop()
        with self._rating_lock:
            self._pending_rating = None
        self._stop_post_worker()

    def _stop_post_worker(self) -> None:
        """Let queued posts finish before shutdown — the last one is usually
        the stop event for whatever was playing."""
        with self._post_thread_lock:
            thread = self._post_thread
            self._post_thread = None
        if thread is None or not thread.is_alive():
            return
        sentinel_enqueued = False
        try:
            self._post_queue.put_nowait(None)
            sentinel_enqueued = True
        except queue.Full:
            xbmc.log(
                "[PunchPlay] Post queue full at shutdown — will persist backlog",
                xbmc.LOGDEBUG,
            )
        thread.join(timeout=POST_WORKER_JOIN_TIMEOUT_SECS)
        if thread.is_alive():
            xbmc.log(
                "[PunchPlay] Post worker still busy at shutdown — abandoning it",
                xbmc.LOGWARNING,
            )
            # Stop the worker from taking another job while the queue and its
            # current in-flight job are snapshotted for offline replay.
            with self._post_state_lock:
                self._post_abandon.set()
                active_job = self._active_post_job
            if not sentinel_enqueued:
                try:
                    # Wake a worker that drained a previously-full queue and
                    # is now blocked in get(). If the drain wins this race and
                    # consumes the sentinel first, the leftover daemon thread
                    # is harmless; all real jobs are still persisted below.
                    self._post_queue.put_nowait(None)
                except queue.Full:
                    pass
            self._persist_unsent_queue(active_job=active_job)

    def _persist_unsent_queue(self, *, active_job: _PostJob | None = None) -> None:
        """Drain any jobs still sitting in the queue straight into the
        offline queue, bypassing the network and any side effects (e.g. a
        rating prompt) — shutdown is time-boxed, so the goal is just to not
        lose the watch.

        Once `_post_abandon` is set, the worker cannot start another queued
        job. The job it already popped is included too: it may still succeed
        after being persisted, but `event_id` makes that duplicate replay
        idempotent and is safer than losing it when the daemon is terminated.
        Replay order follows each event's timestamp rather than this drain's
        insertion order."""
        if self._cache is None:
            return
        jobs: list[_PostJob] = []
        while True:
            try:
                job = self._post_queue.get_nowait()
            except queue.Empty:
                break
            if (
                job is not None
                and job.endpoint != _FLUSH_QUEUE_SENTINEL
                and job.auth_generation == self._api.auth_generation
            ):
                jobs.append(job)
            self._post_queue.task_done()
        if (
            active_job is not None
            and active_job.endpoint != _FLUSH_QUEUE_SENTINEL
            and active_job.auth_generation == self._api.auth_generation
        ):
            jobs.append(active_job)
        if jobs:
            self._cache.enqueue_scrobbles([(job.endpoint, job.payload) for job in jobs])
            xbmc.log(
                f"[PunchPlay] Persisted {len(jobs)} unsent event(s) to the "
                "offline queue at shutdown",
                xbmc.LOGINFO,
            )
