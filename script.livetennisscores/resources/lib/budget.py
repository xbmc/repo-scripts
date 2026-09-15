"""The add-on's own daily request budget.

The provider's FREE tier allows 100 requests a DAY
(https://docs.livetennisapi.com/llms.txt, retrieved 2026-09-12). The polling
cadence cannot bound that on its own. The live list is paginated, so one poll
costs one request for every page it has to read -- up to ``api.MAX_PAGES`` --
and a day of polls at the 15-minute floor could therefore cost anywhere
between 96 and 288 requests. The cadence floor bounds POLLS. This module
bounds REQUESTS, which is what the provider actually counts.

Every outbound request consumes one unit, and a request that cannot afford one
is not sent at all. Not sending it is the point: a refused request costs
nothing, whereas a 429 from the provider means the allowance has already been
spent and the next thing the viewer sees is an error.

Persistence. The count lives in ``request_budget.json`` in the add-on's own
profile directory, beside the score cache, written with the same atomic
replace, so restarting Kodi does not hand the add-on a fresh hundred requests.

If that file cannot be read or written -- a read-only profile, a full disk, a
Windows sharing violation against a reader -- the count falls back to an
in-process one, and the greater of the two always wins. The request is still
allowed: refusing every request would leave such a box with an add-on that
silently never works. But it is not allowed unbounded, which is what a plain
fail-open would mean: the cadence floor alone permits 96 * ``MAX_PAGES`` = 288
requests in a day, nearly three times the free allowance, so it is no
safeguard at all. The in-process count holds a single Kodi session to the
limit; only restarting Kodi on a profile it cannot write to loses the count,
and that is said once in the log.

The day. The boundary is UTC midnight, matched to the provider's own daily
window rather than the viewer's local midnight: a box in UTC+13 resetting at
local midnight would spend two local days' worth of allowance inside one
provider day. The stored day is compared for equality, not ordering, so a
clock that jumps backwards starts the day again instead of locking the add-on
out until the date catches up.
"""

import time

from . import api, cache, cadence

FILENAME = "request_budget.json"
_VERSION = 1

# What a free key gets, and the default this add-on assumes.
DEFAULT_DAILY_LIMIT = cadence.FREE_TIER_REQUESTS_PER_DAY

# The setting can raise the budget for a paid key but never lower it below the
# free allowance the add-on was designed against.
MIN_DAILY_LIMIT = DEFAULT_DAILY_LIMIT

# Above a few hundred the budget can no longer bind: the cadence floor caps a
# day at MAX_PAGES requests per poll, so the ceiling here only has to be
# comfortably clear of that plus a day of hand-opened scoreboards.
MAX_DAILY_LIMIT = 1000

# Requests the polling service leaves alone, so that opening the scoreboard by
# hand on the last poll of a day still has something to spend when the cache
# has gone stale. The service asks for a budget with this reserve; the
# scoreboard asks for one without, which is what lets it reach them.
#
# It is the client's page cap, not an arbitrary couple: a scoreboard read
# costs one request per page it has to follow, so a smaller reserve could only
# fund a TRUNCATED manual read -- and a truncated list shown as though it were
# the whole one is the defect this add-on goes to some length to avoid.
RESERVED_FOR_MANUAL = api.MAX_PAGES

# The count of last resort, shared by every Budget in this interpreter, used
# whenever the file cannot be relied on. Keyed by day so it rolls over with
# the persisted count; never lower than it, never a substitute for it.
_IN_PROCESS = {"day": None, "used": 0}
_WARNED = [False]


def utc_day(now=None):
    """The current UTC calendar day as ``"YYYY-MM-DD"``."""
    moment = time.time() if now is None else now
    return time.strftime("%Y-%m-%d", time.gmtime(moment))


def clamp_limit(value):
    """Coerce a settings value to a daily limit this add-on will honour.

    Anything unreadable falls back to the free allowance rather than to the
    ceiling, so a corrupt setting cannot quietly become permission to spend.
    """
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return DEFAULT_DAILY_LIMIT
    if limit < MIN_DAILY_LIMIT:
        return MIN_DAILY_LIMIT
    if limit > MAX_DAILY_LIMIT:
        return MAX_DAILY_LIMIT
    return limit


