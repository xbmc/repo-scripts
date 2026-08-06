"""Adjustment watching: poll the audio-delay infolabel, store user changes.

The watcher polls ``Player.AudioDelay`` on the dispatcher thread via
self-scheduled ``WatchTick`` events. Watching the value rather than the OSD
slider dialog catches every source of an adjustment: a keymap, a remote app,
or a JSON-RPC ``Player.SetAudioDelay`` all change the delay without opening
a dialog.

Three facts span the methods below and belong here rather than in any one of
them.

**Watching and storing are separately gated.** Watchability is just "a
profile exists", because a settle is a user-action fact with consumers of its
own: it posts ``UserOffsetSettled``, which the seek scheduler's 'change'
replay rides, so with learning off a value still settles and still rewinds.
Only the store half consults the learn toggle. The apply toggle gates
neither, which is what makes apply-off with learn-on the legal re-teach
state.

**Self-echo suppression is a contract with the applier.** An automatic apply
is a JSON-RPC player call, so our own value shows up in the infolabel like a
user's would. The applier records ``session.applied`` *before* issuing the
RPC precisely so the comparison here is always current. An automatic delay
change landing inside a pending quiescence window supersedes the candidate,
enforced at three points: ``OffsetApplied`` and ``DelayReset`` clear the
observation here, and ``StoreMutationHandler`` clears it synchronously at
the mutation itself. Without the third, a candidate dialed just before a
delete could quiesce and re-store the entry the user deleted.

**Serialization is not freshness.** Adoption and store run on one thread, so
a store cannot interleave with a re-adoption, but the dispatcher sweeps due
timers before it reads its queue (docs/kodi-platform-notes.md), so an
adoption landing in the same sweep as a quiescence deadline outruns the
``ProfileChanged`` that would have dropped the candidate — on any axis, at
any cadence. The candidate therefore stamps the profile it was dialled
under, and ``_dialled_stream_unmoved`` refuses a value whose stream moved
before it settled.

Pure app layer: Kodi I/O via the injected gateway, eligibility via the
injected settings adapter, offset reads/writes via the injected OffsetTable,
log sinks injected; no Kodi imports.
"""

import time

from resources.lib.aome.app import events
from resources.lib.aome.domain import formats, policies


