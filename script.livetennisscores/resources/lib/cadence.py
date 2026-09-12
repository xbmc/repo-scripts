"""Polling cadence, and the request budget that fixes its floor.

Pure module: no Kodi, no network, so the arithmetic below is directly testable.

The provider's FREE tier allows 30 requests per minute and 100 requests per
DAY (https://docs.livetennisapi.com/llms.txt, retrieved 2026-09-12). The daily
cap, not the per-minute one, is what constrains a service that runs all day:

    a day is 24 * 60            = 1440 minutes
    one request per poll cycle
    at one poll every 15 min    = 1440 // 15 = 96 requests/day  <= 100  OK
    at one poll every 14 min    = 1440 // 14 = 102 requests/day  > 100  over
    at one poll every 20 min    = 1440 // 20 = 72 requests/day   (the default,
                                  leaving 28 for opening the scoreboard by hand)

15 minutes is therefore the tightest cadence a free key can sustain for a full
day, and it is enforced here as a hard floor regardless of what the setting
says -- a user who edits settings.xml by hand, or a future settings change,
cannot push the add-on past the quota it was designed against.
"""

SECONDS_PER_MINUTE = 60
MINUTES_PER_DAY = 24 * 60

FREE_TIER_REQUESTS_PER_DAY = 100
FREE_TIER_REQUESTS_PER_MINUTE = 30

# One list read per poll cycle.
REQUESTS_PER_POLL = 1

MIN_POLL_MINUTES = 15
MAX_POLL_MINUTES = 240
DEFAULT_POLL_MINUTES = 20

# How long a single wait slice lasts. The loop waits in slices so it can pick
# up a settings change (a key pasted in, a new cadence) without sitting out the
# rest of a 15-minute wait.
WAIT_SLICE_SECONDS = 5


def requests_per_day(poll_minutes):
    """Requests a day of polling at this cadence would cost."""
    minutes = max(1, int(poll_minutes))
    return (MINUTES_PER_DAY // minutes) * REQUESTS_PER_POLL


def fits_free_tier(poll_minutes):
    """Whether a full day at this cadence stays inside the free daily quota."""
    return requests_per_day(poll_minutes) <= FREE_TIER_REQUESTS_PER_DAY


def clamp_poll_minutes(value):
    """Coerce a settings value to a cadence this add-on is willing to run.

    Anything unreadable falls back to the default rather than to the floor, so
    a corrupt setting does not silently become the most aggressive option.
    """
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return DEFAULT_POLL_MINUTES
    if minutes < MIN_POLL_MINUTES:
        return MIN_POLL_MINUTES
    if minutes > MAX_POLL_MINUTES:
        return MAX_POLL_MINUTES
    return minutes


def poll_seconds(value):
    """The clamped cadence in seconds, ready to hand to the wait loop."""
    return clamp_poll_minutes(value) * SECONDS_PER_MINUTE
