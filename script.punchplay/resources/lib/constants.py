"""Shared addon constants and lightweight helpers."""

from __future__ import annotations

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

HOME_WINDOW_ID = 10000

FLUSH_INTERVAL_SECS = 60
PRUNE_INTERVAL_SECS = 24 * 60 * 60
IDENTIFIER_CACHE_TTL_SECS = 7 * 24 * 60 * 60
IDENTIFIER_SUCCESS_CACHE_TTL_SECS = 30 * 24 * 60 * 60
IDENTIFIER_NO_MATCH_CACHE_TTL_SECS = 24 * 60 * 60
QUEUE_ENTRY_MAX_AGE_SECS = 30 * 24 * 60 * 60
OFFLINE_QUEUE_MAX_ITEMS = 500
LIBRARY_SYNC_BATCH_SIZE = 50
STOP_COMPLETE_GRACE_SECS = 3
HEARTBEAT_INTERVAL_SECS = 15

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
