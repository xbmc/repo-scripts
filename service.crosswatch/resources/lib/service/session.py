# SPDX-License-Identifier: GPL-2.0-only
"""One playback, from onAVStarted to stop.

Player.getTime and getTotalTime raise once playback stops, so the final position cannot be
read at onPlayBackStopped. The tick samples while playback runs and the stop event uses the
last sample.

An unknown duration is a real state, not an error: Kodi reports zero for live TV, for
streams and at the instant onAVStarted fires. percent() therefore returns None rather than
0.0, because the receiver discards a stop below one percent.
"""

from __future__ import annotations

from resources.lib.constants import SEEK_MIN_GAP_SECONDS
from resources.lib.identity import Identity
from resources.lib.models import MediaItem


class PlaybackSession:
    def __init__(self, session_id: str, media: MediaItem, identity: Identity) -> None:
        self.session_id = session_id
        self.media = media
        self.identity = identity
        self.position_ms: int | None = None
        self.duration_ms: int | None = None
        self.completed = False
        self._last_emitted_at: float | None = None
        self._seeked = False

    def sample(self, position_ms: int | None, duration_ms: int | None) -> None:
        if position_ms is not None:
            self.position_ms = int(position_ms)
        if duration_ms:
            self.duration_ms = int(duration_ms)

    def percent(self) -> float | None:
        if not self.duration_ms or self.position_ms is None:
            return None
        raw = (float(self.position_ms) / float(self.duration_ms)) * 100.0
        return round(max(0.0, min(100.0, raw)), 1)

    def mark_complete(self) -> None:
        """Played to the end. The flag survives an unknown duration; position cannot."""
        self.completed = True
        if self.duration_ms:
            self.position_ms = self.duration_ms

    def note_seek(self) -> None:
        """Record that the viewer jumped. The next eligible tick emits; the callback does not.

        Emitting from the callback would put a network submit on the one thread that
        delivers callbacks and observes abort.
        """
        self._seeked = True

    def should_emit_progress(self, now: float, interval: float, paused: bool) -> bool:
        """True once per interval, and after a seek once the floor has passed.

        The caller supplies the clock and the paused flag, so this stays a pure decision.
        """
        if interval <= 0:
            return False
        if paused:
            # Nothing is advancing, so there is nothing to report. Crucially the timestamp
            # is dragged forward too: a session paused for an hour must not look an hour
            # overdue on the first tick after resume and fire immediately. A seek recorded
            # while paused is kept, and lands when playback resumes.
            self._last_emitted_at = now
            return False
        if self._last_emitted_at is None:
            # The start event has just carried this position, so do not duplicate it. The
            # seek flag is deliberately NOT cleared here: a seek between on_av_started and
            # the first tick is real and must survive.
            self._last_emitted_at = now
            return False

        elapsed = now - self._last_emitted_at
        if self._seeked:
            # Floored, not immediate. Kodi's seek debounce is user-configurable to zero and
            # analog seek repeats twice a second, so an unfloored seek branch emits once per
            # tick for as long as the button is held.
            if elapsed < SEEK_MIN_GAP_SECONDS:
                return False
        elif elapsed < interval:
            return False

        self._last_emitted_at = now
        self._seeked = False
        return True
