"""Seek-back scheduling: the quiet-window policy, enforced by rescheduling.

ONE rule, decided by the pure ``policies.seek_decision`` and enforced by
``ExecuteSeek`` events that re-check every 0.5s instead of blocking the
dispatcher:

    Do not seek until there has been no seek activity — ours, another
    addon's, or the user's — for QUIET_WINDOW seconds. Defer by
    rescheduling. Give up DEADLINE seconds after the request.

Every attempt runs the same pipeline: probe the vendor list (a busy vendor
is recorded as activity, so the quiet window itself defers past it — no
separate vendor gate), ask the policy (sole owner of the quiet/deadline/
served math), then apply the stability preference: a 'seek' verdict is
downgraded to defer while the session is not yet STABLE, for up to
STABILITY_GRACE seconds — after which the quiet window alone decides, so a
stream whose profile never completes still gets its replay (holding the
user's replay hostage to detection success would be wrong).

Behavior notes:

- Triggers: PlaybackStarted -> 'resume'; Resumed -> 'unpause'; a
  change-announcing, non-initial StreamStabilized (the detector stamps
  ``initial`` on the session's first stabilization — startup settling gets
  no 'adjust' replay) -> 'adjust'; UserOffsetSaved (the watcher stored a
  manual adjustment; session-stamped, so a store racing an in-place reopen
  can never seek the new session) -> 'change'.
- Per-reason trigger debounce: a trigger within DEBOUNCE_SECONDS of that
  reason's last EXECUTED seek is dropped; a re-trigger while pending
  key-replaces the attempt chain (and its event-carried requested_at
  restarts the deadline). The enabled check runs at trigger time; an
  enabled-but-zero length warns.
- Cross-type suppression: a request served by one of our own seeks
  (executed at/after the request) is abandoned by the policy. A
  genuinely-new trigger arriving shortly after one of our own seeks
  defers and executes — a fresh user action gets its replay.
- A post-start settle falls out of session-start-as-activity: Kodi's own
  resume-position seek defers the replay ~2s past itself, and a start
  under a sustained seek storm abandons at the deadline rather than
  rewinding under an actively seeking user.
- Pause cancels the pending seek at fire time (a replay must never land
  in a paused player).
- Stale requests are inert: ExecuteSeek is session-stamped and stop/end/
  reopen cancels the (closed, per-reason) timer keys. There is no side
  bookkeeping to strand: the request state IS the key-replaced timer and
  its event payload.

``ExternalSeekCoordinator`` owns the inter-addon seek protocol, both
directions: the read side (vendor busy-property list as DATA — PM4K's two
properties today; its busy-recency is deliberately cross-session —
aggregated with session activity into the
policy's ``last_activity`` view) and the write side (the seek actuator,
which sets our reciprocal ``script.audiooffsetmanager.seeking`` property
around the seek so other addons get the courtesy we consume from PM4K).

Pure app layer: Kodi I/O through the injected gateway, settings through the
injected facade, log sinks injected; no Kodi imports.
"""

import time

from resources.lib.aom.app import events
from resources.lib.aom.domain import policies
from resources.lib.aom.domain.stream_state import StreamState


