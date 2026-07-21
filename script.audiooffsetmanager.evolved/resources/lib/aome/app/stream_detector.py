"""Stream detection: scheduled single-shot probes + whole-profile verification.

Patience lives here, expressed as budgeted, session-stamped, cancelable
scheduled events rather than sleeps:

- ``PlaybackStarted`` starts a discovery chain: ``ProbeStream(attempt=n)``
  every ~0.5s (jittered) until the profile is complete or the budget runs
  out (~10s, sized to outlast slow player-id and codec reporting at start).
- A complete profile is adopted (this component is the sole writer of
  ``session.profile`` and owns every stream-state transition), then
  verified: ``VerifyStream`` re-gathers after 1s and requires the whole
  profile (HDR, FPS, and audio) to have held before marking the session
  STABLE and posting ``StreamStabilized``.
- A failed verification (profile changed or went incomplete inside the
  window) re-adopts or re-schedules instead of stranding STABILIZING.
- ``AvChanged`` triggers an immediate single-shot re-probe: unchanged
  profile ignored; changed re-adopts and re-verifies; lost regresses to
  STABILIZING for the verify loop to chase.

Every gather posts ``StreamProbed`` platform facts (log-only).

"Same stream" is judged on the offset-relevant identity
(``policies.stream_identity`` with the live granularity toggles), not
raw dataclass equality: incidental fields (player_id and, per the toggles,
the fps rate, a spatial-variant distinction, or the channel count) can
wiggle between gathers without the stream changing for offset purposes. An
identity-equal gather silently refreshes ``session.profile`` with no
events and no state change; comparing raw equality would strand
verification in a perpetual re-adopt loop.

Verbatim acceptance: the audio and HDR axes carry what Kodi reported,
normalized by ``aome.store.keys`` (case-fold/trim, absence to 'unknown', and
on the HDR axis the cross-build canonicalization). The per-fps granularity
question lives at the store's lookup/write instant. The HDR chain-of-evidence
runs primary -> fallback -> sdr default -> HLG-gamut sniff.

Timing:
- Offsets re-apply eagerly on mid-play changes: adoption posts
  ``ProfileChanged`` immediately (the apply is provisional; notifications
  wait for STABLE), because A/V sync matters before the stream settles.
- HDR- or FPS-only mid-play changes are full change episodes (offset
  re-apply, notification, the 'adjust' seek-back), not just codec changes.

Pure app layer: Kodi I/O through the injected gateway, settings through the
injected facade; no Kodi imports, log sinks injected.
"""

import math
import random
from dataclasses import dataclass

from resources.lib.aome.app import events
from resources.lib.aome.domain import formats, policies
from resources.lib.aome.domain.profile import StreamProfile
from resources.lib.aome.store import keys


INFOLABEL_FPS = 'Player.Process(videofps)'
INFOLABEL_HDR = 'Player.Process(video.source.hdr.type)'
INFOLABEL_HDR_FALLBACK = 'VideoPlayer.HdrType'
INFOLABEL_GAMUT = 'Player.Process(amlogic.eoft_gamut)'


