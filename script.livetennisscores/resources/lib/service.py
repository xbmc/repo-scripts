"""The polling service behind the ``xbmc.service`` extension point.

Started by Kodi at launch, it polls the live-match list on a quota-safe cadence
and raises a Kodi notification on the few changes worth interrupting a viewer
for. It stops when Kodi asks it to.

Abort handling, which is the part that has to be right. Kodi gives a service
five seconds to return after it signals abort and then force-kills the script
with an error in the log (``PYTHON_SCRIPT_TIMEOUT`` in Kodi's
``PythonInvoker.cpp``), so the wait between polls must be interruptible.

``xbmc.Monitor().waitForAbort(timeout)`` is that interruptible wait: it returns
True the moment abort is requested -- immediately, if abort was already
requested -- and False only when the timeout elapsed first. It is not a plain
sleep, so even a single 15-minute call would not delay shutdown. Two rules are
still observed here:

* every wait's return value is checked and propagated, so abort unwinds the
  loop rather than being noticed one poll later, and nothing uses
  ``time.sleep``, which genuinely would block shutdown;
* the timeout handed to ``waitForAbort`` is never zero or negative -- Kodi
  reads that as "no timeout" and waits until shutdown.

The wait is sliced into ``cadence.WAIT_SLICE_SECONDS`` chunks for a different
reason: between slices it re-reads the settings, so a cadence change -- or a
key being pasted in for the first time -- takes effect in seconds rather than
after the remainder of a 20-minute wait.

What the loop may spend is not decided here. Every request goes through the
day's :class:`resources.lib.budget.Budget`, and a poll that cannot afford its
first request is not made at all: the previous snapshot is left exactly as it
was, because an empty list would read as every match having finished.
"""

import time

import xbmc
import xbmcgui

from . import api, budget, cache, cadence, changes, scoring, strings
from .settings import Settings, log, log_error

# Re-read settings every this many wait slices (5s each -> every 30s).
_SETTINGS_CHECK_EVERY = 6

# Most notifications to show from a single poll. The list drains at the end of
# a playing day, which without a cap would queue one popup per match that
# finished; past this many the rest are summarised in one line instead.
_MAX_NOTIFICATIONS_PER_POLL = 5


