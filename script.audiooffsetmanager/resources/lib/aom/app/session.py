"""Playback sessions: one object owns ALL per-playback state.

A ``PlaybackSession`` is created on ``PlaybackStarted`` and destroyed on
stop/end. A new playback while one is live (in-place reopen) tears the old
session down and starts a fresh one — so "reset logic" does not exist: a new
session IS the reset, and anything still referencing the old ``session_id``
is inert by construction.

``SessionTracker`` owns the current session and its lifecycle. Its
``PlaybackStarted``/``PlaybackStopped``/``PlaybackEnded`` handlers must be
subscribed BEFORE any component that reads the session for the same events
(the runtime constructs it first, and dispatcher dispatch follows
subscription order; tests/contract pin this). Note the stop/end ordering
consequence: by the time other PLAYBACK_STOPPED/ENDED handlers run, the
session is already gone — the ending session is deliberately not exposed.

Stream-state transitions go through the ``mark_*`` methods so the legal
diagram (see aom.domain.stream_state) lives in ONE place; illegal requests
are ignored and reported via the return value instead of corrupting state.

Pure Python: no Kodi imports; logging callables are injected.
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from resources.lib.aom.app import events
from resources.lib.aom.domain.stream_state import StreamState


def _noop(_message):
    return None


@dataclass
class PlaybackSession:
    session_id: int
    # Monotonic session birth time — the seek quiet-window's "session start
    # counts as seek activity" input.
    started_at: float
    stream_state: StreamState = StreamState.STARTING
    # The session's profile. Written ONLY by the StreamDetector (its sole
    # writer), on the dispatcher thread — where every reader lives too.
    profile: object = None
    # True while a profile (re)adoption has happened since the last
    # StreamStabilized post. The detector consumes it to stamp
    # StreamStabilized.profile_changed, which downstream consumers (the seek
    # scheduler's 'adjust' replay) use to ignore pure re-confirmations (a
    # codec blip that reverted).
    profile_changed_since_stabilized: bool = False
    # (setting_key, delay_ms) — what we believe Kodi's audio delay is set to.
    # TWO sanctioned writers, both on the dispatcher thread: the OffsetApplier
    # records it BEFORE each apply RPC (restoring on failure), and the
    # AdjustmentWatcher updates it when it stores a user's manual value (the
    # user's value IS the applied value; skipping this would make the next
    # same-profile AV event re-apply and re-notify). It is both the applier's
    # dedupe guard and the watcher's self-echo reference.
    applied: tuple = None
    pending_notification: tuple = None      # (setting_key, delay_ms) awaiting STABLE
    paused: bool = False
    # How many times this session has earned STABLE. Written only by
    # mark_stable() (the diagram's one edge into STABLE); the detector stamps
    # StreamStabilized.initial from it — the "is this startup settling?"
    # question is answered by the state machine itself.
    stabilized_count: int = 0
    # Monotonic timestamps; None = never (a 0.0 sentinel would be wrong for
    # monotonic clocks, whose epoch is arbitrary).
    last_seek_activity: Optional[float] = None
    seek_history: dict = field(default_factory=dict)  # reason -> monotonic ts
    # AdjustmentWatcher observation state. The baseline is the last delay
    # value accounted for (ours, or already stored): only a CHANGE away from
    # it can become a user adjustment, so a pre-existing delay the watcher
    # first observes (e.g. left behind by a failed apply RPC) is adopted
    # silently, never stored. watch_pending is the quiescence candidate:
    # (observed_ms, first_seen_monotonic).
    watch_baseline_ms: Optional[int] = None
    watch_pending: tuple = None

    def describe(self):
        """One-line state snapshot for field logs.

        Emitted by the applier after each apply decision so field logs keep a
        greppable state line at the moments that matter.
        """
        setting_id = (self.profile.setting_id()
                      if self.profile is not None else None)
        return (f"session#{self.session_id} state={self.stream_state.value} "
                f"profile={setting_id} applied={self.applied} "
                f"paused={self.paused}")

    # -- stream-state transitions (the only sanctioned writers) ---------------

    def mark_profile_built(self):
        """STARTING -> STABILIZING once a complete profile exists."""
        if self.stream_state is StreamState.STARTING:
            self.stream_state = StreamState.STABILIZING
            return True
        return False

    def mark_verifying(self):
        """Any state -> STABILIZING: a codec verification is now pending."""
        changed = self.stream_state is not StreamState.STABILIZING
        self.stream_state = StreamState.STABILIZING
        return changed

    def mark_stable(self):
        """STABILIZING -> STABLE (the diagram's only edge into STABLE).

        A confirmation landing on STARTING means no verification was ever
        requested for this session — refuse rather than jump states; the
        caller logs it. Returns True when the transition happened. A failed
        verification no longer strands STABILIZING: the StreamDetector
        re-schedules verification until the profile settles (the recovery
        edge).
        """
        if self.stream_state is StreamState.STABILIZING:
            self.stream_state = StreamState.STABLE
            self.stabilized_count += 1
            return True
        return self.stream_state is StreamState.STABLE


class SessionTracker:
    """Owns the current PlaybackSession; allocates monotonically rising ids."""

    def __init__(self, dispatcher, clock=time.monotonic, log_debug=None):
        self._clock = clock
        self._log = log_debug or _noop
        self.current = None
        self._next_id = 1
        dispatcher.subscribe(events.PlaybackStarted, self._on_started)
        dispatcher.subscribe(events.PlaybackStopped, self._on_ended)
        dispatcher.subscribe(events.PlaybackEnded, self._on_ended)
        # The tracker owns generic session state, so the paused flag is
        # written here (not by whichever consumer happens to need it) —
        # subscription order guarantees it is current before any other
        # handler of the same event reads it.
        dispatcher.subscribe(events.Paused, self._on_paused)
        dispatcher.subscribe(events.Resumed, self._on_resumed)

    def is_alive(self, session_id):
        """True while the given session is still the live one.

        Every caller — indeed every reader of session state — runs on the
        dispatcher thread.
        The single read of self.current is kept: it is free, and it makes the
        method safe for any future off-thread caller without a change here.
        """
        current = self.current
        return current is not None and current.session_id == session_id

    def _on_started(self, _event):
        if self.current is not None:
            # In-place reopen: the old session is superseded; every scheduled
            # or marshaled event stamped with its id is now inert.
            self._log(f"AOM_SessionTracker: superseding session "
                      f"#{self.current.session_id} (in-place reopen)")
        self.current = PlaybackSession(session_id=self._next_id,
                                       started_at=self._clock())
        self._next_id += 1
        self._log(f"AOM_SessionTracker: session #{self.current.session_id} started")

    def _on_ended(self, _event):
        if self.current is not None:
            self._log(f"AOM_SessionTracker: session #{self.current.session_id} ended")
        self.current = None

    def _on_paused(self, _event):
        if self.current is not None:
            self.current.paused = True

    def _on_resumed(self, _event):
        if self.current is not None:
            self.current.paused = False
