# SPDX-License-Identifier: GPL-2.0-only
"""What the rating window shows and what its answer means, free of Kodi windows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from resources.lib.constants import RATING_QUESTION_HOUSEHOLD, RATING_QUESTION_NAMED, RATING_WORDS, WINDOW_COUNT_SOME

# The window could not be shown. Told apart from a skip, because a window that failed once
# will fail for every question after it.
RATE_FAILED = -1

SCORE_WORDS = RATING_WORDS

Localised = Callable[[int], str]


@dataclass(frozen=True)
class RateRequest:
    title: str
    subtitle: str
    poster: str
    question: str
    # "2 of 3" in a run of questions, "" for a single one.
    counter: str = ""
    autoclose_seconds: int = 0
    close_on_playback: bool = False


def question_text(localised: Localised, viewer: str | None) -> str:
    if viewer is None:
        return localised(RATING_QUESTION_HOUSEHOLD)
    # replace rather than %: a translation that drops the placeholder must not raise.
    return localised(RATING_QUESTION_NAMED).replace("%s", viewer, 1)


def counter_text(localised: Localised, index: int, total: int) -> str:
    if total < 2:
        return ""
    return localised(WINDOW_COUNT_SOME).replace("%s", str(index), 1).replace("%s", str(total), 1)
