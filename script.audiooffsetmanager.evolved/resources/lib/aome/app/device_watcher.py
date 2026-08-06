"""Device watching: poll the EFFECTIVE audio endpoint, announce a change.

Polling is the only option: Kodi announces neither a core setting change nor
an ActiveAE device reconfigure, so a self-scheduled ``DeviceTick`` reads the
endpoint every ``TICK_SECONDS`` and posts ``AudioDeviceChanged`` when it
moves. What is polled is the ENDPOINT rather than a setting, resolved the
way the StreamDetector resolves it, so no component can poll one endpoint
while keying another. Why no setting can answer this instead is in
docs/kodi-platform-notes.md.

What is COMPARED is ``formats.normalize_device`` of the reading, never the
raw string, because one endpoint has several spellings. The canonical
segment is what the store key and ``policies.stream_identity`` are built
from, so it is the only comparison that predicts whether the detector would
see a different stream; a friendly-half rename under the same id therefore
does not announce.

Scope is deliberately tiny: this component owns the single fact "the reading
changed" and never writes ``session.profile``, so its payload is a log line
rather than data. The one exception is the same one ``StoreMutationHandler``
makes for the same reason: announcing also cancels any in-flight learn
candidate synchronously, because a queued event can lose the race to a timer
due in the same dispatcher sweep.

Baseline rule, mirroring the AdjustmentWatcher's: the first reading of a
session is adopted silently, being the state we started in rather than a
change, and that first tick is posted rather than scheduled so a switch
inside the opening ``TICK_SECONDS`` still announces. Two screening rules
diverge deliberately. A polled reading naming no device is skipped entirely,
since a transient failure would otherwise post a change away from the device
and another back, each a full change episode downstream. The passthrough
reading is not screened at all, because false doubles as its "not knowable"
answer and names the setting Kodi routes a decoded stream to, so every tick
reads a device rather than going blind through each audio negotiation.

Silence is bounded by one invariant: a reading may only be adopted without
announcing when there is nothing for it to contradict, so an unset baseline
falls back to ``session.profile``'s device (``_baseline``).

Logs name the device by its canonical key segment, never the friendly half,
which routinely carries a person's name on a Bluetooth endpoint while the
support-log export redacts paths rather than names.

Pure app layer: Kodi I/O through the injected gateway, the toggle through
the injected settings facade, log sink injected; no Kodi imports.
"""

import time

from resources.lib.aome.app import events
from resources.lib.aome.domain.formats import (CONDITION_PASSTHROUGH,
                                               device_setting_id,
                                               normalize_device)


