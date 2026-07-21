"""User-facing offset notifications: the app-layer toast owner.

Whether a toast fires and which message it carries is decided here, driven
by typed events on the dispatcher thread:

* ``OffsetApplied`` — an automatic apply. A provisional apply (stream not
  yet STABLE) does not toast; its message is held on
  ``session.pending_notification`` and released on the next
  ``StreamStabilized``. A non-provisional apply toasts immediately.
* ``StreamStabilized`` — releases a held provisional toast, but only if the
  profile still has the identity it was held under (a profile that changed
  underneath drops the stale toast). Identity uses
  ``policies.stream_identity`` with the live granularity toggles
  (``per_fps_offsets``, ``distinct_spatial_formats``,
  ``distinct_channel_counts``), so a wiggle the offset system ignores (an
  fps drift, a spatial-variant track switch, a channel-count wiggle)
  never drops a toast for an apply that really happened.
* ``UserOffsetSaved`` — a manual adjustment the AdjustmentWatcher stored.
  Toasts from the event's own profile/ms (captured at store time); session
  and settings are not re-read.

The dedupe clock is the injected ``time.monotonic``, never ``time.time``,
which would mis-measure across wall-clock adjustments.

The fade guard works around a Kodi GUI hazard: GUIDialogKaiToast swaps a
queued toast's content into the window in place while it is showing (fine)
and opens fresh when fully closed (fine), but a toast arriving during the
window's close animation is painted onto the dying window and vanishes with
the fade. A toast raised in roughly [duration, duration + fade] after its
predecessor is therefore swallowed. Every toast the notifier raises flows
through one choke point (``_present``/``_raise``) that records when the last
toast was raised and for how long; only a toast that would land inside that
guarded window is deferred, released past the fade via a scheduled
``RaiseToast`` (key-replaced, so the newest contender wins and an immediate
raise cancels any pending release). Best-effort: toasts raised by Kodi or
other addons share the window but are invisible to this bookkeeping.

Settings come through the injected facade (the per-kind gates
``notify_apply_enabled`` / ``notify_learn_enabled``, both default on, plus
``notification_duration_ms``); toasts go through the injected gui. Pure app
layer: stdlib + ``resources.lib.aome`` only.
"""

import time

from resources.lib.aome.app import events
from resources.lib.aome.domain import policies
from resources.lib.aome.domain.stream_state import StreamState
from resources.lib.aome.store import keys as store_keys

STRING_OFFSET_APPLIED = 32092
STRING_OFFSET_SAVED = 32093
# "Stored offsets were unreadable and were reset (backup kept as
# offsets.json.bad)" — the startup corruption notice (raised via the
# typed StoreCorrupted event).
STRING_STORE_CORRUPTED = 32121
CORRUPTION_NOTICE_MS = 7000
# "Offset not saved" / "Reset to 0 ms. Nothing is stored for this stream":
# the zero-reset discarded a manual adjustment that never reached the
# store.
STRING_OFFSET_NOT_SAVED = 32132
STRING_RESET_BASELINE = 32133


