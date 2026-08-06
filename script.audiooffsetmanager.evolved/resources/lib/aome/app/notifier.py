"""User-facing offset notifications: the app-layer toast owner.

Whether a toast fires and which message it carries is decided here, driven
by typed events on the dispatcher thread:

* ``OffsetApplied`` — an automatic apply. A provisional apply (stream not
  yet STABLE) does not toast; its message is held on
  ``session.pending_notification`` and released on the next
  ``StreamStabilized``. A non-provisional apply toasts immediately.
* ``StreamStabilized`` — releases a held provisional toast, but only if the
  profile still has the identity it was held under. Identity uses
  ``policies.stream_identity`` with the live granularity toggles, so a
  wiggle the offset system ignores never drops a toast for an apply that
  really happened.
* ``UserOffsetSaved`` — a manual adjustment the AdjustmentWatcher stored.
  Toasts from the event's own profile/ms, captured at store time; session
  and settings are not re-read.

The dedupe clock is the injected ``time.monotonic``, never ``time.time``,
which would mis-measure across wall-clock adjustments.

The device a toast names is labelled by the injected offset table, never
from the profile's own setting string: two endpoints can report one friendly
name, so only the set of devices the store knows can disambiguate, and the
management view labels its rows from the same rule over the same entries.

This is the ONE component that deliberately shows a device's friendly name
while withholding it from the log, since naming the device the user just
switched to is the point of the toast but a Bluetooth endpoint's name
routinely carries a person's. Every toast carrying a device is rendered
twice through the same path, and ``RaiseToast.log_message`` carries the
withheld copy so a fade-deferred release logs what an immediate raise would.

The fade guard works around a Kodi GUI hazard: a toast arriving during the
previous one's close animation is painted onto the dying window and vanishes
with it (docs/kodi-platform-notes.md). Every toast therefore flows through
one choke point (``_present``/``_raise``) that records when the last was
raised and for how long, and only a toast landing inside the guarded window
is deferred, released past the fade via a key-replaced ``RaiseToast``.
Best-effort: toasts from Kodi or other addons share the window and are
invisible to this bookkeeping.

Settings come through the injected facade, toasts through the injected gui.
Pure app layer: stdlib + ``resources.lib.aome`` only.
"""

import time

from resources.lib.aome.app import events
from resources.lib.aome.domain import policies
from resources.lib.aome.domain.stream_state import StreamState
from resources.lib.aome.store import keys as store_keys

STRING_OFFSET_APPLIED = 32092
STRING_OFFSET_SAVED = 32093
STRING_PREVIOUS_VALUE = 32184
# The startup corruption notice, raised via the typed StoreCorrupted event.
STRING_STORE_CORRUPTED = 32121
STRING_STORE_RESTORED = 32183
CORRUPTION_NOTICE_MS = 7000
# The zero-reset discarded a manual adjustment that never reached the store.
STRING_OFFSET_NOT_SAVED = 32132
STRING_RESET_BASELINE = 32133

# English fallbacks for strings that must never render blank, since
# localized() degrades to '' on a transient failure. The apply/saved headings
# are absent because a toast whose value line cannot be named has nothing to
# announce; every notice here carries its own whole meaning. The "Was N ms"
# line is the one decoration in the table: its toast renders without it, so
# the fallback buys the line an English rendering rather than a blank one.
_FALLBACKS = {
    STRING_PREVIOUS_VALUE: "Was {0} ms",
    STRING_STORE_CORRUPTED: ("Stored offsets were unreadable and were reset. "
                             "The unreadable file is kept as "
                             "offsets.json.bad"),
    STRING_STORE_RESTORED: ("Stored offsets were unreadable and were restored "
                            "from the automatic backup. The most recent "
                            "change may be missing"),
    STRING_OFFSET_NOT_SAVED: "Offset not saved",
    STRING_RESET_BASELINE: "Reset to 0 ms. Nothing is stored for this stream",
}


