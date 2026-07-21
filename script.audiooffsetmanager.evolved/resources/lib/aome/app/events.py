"""Typed events dispatched on the aome dispatcher.

Events are frozen dataclasses dispatched by type (subscribe registers
against the class); payloads are explicit fields, never positional *args.

SeekChapter and SpeedChanged are posted by the player bridge but currently
have no consumer, kept so the bridge covers Kodi's full playback-callback
surface (chapter jumps also fire onPlayBackSeek, so the seek quiet window
already sees them via SeekOccurred). Pure Python: no Kodi imports.
"""

from dataclasses import dataclass


# --- Player/monitor events (posted by kodi.player_bridge / monitor_bridge) --

@dataclass(frozen=True)
class PlaybackStarted:
    """Kodi onAVStarted: audio and video are rendering."""


@dataclass(frozen=True)
class AvChanged:
    """Kodi onAVChange: raw, noisy; stability is judged downstream."""


@dataclass(frozen=True)
class PlaybackStopped:
    """Kodi onPlayBackStopped: user stopped playback."""


@dataclass(frozen=True)
class PlaybackEnded:
    """Kodi onPlayBackEnded: playback reached the end."""


@dataclass(frozen=True)
class Paused:
    """Kodi onPlayBackPaused."""


@dataclass(frozen=True)
class Resumed:
    """Kodi onPlayBackResumed."""


@dataclass(frozen=True)
class SeekOccurred:
    """Kodi onPlayBackSeek — any seek, from any source (feeds quiet window)."""
    time_ms: int
    offset_ms: int


@dataclass(frozen=True)
class SeekChapter:
    """Kodi onPlayBackSeekChapter."""
    chapter: int


@dataclass(frozen=True)
class SpeedChanged:
    """Kodi onPlayBackSpeedChanged."""
    speed: int


@dataclass(frozen=True)
class SettingsChanged:
    """Kodi Monitor.onSettingsChanged: refresh cached flags; never write here."""


# --- Detection events (posted/consumed by the StreamDetector) ---------------

@dataclass(frozen=True)
class ProbeStream:
    """Self-scheduled stream probe attempt for a session."""
    session_id: int
    attempt: int


@dataclass(frozen=True)
class VerifyStream:
    """Scheduled whole-profile stability verification (key-replaced)."""
    session_id: int
    seq: int


@dataclass(frozen=True)
class StreamProbed:
    """A detection pass observed the platform (log-only).

    Posted on every gather (probes, AV-change re-probes, verifications). The
    fields are facts about what the platform reported; nothing stores them,
    but they show which detection path fired in the logs.
    """
    session_id: int
    platform_hdr_full: bool
    advanced_hlg: bool


@dataclass(frozen=True)
class StreamStabilized:
    """The session's profile held for the verification window.

    ``profile_changed`` is False for a pure re-confirmation (a blip that
    reverted with no adoption): the state machine re-earned STABLE, but no
    stream change is announced, so the seek scheduler skips the 'adjust'
    replay. Defaults True so hand-posted events announce.

    ``initial`` is True on the session's first stabilization (startup
    settling, not a mid-play change); the detector stamps it from
    ``session.stabilized_count``, and the seek scheduler skips the 'adjust'
    replay for it. Defaults False so hand-posted change events act like
    changes.
    """
    session_id: int
    profile_changed: bool = True
    initial: bool = False


@dataclass(frozen=True)
class ProfileChanged:
    """The session's profile was created or replaced."""
    session_id: int


# --- Offset/adjustment events -----------------------------------------------

@dataclass(frozen=True)
class OffsetApplied:
    """An offset was applied via JSON-RPC (provisional until STABLE)."""
    session_id: int
    profile: object  # StreamProfile
    ms: int
    provisional: bool


@dataclass(frozen=True)
class DelayReset:
    """A zero-reset RPC landed (baseline or deleted-profile).

    Posted by the applier's reset paths on a successful reset only (the
    already-0, preserve, and failed-RPC branches post nothing). The watcher
    consumes it to drop any in-flight observation, since a reset is an
    automatic delay change like an apply. No OffsetApplied fires for a reset,
    so no apply toast; the diverged-baseline reset separately posts
    UnsavedOffsetDiscarded, while the deleted-profile reset is fully silent.
    """
    session_id: int


