"""Shared addon constants and lightweight helpers."""

from __future__ import annotations

import time
from datetime import datetime, timezone

import xbmc
import xbmcaddon
import xbmcvfs

ADDON_ID = "script.punchplay"
ADDON_NAME = "PunchPlay"
ADDON_DISPLAY_NAME = "PunchPlay"
NOTIFICATION_TITLE = ADDON_NAME
DEFAULT_BACKEND_URL = "https://punchplay.tv"

SCROBBLE_START_ENDPOINT = "/api/scrobble/start"
SCROBBLE_PROGRESS_ENDPOINT = "/api/scrobble/progress"
SCROBBLE_PAUSE_ENDPOINT = "/api/scrobble/pause"
SCROBBLE_RESUME_ENDPOINT = "/api/scrobble/resume"
SCROBBLE_STOP_ENDPOINT = "/api/scrobble/stop"
SCROBBLE_RATE_ENDPOINT = "/api/scrobble/rate"
SCROBBLE_IMPORT_ENDPOINT = "/api/scrobble/import"
SCROBBLE_SYNC_ENDPOINT = "/api/scrobble/sync"

AUTH_DEVICE_CODE_ENDPOINT = "/api/auth/device/code"
AUTH_DEVICE_TOKEN_ENDPOINT = "/api/auth/device/token"
AUTH_REFRESH_ENDPOINT = "/api/auth/refresh"
AUTH_ME_ENDPOINT = "/api/auth/me"
IDENTIFY_ENDPOINT = "/api/identify"

ACTION_PROPERTY_LOGIN = "punchplay_login"
ACTION_PROPERTY_LOGOUT = "punchplay_logout"
ACTION_PROPERTY_SYNC_LIBRARY = "punchplay_sync_library"
ACTION_PROPERTY_PREVIEW_LIBRARY = "punchplay_preview_library"
ACTION_PROPERTY_TEST_CONNECTION = "punchplay_test_connection"
ACTION_PROPERTY_SHOW_STATUS = "punchplay_show_status"
ACTION_PROPERTY_EXPORT_DEBUG = "punchplay_export_debug"
ACTION_PROPERTY_EXPORT_VERBOSE_DEBUG = "punchplay_export_verbose_debug"
ACTION_PROPERTY_CLEAR_QUEUE = "punchplay_clear_queue"
ACTION_PROPERTY_PULL_SYNC = "punchplay_pull_sync"
ACTION_PROPERTY_CLEAR_SUPPRESSIONS = "punchplay_clear_suppressions"

HOME_WINDOW_ID = 10000

FLUSH_INTERVAL_SECS = 60
PRUNE_INTERVAL_SECS = 24 * 60 * 60
IDENTIFIER_CACHE_TTL_SECS = 7 * 24 * 60 * 60
IDENTIFIER_SUCCESS_CACHE_TTL_SECS = 30 * 24 * 60 * 60
IDENTIFIER_NO_MATCH_CACHE_TTL_SECS = 24 * 60 * 60
QUEUE_ENTRY_MAX_AGE_SECS = 30 * 24 * 60 * 60
OFFLINE_QUEUE_MAX_ITEMS = 500
# Flush touches at most one failing entry per minute, so this cap (~1 day of
# continuous failures) drops poison payloads the backend will never accept.
MAX_QUEUE_ATTEMPTS = 1440
LIBRARY_SYNC_BATCH_SIZE = 100
# Give up on a library sync after this many batches fail back-to-back — the
# backend is down or rejecting us, and grinding through the rest just reports
# a success that never happened.
LIBRARY_SYNC_MAX_CONSECUTIVE_FAILURES = 3
STOP_COMPLETE_GRACE_SECS = 3
HEARTBEAT_INTERVAL_SECS = 15
HEARTBEAT_MAX_CONSECUTIVE_ERRORS = 3

PULL_SYNC_INTERVAL_SECS = 6 * 60 * 60
PULL_SYNC_OVERLAP_SECS = 60 * 60
PULL_SYNC_TIMEOUT_SECS = 60
AUTO_PULL_CHECK_INTERVAL_SECS = 60
# A pull sync that can't apply one or more items holds back its incremental
# checkpoint so they're retried next time (see _pull_sync in service.py).
# After a failed item reaches this many consecutive held runs, it would
# otherwise block the checkpoint — and every newer item behind it — forever.
# Counts are per item so a newly failing item cannot inherit another item's
# exhausted allowance.
PULL_SYNC_MAX_HELD_RUNS = 3

