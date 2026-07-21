"""Stream stability states: has the stream settled enough to act on?

    STARTING ──(profile built)──▶ STABILIZING ──(profile held ~1s)──▶ STABLE
                                       ▲                                │
                                       └──(profile change detected)─────┘

Consumers check ``session.stream_state is StreamState.STABLE``. The
StreamDetector drives every transition, judging stability on the whole
profile (HDR + FPS + audio, not just the codec).

Pure Python: no Kodi imports.
"""

from enum import Enum


class StreamState(Enum):
    STARTING = 'starting'        # session exists, no complete profile yet
    STABILIZING = 'stabilizing'  # profile built, not yet confirmed stable
    STABLE = 'stable'            # whole profile held through the verify window