class Notifier:
    """Owns offset toasts: deferral-until-stable, dedupe, and the fade guard."""

    DEDUPE_SECONDS = 1.0
    # Width of the guarded window after a toast's display time expires, and
    # where the deferred release lands. Kodi's display timer starts at the
    # end of the open animation and the close animation adds a few hundred ms
    # more, so the release must land past that total with margin. One
    # constant governs both the detection band and the release target so no
    # unguarded slice can open between them.
    FADE_GUARD_SECONDS = 1.25
    # GUIDialogKaiToast::AddToQueue clamps displayTime to a floor of
    # TOAST_MESSAGE_TIME (1000) + 500, whatever the caller asked for.
    KODI_MIN_DISPLAY_MS = 1500

    _FADE_KEY = 'aome.notifier.toast'

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
        dispatcher.subscribe(events.StoreCorrupted, self._on_store_corrupted)
        dispatcher.subscribe(events.UnsavedOffsetDiscarded,
                             self._on_unsaved_discarded)
        dispatcher.subscribe(events.RaiseToast, self._on_raise_toast)

    # -- handlers (dispatcher thread) -------------------------------------------

    def _on_offset_applied(self, event):
        if not self._sessions.is_alive(event.session_id):
            return
        session = self._sessions.current
        if event.provisional:
            # Held until the stream stabilizes; the whole profile rides on
            # the hold so the release can compare identity at the granularity
            # in force then (toggle read at release instant).
            session.pending_notification = (event.profile, event.ms)
            self._log("AOMe_Notifier: holding provisional notification until "
                      "the stream stabilizes")
            return
        session.pending_notification = None
        self._toast(STRING_OFFSET_APPLIED, event.ms, event.profile,
                    enabled=self._settings.notify_apply_enabled)

    def _on_stream_stabilized(self, event):
        if not self._sessions.is_alive(event.session_id):
            return
        session = self._sessions.current
        if session.pending_notification is None:
            return
        # Only release once the session is genuinely STABLE.
        if session.stream_state is not StreamState.STABLE:
            return
        pending_profile, pending_ms = session.pending_notification
        # Read the profile fresh and compare at the granularity the offset
        # system uses now: with per_fps off, an fps wiggle is not a stream
        # change and must not drop the toast for a real apply.
        profile = session.profile
        if profile is None or not self._same_stream(pending_profile, profile):
            session.pending_notification = None
            return
        session.pending_notification = None
        self._toast(STRING_OFFSET_APPLIED, pending_ms, profile,
                    enabled=self._settings.notify_apply_enabled)
        self._log("AOMe_Notifier: Released pending offset notification after "
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
        self._toast(STRING_OFFSET_SAVED, event.ms, event.profile,
                    enabled=self._settings.notify_learn_enabled)

    def _on_unsaved_discarded(self, event):
        if not self._sessions.is_alive(event.session_id):
            return
        # Save-related feedback, so it lives under the learn gate: the user's
        # manual adjustment was discarded by the zero-reset because it never
        # reached the store. Outside the dedupe window (dedupe_key=None; it
        # fires once per reset) and with English fallbacks. It rides the fade
        # guard like every toast: a zero-reset lands on stream changes, right
        # where apply/saved toasts fade out.
        if not self._settings.notify_learn_enabled():
            return
        title = self._gui.localized(STRING_OFFSET_NOT_SAVED) or (
            "Offset not saved")
        message = self._gui.localized(STRING_RESET_BASELINE) or (
            "Reset to 0 ms. Nothing is stored for this stream")
        self._log(f"AOMe_Notifier: {title} — discarded unstored "
                  f"{event.ms}ms for {event.profile.describe()}")
        self._present(message, self._settings.notification_duration_ms(),
                      title=title, dedupe_key=None,
                      enabled=self._settings.notify_learn_enabled)

    def _on_store_corrupted(self, _event):
        # An error notice, not a per-kind toast: outside the apply/learn
        # gates (enabled=None, never muted) and the dedupe window
        # (dedupe_key=None). It still flows through the choke point so its 7s
        # window is stamped and the first apply toast cannot ride its
        # fade-out. localized() degrades to '' on failure, and this is the
        # user's only signal that offsets were reset, so fall back to the
        # English string rather than a blank toast.
        message = self._gui.localized(STRING_STORE_CORRUPTED) or (
            "Stored offsets were unreadable and were reset "
            "(backup kept as offsets.json.bad)")
        self._log("AOMe_Notifier: surfaced store corruption notice")
        self._present(message, CORRUPTION_NOTICE_MS,
                      title=None, dedupe_key=None, enabled=None)

    def _on_raise_toast(self, event):
        # The fade-guarded release. Dedupe and the guard were decided at
        # request time and cannot have gone stale, but the per-kind gate is a
        # live setting re-checked at fire time — it rides on the event, so
        # the release re-gates under its own kind's toggle. None = ungated.
        if event.enabled is not None and not event.enabled():
            return
        self._raise(event.message, event.duration_ms, event.title,
                    event.dedupe_key)

    # -- internals --------------------------------------------------------------

    def _same_stream(self, held, current):
        """Offset-relevant identity at the granularity in force RIGHT NOW."""
        per_fps = self._settings.per_fps_offsets_enabled()
        distinct = self._settings.distinct_spatial_enabled()
        channels = self._settings.distinct_channels_enabled()
        return (policies.stream_identity(held, per_fps, distinct, channels)
                == policies.stream_identity(current, per_fps, distinct,
                                            channels))

    def _toast(self, string_id, ms, profile, *, enabled):
        # ``enabled`` is the per-kind gate accessor, passed by the call site
        # (which knows its kind statically), so a toast kind can never
        # silently inherit another kind's toggle.
        if not enabled():
            return

        now = self._clock()
        # Dedupe at the offset-relevant granularity: with per_fps off an
        # fps wiggle must not defeat the window and re-toast a duplicate,
        # nor, with distinct_spatial off, a spatial-variant track switch,
        # nor, with distinct_channels off, a channel-count wiggle.
        per_fps = self._settings.per_fps_offsets_enabled()
        distinct = self._settings.distinct_spatial_enabled()
        channels = self._settings.distinct_channels_enabled()
        key = self._dedupe_key(string_id, ms, profile, per_fps, distinct,
                               channels)
        if self._last_raise is not None:
            last_key, last_at, _ = self._last_raise
            if key == last_key and now - last_at < self.DEDUPE_SECONDS:
                return

        # Toast shape: the saved/applied line is the title and the profile
        # summary is the message. Packing both into the message with a
        # newline made Kodi's single-line label auto-scroll and truncate the
        # codec. Each axis shows only what is offset-relevant: the rate only
        # with per_fps on (off, the value lives under the all-rates key, so
        # "23.976 fps" would mislead), the channel layout only with
        # distinct_channels on (same reasoning), and with distinct_spatial
        # off the base codec name, since that names the key the value lives
        # under.
        sign = '+' if ms > 0 else ''
        heading = f"{self._gui.localized(string_id)}: {sign}{ms} ms"
        summary = store_keys.profile_summary(
            profile.hdr_type,
            store_keys.audio_segment(profile.audio_format, distinct),
            profile.video_fps if per_fps else None,
            profile.audio_channels if channels else None)
        self._present(summary, self._settings.notification_duration_ms(),
                      title=heading, dedupe_key=key, enabled=enabled)

    def _present(self, message, duration_ms, *, title, dedupe_key, enabled):
        # The single choke point: every notifier toast flows through the fade
        # guard here, so each raise is visible to the next one's band check.
        delay = self._fade_guard_delay(self._clock())
        if delay > 0.0:
            self._dispatcher.schedule(
                delay,
                events.RaiseToast(message=message, title=title,
                                  duration_ms=duration_ms,
                                  dedupe_key=dedupe_key, enabled=enabled),
                key=self._FADE_KEY)
            self._log(f"AOMe_Notifier: deferring toast {delay * 1000:.0f}ms "
                      f"past the previous toast's fade-out")
            return
        self._raise(message, duration_ms, title, dedupe_key)

    def _fade_guard_delay(self, now):
        """Seconds to wait so this toast misses the previous toast's fade.

        Zero (raise immediately) unless the toast would land inside
        [shown, shown + FADE_GUARD_SECONDS] after our last raise, where
        ``shown`` is the last toast's display time floored at Kodi's clamp.
        Earlier arrivals are in-place swaps on the still-open window, later
        ones reopen it fresh.
        """
        if self._last_raise is None:
            return 0.0
        _, last_at, last_duration_ms = self._last_raise
        shown_s = max(last_duration_ms, self.KODI_MIN_DISPLAY_MS) / 1000.0
        elapsed = now - last_at
        if elapsed < shown_s or elapsed >= shown_s + self.FADE_GUARD_SECONDS:
            return 0.0
        return shown_s + self.FADE_GUARD_SECONDS - elapsed

    def _raise(self, message, duration_ms, title, dedupe_key):
        # This raise makes any pending deferred release stale (the fresher
        # fact is taking the window). No-op when we are the deferred release.
        self._dispatcher.cancel(self._FADE_KEY)
        self._gui.notification(message, duration_ms, title=title)
        self._log(f"AOMe_Notifier: {title + ' — ' if title else ''}{message}")
        self._last_raise = (dedupe_key, self._clock(), duration_ms)

    @staticmethod
    def _dedupe_key(string_id, ms, profile, per_fps, distinct_spatial,
                    distinct_channels):
        # Offset-toast dedupe identity. _toast's single read of each toggle
        # feeds both this key and the rendered summary, so they cannot
        # disagree.
        return (string_id,
                policies.stream_identity(profile, per_fps, distinct_spatial,
                                         distinct_channels),
                ms)