class DeviceWatcher:
    """Polls the live audio endpoint; posts AudioDeviceChanged on a move."""

    # Must stay STRICTLY FASTER than AdjustmentWatcher.QUIESCENCE_SECONDS,
    # which a contract test pins. That inequality is comfort rather than
    # correctness: _dialled_stream_unmoved is what keeps a value from being
    # misfiled, and it holds with this poll stalled, starved or cancelled
    # outright. The margin only means an ordinary switch is noticed inside
    # the quiescence window, so the user re-dials once instead of dialling
    # into a value that quietly declines to store. It bounds no latency:
    # adoption also costs the tick's reads, a queue hop and the detector's
    # re-gather.
    TICK_SECONDS = 1.0
    # Floor under the computed delay, for exactly one reason: the next timer
    # must never be already due when the handler returns, or the dispatcher
    # re-enters this handler forever and starves every queued event
    # (docs/kodi-platform-notes.md). Any strictly positive value satisfies
    # that; 50ms is invisible next to the read that caused the overrun.
    MIN_GAP_SECONDS = 0.05
    _TICK_KEY = 'aome.devicewatcher.tick'

    def __init__(self, dispatcher, session_tracker, gateway, settings,
                 clock=time.monotonic, *, log_debug):
        self._dispatcher = dispatcher
        self._sessions = session_tracker
        self._gateway = gateway
        self._settings = settings
        # Measures how long a tick took, so the next one can be aimed at
        # this one's deadline.
        self._clock = clock
        self._log = log_debug
        # The one piece of state: the last device string seen, or None for
        # "no baseline of our own yet" (see _baseline). Held RAW, since the
        # event payload and the profile fallback are both raw, and
        # normalized at COMPARE time. A new session and a disarm clear it.
        self._last_device = None

        dispatcher.subscribe(events.PlaybackStarted, self._on_playback_started)
        dispatcher.subscribe(events.SettingsChanged, self._on_settings_changed)
        dispatcher.subscribe(events.DeviceTick, self._on_tick)
        dispatcher.subscribe(events.PlaybackStopped, self._on_playback_ended)
        dispatcher.subscribe(events.PlaybackEnded, self._on_playback_ended)

    # -- lifecycle (dispatcher thread) -----------------------------------------

    def _on_playback_started(self, _event):
        session = self._sessions.current
        if session is None:
            return  # tracker subscribes first; defensive only
        # A new session is the reset: the previous session's baseline says
        # nothing about this one.
        self._last_device = None
        self._evaluate(session)

    def _on_settings_changed(self, _event):
        session = self._sessions.current
        if session is None:
            return
        self._evaluate(session)

    def _on_playback_ended(self, _event):
        # Cancelling the chain is the whole teardown: the baseline is
        # unreachable without a live session, and _on_playback_started
        # clears it before the next one can read it.
        self._dispatcher.cancel(self._TICK_KEY)

    def _evaluate(self, session):
        """Arm or disarm the poll chain for the toggle in force now.

        Re-read here and on every tick, so a flip acts at once in both
        directions; with the toggle off at ``PlaybackStarted`` no tick is
        ever scheduled.
        """
        if not self._settings.distinct_devices_enabled():
            self._dispatcher.cancel(self._TICK_KEY)
            self._last_device = None
            return
        # Posted, not scheduled, so arming reads immediately (the baseline
        # rule); the tick handler owns every subsequent hop. Any pending
        # scheduled tick is key-replaced by the reschedule this one
        # performs, so re-evaluating never spawns a second chain.
        self._dispatcher.post(events.DeviceTick(session_id=session.session_id))

    # -- the poll (dispatcher thread) -------------------------------------------

    def _on_tick(self, event):
        """One poll: guard, read, then reschedule from this tick's deadline.

        The reschedule is LAST and its delay is measured from where the tick
        BEGAN, so a tick whose reads fit inside the period lands the next one
        exactly ``TICK_SECONDS`` later however long Kodi blocked; one that
        outruns it degrades to read + ``MIN_GAP_SECONDS``.

        Scheduling at handler ENTRY instead looks equivalent and is not: past
        an overrun the timer it armed is already due when the handler
        returns, and the dispatcher then re-enters this handler forever
        (docs/kodi-platform-notes.md). Keep the schedule below the reads.

        Both guards run first, so a superseded session's tick drops its chain
        while the toggle-off branch keeps the one it deliberately keeps. A
        read that RAISES ends the poll chain, the reschedule being below it;
        production-inert, since the gateway catches and answers a sentinel.
        """
        started = self._clock()
        if not self._sessions.is_alive(event.session_id):
            return  # a superseded session's chain is inert
        if not self._settings.distinct_devices_enabled():
            # Skip the device read, so "never polls with the toggle off" is
            # a property of this handler rather than of event delivery. The
            # baseline goes with it: whatever moves while nothing is
            # watching is the state we resume in, not a change.
            #
            # The chain is RESCHEDULED rather than dropped, because this
            # branch cannot tell a real flip from a failed settings read
            # (Settings.get_bool answers its default, False, on ANY
            # exception), and dropping it would disarm the poll for the rest
            # of a playback whose toggle was actually on. A real flip is
            # torn down by the accompanying SettingsChanged, where _evaluate
            # cancels, and by playback end, so the surviving chain costs
            # nothing in the steady state.
            self._last_device = None
            self._schedule_tick(event.session_id, started)
            return
        # Kodi's per-stream endpoint choice, mirrored: which device setting
        # the sink obeys follows the passthrough condition. Read
        # unconditionally, since an unknown answer is false and names the
        # decoded-audio setting, so a tick never declines to read a device.
        # Comparing the RESULTING endpoint keeps the common case free: two
        # settings naming one endpoint compare equal and announce nothing.
        setting_id = device_setting_id(
            self._gateway.condition(CONDITION_PASSTHROUGH))
        device = self._gateway.setting_value(setting_id)
        if device:
            baseline = self._baseline()
            current = normalize_device(device)
            if baseline is None:
                self._last_device = device
                self._log(f"AOMe_DeviceWatcher: baseline audio output "
                          f"device {current!r} (from {setting_id})")
            elif current != normalize_device(baseline):
                self._last_device = device
                self._log(f"AOMe_DeviceWatcher: audio output device "
                          f"changed {normalize_device(baseline)!r} -> "
                          f"{current!r} (from {setting_id})")
                self._dispatcher.post(events.AudioDeviceChanged(
                    session_id=event.session_id, device=device))
                self._cancel_pending_adjustment()
        # Last, and from the deadline: see this handler's docstring.
        self._schedule_tick(event.session_id, started)

    def _cancel_pending_adjustment(self):
        """Drop any in-flight learn candidate at DETECTION, not delivery.

        A queued event leaves a timer-interleave window and the store can
        run inside it, so by the time ``ProfileChanged`` arrives to say a
        value was dialled for an endpoint we have left, it may already be
        stored under it.

        Dropping the baseline alongside the candidate keeps this from
        re-detecting: the next reading is re-adopted silently, so the user
        re-dials once rather than watching the same value refuse itself
        every cycle.
        """
        session = self._sessions.current
        if session is None:
            return
        session.clear_watch_observation()

    def _baseline(self):
        """The device the live session is keyed on, or None for "no claim".

        Our own last reading first; failing that, the session profile's
        device, adopted so it can be contradicted. That profile device may be
        '' when the profile was gathered with the toggle off, and seeding it
        is the point: '' normalizes to the all-devices segment, so the next
        real reading contradicts it and announces, which is how an OFF->ON
        flip reaches a live session.

        Seeded RAW and compared canonically, since the profile's spelling
        came from whichever setting was in force at the gather. None only
        while no profile has been adopted, which is the one case a reading
        may be taken silently.
        """
        if self._last_device is None:
            session = self._sessions.current
            profile = session.profile if session is not None else None
            if profile is not None:
                self._last_device = profile.audio_device
        return self._last_device

    def _schedule_tick(self, session_id, started):
        """One place for the self-scheduled poll chain (key-replaced).

        ``started`` is the clock reading taken at handler entry, so the
        delay closes the gap to ``started + TICK_SECONDS`` rather than
        adding a whole fresh period to "now". ``MIN_GAP_SECONDS`` floors it,
        and that floor is not cosmetic (see the constant).
        """
        elapsed = self._clock() - started
        delay = max(self.MIN_GAP_SECONDS, self.TICK_SECONDS - elapsed)
        self._dispatcher.schedule(
            delay, events.DeviceTick(session_id=session_id),
            key=self._TICK_KEY)
