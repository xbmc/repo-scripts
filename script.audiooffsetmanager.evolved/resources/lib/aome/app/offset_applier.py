"""Offset application: gate via policy, resolve via the store, apply, announce.

One decision path, four triggers:

- ``ProfileChanged`` — the detector adopted a (new) complete profile: the
  apply trigger. Not ``PlaybackStarted``, where the profile is always None.
- ``StreamStabilized`` — the retry edge: a failed apply RPC retries on the
  next stabilization, and the ``session.applied`` dedupe makes the common
  already-applied case a no-op.
- ``SettingsChanged`` — the immediate-effect edge: every input to the
  decision is read fresh at decision instant, so re-running it on a settings
  save makes mid-playback edits act now, through the same gates. One
  divergence from the stream-change triggers: a save changes no profile, so
  a foreign delay (the user's hand) still targets the stream in force; the
  miss path's baseline reset is withheld when the delay diverged from our
  last apply (``profile_unchanged``). Only our own orphaned residue (a
  toggle flip stranding the value we applied) is reset by a save.
- ``StoreMutated`` — the management-view edge: a delete/clear that changed
  the store is a resolve moment too, so deleting the playing profile's
  offset takes effect immediately (the marked miss forces its 0 at the
  deletion). Same shape as SettingsChanged otherwise.

Both silent reset paths post a session-stamped ``DelayReset`` on a
successful reset, so the watcher drops any in-flight observation (a reset is
an automatic delay change like an apply).

Two contracts, both pinned by tests:

- **applied-before-RPC**: ``session.applied`` is recorded before the
  ``set_audio_delay`` call and restored on failure. The watcher's self-echo
  suppression compares observed delays against it, so record-after-success
  would let it store our own apply as a user adjustment. Do not reorder.
- **Freshness**: the profile is read from ``session.profile`` at the moment
  of use (the detector is its sole writer, on this same thread); the
  granularity toggles (per-fps, distinct-spatial, distinct-channels) are
  resolved inside the OffsetTable for the same reason.

The apply is eager: it runs on adoption, before stability, because A/V sync
matters immediately. It is marked ``provisional`` unless the session is
already STABLE, and the ``OffsetApplied`` lets the Notifier hold the toast
until stabilization. This component never toasts.

Offsets come from the injected ``OffsetTable``. A miss is a no-op until the
addon has acted on the session, then a zero-reset: before the first
apply/store a miss leaves Kodi's delay untouched (a fresh install must not
clobber the user's own per-file delay); after that the delay in force is
ours or the previous profile's, so an unlearned profile resets it to 0 —
silently for our own residue, or with an ``UnsavedOffsetDiscarded`` (the
"Offset not saved" toast) when it diverged from the last apply. One debug
line per distinct consulted chain (``session.miss_announced`` dedupes), and
the reset is idempotent.

A miss whose consulted chain carries reset markers (the user deleted those
keys) forces the delay to 0 immediately, first action or not: the deletion
is the authorization the gate otherwise waits for. The forced 0 consumes the
markers (one-shot) and is silent.

The applier also publishes the live profile to the home-window property
``script.audiooffsetmanager.evolved.profile``: the write key of the current
complete profile under the current toggle, retracted at every playback
boundary — start included, since an in-place reopen fires no stop callback
and the old key must not outlive its stream — and when the profile is
incomplete. Publishing rides the same four triggers and runs before the
apply gates, so the property stays fresh at every resolve moment (a toggle
flip republishes the other mode's key) and keeps working with applying off.
The management view in the script process reads it to tag the playing
entry; nothing in-process consumes it. Window properties outlive a
crashed service until Kodi exits, so the runtime retracts at service
start/stop via ``clear_published_profile``, which bypasses the repeat-write
dedupe.

Pure app layer: Kodi I/O via the injected gateway, settings via the injected
adapter, log sinks injected; no Kodi imports.
"""

