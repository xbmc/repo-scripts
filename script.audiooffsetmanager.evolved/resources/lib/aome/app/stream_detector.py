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
- ``AudioDeviceChanged`` (the DeviceWatcher's polled fact, since Kodi fires
  nothing for a core setting change) rides the same path. Its payload is
  logged, never trusted: this component re-gathers for authority, exactly as
  it treats Kodi's own ``AvChanged``.

A mid-session change is adopted eagerly unless the reading is SUSPECT: the
device segment moved AND the passthrough condition dropped true -> false.
Kodi closes the old audio codec before opening the new one, and with no
codec to ask the condition reads false, resolving the decoded endpoint — so
at that instant a genuine device move and a codec-switch gap are one fact.
A suspect gather is held and re-verified rather than adopted, and adopted
once a gather a verify window later agrees with it.

The rule is directional because the gap can only read FALSE, so a gather
that RAISED the condition is provably not it. What that leaves uncovered is
accepted: a switch into a bitstreamed track spends its gap reading false on
the decoded endpoint, which is what an ordinary decoded codec change reads
too, so it is adopted eagerly and the decoded endpoint's offset lands until
the condition rises.

``SettingsChanged`` is deliberately NOT a trigger. A save changes no stream
fact, so re-gathering on one buys nothing and costs a full probe at an
arbitrary instant: any infolabel transiently blank at that moment yields a
confident, complete profile, since the HDR chain-of-evidence defaults to
'sdr', and this component would adopt it — a wrong offset, a toast and a
seek-back for no net change. The one case a re-gather was meant to serve, a
distinct-devices flip, belongs to the ``DeviceWatcher``. Do not add that
subscription.

"Same stream" is judged on the offset-relevant identity
(``policies.stream_identity`` with the live granularity toggles) rather than
raw dataclass equality, since incidental fields wiggle between gathers
without the stream changing for offset purposes. An identity-equal gather
silently refreshes ``session.profile``; comparing raw equality would strand
verification in a perpetual re-adopt loop.