class Service:
    """Polls live matches and notifies on state changes until Kodi aborts."""

    def __init__(self, monitor=None, settings=None, dialog=None):
        self._monitor = monitor or xbmc.Monitor()
        self._settings = settings or Settings()
        self._dialog = dialog or xbmcgui.Dialog()
        self._state = {}
        self._warned_no_key = False
        self._warned_unauthorized = False
        # False until the first successful poll. Tracked explicitly rather than
        # inferred from the state being empty, which is also what a quiet spell
        # with nothing on court looks like.
        self._have_polled = False
        self._last_request_at = None
        # Set when a key appears in settings where there was none, and cleared
        # by the one poll it unblocks.
        self._wake_for_key = False
        # Whether the last poll attempt found a usable key. This, rather than a
        # fresh read when the wait begins, is what "there was no key before" is
        # measured against: a key pasted in between the poll and the start of
        # the wait would otherwise already look like the baseline, and the user
        # would sit out the whole interval.
        self._key_seen = False
        # The UTC day whose spent budget has already been reported, so an
        # exhausted budget says so once rather than on every cycle.
        self._budget_warned_for_day = None

    # -- lifecycle --------------------------------------------------------
    def run(self):
        """The service loop. Returns when Kodi has asked the add-on to stop."""
        minutes = self._settings.poll_minutes
        log(f"service started (cadence {minutes} min, "
            f"{cadence.polls_per_day(minutes)} polls/day, at most "
            f"{cadence.max_requests_per_day(minutes, api.MAX_PAGES)} requests/day "
            f"before the budget of {self._settings.daily_request_limit} stops it)")

        while not self._monitor.abortRequested():
            interval = self._settings.poll_seconds
            if self._may_request(interval):
                try:
                    self._poll_once()
                except Exception as error:  # noqa: BLE001
                    # A service add-on must not put a traceback in the Kodi log
                    # on a bad response or an offline network, so the loop
                    # reports the failure in one line and carries on.
                    log_error(f"poll failed: {type(error).__name__}: {error}")

            if self._wait(interval):
                break

        log("service stopped")

    def _may_request(self, interval):
        """Whether the clamped cadence has actually elapsed since the last call.

        The wait loop can return early when the cadence setting changes, and
        dragging the cadence slider changes it on every step. Without this
        check each of those would start a fresh poll immediately, so the
        15-minute floor would bound the wait but not the request rate -- which
        is the thing the free daily allowance actually cares about.

        The one sanctioned exception is a key having just been entered. It is
        consumed here, so one absent-to-present transition unblocks exactly
        one poll and then the floor applies again from that poll's timestamp.
        It is not a way round the quota either: the poll it unblocks pays for
        its requests out of the same daily budget as any other.
        """
        if self._wake_for_key:
            self._wake_for_key = False
            return True
        if self._last_request_at is None:
            return True
        elapsed = time.monotonic() - self._last_request_at
        # A backwards jump cannot happen with a monotonic clock, but a poll is
        # cheap to allow and a stuck service is not.
        if elapsed < 0:
            return True
        return elapsed >= interval

    def _wait(self, seconds):
        """Wait ``seconds`` in short slices.

        :returns: True when Kodi asked the add-on to stop (the caller must then
            return promptly), False when the wait finished or was cut short
            because the polling cadence changed or a key was entered.
        """
        baseline = self._settings.poll_minutes
        # What the last poll attempt saw. A key arriving after that is the one
        # event worth cutting this wait short for: the user has just pasted one
        # in and is watching to see whether the add-on works.
        had_key = self._key_seen
        remaining = int(seconds)
        slices = 0

        while remaining > 0:
            step = cadence.WAIT_SLICE_SECONDS if remaining > cadence.WAIT_SLICE_SECONDS \
                else remaining
            if step <= 0:
                # waitForAbort treats a timeout of 0 or less as "no timeout"
                # and blocks until shutdown, which would stall this loop for
                # the rest of the Kodi session. Never hand it one.
                break
            # Returns True the moment Kodi requests shutdown, so a long wait
            # never delays it; the slicing is for picking up settings changes.
            if self._monitor.waitForAbort(step):
                return True
            remaining -= step
            slices += 1

            if slices % _SETTINGS_CHECK_EVERY != 0:
                continue

            if not had_key and self._settings.has_api_key:
                # Only on the absent -> present transition, so touching the
                # settings dialog at any other time cannot force a poll.
                log("an API key was entered; polling now")
                self._wake_for_key = True
                return False

            current = self._settings.poll_minutes
            if current != baseline:
                log(f"cadence changed to {current} min")
                return False

        return False

    # -- one cycle --------------------------------------------------------
    def _poll_once(self):
        settings = self._settings

        if not settings.has_api_key:
            # No key: do nothing at all, and say so once rather than every
            # cycle, so an unconfigured add-on stays silent in the log too.
            if not self._warned_no_key:
                log("no API key set in add-on settings; idling until one is")
                self._warned_no_key = True
            self._state = {}
            self._key_seen = False
            return
        self._warned_no_key = False
        # Recorded before the budget gate below, so a poll skipped for budget
        # does not leave the wait thinking the key is still missing.
        self._key_seen = True

        # The day's allowance, minus the couple held back so that opening the
        # scoreboard by hand still works on the last poll of a day.
        day_budget = budget.Budget(settings.daily_request_limit,
                                   reserve=budget.RESERVED_FOR_MANUAL, log=log)
        if not day_budget.available():
            # Nothing is sent, and nothing is forgotten: the previous
            # snapshot stays exactly as it is, because replacing it with an
            # empty list would read as every tracked match having finished.
            self._report_spent_budget(day_budget)
            return
        # Re-armed so that raising the limit mid-day, spending the new
        # allowance too, gets its own line rather than being silent.
        self._budget_warned_for_day = None

        self._last_request_at = time.monotonic()
        client = api.Client(settings.api_key, log=log, budget=day_budget)
        result = client.live_matches()

        if not result:
            self._handle_failure(result)
            return

        self._warned_unauthorized = False
        matches = scoring.parse_matches(result.payload)
        if result.complete:
            cache.write(matches)
        else:
            # A partial list must not become the scoreboard's idea of what is
            # on court either: a third of the matches shown as though that
            # were all of them is the same defect in a different window. The
            # previous cache entry stays, and ages honestly.
            log(f"live list incomplete ({len(matches)} matches read); "
                "no absence counted and the cache left alone")

        events, self._state = changes.diff(
            self._state, matches,
            notify_break_points=settings.notify_break_point,
            first_poll=not self._have_polled,
            complete=result.complete)
        # Only a COMPLETE list ends the first-poll grace. An incomplete first
        # poll leaves matches it never read out of the state, and they would
        # then arrive on the next poll looking brand new -- a burst of "now on
        # court" for matches that were already being played before Kodi
        # started. The cost of holding the grace open is one missed "now on
        # court" for a match that genuinely started in between, which is the
        # cheaper of the two mistakes.
        self._have_polled = self._have_polled or result.complete

        self._announce_all(events)

    def _report_spent_budget(self, day_budget):
        """Say once per day that the request budget is gone."""
        day = day_budget.day
        if self._budget_warned_for_day == day:
            return
        self._budget_warned_for_day = day
        # `spendable`, not `limit`: the reserve is not the service's to spend,
        # so the number the service actually stops at is the smaller one.
        log(f"the polling budget for {day} (UTC) is spent "
            f"({day_budget.spendable} of {day_budget.limit} requests, the rest "
            "reserved for opening the scoreboard); not polling again until it "
            "resets at UTC midnight")

    def _handle_failure(self, result):
        """Report a failed read at the right volume for its cause."""
        if result.status == api.UNAUTHORIZED:
            # Worth telling the user once: nothing will work until it is fixed.
            if not self._warned_unauthorized:
                self._warned_unauthorized = True
                log_error("the API key was rejected (HTTP 401)")
                self._notify(self._text(strings.HEADING_ADDON),
                             self._text(strings.ERROR_UNAUTHORIZED))
            return
        if result.status == api.RATE_LIMITED:
            log("rate limited; skipping this cycle")
            return
        if result.status == api.BUDGET_SPENT:
            # Only reachable when the scoreboard spent the last of the day
            # between this poll's budget check and its first request.
            log("the daily request budget went while this poll was starting; "
                "skipping this cycle")
            return
        if result.status == api.UPGRADE_REQUIRED:
            log_error("this key's plan does not include the live match list")
            return
        # Transport trouble and bad bodies are expected occasionally and are
        # already logged by the client; nothing further to do.

    # -- notifications ----------------------------------------------------
    def _announce_all(self, events):
        """Show this poll's events, capped so one poll cannot flood the screen.

        The live list empties at the end of a playing day, which can turn a
        single poll into dozens of finished matches. Past the cap the remainder
        becomes one summary line rather than a queue of popups the viewer has
        to sit through.
        """
        wanted = [event for event in events if self._is_enabled(event.kind)]
        for event in wanted[:_MAX_NOTIFICATIONS_PER_POLL]:
            self._announce(event)

        hidden = len(wanted) - _MAX_NOTIFICATIONS_PER_POLL
        if hidden > 0:
            self._notify(self._text(strings.HEADING_ADDON),
                         self._text(strings.MORE_CHANGES).format(count=hidden))

    def _is_enabled(self, kind):
        """Whether the user asked to be told about this kind of change."""
        rule = _RULE_FOR_KIND.get(kind)
        return bool(rule) and bool(getattr(self._settings, rule[1]))

    def _announce(self, event):
        """Show one event, if the user asked to be told about that kind."""
        rule = _RULE_FOR_KIND.get(event.kind)
        if rule is None:
            return
        heading_id, toggle = rule
        # Read only the one toggle this event depends on.
        if not getattr(self._settings, toggle):
            return

        self._notify(self._text(heading_id), f"{event.label}  {event.detail}".strip())

    def _text(self, string_id):
        """The translated string for an id, with its English text as fallback."""
        return self._settings.localized(string_id, strings.FALLBACKS.get(string_id, ""))

    def _notify(self, title, message):
        """Raise a Kodi notification from already-resolved text."""
        try:
            self._dialog.notification(
                title,
                message,
                self._settings.icon_path() or xbmcgui.NOTIFICATION_INFO,
                self._settings.display_seconds * 1000,
                False,
            )
        except Exception as error:  # noqa: BLE001
            log_error(f"could not show notification: {type(error).__name__}: {error}")


# event kind -> (notification heading string id, the settings toggle gating it)
_RULE_FOR_KIND = {
    changes.MATCH_LIVE: (strings.HEADING_MATCH_LIVE, "notify_match_live"),
    changes.SET_DONE: (strings.HEADING_SET_DONE, "notify_set_done"),
    changes.MATCH_DONE: (strings.HEADING_MATCH_DONE, "notify_match_done"),
    changes.BREAK_POINT: (strings.HEADING_BREAK_POINT, "notify_break_point"),
}
