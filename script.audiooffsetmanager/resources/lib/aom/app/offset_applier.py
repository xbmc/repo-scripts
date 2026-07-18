"""Offset application: gate via policy, apply via gateway, announce typed.

One decision path, three triggers:

- ``ProfileChanged`` — the detector adopted a (new) complete profile: the
  apply trigger. NOT ``PlaybackStarted``: the profile is always None at AV
  start (discovery has not run), so an apply there could only skip.
- ``StreamStabilized`` — the retry edge: a failed apply RPC is retried on
  the next stabilization, and the ``session.applied`` dedupe makes the
  common already-applied case a no-op.
- ``SettingsChanged`` — the settings-save edge: an offset reconfigured in
  the addon settings dialog during playback reaches the live player on
  dialog save, not on the next profile adoption. The same dedupe makes
  every save that did not change the current profile's offset a no-op.
  The AdjustmentWatcher's store-echo is covered by dispatcher
  serialization, NOT by write ordering: ``_store`` runs to completion
  (settings write, then ``session.applied`` update) on the dispatcher
  thread before the posted ``SettingsChanged`` can be dispatched, so the
  dedupe always compares against the just-stored value. An apply here
  announces via ``OffsetApplied`` like any other: an immediate toast when
  the session is STABLE (the dialog-edit case in practice), the usual
  held-until-stable path otherwise — and it stamps the event
  ``user_initiated``, which the seek scheduler keys its 'change' replay
  on, so a dialog edit seeks back exactly like a slider adjustment while
  detector-driven applies never seek. The handler carries its own QUIET
  gates (see its docstring) — every settings save in the process lands
  on this trigger, so a non-actionable save must produce neither log
  noise nor a doomed RPC.

Contracts (pinned by tests):

- **applied-before-RPC**: ``session.applied`` is recorded BEFORE the
  ``set_audio_delay`` call and restored on failure. The AdjustmentWatcher's
  self-echo suppression compares observed delays against ``session.applied``
  — record-after-success would let it store our own apply as a user
  adjustment. Two flow tests pin this at the RPC boundary; do not reorder.
- **Freshness**: the profile is read from ``session.profile`` at the moment
  of use (the detector, on this same dispatcher thread, is its sole writer)
  — never captured across events (settings doctrine).

The apply is *eager*: it runs on adoption, before stability, because A/V
sync matters immediately. It is marked ``provisional`` unless the session is
already STABLE, and the posted ``OffsetApplied(provisional=...)`` lets the
Notifier hold the toast until stabilization. This component never toasts.

Offsets come from the injected ``OffsetTable`` (get by profile; the settings
generator guarantees every setting id exists, so "missing offset" is not a
state).

Pure app layer: Kodi I/O via the injected gateway, settings via the injected
adapter, log sinks injected; no Kodi imports.
"""

from resources.lib.aom.app import events
from resources.lib.aom.domain import policies
from resources.lib.aom.domain.stream_state import StreamState


