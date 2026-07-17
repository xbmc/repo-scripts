"""User-facing offset notifications — the app-layer toast owner.

Everything about "should a toast fire, and which message" lives here,
driven by typed events on the dispatcher thread:

* ``OffsetApplied`` — an automatic apply. A provisional apply (the stream is
  not yet STABLE) does NOT toast; its message is HELD on
  ``session.pending_notification`` and released on the session's next
  ``StreamStabilized``. A non-provisional apply toasts immediately and clears
  any pending hold.
* ``StreamStabilized`` — releases a held provisional toast, but only if the
  profile still keys the same setting id it was held under: a profile that
  changed underneath drops the stale toast (settings-doctrine — never toast a
  stale key). The setting id is re-derived FRESH from ``session.profile`` at
  release time.
* ``UserOffsetSaved`` — a manual adjustment the AdjustmentWatcher stored.
  Toasts from the event's own profile/ms (captured at store time on the
  dispatcher thread); session/settings are deliberately NOT re-read.

The dedupe clock for the 1s duplicate-suppression window is the injected
``time.monotonic`` — deliberately not ``time.time``, which would mis-measure
the window across wall-clock adjustments.

The fade guard covers a Kodi GUI hazard:
GUIDialogKaiToast swaps a queued toast's content into the
window in place while it is showing (restarting the display timer, window
stays open — fine) and opens fresh when fully closed (fine), but a toast
popping from Kodi's queue during the window's CLOSE ANIMATION is painted onto
the dying window and vanishes with the fade. A toast raised in roughly
[duration, duration + fade] after its predecessor is therefore swallowed
(observed in the wild: an "applied" toast landing 5.2s after a 5s "saved"
toast flashed for ~100ms). The notifier remembers when it last raised a toast
and for how long, and ONLY a toast that would land inside that guarded window
is deferred — released past the fade via a scheduled ``RaiseToast``
(key-replaced: the newest contender wins, across message kinds too — the
survivor is always the fresher fact — and an immediate raise cancels any
pending release outright). Every other toast fires immediately.
Best-effort by design: toasts raised by Kodi itself or other addons
share the same GUI window but are invisible to this bookkeeping.

Settings (``notifications_enabled`` / ``notification_duration_ms``) are read
through the injected facade; toasts go through the injected gui. Pure app
layer: stdlib + ``resources.lib.aom`` only.
"""

import time

from resources.lib.aom.app import events
from resources.lib.aom.domain.stream_state import StreamState

STRING_OFFSET_APPLIED = 32092
STRING_OFFSET_SAVED = 32093


