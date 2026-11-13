"""Whether an episode found by its season and episode number is the same
episode Kodi has.

An episode without a usable id of its own (one scraped from TVmaze carries
only a TVmaze id) can only be found at TMDB or TheTVDB by its number under
the show. Sites number some shows differently (split double episodes, a TV
cut against a streaming cut), so a number alone proves nothing: the title or
the air date has to agree as well. A wrong match writes another episode's
title and plot, which is worse than leaving the episode as it is, so every
doubt rejects.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from resources.lib.engine.idverify import normalize_title
from resources.lib.engine.textrules import is_placeholder_title

# Dates of one episode at two sites differ by a day at most when both record
# the same broadcast (time zones, a late-night slot). A streaming release
# against a weekly broadcast is weeks apart and is not the same date.
DATE_TOLERANCE_DAYS = 1

# "Home, Part 1", "Home Part 1", "Home Pt. 1" and "Home (1)" are one title:
# normalize_title has already dropped the punctuation, so the marker word
# before the number is all that differs.
_PART_MARKER = re.compile(r"\b(?:part|pt|deel|teil|partie|parte)\s+(\d+)\b")


@dataclass(frozen=True)
class SiteEpisode:
    """One episode of a site's season list."""

    ep_id: str
    season: int
    number: int
    aired: str
    # The site's titles for the episode, one per language asked.
    titles: tuple[str, ...]


@dataclass(frozen=True)
class MatchVerdict:
    """The outcome for one site: the matched episode and why it passed
    ("title" or "date"), or no episode and "not_found" / "rejected"."""

    episode: SiteEpisode | None
    reason: str


# A key that is only a number, a generic word and a number, or an SxxEyy code
# names a position, not an episode: "Deel 3" at two sites that cut a series
# differently are two different episodes.
_GENERIC_KEY = re.compile(
    r"^(?:(?:chapter|episode|ep|afl|aflevering|folge|capitulo|hoofdstuk)\s*)?\d+$"
    r"|^s\d+\s*e\d+$"
)


def episode_title_key(text: str | None) -> str:
    """The comparison form of an episode title; "" when the title says
    nothing about which episode it is (blank, a placeholder, a bare number,
    "Part 3", "Afl. 3", "S01E03")."""
    text = (text or "").strip()
    if not text or is_placeholder_title(text):
        return ""
    key = _PART_MARKER.sub(r"\1", normalize_title(text))
    return "" if _GENERIC_KEY.match(key) else key


def _parse_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def _close(a: date, b: date) -> bool:
    return abs((a - b).days) <= DATE_TOLERANCE_DAYS


def check_number_match(
    kodi_title: str | None,
    kodi_aired: str | None,
    season: int,
    number: int,
    site: Sequence[SiteEpisode],
) -> MatchVerdict:
    """Match Kodi's episode against the site episode with the same number.

    It passes on the title when any of the site's titles agrees, or on the
    date when it lies within DATE_TOLERANCE_DAYS of Kodi's and no other
    episode of that season does: a season released on one day (a streaming
    drop), or a neighbour aired the next night, makes the date ambiguous.
    """
    candidate = next(
        (ep for ep in site if ep.season == season and ep.number == number), None,
    )
    if candidate is None:
        return MatchVerdict(None, "not_found")

    key = episode_title_key(kodi_title)
    if key and any(episode_title_key(t) == key for t in candidate.titles):
        return MatchVerdict(candidate, "title")

    kodi_date = _parse_date(kodi_aired)
    own = _parse_date(candidate.aired)
    if kodi_date and own and _close(kodi_date, own):
        near = [
            ep for ep in site
            if ep.season == season
            and (d := _parse_date(ep.aired)) is not None and _close(kodi_date, d)
        ]
        if near == [candidate]:
            return MatchVerdict(candidate, "date")
    return MatchVerdict(None, "rejected")
