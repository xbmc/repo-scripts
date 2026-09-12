"""Polling cadence: how often the service may poll, and what a day of it costs.

Pure module: no Kodi, no network, so the arithmetic below is directly testable.

The provider's FREE tier allows 30 requests per minute and 100 requests per
DAY (https://docs.livetennisapi.com/llms.txt, retrieved 2026-09-12). The daily
cap, not the per-minute one, is what constrains a service that runs all day:

    a day is 24 * 60            = 1440 minutes
    at one poll every 15 min    = 1440 // 15 = 96 polls in a day
    at one poll every 14 min    = 1440 // 14 = 102 polls in a day
    at one poll every 20 min    = 1440 // 20 = 72 polls in a day (the default)

15 minutes is therefore the tightest cadence a free key can sustain for a full
day, and it is enforced here as a hard floor regardless of what the setting
says -- a user who edits settings.xml by hand, or a future settings change,
cannot push the add-on past the cadence it was designed against.

A POLL IS NOT A REQUEST, and that is the part this module cannot fix on its
own. The live list is paginated, so a poll costs one request per page it has
to read, up to ``api.MAX_PAGES``. The 96 polls above are therefore somewhere
between 96 and 96 * 3 = 288 requests, and only the cheapest case fits inside
100. The floor bounds POLLS; it cannot bound requests.

Requests are bounded separately, by the persisted daily budget in
:mod:`resources.lib.budget`: every outbound request consumes one unit of the
day's allowance -- 100 by default, raised only if the user's plan allows it --
a poll that cannot afford its next page stops there and says the list it
returned is incomplete, and a poll that cannot afford its first page is not
made at all. The two limits do different jobs and both are needed --
the floor keeps the add-on polite minute to minute, the budget keeps the day
inside the allowance whatever pagination does.
"""

SECONDS_PER_MINUTE = 60
MINUTES_PER_DAY = 24 * 60

FREE_TIER_REQUESTS_PER_DAY = 100
FREE_TIER_REQUESTS_PER_MINUTE = 30

MIN_POLL_MINUTES = 15
MAX_POLL_MINUTES = 240
DEFAULT_POLL_MINUTES = 20

# How long a single wait slice lasts. The loop waits in slices so it can pick
# up a settings change (a key pasted in, a new cadence) without sitting out the
# rest of a 15-minute wait.
WAIT_SLICE_SECONDS = 5


def polls_per_day(poll_minutes):
    """How many polls a full day at this cadence makes."""
    minutes = max(1, int(poll_minutes))
    return MINUTES_PER_DAY // minutes


def max_requests_per_day(poll_minutes, pages_per_poll=1):
    """The worst case a day at this cadence can cost in REQUESTS.

    ``pages_per_poll`` is the client's page cap: every poll is assumed to read
    the most pages it is allowed to. Pass ``api.MAX_PAGES`` for the real
    ceiling; the default of one describes the cheapest possible day.
    """
    return polls_per_day(poll_minutes) * max(1, int(pages_per_poll))


def fits_free_tier(poll_minutes):
    """Whether a day of polls at this cadence fits the free daily allowance.

    This is the floor's own test, and it deliberately counts one request per
    poll: it asks whether the CADENCE is affordable, which is the only thing a
    cadence can be asked. Whether the day's actual requests stay inside the
    allowance depends on pagination and is the request budget's job, not this
    function's.
    """
    return polls_per_day(poll_minutes) <= FREE_TIER_REQUESTS_PER_DAY


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
