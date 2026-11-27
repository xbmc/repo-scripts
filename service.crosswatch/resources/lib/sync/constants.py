# SPDX-License-Identifier: GPL-2.0-only
"""Library sync's limits and intervals, in one place.

The wire limits come from the sync contract (docs/contract-sync.md) and CrossWatch's own
checks; the intervals are the add-on's choices, each explained where it is used.
"""

# Nothing is read, uploaded, fetched or written while something plays or for this long after.
from __future__ import annotations

PLAYBACK_QUIET_SECONDS = 60
DAILY_FULL_SECONDS = 86_400
QUEUE_FALLBACK_SECONDS = 900
RATING_SCAN_SECONDS = 300
# How long after the first complete full a quiet queue counts as settled. CrossWatch retries
# starting the pair run for 1800 s; the run itself has no bound, so this is a heuristic.
SETTLE_SECONDS = 2400
BACKOFF_SECONDS = (5, 15, 60, 300, 900)
# A media server add-on's map that couldn't be read is tried again after this long.
SERVER_MAP_RETRY_SECONDS = 60
# A connect in progress has no socket for SyncClient.cancel() to shut down, so it alone gets
# a timeout short enough to fit Kodi's exit window; the request and reply keep the full one.
CONNECT_TIMEOUT_SECONDS = 2.0

MAX_REQUEST_BYTES = 900_000
MAX_ROWS_PER_LIST = 10_000
MAX_FULL_ROWS = 250_000
MAX_PARTS = 1000
MIN_PART_ROWS = 1000

OWN_WRITE_TICKS = 30
ACKED_SEQS_KEPT = 10_000
MASS_RATING_CHANGE = 50
SEED_WINDOW_SECONDS = 86_400
INBOX_MAX = 10_000
INBOX_MAX_AGE_SECONDS = 2_592_000
RESUME_GUARD_SECONDS = 604_800

# The status screen's upload time and changes waiting are recounted from the whole record, so at
# most this often while the record keeps changing.
STATUS_FIGURES_SECONDS = 30.0
