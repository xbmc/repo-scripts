# SPDX-License-Identifier: GPL-2.0-only
"""What the library sync setup window shows and what it returns; no Kodi objects here."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SetupRequest:
    heading: str
    intro: str
    # One line per viewer, then shared and no owner, each "label: counts".
    counts: tuple[str, ...]
    note: str
    warnings: tuple[str, ...]
    ratings_label: str
    # False: the window says why and offers only Close.
    can_start: bool = True


@dataclass(frozen=True)
class SetupResult:
    start: bool
    existing_ratings: bool = False