class Budget:
    """The requests still available today, backed by a file.

    It caches nothing: every question re-reads the file, so the service and a
    hand-opened scoreboard -- which Kodi runs as separate scripts -- see each
    other's spending.

    Two requests genuinely in flight at the same instant can still both read
    the same count before either writes, and lose an increment. Within one
    interpreter :data:`_IN_PROCESS` closes that, because it is a plain
    in-memory counter that both instances share; across the service and the
    scoreboard, which Kodi runs separately, it stays open. The day can
    therefore end a few requests over its limit, but only if the scoreboard is
    opened by hand in the same instant as a poll, on a day already at its
    ceiling, and the provider answers an over-cap request with a 429 that both
    callers already handle. It is left unlocked at that price: a lock file
    would have to be broken safely after a crash, and one left behind would
    stop the add-on working at all.
    """

    __slots__ = ("limit", "reserve", "_path", "_log", "_now")

    def __init__(self, limit=None, reserve=0, path=None, log=None, now=None):
        self.limit = clamp_limit(DEFAULT_DAILY_LIMIT if limit is None else limit)
        self.reserve = max(0, int(reserve))
        # Injectable so the file and the day boundary can both be exercised
        # against a stub profile, and without waiting for midnight.
        self._path = path
        self._now = now or time.time
        self._log = log or (lambda message: None)

    @property
    def day(self):
        """The UTC day this budget is currently counting against."""
        return utc_day(self._now())

    @property
    def spendable(self):
        """The limit this budget will actually spend up to, reserve removed."""
        return max(0, self.limit - self.reserve)

    def path(self):
        """Where the count is persisted, or None when there is nowhere.

        Resolving it needs the add-on's profile directory, and a profile that
        cannot be reached at all is a configuration accident, not something a
        poll should raise over.
        """
        if self._path is not None:
            return self._path
        try:
            return cache.profile_path(FILENAME)
        except Exception:  # noqa: BLE001 - an unreachable profile is not an error
            return None

    def used(self):
        """Requests already spent in the CURRENT UTC day."""
        return self._used_on(self.day)

    def _used_on(self, day):
        """Requests spent on ``day``, taking the day as given.

        A record of any other day reads as zero, which is what makes the day
        roll over without anything having to run at midnight. The count is the
        greater of what the file says and what this interpreter has counted, so
        a file that cannot be written still cannot be spent past.
        """
        stored = 0
        path = self.path()
        if path is not None:
            payload = cache.read_json(path)
            if (isinstance(payload, dict)
                    and payload.get("version") == _VERSION
                    and payload.get("day") == day):
                value = payload.get("used")
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    stored = value
        in_process = _IN_PROCESS["used"] if _IN_PROCESS["day"] == day else 0
        return max(stored, in_process)

    def remaining(self):
        """Requests this budget may still spend."""
        return max(0, self.spendable - self.used())

    def available(self):
        """Whether one more request can be afforded right now."""
        return self.remaining() > 0

    def take(self):
        """Consume one request.

        :returns: True when the request may be sent, False when the day's
            budget is spent and it must not be.
        """
        # Sampled once. Reading it again after the count would let a request
        # that straddles midnight be recorded against the day before it,
        # which would then let the new day start over from one.
        day = self.day
        used = self._used_on(day)
        if used >= self.spendable:
            return False

        _IN_PROCESS["day"] = day
        _IN_PROCESS["used"] = used + 1

        path = self.path()
        stored = path is not None and cache.write_json(
            path, {"version": _VERSION, "day": day, "used": used + 1})
        if not stored and not _WARNED[0]:
            _WARNED[0] = True
            self._log("could not record the request budget to disk; "
                      "counting in memory, so the daily cap holds for this "
                      "session but not across a restart")
        return True
