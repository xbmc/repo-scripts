"""Stream detection: scheduled single-shot probes + whole-profile verification.

Patience lives HERE, expressed as budgeted, session-stamped, cancelable
scheduled events — never as sleeps:

- ``PlaybackStarted`` starts a discovery chain: ``ProbeStream(attempt=n)``
  every ~0.5s (jittered) until the profile is complete or the budget runs
  out. The budget (~10s) covers slow platforms negotiating the player id
  and the audio codec.
- A complete profile is adopted (this component is the SOLE writer of
  ``session.profile`` and the owner of every stream-state transition), then
  verified: ``VerifyStream`` re-gathers after 1s and requires the WHOLE
  profile — HDR, FPS and audio, not just the codec — to have held before
  marking the session STABLE and posting ``StreamStabilized``.
- A failed verification (profile changed or went incomplete inside the
  window) re-adopts or re-schedules verification instead of stranding the
  session STABILIZING — the recovery edge.
- ``AvChanged`` triggers an immediate single-shot re-probe: unchanged
  profile → ignored; changed → re-adopt + re-verify; lost → regress to
  STABILIZING and let the verify loop chase it.

Every gather posts ``StreamProbed`` platform facts for the PlatformRecorder.

"Same stream" is judged on the OFFSET-RELEVANT identity — the setting_id()
axes (hdr/fps-bucket/audio) — not raw dataclass equality: incidental fields
(player_id, audio_channels, video_fps) can wiggle between gathers
(channel-count flicker during passthrough sync, VFR fps re-reads) without
the stream changing for offset purposes. An identity-equal gather silently
refreshes ``session.profile`` (so downstream readers see fresh incidental
fields) with no events and no state change; comparing raw equality instead
would strand verification in a perpetual re-adopt loop.

Pure app layer: Kodi I/O goes through the injected gateway, settings reads
through the injected facade; no Kodi imports, log sinks are injected.
"""

import random
from dataclasses import dataclass

from resources.lib.aom.app import events
from resources.lib.aom.domain import formats, policies
from resources.lib.aom.domain.profile import StreamProfile


INFOLABEL_FPS = 'Player.Process(videofps)'
INFOLABEL_HDR = 'Player.Process(video.source.hdr.type)'
INFOLABEL_HDR_FALLBACK = 'VideoPlayer.HdrType'
INFOLABEL_GAMUT = 'Player.Process(amlogic.eoft_gamut)'


@dataclass(frozen=True)
class StreamFacts:
    """One detection pass: the derived profile plus platform observations.

    ``hdr_source`` records which branch of the chain-of-evidence produced
    the HDR type ('primary', 'fallback', 'default-sdr', or 'gamut-hlg') —
    surfaced in the probe log line so field logs show WHICH detection path
    fired.
    """
    profile: StreamProfile
    platform_hdr_full: bool
    advanced_hlg: bool
    gamut_info: str
    hdr_source: str


def _is_valid_infolabel(label, value):
    """Echo guard: xbmc.getInfoLabel returns the literal label text when it
    cannot resolve a label, so value==label means "no data", not data."""
    return bool(value and value.strip() and value.lower() != label.lower())


def _same_stream(profile, adopted):
    """Offset-relevant identity: True when both map to the same setting key.

    See the module docstring — raw dataclass equality would also compare
    player_id/audio_channels/video_fps, which may wiggle between gathers.
    """
    return adopted is not None and profile.setting_id() == adopted.setting_id()


def _derive_audio_format(raw_codec):
    """Map a reported codec string onto the settings vocabulary.

    Ordered substring match — eac3 before ac3 is load-bearing — with PCM
    fallback; 'unknown'/'none' normalize to the unknown sentinel.
    """
    reported = raw_codec.lower()
    for valid_format in formats.AUDIO_FORMATS:
        if valid_format in reported:
            return valid_format
    if raw_codec in ('unknown', 'none'):
        return formats.UNKNOWN
    return 'pcm'