class Notifier:
    """Owns offset toasts: deferral-until-stable, dedupe, and the fade guard."""

    DEDUPE_SECONDS = 1.0
    # Width of the guarded window after a toast's display time expires, and
    # where the deferred release lands. One constant governs both the
    # detection band and the release target, so no unguarded slice can open
    # between them.
    FADE_GUARD_SECONDS = 1.25
    # Kodi clamps displayTime to this floor whatever the caller asked for.
    KODI_MIN_DISPLAY_MS = 1500

    _FADE_KEY = 'aome.notifier.toast'

    def __init__(self, dispatcher, session_tracker, settings, gui, offsets,
                 clock=time.monotonic, *, log_debug):
        self._dispatcher = dispatcher
        self._sessions = session_tracker
        self._settings = settings
        self._gui = gui
        # The offset table, for one read only: the device label rule the
        # management view names its rows with (see _toast). Required rather
        # than optional, so a Notifier can never fall back to naming the
        # device itself.
        self._offsets = offsets
        self._clock = clock
        self._log = log_debug
        # The last raised toast, or None: (dedupe key, monotonic stamp,
        # duration given). One field, so the dedupe/fade-guard lockstep is
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
            # Held until the stream stabilizes. The whole profile rides on
            # the hold so the release can compare identity at whatever
            # granularity is in force then.
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
                    enabled=self._settings.notify_learn_enabled,
                    previous_ms=event.previous_ms)

    def _on_unsaved_discarded(self, event):
        if not self._sessions.is_alive(event.session_id):
            return
        # Save-related feedback, so it lives under the learn gate. Outside
        # the dedupe window, since it fires once per reset, and with English
        # fallbacks. It rides the fade guard like every toast: a zero-reset
        # lands on stream changes, right where apply/saved toasts fade out.
        if not self._settings.notify_learn_enabled():
            return
        title = self._text(STRING_OFFSET_NOT_SAVED)
        message = self._text(STRING_RESET_BASELINE)
        self._log(f"AOMe_Notifier: {title} — discarded unstored "
                  f"{event.ms}ms for {event.profile.describe()}")
        self._present(message, self._settings.notification_duration_ms(),
                      title=title, dedupe_key=None,
                      enabled=self._settings.notify_learn_enabled)

    def _on_store_corrupted(self, event):
        # An error notice rather than a per-kind toast: outside the
        # apply/learn gates and the dedupe window, but still through the
        # choke point so its 7s window is stamped and the first apply toast
        # cannot ride its fade-out. This is the user's only signal that the
        # stored offsets were reset or restored, so it falls back to English
        # rather than rendering blank.
        if event.recovered:
            message = self._text(STRING_STORE_RESTORED)
        else:
            message = self._text(STRING_STORE_CORRUPTED)
        self._log("AOMe_Notifier: surfaced store corruption notice")
        self._present(message, CORRUPTION_NOTICE_MS,
                      title=None, dedupe_key=None, enabled=None)

    def _on_raise_toast(self, event):
        # The fade-guarded release. Dedupe and the guard were decided at
        # request time and cannot have gone stale, but the per-kind gate is a
        # live setting, so it rides on the event and is re-checked here.
        # None means ungated.
        if event.enabled is not None and not event.enabled():
            return
        self._raise(event.message, event.duration_ms, event.title,
                    event.dedupe_key, log_message=event.log_message)

    # -- internals --------------------------------------------------------------

    def _same_stream(self, held, current):
        """Offset-relevant identity at the granularity in force RIGHT NOW."""
        per_fps = self._settings.per_fps_offsets_enabled()
        distinct = self._settings.distinct_spatial_enabled()
        channels = self._settings.distinct_channels_enabled()
        devices = self._settings.distinct_devices_enabled()
        return (policies.stream_identity(held, per_fps, distinct, channels,
                                         devices)
                == policies.stream_identity(current, per_fps, distinct,
                                            channels, devices))

    def _toast(self, string_id, ms, profile, *, enabled, previous_ms=None):
        # ``enabled`` is the per-kind gate accessor, passed by the call site
        # (which knows its kind statically), so a toast kind can never
        # silently inherit another kind's toggle.
        if not enabled():
            return

        now = self._clock()
        # Dedupe at the offset-relevant granularity, so a wiggle on an axis
        # the current mode folds out cannot defeat the window and re-toast a
        # duplicate.
        per_fps = self._settings.per_fps_offsets_enabled()
        distinct = self._settings.distinct_spatial_enabled()
        channels = self._settings.distinct_channels_enabled()
        devices = self._settings.distinct_devices_enabled()
        key = self._dedupe_key(string_id, ms, profile, per_fps, distinct,
                               channels, devices)
        if self._last_raise is not None:
            last_key, last_at, _ = self._last_raise
            if key == last_key and now - last_at < self.DEDUPE_SECONDS:
                return

        # Toast shape: the saved/applied line is the title, the profile
        # summary is the message's first line, and a save that replaced a
        # value adds a second under it. A skin showing one message line keeps
        # the essential half, and every line stays narrow because Kodi's
        # fadelabel scrolls on a line's WIDTH, not on line count
        # (docs/kodi-platform-notes.md). Each axis shows only what is
        # offset-relevant, since a value living under an 'all' key would be
        # misdescribed by naming the specific rate, layout or device it
        # happened to play under.
        sign = '+' if ms > 0 else ''
        heading = f"{self._gui.localized(string_id)}: {sign}{ms} ms"

        def summary_for(device_label):
            return store_keys.profile_summary(
                profile.hdr_type,
                store_keys.audio_segment(profile.audio_format, distinct),
                profile.video_fps if per_fps else None,
                profile.audio_channels if channels else None,
                device_label)

        # The device label comes from the STORE, not from this profile's own
        # string: two endpoints can report one friendly name (Kodi's ALSA
        # sink names them by card), so only the set of known devices can say
        # whether this one needs part of its id in parentheses. The
        # management view labels its rows from the same rule over the same
        # entries, which is the whole parity claim.
        label = self._offsets.device_label(profile.audio_device) \
            if devices else None
        summary = summary_for(label)
        # The logged copy names the device by its id half only, since a
        # Bluetooth endpoint's friendly name routinely carries a person's
        # name and the support-log export redacts paths rather than names.
        # Same rendering path, so the two lines cannot drift apart in
        # anything but that half.
        log_summary = summary_for(
            store_keys.device_segment(profile.audio_device, True)
            if label is not None else None)
        message = summary
        was_line = self._previous_line(previous_ms)
        if was_line:
            message = f"{summary}\n{was_line}"
            # The log stays one line, joined by a separator no profile
            # summary uses (its axes are ' | ' apart).
            log_summary = f"{log_summary} — {was_line}"
        self._present(message, self._settings.notification_duration_ms(),
                      title=heading, dedupe_key=key, enabled=enabled,
                      log_message=log_summary)

    def _present(self, message, duration_ms, *, title, dedupe_key, enabled,
                 log_message=None):
        # The single choke point: every notifier toast flows through the fade
        # guard here, so each raise is visible to the next one's band check.
        # ``log_message`` is the shown text with anything that must not reach
        # the log withheld; None means the message is already log-safe. It
        # rides the deferral event so a released toast logs the same withheld
        # copy an immediate one does.
        delay = self._fade_guard_delay(self._clock())
        if delay > 0.0:
            self._dispatcher.schedule(
                delay,
                events.RaiseToast(message=message, title=title,
                                  duration_ms=duration_ms,
                                  dedupe_key=dedupe_key, enabled=enabled,
                                  log_message=log_message),
                key=self._FADE_KEY)
            self._log(f"AOMe_Notifier: deferring toast {delay * 1000:.0f}ms "
                      f"past the previous toast's fade-out")
            return
        self._raise(message, duration_ms, title, dedupe_key,
                    log_message=log_message)

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

    def _raise(self, message, duration_ms, title, dedupe_key,
               log_message=None):
        # This raise makes any pending deferred release stale (the fresher
        # fact is taking the window). No-op when we are the deferred release.
        self._dispatcher.cancel(self._FADE_KEY)
        self._gui.notification(message, duration_ms, title=title)
        logged = message if log_message is None else log_message
        self._log(f"AOMe_Notifier: {title + ' — ' if title else ''}{logged}")
        self._last_raise = (dedupe_key, self._clock(), duration_ms)

    def _text(self, string_id):
        """localized() with the English fallback for must-never-blank strings."""
        return self._gui.localized(string_id) or _FALLBACKS[string_id]

    def _previous_line(self, previous_ms):
        """The message's 'Was X ms' line, '' when the save replaced nothing.

        Signed like the value it follows. A translation that is blank, drops
        the placeholder, or will not format degrades to the English line, and
        a line that renders from neither is dropped: the toast it decorates
        must survive whatever the string table holds.
        """
        if previous_ms is None:
            return ''
        sign = '+' if previous_ms > 0 else ''
        value = f"{sign}{previous_ms}"
        for template in (self._gui.localized(STRING_PREVIOUS_VALUE),
                         _FALLBACKS[STRING_PREVIOUS_VALUE]):
            if not template or '{0}' not in template:
                continue
            try:
                return template.format(value)
            except Exception:
                continue
        return ''

    @staticmethod
    def _dedupe_key(string_id, ms, profile, per_fps, distinct_spatial,
                    distinct_channels, distinct_devices):
        # Offset-toast dedupe identity. _toast's single read of each toggle
        # feeds both this key and the rendered summary, so they cannot
        # disagree.
        return (string_id,
                policies.stream_identity(profile, per_fps, distinct_spatial,
                                         distinct_channels, distinct_devices),
                ms)
