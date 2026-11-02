"""What to ask SubDL for, from what Kodi knows about the playing video.

SubDL resolves one title per request. When any id is sent, the name and the file name
are ignored, and two ids that point at different titles fail the whole request. So
each attempt sends exactly one way of finding the title, strongest first, and the
caller stops at the first attempt that finds a title.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from . import releases

_IMDB = re.compile(r"^tt\d{5,10}$")
_MAX_TEXT = 255  # the API's limit for film_name and file_name


@dataclass
class PlayingItem:
    """The video in the player, as far as Kodi knows it. Every field may be empty."""

    title: str = ""
    original_title: str = ""
    year: Optional[int] = None
    tvshow: str = ""
    tvshow_original: str = ""
    tvshow_year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    #: The item's own ids. For a library episode these name the episode, not the show.
    imdb_id: str = ""
    tmdb_id: str = ""
    #: The show's ids, read from Kodi's library for a library episode.
    show_imdb_id: str = ""
    show_tmdb_id: str = ""
    #: The playing file's release name ("Film.2010.1080p.BluRay.x264-GROUP"), or "".
    filename: str = ""
    #: True when Kodi's library supplied the item, so its ids are trustworthy.
    from_library: bool = False

    def __post_init__(self) -> None:
        # Outside the library Kodi knows no season or episode, but the file name does.
        if self.filename and (self.season is None or self.episode is None):
            found = releases.parse_episode(self.filename)
            if found:
                self.season, self.episode = found

    @property
    def is_episode(self) -> bool:
        return self.episode is not None and (bool(self.tvshow) or self.season is not None)


@dataclass
class Attempt:
    """One search request: how the title is found, plus the episode filter."""

    kind: str  # imdb, tmdb, title, original_title, filename, manual
    params: Dict[str, str] = field(default_factory=dict)
    #: Year the found title must have (give or take one), for searches by name.
    expect_year: Optional[int] = None
    #: (season, episode) the subtitles must belong to, or None for a film.
    episode: Optional[Tuple[Optional[int], int]] = None


def imdb_id(value: str) -> str:
    """The id in the form tt0133093, or "" for anything else.

    Bare digits are refused on purpose: Kodi's IMDBNumber holds the TMDB or TVDB id
    when that scraper is the item's default, and reading "603" as tt0000603 would
    find a different film.
    """
    text = (value or "").strip().lower()
    return text if _IMDB.match(text) else ""


def tmdb_id(value: str) -> str:
    text = (value or "").strip()
    return text if text.isdigit() and int(text) > 0 else ""


def _text(value: str) -> str:
    return " ".join((value or "").split())[:_MAX_TEXT]


def _episode_params(season: Optional[int], episode: Optional[int]) -> Dict[str, str]:
    params = {"type": "tv"}
    if season is not None:
        params["season_number"] = str(season)
    if episode is not None:
        params["episode_number"] = str(episode)
    return params


def _add(plan: List[Attempt], attempt: Attempt) -> None:
    if all(existing.params != attempt.params for existing in plan):
        plan.append(attempt)


def _names(item: PlayingItem, *names: str) -> List[str]:
    """Distinct names worth searching. Outside the library Kodi's title is often just
    the file name, which the file-name search below parses far better."""
    found: List[str] = []
    for name in names:
        name = _text(name)
        if name and name not in found and not releases.is_exact(name, item.filename):
            found.append(name)
    return found


def build_plan(item: PlayingItem) -> List[Attempt]:
    """Attempts for an automatic search, strongest first."""
    plan: List[Attempt] = []
    if item.is_episode:
        target = (item.season, item.episode)
        base = _episode_params(item.season, item.episode)
        for kind, key, value in (
            ("imdb", "imdb_id", imdb_id(item.show_imdb_id)),
            ("tmdb", "tmdb_id", tmdb_id(item.show_tmdb_id)),
            # Outside the library an add-on may put the show's IMDb id on the episode.
            # A wrong guess costs one request: SubDL answers that it found no title.
            ("imdb", "imdb_id", "" if item.from_library else imdb_id(item.imdb_id)),
        ):
            if value:
                _add(plan, Attempt(kind, dict(base, **{key: value}), episode=target))
        for name in _names(item, item.tvshow, item.tvshow_original):
            _add(plan, Attempt("title", dict(base, film_name=name), item.tvshow_year, target))
        if item.filename:
            _add(plan, Attempt("filename", dict(base, file_name=_text(item.filename)), episode=target))
        return plan

    movie = {"type": "movie"}
    for kind, key, value in (
        ("imdb", "imdb_id", imdb_id(item.imdb_id)),
        ("tmdb", "tmdb_id", tmdb_id(item.tmdb_id)),
    ):
        if value:
            _add(plan, Attempt(kind, dict(movie, **{key: value})))
    for name in _names(item, item.title, item.original_title):
        _add(plan, Attempt("title", dict(movie, film_name=name), item.year))
    if item.filename:
        # No type: the file may be an episode that Kodi knows nothing about.
        year = item.year or releases.parse_year(item.filename)
        _add(plan, Attempt("filename", {"file_name": _text(item.filename)}, year))
    return plan


_MANUAL_EPISODE = re.compile(r"(?:s(\d{1,2})[ ._-]?e(\d{1,4})|(\d{1,2})x(\d{2,3}))(?![0-9])", re.I)
_MANUAL_YEAR = re.compile(r"[\s(\[]+(19[2-9]\d|20\d{2})[)\]]?\s*$")


def build_manual_plan(text: str, playing: Optional[PlayingItem] = None) -> List[Attempt]:
    """Attempts for text typed into Kodi's manual search.

    "tt0133093" searches by IMDb id and "Show S02E05" or "Show 2x05" searches that
    episode. "Film 1999" or "Film (1999)" is first searched as typed (it might be
    "Blade Runner 2049") and then without the year, which must then match. Plain
    text while an episode is playing searches that name for the same season and
    episode: the usual reason to search by hand is that the library's show name
    differs from SubDL's.
    """
    text = _text(text)
    if not text:
        return []
    if imdb_id(text):
        return [Attempt("manual", {"imdb_id": imdb_id(text)})]

    match = _MANUAL_EPISODE.search(text)
    if match:
        season = int(match.group(1) or match.group(3))
        episode = int(match.group(2) or match.group(4))
        name = _text(text[: match.start()].strip(" -._"))
        if name:
            params = dict(_episode_params(season, episode), film_name=name)
            return [Attempt("manual", params, episode=(season, episode))]

    base: Dict[str, str] = {}
    target = None
    if playing is not None and playing.is_episode:
        base = _episode_params(playing.season, playing.episode)
        target = (playing.season, playing.episode)
    plan = [Attempt("manual", dict(base, film_name=text), episode=target)]
    year = _MANUAL_YEAR.search(text)
    name = _text(text[: year.start()]) if year else ""
    if year and name:
        plan.append(Attempt("manual", dict(base, film_name=name), int(year.group(1)), target))
    return plan