def derive_stream_facts(player_id, raw_codec, raw_channels, raw_fps, raw_hdr,
                        raw_hdr_fallback, raw_gamut, fps_override_enabled):
    """Pure derivation of a StreamProfile from raw single-shot readings.

    The HDR chain-of-evidence, echo guards, HLG-via-gamut sniff, FPS
    bucketing and override collapse all live here. One deliberate
    asymmetry: the post-normalization echo check compares against the
    PRIMARY label even for the fallback value (the fallback returns ''
    rather than an echo when unresolved, so only the primary echo shape
    occurs in practice).

    Args are raw strings as read from the gateway; ``fps_override_enabled``
    is a callable ``hdr_type -> bool`` (settings read resolved by the
    caller's facade so this function stays pure).
    """
    audio_format = _derive_audio_format(raw_codec)

    try:
        fps_value = int(float(raw_fps))
        fps_type = fps_value if fps_value in formats.FPS_BUCKETS else formats.UNKNOWN
    except (ValueError, TypeError):
        fps_value = None
        fps_type = formats.UNKNOWN

    if _is_valid_infolabel(INFOLABEL_HDR, raw_hdr):
        platform_hdr_full = True
        hdr_type = raw_hdr
        hdr_source = 'primary'
    else:
        platform_hdr_full = False
        hdr_type = raw_hdr_fallback
        hdr_source = 'fallback'

    hdr_type = hdr_type.replace('+', 'plus').replace(' ', '').lower()
    if not hdr_type or hdr_type == INFOLABEL_HDR.lower():
        hdr_type = 'sdr'
        hdr_source = 'default-sdr'
    elif hdr_type == 'hlghdr':
        hdr_type = 'hlg'
    if hdr_type not in formats.HDR_TYPES:
        hdr_type = formats.UNKNOWN

    gamut_valid = _is_valid_infolabel(INFOLABEL_GAMUT, raw_gamut)
    gamut_info = raw_gamut if gamut_valid else 'not available'
    if hdr_type == 'sdr' and gamut_valid and 'hlg' in raw_gamut.lower():
        hdr_type = 'hlg'
        hdr_source = 'gamut-hlg'

    if hdr_type != formats.UNKNOWN and not fps_override_enabled(hdr_type):
        fps_type = formats.FPS_ALL

    profile = StreamProfile(
        hdr_type=hdr_type,
        fps_type=fps_type,
        audio_format=audio_format,
        video_fps=fps_value,
        player_id=player_id,
        audio_channels=raw_channels,
    )
    return StreamFacts(
        profile=profile,
        platform_hdr_full=platform_hdr_full,
        advanced_hlg=gamut_valid,
        gamut_info=gamut_info,
        hdr_source=hdr_source,
    )


