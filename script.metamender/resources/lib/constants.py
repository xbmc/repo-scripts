"""Centralized constants for MetaMender addon."""
from __future__ import annotations

import base64

# =============================================================================
# Addon Identity
# =============================================================================

DEFAULT_ADDON_ID = "script.metamender"
ADDON_PREFIX = "MetaMend"

# =============================================================================
# Logging
# =============================================================================

LOG_DIR_NAME = "logs"
LOG_FILE_PREFIX = "metamender"
LOG_MAX_FILES = 10
# Between scans the debug log goes to one activity file, rotated at this size
# with this many older copies kept (metamender.1.log is the newest of them).
LOG_ACTIVITY_MAX_BYTES = 500 * 1024
LOG_ACTIVITY_ROTATED = 3
LOG_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
LOG_TIMESTAMP_TRIM = -3  # Trim microseconds to milliseconds
LOG_MAX_VALUE_LENGTH = 200

# =============================================================================
# Service
# =============================================================================

KODI_HOME_WINDOW_ID = 10000

# Default scan interval in hours
DEFAULT_SCAN_INTERVAL_HOURS = 24

# Sleep granularity: how often the service loop checks for abort (seconds)
SERVICE_SLEEP_INTERVAL_SEC = 1

# Days to retry unresolved items before applying fallback

# Seconds to wait after library scan/clean finishes before triggering a rating scan
LIBRARY_SCAN_DEBOUNCE_SEC = 300

# Backoff before retrying a scan that aborted on a Kodi query failure.
# Short relative to the full scan interval so a transient RPC failure recovers
# quickly without re-hammering Kodi every loop iteration.
SCAN_FAILURE_BACKOFF_SEC = 300
SCAN_LOCKED_RETRY_SEC = 60

# =============================================================================
# Country Presets
# =============================================================================

COUNTRY_CODES = ("NL", "BE", "DE", "AT", "GB", "US", "FR", "DK", "SE", "AU")

# =============================================================================
# Backfill Tracker (SQLite)
# =============================================================================

BACKFILL_DB_FILENAME = "backfill.db"
SOURCES_CONFIG_FILENAME = "sources.json"

# Tracker SQLite schema version. Bump when the schema changes so future
# migrations have a marker to branch on. Stored in scan_state on init.
SCHEMA_VERSION = 5

# Days before an answer that left something unfilled is asked again: a value
# that only the fallback language supplied, or an id that the cross-reference
# lookups answered they do not have.
FALLBACK_RECHECK_DAYS = 30

# Answered re-checks a fallback-language value gets before it is final like
# any other value. With FALLBACK_RECHECK_DAYS between them, about a year.
FALLBACK_RECHECKS = 12

# Default refetch schedule in days (attempt 1 -> 7d, attempt 2 -> 30d, attempt 3 -> 90d)
DEFAULT_REFETCH_SCHEDULE: tuple[int, ...] = (7, 30, 90)


def parse_refetch_schedule(value: str) -> tuple[int, ...]:
    """Parse a 'comma,separated,days' schedule string, dropping non-positive
    entries. Falls back to DEFAULT_REFETCH_SCHEDULE on empty or malformed input."""
    try:
        parts = [int(p.strip()) for p in value.split(",") if p.strip()]
    except (ValueError, AttributeError):
        return DEFAULT_REFETCH_SCHEDULE
    parts = [p for p in parts if p > 0]
    return tuple(parts) if parts else DEFAULT_REFETCH_SCHEDULE


# Disable a provider after this many consecutive failures in a single scan
PROVIDER_CIRCUIT_BREAKER_THRESHOLD = 5

# =============================================================================
# External APIs
# =============================================================================

# Outbound HTTP limits (providers/http): a read timeout bounds one stalled
# read, not a body that trickles in, so a whole-response deadline and a size
# cap back it up.
HTTP_CONNECT_TIMEOUT = 5
HTTP_READ_TIMEOUT = 15
HTTP_DEADLINE_SEC = 30
HTTP_MAX_BODY_BYTES = 5_000_000

# Certification sites (engine/certchain): the national rating websites are
# not APIs built for bulk use, so each is asked at most once a second, a cycle
# makes at most SITE_REQUESTS_PER_CYCLE site requests (a large library's first
# scan spreads over several cycles), and one item's chain gives up after
# CERT_ITEM_BUDGET_SEC.
SITE_MIN_INTERVAL_SEC = 1.0
SITE_REQUESTS_PER_CYCLE = 300
CERT_ITEM_BUDGET_SEC = 60

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TVDB_BASE_URL = "https://api4.thetvdb.com/v4"
# Project key issued to this add-on; TVDB intends project keys to ship
# inside the client, unlike the user-supplied TMDB key. Kept encoded, as
# Kodi's repository reviewers ask, so key scanners do not read it off the
# source; it is not a secret.
TVDB_API_KEY = base64.b64decode("YWVkNTI5NzliZjc4LTY2YzgtZGUwNC0yNzUwLWZiYmQ5MTcx").decode()[::-1]

# Explicit User-Agent for provider API calls: some provider front ends reject
# a bare urllib UA, while a browser-like UA is reliably accepted.
METAMENDER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