@dataclass(frozen=True)
class UnsavedOffsetDiscarded:
    """The zero-reset discarded a manual adjustment that was never stored.

    Posted by the applier's miss path when an unlearned profile resets the
    delay to baseline and the value in force diverged from our last apply
    (learning off, or a stream change inside the quiescence window). The
    Notifier raises the "Offset not saved" toast; a reset of our own residue
    posts nothing. ``ms`` is the discarded value, for the toast/log only.
    """
    session_id: int
    profile: object  # StreamProfile
    ms: int


@dataclass(frozen=True)
class UserOffsetSettled:
    """A manual audio-offset adjustment held through quiescence.

    The user-action fact, posted by the AdjustmentWatcher for every quiesced
    foreign value, regardless of whether the learn loop stores it
    (``UserOffsetSaved`` is the storage fact). Consumers reacting to the
    adjustment itself (the seek scheduler's 'change' replay) subscribe here,
    so they keep working with learning off, an incomplete profile, or an
    unwritable store. ``ms`` is the settled value, for logging only.
    """
    session_id: int
    ms: int


@dataclass(frozen=True)
class UserOffsetSaved:
    """The adjustment watcher stored a user's manual offset change.

    The profile/ms are captured at store time on the dispatcher thread, so
    consumers (notification, 'change' seek-back) act on exactly what was
    stored, and an in-place reopen between post and dispatch makes the event
    inert. ``key`` is the store key the value landed under.
    """
    session_id: int
    profile: object  # StreamProfile
    ms: int
    key: str = None


# --- Seek scheduling events --------------------------------------------------

@dataclass(frozen=True)
class ExecuteSeek:
    """Self-scheduled seek execution attempt (re-validated at fire time).

    ``requested_at`` (monotonic) rides on the event so the deadline is
    measured from the request with no side bookkeeping; a re-request
    key-replaces the chain with a fresh requested_at (deadline restart).
    """
    session_id: int
    reason: str
    requested_at: float


# --- Notifier events ----------------------------------------------------------

@dataclass(frozen=True)
class RaiseToast:
    """Self-scheduled toast release delayed past a fading predecessor.

    See the fade-guard section of ``aome.app.notifier`` for the mechanics.
    Not session-stamped: the payload describes a fact that stays true even
    if the session ends inside the deferral. The surface is pre-rendered at
    request time, so every toast kind can ride this one event.
    """
    message: str
    title: object       # str, or None for the gui's addon-name default
    duration_ms: int
    dedupe_key: object  # Notifier dedupe identity; None for notices
    enabled: object     # bound per-kind gate accessor re-checked at fire
                        # time (live setting), or None = ungated notice


# --- Watcher events -----------------------------------------------------------

@dataclass(frozen=True)
class WatchTick:
    """Recurring adjustment-watcher poll tick for a session."""
    session_id: int


# --- Store lifecycle ----------------------------------------------------------

@dataclass(frozen=True)
class StoreCorrupted:
    """The offsets file was quarantined to .bad at load (one-shot).

    Posted by the runtime after construction when the store's corruption
    flag was set; the Notifier owns the user-facing notice (the
    composition root never raises GUI toasts itself).
    """


# --- Store mutation channel (script process -> service) ----------------------

@dataclass(frozen=True)
class StoreMutationRequested:
    """A cross-process store mutation request received over NotifyAll.

    Posted by the monitor bridge verbatim from the untrusted payload (fields
    may be None or wrong-typed); the StoreMutationHandler owns validation
    and the op whitelist (delete/clear/import only, no value field).
    ``request_id`` is echoed on the ack so the script process can match
    replies.
    """
    op: object
    key: object = None
    request_id: object = None


@dataclass(frozen=True)
class StoreMutated:
    """A whitelisted mutation changed the live (in-memory) store.

    Posted after a delete that removed an entry or a clear with entries,
    including their persist-failed variants (OffsetStore keeps the in-memory
    change when only the disk write fails, and the live session resolves
    against memory). A missing-key delete, an empty clear, and refused ops
    post nothing. The applier consumes it like ``SettingsChanged``: a
    mutation is a resolve moment for the live session (deleting the playing
    profile's offset takes effect immediately), and it changes no profile,
    so the same foreign-delay preservation applies. ``op``/``key`` ride
    along for the debug trail only.
    """
    op: str
    key: object = None