class ExternalSeekCoordinator:
    """The inter-addon seek protocol: activity view + reciprocal actuator."""

    # Vendor busy signals as data: home-window properties that read '1'
    # while that addon is running its own seeks.
    VENDOR_BUSY_PROPERTIES = (
        'script.plex.playback_seeking',
        'script.plex.playback_initializing',
    )
    RECIPROCAL_PROPERTY = 'script.audiooffsetmanager.seeking'

    def __init__(self, gateway, clock=time.monotonic, *, log_debug):
        self._gateway = gateway
        self._clock = clock
        self._log = log_debug
        # Cross-session on purpose (see module docstring). None = never seen.
        self._last_vendor_busy = None

    def vendor_busy(self):
        """Probe the vendor list; a busy vendor also counts as activity."""
        for name in self.VENDOR_BUSY_PROPERTIES:
            if self._gateway.window_property(name) == '1':
                self._last_vendor_busy = self._clock()
                self._log(f"AOM_SeekCoordinator: {name} indicates seek "
                          f"activity; deferring")
                return True
        return False

    def last_activity(self, session):
        """Most recent seek-like activity relevant to this session.

        Session start counts as activity (the natural post-start
        settle); SeekOccurred and our own executed seeks feed
        ``session.last_seek_activity``; vendor busy sightings are
        coordinator-wide (they outlive sessions).
        """
        candidates = [session.started_at]
        if session.last_seek_activity is not None:
            candidates.append(session.last_seek_activity)
        if self._last_vendor_busy is not None:
            candidates.append(self._last_vendor_busy)
        return max(candidates)

    def execute_seek(self, seconds, player_id=None):
        """Run one seek with the reciprocity property set around it.

        ``player_id=None`` means the caller has no detected profile to read
        it from (a stream seeking past the stability grace): query the
        player directly and let the gateway's default (player 1) absorb a
        -1 answer.
        """
        if player_id is None:
            player_id = self._gateway.active_player_id()
            if player_id == -1:
                player_id = None
        self._gateway.set_window_property(self.RECIPROCAL_PROPERTY, '1')
        try:
            return self._gateway.seek_back(seconds, player_id=player_id)
        finally:
            self._gateway.clear_window_property(self.RECIPROCAL_PROPERTY)


