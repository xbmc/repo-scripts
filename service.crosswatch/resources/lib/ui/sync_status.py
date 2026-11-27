# SPDX-License-Identifier: GPL-2.0-only
"""What the library sync status window shows, and what the household chose on it."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Tone = Literal["good", "busy", "stopped"]

# The window's answer when the household pressed "Send existing ratings".
SEND_RATINGS = "send_ratings"


@dataclass(frozen=True)
class StatusRow:
    """A line under "Needs you". A problem only explains, so selecting it shows its full
    text; any other row opens the step that deals with it."""

    key: str
    text: str
    problem: bool = False


@dataclass(frozen=True)
class StatusRequest:
    heading: str
    state: str
    tone: Tone
    summary: str
    counts: tuple[str, ...]
    needs_you: str
    rows: tuple[StatusRow, ...]
    empty: str
    note: str
    send_ratings: str
