"""Adjustment watching: poll the audio-delay infolabel, store user changes.

The watcher polls ``Player.AudioDelay`` on the dispatcher thread via
self-scheduled ``WatchTick`` events. Watching the value rather than the OSD
slider dialog catches every source of an adjustment: a keymap, a remote app,
or a JSON-RPC ``Player.SetAudioDelay`` all change the delay without opening
a dialog.

Watching and storing are separately gated. Watchability (``_watchable``) is
just "a profile exists": the settle is a user-action fact with its own
consumers (every quiesced value posts ``UserOffsetSettled``, which the seek
scheduler's 'change' replay rides), independent of the learn loop. Storing
is the learn half (``_store_eligible``: "Learn audio offsets" on and the
store writable); only then does the settle also store and post
``UserOffsetSaved``. A settle that cannot store still advances the baseline
(no re-detect/re-fail loop), and the ``watch_settled_ms`` marker keeps the
event at one per adjustment even on the store-failure retry path. The apply
toggle gates neither half: with applying off, dials still settle and, with
learning on, still store (the re-teach mode). The store path re-validates
the whole profile before writing, so an incomplete stream is watched and
settles but never stores.

Baseline rule: ``session.watch_baseline_ms`` is the last delay value
accounted for (our own apply, or a value already stored). Only a change away
from it observed while watching can become a user adjustment. The first
non-ours value a session sees is adopted as the baseline silently, never
stored — the failed-RPC-leftover guard: a delay left by a failed apply RPC
or pre-existing player state must not overwrite the user's configured offset.

Quiescence stands in for a "user is done" signal: a foreign value must hold
unchanged for ``QUIESCENCE_SECONDS`` before it is stored (the tick cadence
tightens to ``ACTIVE_TICK_SECONDS`` while a candidate is pending). Two
teardown-phantom defenses back this up: during a slow stop (measured at
0.3-1.15s) Kodi's delay infolabel reads a parseable 0 while the session is
still alive, indistinguishable from a user dialing to 0. QUIESCENCE_SECONDS
outruns that window, and the store path re-checks
``gateway.active_player_id()`` at store time, discarding the observation
when the player is already gone.

Self-echo suppression: an automatic apply is a JSON-RPC player call, so our
own applied value shows up in the infolabel like a user's would. The applier
records ``session.applied`` before issuing the RPC precisely so
``observed == session.applied[1]`` here is always current; a match is our
own value (baseline-refresh, never store). An automatic apply landing inside
a pending quiescence window supersedes the candidate, since its target is
ambiguous. This is enforced structurally at three points: ``OffsetApplied``
and ``DelayReset`` both clear the observation here, and the
StoreMutationHandler clears it synchronously at the mutation itself (queued
events leave timer-interleave windows, and the already-0/failed-RPC reset
branches post no event) — without which a candidate dialed just before a
delete could quiesce and re-store the very entry the user deleted.

Adoption (StreamDetector) and store (here) are serialized on one thread, and
the write key is derived from ``session.profile`` plus the live granularity
toggles (per-fps, distinct-spatial, distinct-channels) at store instant, so
a store can never interleave with a concurrent profile re-adoption.

Pure app layer: Kodi I/O via the injected gateway, eligibility via the
injected settings adapter, offset reads/writes via the injected OffsetTable,
log sinks injected; no Kodi imports.
"""

import time

from resources.lib.aome.app import events
from resources.lib.aome.domain import policies


class AdjustmentWatcher:
    """Polls the audio-delay infolabel; stores quiesced user adjustments."""

    IDLE_TICK_SECONDS = 1.0     # poll cadence when nothing is happening
    ACTIVE_TICK_SECONDS = 0.25  # tightened cadence while observing a change
    # Foreign value must hold this long to be stored. 2.0s outruns the
    # teardown phantom: stop windows where the delay infolabel reads a
    # parseable 0 while the session is still alive ran 0.3-1.15s, and a
    # shorter quiescence let that phantom 0 store over the user's offset.
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
        the learn toggle nor the store's writability gates the watch (the
        settle-time ``_store_eligible`` check owns those). Profile
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
        if not self._sessions.is_alive(event.session_id):
            return
        session = self._sessions.current
        # A (re)adoption makes any in-flight observation ambiguous: a pending
        # candidate was dialed against the previous profile, and the baseline
        # belongs to that episode too. Drop both; the next tick re-establishes
        # them (the applier, ordered before us, has recorded its apply, so our
        # own value reads as self-echo).
        self._clear_observation(session)
        self._evaluate(session)

    def _on_settings_changed(self, _event):
        session = self._sessions.current
        if session is None:
            return
        self._evaluate(session)

    def _on_automatic_delay_set(self, event):
        """Drop any in-flight observation on our own automatic delay change.

        Handles both ``OffsetApplied`` and ``DelayReset``. Any automatic
        delay change makes an in-flight observation ambiguous: the pending
        candidate was dialed against the superseded resolution. Relying on
        the next tick's echo comparison would leave a hole, since the
        infolabel can lag the RPC and a stale pre-change reading crossing
        quiescence then would be stored (for a reset, re-storing the value
        the user just deleted). Dropping the chain here makes the first
        post-change observation re-adopt or echo-match cleanly.
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
        """Classify the current delay reading; return the next tick cadence."""
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
            session.watch_pending = (observed, now)
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
        self._settle(session, observed)
        return self.IDLE_TICK_SECONDS

    # -- settle + store (dispatcher thread) --------------------------------------

    def _settle(self, session, observed_ms):
        """A foreign value held through quiescence: the user-action fact.

        ``UserOffsetSettled`` posts before and independent of storage, but
        at most once per adjustment: the store-failure branch keeps the
        baseline so the store retries, and without the ``watch_settled_ms``
        marker every retry cycle would re-post the event and rewind playback
        in a loop. The marker is episode state, reset by
        ``_clear_observation``. When the learn half is gated off, the settled
        value is accounted for immediately.
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

        if self._offsets.stored_ms_at(write_key) == observed_ms:
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
            key=stored_key))

    # -- internals --------------------------------------------------------------

    def _account(self, session, observed_ms):
        """Account for the settled value so it can never re-detect.

        One helper for both halves of the invariant (candidate dropped and
        baseline advanced) — a re-detect loop is what either half alone
        reintroduces. The store-failure branch is the exception: it keeps the
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
        session.watch_pending = None
        session.watch_baseline_ms = None
        session.watch_settled_ms = None

    def _schedule_tick(self, session_id, delay):
        """One place for the self-scheduled poll chain (key-replaced)."""
        self._dispatcher.schedule(
            delay, events.WatchTick(session_id=session_id), key=self._TICK_KEY)