class Notifier:
    """Owns offset toasts: deferral-until-stable, dedupe, and the fade guard."""

    DEDUPE_SECONDS = 1.0
    # Width of the guarded window after a toast's display time expires — and
    # therefore where the deferred release lands. Budget: Kodi's display timer
    # starts at the END of the window's open animation (so true expiry lags
    # our raise stamp by up to a few hundred ms), the skin-defined close
    # animation runs a few hundred more, and the release must land PAST that
    # total with margin, never at its edge. One constant governs both the
    # detection band and the release target so no unguarded slice can open
    # between them.
    FADE_GUARD_SECONDS = 1.25
    # GUIDialogKaiToast::AddToQueue clamps displayTime to a floor of
    # TOAST_MESSAGE_TIME (1000) + 500, whatever the caller asked for.
    KODI_MIN_DISPLAY_MS = 1500

    _FADE_KEY = 'aom.notifier.toast'

    def __init__(self, dispatcher, session_tracker, settings, gui,
                 clock=time.monotonic, *, log_debug):
        self._dispatcher = dispatcher
        self._sessions = session_tracker
        self._settings = settings
        self._gui = gui
        self._clock = clock
        self._log = log_debug
        # The last raised toast, or None: (dedupe key, monotonic stamp,
        # duration given). One field so the dedupe/fade-guard lockstep is
        # structural rather than by convention.
        self._last_raise = None

        dispatcher.subscribe(events.OffsetApplied, self._on_offset_applied)
        dispatcher.subscribe(events.UserOffsetSaved, self._on_user_offset_saved)
        dispatcher.subscribe(events.StreamStabilized, self._on_stream_stabilized)
        dispatcher.subscribe(events.RaiseToast, self._on_raise_toast)

    # -- handlers (dispatcher thread) -------------------------------------------

    def _on_offset_applied(self, event):
        if not self._sessions.is_alive(event.session_id):
            return
        session = self._sessions.current
        if event.provisional:
            # Held until the stream stabilizes; the release path re-derives the
            # key from the live profile and drops the toast if it changed.
            session.pending_notification = (event.profile.setting_id(), event.ms)
            self._log("AOM_Notifier: holding provisional notification until "
                      "the stream stabilizes")
            return
        session.pending_notification = None
        self._toast(STRING_OFFSET_APPLIED, event.ms, event.profile)

    def _on_stream_stabilized(self, event):
        if not self._sessions.is_alive(event.session_id):
            return
        session = self._sessions.current
        if session.pending_notification is None:
            return
        # Defensive: only release once the session is genuinely STABLE.
        if session.stream_state is not StreamState.STABLE:
            return
        pending_setting_id, pending_ms = session.pending_notification
        # Read the profile FRESH: a profile that changed underneath must not
        # release a toast against a stale key (settings-doctrine).
        profile = session.profile
        if profile is None or pending_setting_id != profile.setting_id():
            session.pending_notification = None
            return
        session.pending_notification = None
        self._toast(STRING_OFFSET_APPLIED, pending_ms, profile)
        self._log("AOM_Notifier: Released pending offset notification after "
                  "stream stabilization")

    def _on_user_offset_saved(self, event):
        if not self._sessions.is_alive(event.session_id):
            return
        # A manual save supersedes any held provisional toast: the user's
        # value is the fact on the ground, and releasing the old held ms on
        # the next stabilization would announce a value that no longer
        # applies.
        self._sessions.current.pending_notification = None
        # The payload is the profile/ms captured at store time by the watcher;
        # do NOT re-read session/settings for the message.
        self._toast(STRING_OFFSET_SAVED, event.ms, event.profile)

    def _on_raise_toast(self, event):
        # The fade-guarded release. Dedupe and the guard were decided at
        # request time and cannot have gone stale (an immediate raise cancels
        # this timer; a contender key-replaces it), but the enabled gate is a
        # live setting and must be re-checked at fire time.
        if not self._settings.notifications_enabled():
            return
        self._raise(event.string_id, event.ms, event.profile)

    # -- internals --------------------------------------------------------------

    def _toast(self, string_id, ms, profile):
        if not self._settings.notifications_enabled():
            return

        now = self._clock()
        if self._last_raise is not None:
            last_key, last_at, _ = self._last_raise
            if self._dedupe_key(string_id, ms, profile) == last_key and \
                    now - last_at < self.DEDUPE_SECONDS:
                return

        delay = self._fade_guard_delay(now)
        if delay > 0.0:
            self._dispatcher.schedule(
                delay,
                events.RaiseToast(string_id=string_id, ms=ms, profile=profile),
                key=self._FADE_KEY)
            self._log(f"AOM_Notifier: deferring toast {delay * 1000:.0f}ms "
                      f"past the previous toast's fade-out")
            return
        self._raise(string_id, ms, profile)

    def _fade_guard_delay(self, now):
        """Seconds to wait so this toast misses the previous toast's fade.

        Zero (raise immediately) unless the toast would land inside
        [shown, shown + FADE_GUARD_SECONDS] after our last raise, where
        ``shown`` is the display time the last toast was given, floored at
        Kodi's internal clamp: earlier arrivals are in-place swaps on the
        still-open window, later ones reopen it fresh (the module docstring
        has the Kodi mechanics).
        """
        if self._last_raise is None:
            return 0.0
        _, last_at, last_duration_ms = self._last_raise
        shown_s = max(last_duration_ms, self.KODI_MIN_DISPLAY_MS) / 1000.0
        elapsed = now - last_at
        if elapsed < shown_s or elapsed >= shown_s + self.FADE_GUARD_SECONDS:
            return 0.0
        return shown_s + self.FADE_GUARD_SECONDS - elapsed

    def _raise(self, string_id, ms, profile):
        # This raise makes any pending deferred release stale by definition —
        # the fresher fact is taking the window. (No-op when we ARE the
        # deferred release: its timer was consumed before dispatch.)
        self._dispatcher.cancel(self._FADE_KEY)
        duration_ms = self._settings.notification_duration_ms()
        sign = '+' if ms > 0 else ''
        message = (f"{self._gui.localized(string_id)}: {sign}{ms} ms\n"
                   f"{profile.summary(include_fps=True)}")

        self._gui.notification(message, duration_ms)
        self._log(f"AOM_Notifier: {message}")
        self._last_raise = (self._dedupe_key(string_id, ms, profile),
                            self._clock(), duration_ms)

    @staticmethod
    def _dedupe_key(string_id, ms, profile):
        return (string_id, profile.setting_id(), ms)