class AdjustmentWatcher:
    """Polls the audio-delay infolabel; stores quiesced user adjustments."""

    IDLE_TICK_SECONDS = 1.0     # poll cadence when nothing is happening
    ACTIVE_TICK_SECONDS = 0.25  # tightened cadence while observing a change
    # A foreign value must hold this long to be stored. 2.0s outruns the
    # teardown phantom (docs/kodi-platform-notes.md), whose measured window
    # ran 0.3-1.15s.
    #
    # Cross-component invariant pinned by a contract test: this must stay
    # STRICTLY LONGER than DeviceWatcher.TICK_SECONDS. Lowering it is
    # bounded by the phantom above and by that inequality both.
    QUIESCENCE_SECONDS = 2.0
    INFOLABEL_AUDIO_DELAY = 'Player.AudioDelay'
    _TICK_KEY = 'aome.watcher.tick'

    def __init__(self, dispatcher, session_tracker, gateway, settings,
                 offsets, clock=time.monotonic, *, log_debug, log_warning):
        self._dispatcher = dispatcher
        self._sessions = session_tracker
        self._gateway = gateway
        self._settings = settings
        self._offsets = offsets      # OffsetTable: get/store by profile
        self._clock = clock
        self._log = log_debug
        self._warn = log_warning

        dispatcher.subscribe(events.ProfileChanged, self._on_profile_changed)
        dispatcher.subscribe(events.SettingsChanged, self._on_settings_changed)
        dispatcher.subscribe(events.OffsetApplied, self._on_automatic_delay_set)
        dispatcher.subscribe(events.DelayReset, self._on_automatic_delay_set)
        dispatcher.subscribe(events.WatchTick, self._on_watch_tick)
        dispatcher.subscribe(events.PlaybackStopped, self._on_playback_ended)
        dispatcher.subscribe(events.PlaybackEnded, self._on_playback_ended)

    # -- watchability and the learn gate ----------------------------------------

    def _watchable(self, profile):
        """Watch whenever a profile exists.

        Settling is a user-action fact with its own consumers, so neither
        the learn toggle nor the store's writability gates the watch;
        ``_store_eligible`` owns those at settle time, and profile
        completeness is the store path's concern.
        """
        return profile is not None

    def _store_eligible(self):
        """The learn half's gate, read fresh at settle instant.

        Learning on and the store writable — a permanently unwritable store
        must never reach a store attempt (the settle path's baseline advance
        prevents the re-detect loop).
        """
        return (self._settings.remember_adjustments_enabled()
                and not self._offsets.read_only)

    # -- watch triggers (dispatcher thread) -------------------------------------

    def _on_profile_changed(self, event):
        """Restart the watch against the newly adopted profile.

        A (re)adoption makes any in-flight observation ambiguous: a pending
        candidate was dialed against the previous profile, and the baseline
        belongs to that episode too. Drop both; the next tick re-establishes
        them (the applier, ordered before us, has recorded its apply, so our
        own value reads as self-echo).

        KNOWN LIMITATION, deliberate: an adjustment dialed inside the
        adoption window is dropped, because clearing resets the baseline and
        the value the user is holding is re-adopted as the new baseline on
        the next tick. It fails visibly rather than wrongly, since nothing is
        misfiled, no "Offset saved" toast appears, and the next adjustment
        stores normally.
        """
        if not self._sessions.is_alive(event.session_id):
            return
        session = self._sessions.current
        self._clear_observation(session)
        self._evaluate(session)

    def _on_settings_changed(self, _event):
        session = self._sessions.current
        if session is None:
            return
        self._evaluate(session)

    def _on_automatic_delay_set(self, event):
        """Drop any in-flight observation on our own automatic delay change.

        Handles both ``OffsetApplied`` and ``DelayReset``: either makes the
        pending candidate ambiguous, since it was dialed against the
        superseded resolution. Relying on the next tick's echo comparison
        would leave a hole, because the infolabel can lag the RPC and a
        stale pre-change reading crossing quiescence would then be stored
        (for a reset, re-storing the value the user just deleted).
        """
        if not self._sessions.is_alive(event.session_id):
            return
        self._clear_observation(self._sessions.current)

    def _evaluate(self, session):
        if self._watchable(session.profile):
            # key-replace keeps exactly one live chain, so re-evaluating
            # (ProfileChanged + SettingsChanged in quick succession) is
            # idempotent — never spawns a second watch loop.
            self._schedule_tick(session.session_id, self.IDLE_TICK_SECONDS)
        else:
            self._dispatcher.cancel(self._TICK_KEY)
            self._clear_observation(session)
            self._log(f"AOMe_AdjustmentWatcher: not watching session "
                      f"#{session.session_id} (ineligible: "
                      f"profile={session.profile})")

    def _on_playback_ended(self, _event):
        self._dispatcher.cancel(self._TICK_KEY)

    # -- the poll (dispatcher thread) -------------------------------------------

    def _on_watch_tick(self, event):
        if not self._sessions.is_alive(event.session_id):
            return  # a superseded session's chain is inert
        session = self._sessions.current
        if not self._watchable(session.profile):
            self._clear_observation(session)
            self._log("AOMe_AdjustmentWatcher: no longer watchable; stopping "
                      "watch")
            return  # ProfileChanged/SettingsChanged restart the chain
        # One poll, one reschedule: _observe classifies the reading and only
        # picks the next cadence — every continue-watching path funnels here.
        self._schedule_tick(session.session_id, self._observe(session))

    def _observe(self, session):
        """Classify the current delay reading; return the next tick cadence.

        The baseline (``session.watch_baseline_ms``) is the last value
        accounted for, ours or already stored, and only a change away from it
        while watching can become a user adjustment. The first non-ours value
        a session sees is adopted silently and never stored, so a delay left
        by a failed apply RPC or by pre-existing player state cannot overwrite
        the user's configured offset.

        A foreign change opens a quiescence candidate, which stands in for a
        "user is done" signal and tightens the cadence while it is pending.
        """
        observed = policies.parse_delay_ms(
            self._gateway.infolabel(self.INFOLABEL_AUDIO_DELAY))
        if observed is None:
            self._log("AOMe_AdjustmentWatcher: audio delay unreadable; "
                      "retrying")
            return self.IDLE_TICK_SECONDS

        applied_ms = session.applied[1] if session.applied is not None else None

        if observed == applied_ms:
            # Our own apply echoing back (the applier records session.applied
            # BEFORE the RPC, so this comparison is always current).
            session.watch_baseline_ms = observed
            session.watch_pending = None
            return self.IDLE_TICK_SECONDS

        if session.watch_baseline_ms is None:
            # First observation and it isn't ours: adopt as baseline silently.
            # Never store a value we merely found (failed-apply leftover or
            # pre-existing player state) — only a CHANGE while watching is a
            # user adjustment.
            session.watch_baseline_ms = observed
            self._log(f"AOMe_AdjustmentWatcher: adopting baseline "
                      f"{observed}ms (first observation)")
            return self.IDLE_TICK_SECONDS

        if observed == session.watch_baseline_ms:
            # Nothing changed, or the user dialed back to the baseline before
            # quiescence ("adjust back to what it was" stores nothing).
            session.watch_pending = None
            return self.IDLE_TICK_SECONDS

        # A foreign CHANGE away from the baseline: a quiescence candidate.
        now = self._clock()
        pending = session.watch_pending
        if pending is None or pending[0] != observed:
            # The candidate carries the PROFILE it is being dialled under, so
            # the settle can refuse a value the stream moved out from under.
            # Captured here rather than at settle time, because this is the
            # instant the user's intent attaches to a stream.
            session.watch_pending = (observed, now, session.profile)
            self._log(f"AOMe_AdjustmentWatcher: observing manual adjustment "
                      f"{observed}ms; awaiting quiescence")
            return self.ACTIVE_TICK_SECONDS
        if now - pending[1] < self.QUIESCENCE_SECONDS:
            return self.ACTIVE_TICK_SECONDS
        if self._gateway.active_player_id() == -1:
            # Teardown phantom guard: during a slow stop the delay infolabel
            # can read a parseable 0 before PlaybackStopped lands, so the
            # quiesced "adjustment" belongs to a dying player. Discard the
            # whole observation chain (the baseline is tainted too).
            self._clear_observation(session)
            self._log("AOMe_AdjustmentWatcher: no active player at store "
                      "time; discarding pending adjustment")
            return self.IDLE_TICK_SECONDS
        if not self._dialled_stream_unmoved(session, pending):
            # Same shape as the phantom guard above, and deliberately BEFORE
            # _settle: a value dialled for a stream the playback has left is
            # not a user action for the current one at all, so it must not
            # post UserOffsetSettled and rewind playback either.
            self._clear_observation(session)
            return self.IDLE_TICK_SECONDS
        self._settle(session, observed)
        return self.IDLE_TICK_SECONDS

    # -- settle + store (dispatcher thread) --------------------------------------

    def _settle(self, session, observed_ms):
        """A foreign value held through quiescence: the user-action fact.

        ``UserOffsetSettled`` posts before and independent of storage, but at
        most once per adjustment: the store-failure branch keeps the baseline
        so the store retries, and without the ``watch_settled_ms`` marker
        every retry cycle would re-post the event and rewind playback in a
        loop. The marker is episode state, reset by ``_clear_observation``.
        """
        if session.watch_settled_ms != observed_ms:
            session.watch_settled_ms = observed_ms
            self._dispatcher.post(events.UserOffsetSettled(
                session_id=session.session_id, ms=observed_ms))
        if self._store_eligible():
            self._store(session, observed_ms)
            return
        self._account(session, observed_ms)
        self._log(f"AOMe_AdjustmentWatcher: adjustment {observed_ms}ms "
                  f"settled; not stored (learning off or store read-only)")

    def _store(self, session, observed_ms):
        session.watch_pending = None
        # Read the profile fresh at store time: the write key is derived from
        # whatever profile and toggle value is in force now.
        profile = session.profile
        if not policies.is_complete(profile):
            # Watched but not persistable: account for the value so we don't
            # chase it, but never write an incomplete key.
            self._log(f"AOMe_AdjustmentWatcher: profile incomplete "
                      f"({profile}); not storing {observed_ms}ms")
            self._account(session, observed_ms)
            return

        write_key = self._offsets.write_key(profile)
        if write_key is None:
            # Cannot compose a key (unparseable fps under per-fps): account,
            # never persist. is_complete makes this unreachable in practice;
            # the guard keeps the invariant local.
            self._log(f"AOMe_AdjustmentWatcher: no write key for {profile}; "
                      f"not storing {observed_ms}ms")
            self._account(session, observed_ms)
            return

        previous_ms = self._offsets.stored_ms_at(write_key)
        if previous_ms == observed_ms:
            # Already the stored value (e.g. re-dialed to the configured
            # offset): account for it, emit nothing further.
            self._account(session, observed_ms)
            self._log(f"AOMe_AdjustmentWatcher: {observed_ms}ms already stored "
                      f"for {write_key}; nothing to do")
            return

        # store() re-derives the key internally; both derivations run inside
        # this one handler on the one dispatcher thread, so no settings
        # change can interleave — they are the same key by construction.
        stored_key = self._offsets.store(profile, observed_ms)
        if stored_key is None:
            # The value is still foreign; leave the baseline untouched so the
            # next quiescence cycle retries the store.
            self._warn(f"AOMe_AdjustmentWatcher: failed to store "
                       f"{observed_ms}ms for {write_key}")
            return

        session.watch_baseline_ms = observed_ms
        # The user's value is now the applied value too, so the applier's
        # dedupe guard stays honest.
        session.applied = (stored_key, observed_ms)
        # The store just changed: any remembered miss-chain is stale (a
        # delete->re-teach->delete cycle must re-log its miss, not be
        # swallowed by session-lifetime dedupe).
        session.miss_announced = None
        self._log(f"AOMe_AdjustmentWatcher: Stored audio offset "
                  f"{observed_ms}ms for {stored_key}")
        self._dispatcher.post(events.UserOffsetSaved(
            session_id=session.session_id, profile=profile, ms=observed_ms,
            key=stored_key, previous_ms=previous_ms))

    # -- internals --------------------------------------------------------------

    def _dialled_stream_unmoved(self, session, pending):
        """Whether the stream is still the one the candidate was dialled
        under, judged against the profile stamped when it opened.

        Two conjuncts:

        * IDENTITY — ``policies.stream_identity`` of the stamp equals the
          live ``session.profile``'s, at the toggles read HERE, so the
          comparison is made at the granularity the write key is about to be
          composed at. An axis a toggle folds out cannot refuse a store, and
          one it folds in refuses only while the two disagree at that
          granularity.
        * ENDPOINT — the device both profiles just agreed on, re-read from
          Kodi through ``formats.device_setting_id``. The comparison is
          against Kodi rather than against the profile, which the identity
          conjunct has already vouched for. Gated on the toggle, and the
          condition is in-process, so it is one JSON-RPC round trip per
          quiesced adjustment and none at all with distinct devices off.

        The identity conjunct needs an adoption to have happened, and Kodi
        announces every axis but this one: a device move fires no player
        event, so nothing may have re-gathered at all. Hence the second look
        here and nowhere else.

        Neither device absence is evidence of a move, so both answer True.
        An empty reading normalizes to the all-devices segment, and testing
        it for inequality would read "the endpoint moved to the all bucket"
        from a value the poll deliberately ignores as transient, refusing
        every adjustment for the rest of the playback; a failed read keeps
        the previously adopted device in force, so a value dialled during
        the outage belongs on the key the session is on. They log
        differently, being what a maintainer greps during an outage.

        RESIDUAL: with no usable reading the endpoint conjunct degrades to
        the identity one, so a device move that happened while the read is
        down is invisible here. The DeviceWatcher cancels the candidate the
        instant it DETECTS a move; what neither covers is a move nobody has
        read yet during an outage, which is the blind spot the detector
        already documents.
        """
        dialled = pending[2]
        per_fps = self._settings.per_fps_offsets_enabled()
        spatial = self._settings.distinct_spatial_enabled()
        channels = self._settings.distinct_channels_enabled()
        devices = self._settings.distinct_devices_enabled()
        if (policies.stream_identity(dialled, per_fps, spatial, channels,
                                     devices)
                != policies.stream_identity(session.profile, per_fps, spatial,
                                            channels, devices)):
            self._log(f"AOMe_AdjustmentWatcher: stream moved from "
                      f"{dialled.describe()} to "
                      f"{session.profile.describe()} since this value was "
                      f"dialled; discarding pending adjustment")
            return False
        if not devices:
            return True
        endpoint = dialled.device_id()
        setting_id = formats.device_setting_id(
            self._gateway.condition(formats.CONDITION_PASSTHROUGH))
        raw = self._gateway.setting_value(setting_id)
        if raw is None:
            self._log(f"AOMe_AdjustmentWatcher: could not read {setting_id} "
                      f"at store time; storing under the dialled "
                      f"{endpoint!r}")
            return True
        if not raw:
            self._log(f"AOMe_AdjustmentWatcher: {setting_id} names no device "
                      f"at store time; storing under the dialled "
                      f"{endpoint!r}")
            return True
        live = formats.normalize_device(raw)
        if live != endpoint:
            self._log(f"AOMe_AdjustmentWatcher: output device is now "
                      f"{live!r} (from {setting_id}), not the {endpoint!r} "
                      f"this value was dialled under; discarding pending "
                      f"adjustment")
            return False
        return True

    def _account(self, session, observed_ms):
        """Account for the settled value so it can never re-detect.

        One helper for both halves of the invariant (candidate dropped and
        baseline advanced), since either half alone reintroduces a re-detect
        loop. The store-failure branch is the exception and keeps the
        baseline so the store retries.
        """
        session.watch_pending = None
        session.watch_baseline_ms = observed_ms

    def _clear_observation(self, session):
        """Drop all observation state whenever the watch chain stops.

        The baseline must not survive a not-watching gap: a delay changed
        while watching was off would otherwise compare against the stale
        baseline on re-enable and be stored as a fresh adjustment. Clearing
        makes the first post-gap observation re-adopt silently. The settled
        marker is episode state and falls with the rest.
        """
        session.clear_watch_observation()

    def _schedule_tick(self, session_id, delay):
        """One place for the self-scheduled poll chain (key-replaced)."""
        self._dispatcher.schedule(
            delay, events.WatchTick(session_id=session_id), key=self._TICK_KEY)