@dataclass(frozen=True)
class StreamFacts:
    """One detection pass: the derived profile plus platform observations.

    ``hdr_source`` records which branch of the chain-of-evidence produced
    the HDR type ('primary', 'fallback', 'default-sdr', or 'gamut-hlg'),
    surfaced in the probe log line.
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


def derive_stream_facts(player_id, raw_codec, raw_channels, raw_fps, raw_hdr,
                        raw_hdr_fallback, raw_gamut):
    """Pure derivation of a StreamProfile from raw single-shot readings.

    The HDR chain-of-evidence runs primary -> fallback -> sdr default, with
    an HLG-via-gamut sniff and echo guards (a reading that merely echoes the
    infolabel name back is treated as absent). Acceptance is verbatim: audio
    strings key the store as reported, HDR strings additionally get the key
    codec's cross-build canonicalization, and fps is the exact parsed rate.
    """
    audio_format = keys.audio_segment(raw_codec)

    try:
        fps_value = float(raw_fps)
        # A rate must be finite and positive to count as detected: 'nan'/
        # 'inf' parse but would blow up fps_int()/key composition later, and
        # a reported 0 is the decoder's not-locked-yet placeholder — storing
        # under an <hdr>|0|<audio> key would strand the offset on a bucket
        # that never recurs.
        if not math.isfinite(fps_value) or fps_value <= 0:
            fps_value = None
    except (ValueError, TypeError):
        fps_value = None

    if _is_valid_infolabel(INFOLABEL_HDR, raw_hdr):
        platform_hdr_full = True
        hdr_raw = raw_hdr
        hdr_source = 'primary'
    else:
        platform_hdr_full = False
        hdr_raw = raw_hdr_fallback
        hdr_source = 'fallback'

    hdr_type = keys.hdr_segment(hdr_raw)
    if hdr_type == formats.UNKNOWN:
        # Absent HDR reading: the chain-of-evidence default. (Echo shapes
        # never reach here: the primary branch is taken only after
        # _is_valid_infolabel screened its echo, and an unresolved fallback
        # reads '' — absence — rather than an echo.)
        hdr_type = 'sdr'
        hdr_source = 'default-sdr'

    gamut_valid = _is_valid_infolabel(INFOLABEL_GAMUT, raw_gamut)
    gamut_info = raw_gamut if gamut_valid else 'not available'
    if hdr_type == 'sdr' and gamut_valid and 'hlg' in raw_gamut.lower():
        hdr_type = 'hlg'
        hdr_source = 'gamut-hlg'

    profile = StreamProfile(
        hdr_type=hdr_type,
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
    # ~10s of discovery at 0.5s spacing — long enough for the player id
    # and codec to both come up on slow starts.
    PROBE_BUDGET = 20
    VERIFY_WINDOW_SECONDS = 1.0
    # Attempt at which a discovery still missing only the frame rate logs
    # its one diagnostic line (~2s in). That shape is the signature of a
    # file that declares no frame rate, leaving Kodi to measure it:
    # Player.Process(videofps) reads 0.000 for ~6s while every other axis
    # is ready. Threshold, not attempt 1: a rate a probe or two behind the
    # codec is ordinary startup, not the signature.
    FPS_WAIT_LOG_ATTEMPT = 5

    _PROBE_KEY = 'aome.detector.probe'
    _VERIFY_KEY = 'aome.detector.verify'

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
        self._log(f"AOMe_StreamDetector: session #{session.session_id} "
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
            self._log(f"AOMe_StreamDetector: discovery complete on attempt "
                      f"{event.attempt}: {facts.profile}")
            self._adopt(session, facts.profile)
        elif event.attempt < self.PROBE_BUDGET:
            if (event.attempt == self.FPS_WAIT_LOG_ATTEMPT
                    and facts.profile.video_fps is None
                    and facts.profile.audio_format != formats.UNKNOWN):
                self._log("AOMe_StreamDetector: only the frame rate is "
                          "still unreported; Kodi is likely measuring it "
                          "because the file does not declare one — "
                          "discovery continues")
            self._dispatcher.schedule(
                self._jittered_spacing(),
                events.ProbeStream(session_id=event.session_id,
                                   attempt=event.attempt + 1),
                key=self._PROBE_KEY)
        else:
            self._discovering = False
            self._warn(f"AOMe_StreamDetector: giving up discovery after "
                       f"{event.attempt} attempts; last probe: {facts.profile}")

    # -- change detection --------------------------------------------------------

    def _on_av_changed(self, _event):
        session = self._sessions.current
        if session is None:
            self._log("AOMe_StreamDetector: AV change with no session; ignoring")
            return
        if self._discovering:
            # The probe chain reads fresh facts on every attempt, so it will
            # observe whatever this change did — no extra work to schedule.
            self._log("AOMe_StreamDetector: AV change during discovery; "
                      "probes will observe it")
            return
        facts = self._gather(session.session_id)
        if self._same_stream(facts.profile, session.profile):
            # Same offset-relevant stream: refresh incidental fields
            # (player_id/channels/raw fps) silently — no events, no state.
            session.profile = facts.profile
            self._log("AOMe_StreamDetector: AV change with unchanged profile; "
                      "ignoring")
            return
        if policies.is_complete(facts.profile):
            self._log(f"AOMe_StreamDetector: stream change detected: "
                      f"{session.profile} -> {facts.profile}")
            self._adopt(session, facts.profile)
        elif session.profile is None:
            # Discovery gave up earlier and the stream is still incomplete —
            # a change means it may be completing now; restart the budget.
            self._discovering = True
            self._log("AOMe_StreamDetector: AV change after exhausted "
                      "discovery; restarting probes")
            self._dispatcher.post(
                events.ProbeStream(session_id=session.session_id, attempt=1))
        else:
            # Had a complete profile, now incomplete: renegotiation in
            # flight. Regress to STABILIZING and let the verify loop
            # re-probe until the stream settles (recovery edge).
            session.mark_verifying()
            self._log("AOMe_StreamDetector: profile lost mid-playback; "
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
        if self._same_stream(facts.profile, session.profile):
            session.profile = facts.profile   # silent incidental-field refresh
            session.mark_stable()
            announce = session.profile_changed_since_stabilized
            session.profile_changed_since_stabilized = False
            self._log(f"AOMe_StreamDetector: profile held for "
                      f"{self.VERIFY_WINDOW_SECONDS}s; session "
                      f"#{event.session_id} stable "
                      f"(profile_changed={announce})")
            self._dispatcher.post(events.StreamStabilized(
                session_id=event.session_id, profile_changed=announce,
                initial=session.stabilized_count == 1))
        elif policies.is_complete(facts.profile):
            self._log(f"AOMe_StreamDetector: profile changed during "
                      f"verification: {session.profile} -> {facts.profile}; "
                      f"re-verifying")
            self._adopt(session, facts.profile)
        else:
            # Profile went incomplete inside the window (codec blip):
            # keep watching. Session-bound: playback stop cancels the key.
            self._log("AOMe_StreamDetector: profile incomplete during "
                      "verification; re-verifying")
            self._schedule_verify(event.session_id)

    # -- internals ----------------------------------------------------------------

    def _same_stream(self, profile, adopted):
        """Offset-relevant identity at the granularity in force now.

        All granularity toggles are read at compare instant: with per-fps
        off, an fps wiggle is an incidental-field refresh; with
        distinct-spatial off, a switch between a codec and its spatial
        variant is too; with distinct-channels off, so is a channel-count
        wiggle. On, each axis joins the identity like the lookup key.
        """
        if adopted is None:
            return False
        per_fps = self._settings.per_fps_offsets_enabled()
        distinct = self._settings.distinct_spatial_enabled()
        channels = self._settings.distinct_channels_enabled()
        return (policies.stream_identity(profile, per_fps, distinct, channels)
                == policies.stream_identity(adopted, per_fps, distinct,
                                            channels))

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
        raw_fps = self._gateway.infolabel(INFOLABEL_FPS)
        raw_hdr = self._gateway.infolabel(INFOLABEL_HDR)
        raw_hdr_fallback = self._gateway.infolabel(INFOLABEL_HDR_FALLBACK)
        raw_gamut = self._gateway.infolabel(INFOLABEL_GAMUT)
        facts = derive_stream_facts(
            player_id=player_id,
            raw_codec=raw_codec,
            raw_channels=raw_channels,
            raw_fps=raw_fps,
            raw_hdr=raw_hdr,
            raw_hdr_fallback=raw_hdr_fallback,
            raw_gamut=raw_gamut,
        )
        # The raw gateway strings are logged verbatim: they are the store's
        # key material, and logs are how key fragmentation gets diagnosed.
        self._log(f"AOMe_StreamDetector: probed {facts.profile} "
                  f"(hdr_source={facts.hdr_source}, "
                  f"platform_hdr_full={facts.platform_hdr_full}, "
                  f"gamut={facts.gamut_info}, "
                  f"raw codec={raw_codec!r} hdr={raw_hdr!r}"
                  f"/{raw_hdr_fallback!r} fps={raw_fps!r})")
        self._dispatcher.post(events.StreamProbed(
            session_id=session_id,
            platform_hdr_full=facts.platform_hdr_full,
            advanced_hlg=facts.advanced_hlg))
        return facts

    def _jittered_spacing(self):
        # Probe jitter: base*(0.8..1.2), floor 0.1s.
        return max(0.1, self.PROBE_SPACING_SECONDS * (0.8 + self._rng() * 0.4))