class StreamDetector:
    """Probe/verify orchestration; sole writer of ``session.profile``."""

    PROBE_SPACING_SECONDS = 0.5
    # ~10s of discovery at 0.5s spacing — enough for slow platforms to
    # negotiate the player id and the audio codec.
    PROBE_BUDGET = 20
    VERIFY_WINDOW_SECONDS = 1.0

    _PROBE_KEY = 'aom.detector.probe'
    _VERIFY_KEY = 'aom.detector.verify'

    def __init__(self, dispatcher, session_tracker, gateway, settings_facade,
                 *, log_debug, log_warning, rng=random.random):
        self._dispatcher = dispatcher
        self._sessions = session_tracker
        self._gateway = gateway
        self._settings = settings_facade
        self._log = log_debug
        self._warn = log_warning
        self._rng = rng
        # Single live session at a time: plain fields, reset on start/stop.
        # Events stamped with a superseded session_id are dropped on receipt.
        self._discovering = False
        self._verify_seq = 0

        dispatcher.subscribe(events.PlaybackStarted, self._on_playback_started)
        dispatcher.subscribe(events.AvChanged, self._on_av_changed)
        dispatcher.subscribe(events.ProbeStream, self._on_probe)
        dispatcher.subscribe(events.VerifyStream, self._on_verify)
        dispatcher.subscribe(events.PlaybackStopped, self._on_playback_ended)
        dispatcher.subscribe(events.PlaybackEnded, self._on_playback_ended)

    # -- lifecycle (dispatcher thread) -----------------------------------------

    def _on_playback_started(self, _event):
        session = self._sessions.current
        if session is None:
            return  # tracker subscribes first; defensive only
        self._cancel_scheduled()
        self._discovering = True
        self._log(f"AOM_StreamDetector: session #{session.session_id} "
                  f"discovery started")
        self._dispatcher.post(
            events.ProbeStream(session_id=session.session_id, attempt=1))

    def _on_playback_ended(self, _event):
        self._cancel_scheduled()
        self._discovering = False

    def _cancel_scheduled(self):
        self._dispatcher.cancel(self._PROBE_KEY)
        self._dispatcher.cancel(self._VERIFY_KEY)

    # -- discovery: budgeted probe chain ---------------------------------------

    def _on_probe(self, event):
        if not self._sessions.is_alive(event.session_id):
            return  # superseded session: the scheduled probe is inert
        session = self._sessions.current
        facts = self._gather(event.session_id)
        if policies.is_complete(facts.profile):
            self._discovering = False
            self._log(f"AOM_StreamDetector: discovery complete on attempt "
                      f"{event.attempt}: {facts.profile}")
            self._adopt(session, facts.profile)
        elif event.attempt < self.PROBE_BUDGET:
            self._dispatcher.schedule(
                self._jittered_spacing(),
                events.ProbeStream(session_id=event.session_id,
                                   attempt=event.attempt + 1),
                key=self._PROBE_KEY)
        else:
            self._discovering = False
            self._warn(f"AOM_StreamDetector: giving up discovery after "
                       f"{event.attempt} attempts; last probe: {facts.profile}")

    # -- change detection --------------------------------------------------------

    def _on_av_changed(self, _event):
        session = self._sessions.current
        if session is None:
            self._log("AOM_StreamDetector: AV change with no session; ignoring")
            return
        if self._discovering:
            # The probe chain reads fresh facts on every attempt, so it will
            # observe whatever this change did — no extra work to schedule.
            self._log("AOM_StreamDetector: AV change during discovery; "
                      "probes will observe it")
            return
        facts = self._gather(session.session_id)
        if _same_stream(facts.profile, session.profile):
            # Same offset-relevant stream: refresh incidental fields
            # (player_id/channels/raw fps) silently — no events, no state.
            session.profile = facts.profile
            self._log("AOM_StreamDetector: AV change with unchanged profile; "
                      "ignoring")
            return
        if policies.is_complete(facts.profile):
            self._log(f"AOM_StreamDetector: stream change detected: "
                      f"{session.profile} -> {facts.profile}")
            self._adopt(session, facts.profile)
        elif session.profile is None:
            # Discovery gave up earlier and the stream is still incomplete —
            # a change means it may be completing now; restart the budget.
            self._discovering = True
            self._log("AOM_StreamDetector: AV change after exhausted "
                      "discovery; restarting probes")
            self._dispatcher.post(
                events.ProbeStream(session_id=session.session_id, attempt=1))
        else:
            # Had a complete profile, now incomplete: renegotiation in
            # flight. Regress to STABILIZING and let the verify loop
            # re-probe until the stream settles (recovery edge).
            session.mark_verifying()
            self._log("AOM_StreamDetector: profile lost mid-playback; "
                      "verifying until it settles")
            self._schedule_verify(session.session_id)

    # -- verification: whole-profile quiescence ---------------------------------

    def _on_verify(self, event):
        if not self._sessions.is_alive(event.session_id):
            return
        if event.seq != self._verify_seq:
            # Superseded verification. key-replace already supersedes the
            # pending timer; the seq guard documents intent and protects any
            # future path that lets a stale VerifyStream reach the queue.
            return
        session = self._sessions.current
        facts = self._gather(event.session_id)
        if _same_stream(facts.profile, session.profile):
            session.profile = facts.profile   # silent incidental-field refresh
            session.mark_stable()
            announce = session.profile_changed_since_stabilized
            session.profile_changed_since_stabilized = False
            self._log(f"AOM_StreamDetector: profile held for "
                      f"{self.VERIFY_WINDOW_SECONDS}s; session "
                      f"#{event.session_id} stable "
                      f"(profile_changed={announce})")
            self._dispatcher.post(events.StreamStabilized(
                session_id=event.session_id, profile_changed=announce,
                initial=session.stabilized_count == 1))
        elif policies.is_complete(facts.profile):
            self._log(f"AOM_StreamDetector: profile changed during "
                      f"verification: {session.profile} -> {facts.profile}; "
                      f"re-verifying")
            self._adopt(session, facts.profile)
        else:
            # Profile went incomplete inside the window (codec blip):
            # keep watching. Session-bound: playback stop cancels the key.
            self._log("AOM_StreamDetector: profile incomplete during "
                      "verification; re-verifying")
            self._schedule_verify(event.session_id)

    # -- internals ----------------------------------------------------------------

    def _adopt(self, session, profile):
        """Write the session's profile and (re-)earn stability for it."""
        session.profile = profile
        session.profile_changed_since_stabilized = True
        if not session.mark_profile_built():
            session.mark_verifying()
        self._dispatcher.post(
            events.ProfileChanged(session_id=session.session_id))
        self._schedule_verify(session.session_id)

    def _schedule_verify(self, session_id):
        self._verify_seq += 1
        self._dispatcher.schedule(
            self.VERIFY_WINDOW_SECONDS,
            events.VerifyStream(session_id=session_id, seq=self._verify_seq),
            key=self._VERIFY_KEY)

    def _gather(self, session_id):
        """One single-shot detection pass; posts platform facts as it goes."""
        player_id = self._gateway.active_player_id()
        if player_id == -1:
            raw_codec, raw_channels = formats.UNKNOWN, formats.UNKNOWN
        else:
            raw_codec, raw_channels = self._gateway.audio_info(player_id)
        facts = derive_stream_facts(
            player_id=player_id,
            raw_codec=raw_codec,
            raw_channels=raw_channels,
            raw_fps=self._gateway.infolabel(INFOLABEL_FPS),
            raw_hdr=self._gateway.infolabel(INFOLABEL_HDR),
            raw_hdr_fallback=self._gateway.infolabel(INFOLABEL_HDR_FALLBACK),
            raw_gamut=self._gateway.infolabel(INFOLABEL_GAMUT),
            fps_override_enabled=self._settings.fps_override_enabled,
        )
        self._log(f"AOM_StreamDetector: probed {facts.profile} "
                  f"(hdr_source={facts.hdr_source}, "
                  f"platform_hdr_full={facts.platform_hdr_full}, "
                  f"gamut={facts.gamut_info})")
        self._dispatcher.post(events.StreamProbed(
            session_id=session_id,
            platform_hdr_full=facts.platform_hdr_full,
            advanced_hlg=facts.advanced_hlg))
        return facts

    def _jittered_spacing(self):
        # Retry jitter: base*(0.8..1.2), floor 0.1s.
        return max(0.1, self.PROBE_SPACING_SECONDS * (0.8 + self._rng() * 0.4))