Acceptance is verbatim: the audio and HDR axes carry what Kodi reported,
normalized by ``aome.store.keys``, and the granularity question lives at the
store's lookup/write instant. Adoption posts ``ProfileChanged`` immediately
and the apply is marked provisional, because A/V sync matters before the
stream settles. Every gather also posts ``StreamProbed`` platform facts
(log-only).

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
# The device axis's source strings are deliberately NOT here: the
# DeviceWatcher reads the same three, so they live with the rest of the
# device facts in ``domain.formats`` and neither app component imports the
# other.


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
                        raw_hdr_fallback, raw_gamut, raw_device='',
                        passthrough=False):
    """Pure derivation of a StreamProfile from raw single-shot readings.

    The HDR chain-of-evidence runs primary -> fallback -> sdr default, with
    an HLG-via-gamut sniff and echo guards. Acceptance is verbatim: audio
    strings key the store as reported, HDR strings additionally get the key
    codec's cross-build canonicalization, and fps is the exact parsed rate.

    ``raw_device`` is Kodi's audio-device setting verbatim and is carried
    onto the profile untouched, since the id/name split and the 'all'
    degradation are the store's job. None (the read failed) is carried
    through untouched too, because that is the state
    ``policies.is_complete`` screens on; '' is the "deliberately not read"
    reading the detector passes with distinct-devices off.
    """
    audio_format = keys.audio_segment(raw_codec)

    try:
        fps_value = float(raw_fps)
        # A rate must be finite and positive to count as detected: 'nan' and
        # 'inf' parse but blow up key composition later, and a reported 0 is
        # the decoder's not-locked-yet placeholder, which would strand the
        # offset on a bucket that never recurs.
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
        # Absent HDR reading: the chain-of-evidence default. Echo shapes
        # never reach here, since the primary branch is taken only after
        # _is_valid_infolabel screened its echo and an unresolved fallback
        # reads '' rather than an echo.
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
        audio_device=raw_device,
        passthrough=passthrough,
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
    # file declaring no frame rate, leaving Kodi to measure it, so
    # Player.Process(videofps) reads 0.000 for ~6s while every other axis is
    # ready. A threshold rather than attempt 1, since a rate a probe or two
    # behind the codec is ordinary startup.
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
        # The gather held back by the suspect rule. It stands until a
        # gather contradicts it (a different reading, an adoption, or a
        # return to the adopted profile); only _hold_if_suspect sets it.
        self._pending_suspect = None

        dispatcher.subscribe(events.PlaybackStarted, self._on_playback_started)
        dispatcher.subscribe(events.AvChanged, self._on_av_changed)
        dispatcher.subscribe(events.AudioDeviceChanged,
                             self._on_audio_device_changed)
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
        self._pending_suspect = None
        self._log(f"AOMe_StreamDetector: session #{session.session_id} "
                  f"discovery started")
        self._dispatcher.post(
            events.ProbeStream(session_id=session.session_id, attempt=1))

    def _on_playback_ended(self, _event):
        self._cancel_scheduled()
        self._discovering = False
        self._pending_suspect = None

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

    def _on_audio_device_changed(self, event):
        """A polled output-device move: re-probe exactly like an AV change.

        The event's ``device`` is logged, never consumed: ``_gather``
        re-reads the setting, so this component stays the sole authority on
        what the profile says. Only the canonical id segment reaches the log,
        since the friendly half can carry a person's name. The shared path
        adopts and posts ``ProfileChanged``, which is what makes the new
        device's offset apply without waiting for a stream event Kodi will
        never send.
        """
        if not self._sessions.is_alive(event.session_id):
            return
        self._log(f"AOMe_StreamDetector: audio output device changed to "
                  f"{formats.normalize_device(event.device)!r}; re-probing")
        self._reevaluate('device change')

    def _on_av_changed(self, _event):
        self._reevaluate('AV change')

    def _reevaluate(self, reason):
        """Single-shot re-probe: unchanged ignored, changed adopted, lost chased.

        ``reason`` names the trigger in the log lines only. Kodi's AV change
        and a polled device move take the identical path, since both mean
        "what we adopted may no longer describe the stream we are keying on".
        """
        session = self._sessions.current
        if session is None:
            self._log(f"AOMe_StreamDetector: {reason} with no session; "
                      f"ignoring")
            return
        if self._discovering:
            # The probe chain reads fresh facts on every attempt, so it will
            # observe whatever this change did — no extra work to schedule.
            self._log(f"AOMe_StreamDetector: {reason} during discovery; "
                      f"probes will observe it")
            return
        facts = self._gather(session.session_id)
        if self._same_stream(facts.profile, session.profile):
            # Same offset-relevant stream: refresh incidental fields
            # (player_id/channels/raw fps) silently — no events, no state.
            self._pending_suspect = None
            self._refresh(session, facts.profile)
            self._log(f"AOMe_StreamDetector: {reason} with unchanged profile; "
                      f"ignoring")
            return
        if policies.is_complete(facts.profile):
            if self._hold_if_suspect(session, facts.profile, reason):
                return
            self._log(f"AOMe_StreamDetector: stream change detected: "
                      f"{session.profile} -> {facts.profile}")
            self._adopt(session, facts.profile)
        elif session.profile is None:
            # Discovery gave up earlier and the stream is still incomplete —
            # a change means it may be completing now; restart the budget.
            self._discovering = True
            self._pending_suspect = None
            self._log(f"AOMe_StreamDetector: {reason} after exhausted "
                      f"discovery; restarting probes")
            self._dispatcher.post(
                events.ProbeStream(session_id=session.session_id, attempt=1))
        else:
            # Had a complete profile, now incomplete: renegotiation in
            # flight. Regress to STABILIZING and let the verify loop
            # re-probe until the stream settles (recovery edge).
            session.mark_verifying()
            self._log("AOMe_StreamDetector: profile lost mid-playback; "
                      "verifying until it settles")
            if self._pending_suspect is None:
                # A held reading already armed one, and re-arming pushes its
                # deadline out by a whole window each time a trigger lands:
                # a storm faster than the window would hold the second look
                # off indefinitely.
                self._schedule_verify(session.session_id)

    # -- verification: whole-profile quiescence ---------------------------------

    def _on_verify(self, event):
        if not self._sessions.is_alive(event.session_id):
            return
        if event.seq != self._verify_seq:
            # Superseded verification. key-replace already supersedes the
            # pending timer; the seq guard protects any future path that
            # lets a stale VerifyStream reach the queue.
            return
        session = self._sessions.current
        facts = self._gather(event.session_id)
        if self._same_stream(facts.profile, session.profile):
            self._pending_suspect = None
            self._refresh(session, facts.profile)  # silent incidental fields
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
            if self._hold_if_suspect(session, facts.profile, 'verification',
                                     second_look=True):
                return
            self._log(f"AOMe_StreamDetector: profile changed during "
                      f"verification: {session.profile} -> {facts.profile}; "
                      f"re-verifying")
            self._adopt(session, facts.profile)
        else:
            # Profile went incomplete inside the window (codec blip):
            # keep watching, and keep any held reading — an unreadable
            # gather contradicts nothing. Re-arms unconditionally, unlike
            # its sibling in _reevaluate: this branch runs because the one
            # pending verify just fired, so skipping would leave none armed
            # at all. Session-bound: playback stop cancels the key.
            self._log("AOMe_StreamDetector: profile incomplete during "
                      "verification; re-verifying")
            self._schedule_verify(event.session_id)

    # -- internals ----------------------------------------------------------------

    def _same_stream(self, profile, adopted):
        """Offset-relevant identity at the granularity in force now.

        Every granularity toggle is read at compare instant. An axis its
        toggle folds out makes a wiggle an incidental-field refresh rather
        than a stream change; an axis its toggle folds in joins the identity
        exactly as it joins the lookup key.
        """
        if adopted is None:
            return False
        per_fps = self._settings.per_fps_offsets_enabled()
        distinct = self._settings.distinct_spatial_enabled()
        channels = self._settings.distinct_channels_enabled()
        devices = self._settings.distinct_devices_enabled()
        return (policies.stream_identity(profile, per_fps, distinct, channels,
                                         devices)
                == policies.stream_identity(adopted, per_fps, distinct,
                                            channels, devices))

    def _refresh(self, session, profile):
        """Silently replace the session's profile with an identity-equal gather.

        Guarded on completeness, which is the invariant this component owes
        the rest of the graph: ``session.profile`` is only ever written with
        a profile the store can key. An identity-equal gather CAN be
        incomplete on an axis the identity does not carry (an unreadable
        device when the adopted one was the 'all' bucket, or an fps that
        momentarily fails to parse with per-fps off), and writing that in
        would leave the applier, the publisher and the learn loop all reading
        an incomplete profile for a stream that never changed. Keeping the
        previous facts is better: they are the ones the session is keyed on,
        and the next gather refreshes them.
        """
        if policies.is_complete(profile):
            session.profile = profile

    def _hold_if_suspect(self, session, profile, reason, second_look=False):
        """Hold a suspect changed gather rather than adopt it; True when held.

        Suspect is the module docstring's rule, asked of a complete,
        identity-changed gather. ``adopted is None`` is load-bearing rather
        than defensive: an exhausted discovery leaves a live session with no
        profile, and its next complete gather arrives here.

        A held gather stands as evidence until something contradicts it, so
        a trigger that merely re-reads it neither replaces it nor restarts
        the verify it armed — a trigger stream faster than the window would
        otherwise defer adoption for as long as it lasted.

        Only ``second_look``, the verify path, settles on agreement, since
        only there does a whole window separate the two reads. Not while
        playback is paused, though: Kodi recomputes the condition per demux
        packet, so a paused player latches whatever it last read and
        elapsed time proves nothing about it.
        """
        adopted = session.profile
        if (adopted is None
                or not adopted.passthrough
                or profile.passthrough
                or profile.device_id() == adopted.device_id()):
            return False
        if self._same_stream(profile, self._pending_suspect):
            if not second_look:
                self._log(f"AOMe_StreamDetector: {reason}: still the held "
                          f"reading; its verification stands")
                return True
            if not session.paused:
                return False
            self._log("AOMe_StreamDetector: paused while a held reading "
                      "awaits verification; re-verifying")
            self._schedule_verify(session.session_id)
            return True
        self._pending_suspect = profile
        session.mark_verifying()
        self._log(f"AOMe_StreamDetector: {reason}: the output device moved "
                  f"as the passthrough condition dropped, so {adopted} -> "
                  f"{profile} is held for verification")
        self._schedule_verify(session.session_id)
        return True

    def _adopt(self, session, profile):
        """Write the session's profile and (re-)earn stability for it."""
        self._pending_suspect = None
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
        # Whether the PLAYER is bitstreaming this stream, which decides
        # WHICH device setting names its endpoint (one-way: see
        # formats.device_setting_id). Ungated, because a condition is an
        # in-process read and it is the JSON-RPC setting read below that
        # needs the toggle. False also covers "no player / not knowable
        # yet", which is the right default: Kodi routes a non-RAW stream to
        # the ordinary device, so a stream still negotiating reads that one
        # rather than reading nothing.
        passthrough = self._gateway.condition(formats.CONDITION_PASSTHROUGH)
        # The one gathered fact read under a toggle. gateway.setting_value
        # is a full JSON-RPC round trip, and with distinct-devices off the
        # reading keys nothing, so a discovery chain would spend up to
        # PROBE_BUDGET round trips on a fact nobody consults.
        #
        # The two branches answer two DIFFERENT absences and must not be
        # merged: '' is "deliberately not read", which is complete because
        # no key consults the axis, while the gateway's None is "read and
        # failed", which is incomplete so discovery keeps probing and a live
        # session keeps the device it is already keyed on.
        if self._settings.distinct_devices_enabled():
            raw_device = self._gateway.setting_value(
                formats.device_setting_id(passthrough))
        else:
            raw_device = ''
        facts = derive_stream_facts(
            player_id=player_id,
            raw_codec=raw_codec,
            raw_channels=raw_channels,
            raw_fps=raw_fps,
            raw_hdr=raw_hdr,
            raw_hdr_fallback=raw_hdr_fallback,
            raw_gamut=raw_gamut,
            raw_device=raw_device,
            passthrough=passthrough,
        )
        # The raw gateway strings are logged verbatim, since they are the
        # store's key material and logs are how key fragmentation gets
        # diagnosed. The device is the exception: only its id half is
        # logged, never the friendly half. That id half stays RAW here
        # uniquely, because this is the raw-readings line and the same
        # line's profile repr renders the canonical segment beside it, so
        # the pair exposes a spelling problem normalization would hide. A
        # failed read logs as None, which is the one place it is told apart
        # from an absent one (profile.describe() renders both '?').
        logged_device = (None if raw_device is None
                         else formats.split_device(raw_device)[0])
        self._log(f"AOMe_StreamDetector: probed {facts.profile} "
                  f"(hdr_source={facts.hdr_source}, "
                  f"platform_hdr_full={facts.platform_hdr_full}, "
                  f"gamut={facts.gamut_info}, "
                  f"raw codec={raw_codec!r} passthrough={passthrough} "
                  f"hdr={raw_hdr!r}"
                  f"/{raw_hdr_fallback!r} fps={raw_fps!r} "
                  f"device={logged_device!r})")
        self._dispatcher.post(events.StreamProbed(
            session_id=session_id,
            platform_hdr_full=facts.platform_hdr_full,
            advanced_hlg=facts.advanced_hlg))
        return facts

    def _jittered_spacing(self):
        # Probe jitter: base*(0.8..1.2), floor 0.1s.
        return max(0.1, self.PROBE_SPACING_SECONDS * (0.8 + self._rng() * 0.4))