from resources.lib.aome.app import events
from resources.lib.aome.app.adjustment_watcher import AdjustmentWatcher
from resources.lib.aome.domain import policies
from resources.lib.aome.domain.stream_state import StreamState


class OffsetApplier:
    """Applies the stored offset for the session's current profile and
    publishes the live profile's key for the management view."""

    # Cross-process contract with the script process's management view,
    # which reads this home-window property to tag the playing entry.
    PROFILE_PROPERTY = 'script.audiooffsetmanager.evolved.profile'

    def __init__(self, dispatcher, session_tracker, gateway, settings,
                 offsets, *, log_debug, log_warning):
        self._dispatcher = dispatcher
        self._sessions = session_tracker
        self._gateway = gateway
        self._settings = settings
        self._offsets = offsets
        self._log = log_debug
        self._warn = log_warning
        self._published = None

        dispatcher.subscribe(events.ProfileChanged, self._on_profile_changed)
        dispatcher.subscribe(events.StreamStabilized, self._on_stream_stabilized)
        dispatcher.subscribe(events.SettingsChanged, self._on_settings_changed)
        dispatcher.subscribe(events.StoreMutated, self._on_store_mutated)
        dispatcher.subscribe(events.PlaybackStarted, self._on_playback_boundary)
        dispatcher.subscribe(events.PlaybackStopped, self._on_playback_boundary)
        dispatcher.subscribe(events.PlaybackEnded, self._on_playback_boundary)

    # -- triggers (dispatcher thread) --------------------------------------------

    def _on_profile_changed(self, event):
        """Detector adopted a (new) profile: the apply trigger."""
        self._apply(event.session_id)

    def _on_stream_stabilized(self, event):
        """Retry edge: re-run the apply; the dedupe no-ops the common case."""
        self._apply(event.session_id)

    def _on_settings_changed(self, _event):
        """Immediate-effect edge: a settings save re-runs the decision.

        The event carries no session stamp (it is not session work), so the
        live session is fetched here; none live means nothing to reconcile.
        """
        self._reconcile_live_session()

    def _on_store_mutated(self, _event):
        """Management-view edge: a store-changing delete/clear re-runs the
        decision, so deleting the playing profile's offset acts NOW (the
        marked miss forces its 0 at the deletion itself)."""
        self._reconcile_live_session()

    def _on_playback_boundary(self, _event):
        """Retract the published profile at every playback edge.

        A stop/end has no live profile; a start has none YET — and it is
        the only edge an in-place reopen fires, so without it the previous
        stream's key would stand for the whole discovery window (or
        forever, when the new stream never completes a profile).
        """
        self._publish_key(None)

    def _reconcile_live_session(self):
        session = self._sessions.current
        if session is None:
            return
        self._apply(session.session_id, profile_unchanged=True)

    # -- the apply -----------------------------------------------------------------

    def _apply(self, session_id, *, profile_unchanged=False):
        if not self._sessions.is_alive(session_id):
            return  # superseded session: the event is inert
        session = self._sessions.current

        # Read fresh at the moment of use (see Freshness above).
        profile = session.profile
        # Publish before the gates: the indicator reflects what is playing,
        # not whether applying is enabled.
        self._publish_profile(profile)
        if not self._should_apply(profile):
            return

        if profile.player_id == -1:
            self._log("AOMe_OffsetApplier: No valid player ID found to set "
                      "audio delay")
            return

        resolution = self._offsets.resolve(profile)
        if resolution.entry is None:
            # One debug line per distinct consulted chain, then the miss
            # policy — untouched before the addon's first action of the
            # session, zero-reset after; a chain carrying reset markers
            # forces the 0 regardless.
            if session.miss_announced != resolution.tried:
                session.miss_announced = resolution.tried
                self._log(f"AOMe_OffsetApplier: no stored offset for "
                          f"{profile.describe()} (tried "
                          f"{', '.join(resolution.tried)})")
            # A held provisional "applied X" toast cannot survive a miss
            # resolution: whatever the reset paths decide, X is no longer
            # the value this profile stands to announce.
            session.pending_notification = None
            if resolution.reset_keys:
                self._reset_deleted(session, profile, resolution.reset_keys)
            else:
                self._reset_if_owned(session, profile,
                                     profile_unchanged=profile_unchanged)
            return

        key = resolution.key
        delay_ms = resolution.ms

        if session.applied == (key, delay_ms):
            self._log(f"AOMe_OffsetApplier: Offset already applied for "
                      f"{key} at {delay_ms}ms; skipping duplicate apply")
            return

        provisional = session.stream_state is not StreamState.STABLE

        # Bookkeeping BEFORE the RPC (watcher self-echo contract — see the
        # module docstring). Restored on failure so the dedupe guard cannot
        # block the retry.
        previous_applied = session.applied
        session.applied = (key, delay_ms)
        if not self._gateway.set_audio_delay(profile.player_id,
                                             delay_ms / 1000.0):
            session.applied = previous_applied
            self._warn(f"AOMe_OffsetApplier: audio delay RPC failed for "
                       f"{key}; will retry on the next stabilization")
            return

        self._log(f"AOMe_OffsetApplier: Applied {delay_ms}ms for {key} "
                  f"(hit={resolution.hit_kind}, provisional={provisional}); "
                  f"{session.describe()}")
        self._dispatcher.post(events.OffsetApplied(
            session_id=session.session_id, profile=profile, ms=delay_ms,
            provisional=provisional))

    def _reset_deleted(self, session, profile, reset_keys):
        """Force the 0 a deletion promised.

        Runs on a miss whose consulted chain carries reset markers,
        bypassing the ``session.applied`` gate: the user's delete is the
        authorization the gate otherwise waits for. The forced 0 is one-shot
        (markers consumed on success and on the confirmed already-0 case; a
        failed RPC keeps them so the next stabilization retries). Silent: 0
        is the expected outcome of the deletion, so no toast fires.
        """
        raw = self._gateway.infolabel(AdjustmentWatcher.INFOLABEL_AUDIO_DELAY)
        current_ms = policies.parse_delay_ms(raw)
        if current_ms == 0 and (session.applied is None
                                or session.applied[1] == 0):
            # Genuinely at baseline: the label agrees with our bookkeeping.
            # Nothing to do, but the marker is spent. A 0 that contradicts a
            # nonzero session.applied is a stale label (the infolabel can lag
            # our RPC) and falls through to the reset RPC instead; consuming
            # the marker on a stale 0 would cancel the deletion permanently
            # once Kodi's per-file memory replays the old value.
            self._consume_markers(reset_keys)
            return

        # applied-before-RPC contract, same as every other apply path.
        previous_applied = session.applied
        session.applied = (None, 0)
        if not self._gateway.set_audio_delay(profile.player_id, 0.0):
            session.applied = previous_applied
            self._warn("AOMe_OffsetApplier: deleted-profile reset RPC "
                       "failed; will retry on the next stabilization")
            return

        self._consume_markers(reset_keys)
        self._log(f"AOMe_OffsetApplier: reset delay to 0ms for deleted "
                  f"{profile.describe()} (was "
                  f"{'unreadable' if current_ms is None else current_ms}ms; "
                  f"markers {', '.join(reset_keys)})")
        self._dispatcher.post(events.DelayReset(
            session_id=session.session_id))

    def _consume_markers(self, reset_keys):
        for key in reset_keys:
            self._offsets.consume_reset(key)

    def _reset_if_owned(self, session, profile, *, profile_unchanged=False):
        """The miss policy's second half: reset our own stale residue.

        ``session.applied is None`` means the addon has not touched this
        session, so whatever delay exists belongs to the user or Kodi's
        per-file memory and must not be clobbered. Once we have acted, the
        delay in force was set for the previous profile, so an unlearned
        profile returns to 0. The reset is idempotent: a delay already at 0
        is left alone.

        ``profile_unchanged`` (the settings-save and store-mutation
        triggers) withholds the reset when the delay diverged from our last
        apply: those triggers change no profile, so a foreign value still
        targets the stream in force, and wiping it because an unrelated knob
        was saved would clobber the user's hand. Only our own residue,
        orphaned by the trigger itself, is reset. An unreadable delay is also
        left alone on this path.
        """
        if session.applied is None:
            return

        raw = self._gateway.infolabel(AdjustmentWatcher.INFOLABEL_AUDIO_DELAY)
        current_ms = policies.parse_delay_ms(raw)
        if current_ms == 0:
            return

        # Divergence from the last apply means the value being discarded
        # contains a manual adjustment that never reached the store
        # (remember off, or a stream change inside the quiescence window).
        # An unreadable delay resets silently — never toast on a hiccup.
        discarded = None
        if current_ms is not None and current_ms != session.applied[1]:
            discarded = current_ms

        if profile_unchanged and (current_ms is None or discarded is not None):
            shown = 'unreadable' if current_ms is None else f"{current_ms}ms"
            self._log(f"AOMe_OffsetApplier: leaving foreign delay ({shown}) "
                      f"in place for unlearned {profile.describe()} "
                      f"(profile unchanged by this trigger; not ours to "
                      f"reset)")
            return

        previous_applied = session.applied
        session.applied = (None, 0)
        if not self._gateway.set_audio_delay(profile.player_id, 0.0):
            session.applied = previous_applied
            self._warn("AOMe_OffsetApplier: baseline reset RPC failed; "
                       "will retry on the next stabilization")
            return

        self._log(f"AOMe_OffsetApplier: reset delay to 0ms for unlearned "
                  f"{profile.describe()} (was "
                  f"{'unreadable' if current_ms is None else current_ms}ms)")
        self._dispatcher.post(events.DelayReset(
            session_id=session.session_id))
        if discarded is not None:
            self._dispatcher.post(events.UnsavedOffsetDiscarded(
                session_id=session.session_id, profile=profile,
                ms=discarded))

    # -- the published-profile property -------------------------------------------

    def _publish_profile(self, profile):
        """Publish the live profile's write key, or retract for anything less.

        The write key under the current toggle is exactly what the manage
        view's rows are keyed by, so equality there is the "playing now"
        test. An incomplete profile retracts rather than holding the last
        key: a stale tag is worse than none.
        """
        key = None
        if policies.is_complete(profile):
            key = self._offsets.write_key(profile)
        self._publish_key(key)

    def _publish_key(self, key):
        # Dedupe: the repeat triggers (every stabilization) must not
        # re-write an unchanged property.
        if key == self._published:
            return
        self._published = key
        if key:
            self._gateway.set_window_property(self.PROFILE_PROPERTY, key)
        else:
            self._gateway.clear_window_property(self.PROFILE_PROPERTY)

    def clear_published_profile(self):
        """Unconditional retract for the runtime's start/stop hygiene.

        Bypasses the dedupe on purpose: at service start the property may
        hold a value a crashed predecessor never retracted (window
        properties persist until Kodi exits), which fresh dedupe state
        cannot see.
        """
        self._published = None
        self._gateway.clear_window_property(self.PROFILE_PROPERTY)

    def _should_apply(self, profile):
        """Resolve the inputs and log the reason; the decision is the policy's."""
        allowed, reason = policies.should_apply(
            profile, apply_enabled=self._settings.apply_enabled())
        if allowed:
            return True

        if reason == 'apply_off':
            self._log("AOMe_OffsetApplier: applying is off; skipping audio "
                      "offset application")
        elif reason == 'no_profile':
            self._log("AOMe_OffsetApplier: No stream profile available; "
                      "skipping offset")
        elif reason == 'unknown_format':
            self._log(f"AOMe_OffsetApplier: Skipping audio offset - profile "
                      f"incomplete ({profile.describe()})")
        return False