# Live watched-state sync (VideoLibrary.OnUpdate → PunchPlay import).
LIVE_SYNC_DEBOUNCE_SECS = 2.0
LIVE_SYNC_MAX_BATCH = 100
LIVE_SYNC_DETAIL_RETRY_SECS = 30.0
# An OnUpdate caused by one of our own writes should arrive almost
# immediately. Keep bookkeeping for longer so delayed announcements can still
# be compared, but only suppress events whose timestamps actually match the
# write; otherwise a later manual "mark watched" would be swallowed.
LIVE_SYNC_ECHO_MATCH_SECS = 5.0
# Used both for the "just played this" echo guard (player.py) and the "we
# just pull-synced this" echo guard (library_events.py) — one constant,
# since both only need to bridge the same kind of gap: our own write
# landing in Kodi's library before its OnUpdate announcement arrives. A wide
# window here swallows a genuine manual toggle made shortly afterward.
LIVE_SYNC_ECHO_SUPPRESS_SECS = 30
# Library scan finished → wait for Kodi to settle, then pull sync at most
# once per SCAN_SYNC_MIN_INTERVAL_SECS.
SCAN_SYNC_DELAY_SECS = 60
SCAN_SYNC_MIN_INTERVAL_SECS = 30 * 60

# Device-code polling.  The backend allows 200 token polls per 10 minutes per
# IP and a device code lives 600s, so a 5s interval fits one full login attempt
# (120 polls) inside the budget with room for a second device on the same IP.
DEVICE_CODE_POLL_INTERVAL_SECS = 5
DEVICE_CODE_THROTTLED_BACKOFF_SECS = 30
DEVICE_CODE_MAX_BACKOFF_SECS = 60

# Scrobble posts are dispatched to a worker thread so Kodi's player callbacks
# never block on the network.
POST_QUEUE_MAX_ITEMS = 100
POST_QUEUE_PUT_TIMEOUT_SECS = 2
# A short grace period for the in-flight job to finish normally — not a
# correctness guarantee. A 401 mid-shutdown can chain a refresh call plus a
# retried request (each up to REQUEST_TIMEOUT_SECS) well past any timeout
# reasonable to block Kodi's shutdown on, so jobs that don't finish in time
# are persisted directly to the offline queue instead (see
# PunchPlayPlayer._persist_unsent_queue). Replay order is safe either way —
# it's sorted by each event's own timestamp, not by when it happened to be
# written to the offline queue.
POST_WORKER_JOIN_TIMEOUT_SECS = 5

REQUEST_TIMEOUT_SECS = 15
TEST_CONNECTION_TIMEOUT_SECS = 5
IDENTIFY_REQUEST_TIMEOUT_SECS = 5
IDENTIFY_MATCH_THRESHOLD = 0.85

PERMANENT_HTTP_STATUS_CODES = (400, 403, 404, 422)


def get_addon() -> xbmcaddon.Addon:
    return xbmcaddon.Addon(ADDON_ID)


def get_addon_path() -> str:
    return get_addon().getAddonInfo("path")


def get_addon_version() -> str:
    return get_addon().getAddonInfo("version")


def get_profile_dir() -> str:
    return xbmcvfs.translatePath(get_addon().getAddonInfo("profile"))


def localize(message_id: int) -> str:
    return get_addon().getLocalizedString(message_id)


def mask_value(value: str, visible: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible * 2:
        return value
    return "{0}…{1}".format(value[:visible], value[-visible:])


def kodi_datetime_to_utc_iso(value: str | None) -> str | None:
    """Convert Kodi's local-time "YYYY-MM-DD HH:MM:SS" to a UTC ISO 8601 string."""
    if not value:
        return None
    try:
        parsed = time.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
        epoch = time.mktime(parsed)  # interprets the struct as local time
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))
    except (ValueError, OverflowError):
        xbmc.log(
            f"[PunchPlay] Unparsable lastplayed value {value!r} — omitting watched_at",
            xbmc.LOGWARNING,
        )
        return None


def kodi_datetime_to_epoch(value: str | None) -> float | None:
    """Convert Kodi's local-time "YYYY-MM-DD HH:MM:SS" to a Unix timestamp."""
    if not value:
        return None
    try:
        return time.mktime(time.strptime(value.strip(), "%Y-%m-%d %H:%M:%S"))
    except (ValueError, OverflowError):
        xbmc.log(
            f"[PunchPlay] Unparsable Kodi datetime value {value!r}",
            xbmc.LOGWARNING,
        )
        return None


def iso_to_epoch(value: str | None) -> float | None:
    """Parse an ISO 8601 timestamp (with Z or offset) to a Unix timestamp."""
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def iso_to_kodi_datetime(value: str | None) -> str | None:
    """Convert an ISO 8601 timestamp to Kodi's local-time "YYYY-MM-DD HH:MM:SS"."""
    epoch = iso_to_epoch(value)
    if epoch is None:
        return None
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(epoch))