class OffsetApplier:
    """Applies the configured offset for the session's current profile."""

    def __init__(self, dispatcher, session_tracker, gateway, settings,
                 offsets, *, log_debug, log_warning):
        self._dispatcher = dispatcher
        self._sessions = session_tracker
        self._gateway = gateway
        self._settings = settings
        self._offsets = offsets
        self._log = log_debug
        self._warn = log_warning

        dispatcher.subscribe(events.ProfileChanged, self._on_profile_changed)
        dispatcher.subscribe(events.StreamStabilized, self._on_stream_stabilized)
        dispatcher.subscribe(events.SettingsChanged, self._on_settings_changed)

    # -- triggers (dispatcher thread) --------------------------------------------

    def _on_profile_changed(self, event):
        """Detector adopted a (new) profile: the apply trigger."""
        self._apply(event.session_id)

    def _on_stream_stabilized(self, event):
        """Retry edge: re-run the apply; the dedupe no-ops the common case."""
        self._apply(event.session_id)

    def _on_settings_changed(self, _event):
        """Settings-save edge: push a reconfigured offset to the live player.

        Not session-stamped (the save has no session); applies to whatever
        session is live now. Unlike the detector-driven triggers, this one
        fires for EVERY settings save in the process, so the non-actionable
        cases are gated QUIETLY — no skip-log line per save:

        - no session, or no complete profile yet: nothing to key the offset
          by (the adoption that completes the profile applies it anyway);
        - a pending manual observation: the user is mid-adjustment on the
          player's own delay control — re-applying the stored value now
          would yank the dial, and the watcher would then read our write as
          self-echo and drop the user's candidate;
        - no live player (the watcher's teardown-phantom guard, applied at
          the same hazard): a save landing in the sub-second stop gap would
          RPC a dead player and warn about a retry that can never come.
        """
        session = self._sessions.current
        if session is None:
            return
        profile = session.profile
        if profile is None or not policies.is_complete(profile):
            return
        if session.watch_pending is not None:
            return
        if self._gateway.active_player_id() == -1:
            return
        self._apply(session.session_id, user_initiated=True)

    # -- the apply -----------------------------------------------------------------

    def _apply(self, session_id, user_initiated=False):
        if not self._sessions.is_alive(session_id):
            return  # superseded session: the event is inert
        session = self._sessions.current

        # Freshly derived at the moment of use (settings doctrine).
        profile = session.profile
        if not self._should_apply(profile):
            return

        if profile.player_id == -1:
            self._log("AOM_OffsetApplier: No valid player ID found to set "
                      "audio delay")
            return

        setting_id = profile.setting_id()
        delay_ms = self._offsets.get(profile)

        if session.applied == (setting_id, delay_ms):
            self._log(f"AOM_OffsetApplier: Offset already applied for "
                      f"{setting_id} at {delay_ms}ms; skipping duplicate "
                      f"apply")
            return

        provisional = session.stream_state is not StreamState.STABLE

        # Bookkeeping BEFORE the RPC (watcher self-echo contract — see the
        # module docstring). Restored on failure so the dedupe guard cannot
        # block the retry.
        previous_applied = session.applied
        session.applied = (setting_id, delay_ms)
        if not self._gateway.set_audio_delay(profile.player_id,
                                             delay_ms / 1000.0):
            session.applied = previous_applied
            self._warn(f"AOM_OffsetApplier: audio delay RPC failed for "
                       f"{setting_id}; will retry on the next stabilization")
            return

        self._log(f"AOM_OffsetApplier: Applied {delay_ms}ms for {setting_id} "
                  f"(provisional={provisional}); {session.describe()}")
        self._dispatcher.post(events.OffsetApplied(
            session_id=session.session_id, profile=profile, ms=delay_ms,
            provisional=provisional, user_initiated=user_initiated))

    def _should_apply(self, profile):
        """Resolve the inputs and log the reason; the decision is the policy's."""
        # Only read enable_<hdr> for a KNOWN hdr type: 'enable_unknown' is not
        # a setting, and reading it would emit a spurious settings LOGWARNING
        # on every apply attempt for an undetected stream (the policy skips
        # incomplete profiles as 'unknown_format' before hdr_enabled matters,
        # so False is never the deciding answer here).
        hdr_enabled = (profile is not None and
                       policies.is_complete(profile) and
                       self._settings.is_hdr_enabled(profile.hdr_type))
        allowed, reason = policies.should_apply(
            profile,
            hdr_enabled=hdr_enabled)
        if allowed:
            return True

        if reason == 'no_profile':
            self._log("AOM_OffsetApplier: No stream profile available; "
                      "skipping offset")
        elif reason == 'unknown_format':
            self._log(f"AOM_OffsetApplier: Skipping audio offset - Unknown "
                      f"format detected (HDR: {profile.hdr_type}, "
                      f"Audio: {profile.audio_format}, "
                      f"FPS: {profile.fps_type})")
        elif reason == 'hdr_disabled':
            self._log(f"AOM_OffsetApplier: HDR type {profile.hdr_type} is "
                      f"not enabled in settings")
        return False