class SeekScheduler:
    """Plans seeks on triggering events; executes when quiet (+stability)."""

    QUIET_WINDOW_SECONDS = 2.0
    DEADLINE_SECONDS = 8.0
    RECHECK_SECONDS = 0.5
    DEBOUNCE_SECONDS = 2.0
    # How long a 'seek' verdict defers waiting for STABLE before the quiet
    # window alone decides (never-stabilizing streams keep their replay).
    STABILITY_GRACE_SECONDS = 4.0

    # The closed trigger vocabulary; also the cancellation key set.
    REASONS = ('resume', 'unpause', 'adjust', 'change')

    def __init__(self, dispatcher, session_tracker, settings_facade,
                 coordinator, clock=time.monotonic, *, log_debug,
                 log_warning):
        self._dispatcher = dispatcher
        self._sessions = session_tracker
        self._settings = settings_facade
        self._coordinator = coordinator
        self._clock = clock
        self._log = log_debug
        self._warn = log_warning

        dispatcher.subscribe(events.PlaybackStarted, self._on_playback_started)
        dispatcher.subscribe(events.Resumed, self._on_resumed)
        dispatcher.subscribe(events.SeekOccurred, self._on_seek_occurred)
        dispatcher.subscribe(events.StreamStabilized, self._on_stream_stabilized)
        dispatcher.subscribe(events.UserOffsetSaved, self._on_user_offset_saved)
        dispatcher.subscribe(events.ExecuteSeek, self._on_execute_seek)
        dispatcher.subscribe(events.PlaybackStopped, self._on_playback_ended)
        dispatcher.subscribe(events.PlaybackEnded, self._on_playback_ended)

    # -- triggers (dispatcher thread) -------------------------------------------

    def _on_playback_started(self, _event):
        # Fresh session: any timers from a superseded one are stale.
        self._cancel_scheduled()
        self._request('resume')

    def _on_resumed(self, _event):
        # (SessionTracker owns the paused flag and has already cleared it.)
        self._request('unpause')

    def _on_seek_occurred(self, _event):
        session = self._sessions.current
        if session is not None:
            session.last_seek_activity = self._clock()

    def _on_stream_stabilized(self, event):
        if not self._sessions.is_alive(event.session_id):
            return
        if not event.profile_changed:
            return  # pure re-confirmation: nothing changed, nothing to replay
        if event.initial:
            # Startup settling, not an adjustment — stamped by the detector
            # from the state machine's own stabilization count.
            self._log("AOM_SeekScheduler: Skipping initial AV change (startup)")
            return
        self._request('adjust')

    def _on_user_offset_saved(self, event):
        """The watcher stored a manual adjustment: replay the glitched audio."""
        if not self._sessions.is_alive(event.session_id):
            return
        self._request('change')

    def _on_playback_ended(self, _event):
        self._cancel_scheduled()

    # -- execution ---------------------------------------------------------------

    def _on_execute_seek(self, event):
        if not self._sessions.is_alive(event.session_id):
            return
        session = self._sessions.current
        now = self._clock()

        if session.paused:
            # Replaying into a paused player is pointless; an unpause is its
            # own trigger.
            self._log(f"AOM_SeekScheduler: Playback is paused; cancelling "
                      f"{event.reason} seek back")
            return

        # Probe vendors on EVERY attempt (a busy sighting during
        # stabilization must count): the recording feeds last_activity, so
        # the policy's quiet window is the only vendor gate needed.
        self._coordinator.vendor_busy()

        decision = policies.seek_decision(
            now=now,
            requested_at=event.requested_at,
            last_activity=self._coordinator.last_activity(session),
            last_own_seek=max(session.seek_history.values(), default=None),
            quiet_window=self.QUIET_WINDOW_SECONDS,
            deadline=self.DEADLINE_SECONDS)

        if decision == 'abandon':
            self._log(f"AOM_SeekScheduler: Abandoning {event.reason} seek "
                      f"back (already served or deadline passed)")
            return
        if decision == 'defer':
            self._defer(event, 'awaiting quiet window')
            return

        # 'seek' — apply the stability preference: wait for STABLE up to the
        # grace, then let quietness alone decide (see module docstring).
        if (session.stream_state is not StreamState.STABLE
                and now - event.requested_at < self.STABILITY_GRACE_SECONDS):
            self._defer(event, 'stream not stable yet')
            return

        enabled, seek_seconds = self._settings.seek_back_config(event.reason)
        if not enabled or seek_seconds <= 0:
            # Toggled off mid-defer (the trigger-time check is the primary).
            self._log(f"AOM_SeekScheduler: Seek back on {event.reason} no "
                      f"longer enabled; cancelling")
            return

        self._log(f"AOM_SeekScheduler: Seeking back {seek_seconds} seconds "
                  f"on {event.reason}")
        # An undetected stream (profile None past the stability grace) lets
        # the coordinator resolve the player at execution time.
        player_id = (session.profile.player_id
                     if session.profile is not None else None)
        success = self._coordinator.execute_seek(seek_seconds, player_id)
        if success:
            executed_at = self._clock()
            session.seek_history[event.reason] = executed_at
            session.last_seek_activity = executed_at
        else:
            self._log(f"AOM_SeekScheduler: Seek back failed on "
                      f"{event.reason}")

    # -- internals ----------------------------------------------------------------

    def _request(self, reason):
        session = self._sessions.current
        if session is None:
            return
        now = self._clock()
        last_executed = session.seek_history.get(reason)
        if last_executed is not None and \
                now - last_executed < self.DEBOUNCE_SECONDS:
            self._log(f"AOM_SeekScheduler: Skipping {reason} seek back - "
                      f"too soon after the previous one")
            return
        enabled, seek_seconds = self._settings.seek_back_config(reason)
        if not enabled:
            self._log(f"AOM_SeekScheduler: Seek back on {reason} is not "
                      f"enabled")
            return
        if seek_seconds <= 0:
            self._warn(f"AOM_SeekScheduler: Invalid seek back seconds "
                       f"({seek_seconds}) for {reason}")
            return
        # A re-trigger while pending key-replaces the attempt chain; the
        # fresh requested_at restarts the deadline (the newest user action
        # is the one served).
        self._dispatcher.schedule(
            0.0,
            events.ExecuteSeek(session_id=session.session_id, reason=reason,
                               requested_at=now),
            key=self._key(reason))

    def _defer(self, event, why):
        self._log(f"AOM_SeekScheduler: Deferring {event.reason} seek back "
                  f"({why})")
        self._dispatcher.schedule(self.RECHECK_SECONDS, event,
                                  key=self._key(event.reason))

    def _cancel_scheduled(self):
        for reason in self.REASONS:
            self._dispatcher.cancel(self._key(reason))

    @staticmethod
    def _key(reason):
        return f'aom.seek.{reason}'
