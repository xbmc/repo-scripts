"""Turn SubDL search results into the rows Kodi's subtitle dialog lists.

Kodi downloads the first row by itself when the viewer has switched on "download the
first subtitle automatically", so the order matters: the preferred language first,
then the subtitle made for this exact release, then the closest match.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import api, languages, releases

SYNC_SCORE = 90


@dataclass
class Entry:
    language: str  # the SubDL code the row is listed under
    release: str  # what the viewer sees next to the language
    path: str  # dl.subdl.com path to download, without the API key
    hearing_impaired: bool = False
    sync: bool = False
    score: int = 0
    #: A whole season pack: the episode's file is picked once it is downloaded.
    pack: bool = False
    #: One file that SubDL takes out of a season pack for us.
    pack_file: bool = False
    #: The file's format when the path is a single file ("srt").
    format: str = ""
    #: Second language of a two-language subtitle, as a SubDL code.
    secondary: str = ""
    order: int = 0

    @property
    def rating(self) -> int:
        """0-5 stars for Kodi's list."""
        if self.sync:
            return 5
        for stars, floor in ((4, 70), (3, 45), (2, 25), (1, 1)):
            if self.score >= floor:
                return stars
        return 0


def _listed_language(row: dict, wanted: Sequence[str]) -> Tuple[str, str]:
    """(code to list the row under, the other language) or ("", "") if unwanted."""
    first = languages.normalise(row.get("language"))
    second = languages.normalise(row.get("secondary_language"))
    for code, other in ((first, second), (second, first)):
        if code and any(code == want or languages.same_language(code, want) for want in wanted):
            return code, other
    return "", ""


def _is_pack(row: dict) -> bool:
    start, end = row.get("episode_from"), row.get("episode_end")
    return bool(row.get("full_season")) or bool(start and end and start != end)


def _number(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _pick_pack_file(files: List[dict], target: Tuple[Optional[int], int], video: str) -> Tuple[Optional[dict], bool]:
    """The pack file for the target episode, and whether the pack can be ruled out.

    SubDL numbers the files it has indexed. Older packs list file names only, so the
    name is read as well. A pack whose files are all numbered, none of them this
    episode, does not hold the episode.
    """
    season, episode = target
    best: Optional[dict] = None
    best_key = None
    all_numbered = bool(files)
    for row in files:
        if not isinstance(row, dict) or not api.is_download_path(str(row.get("url") or "")):
            continue
        number, row_season = _number(row.get("episode")), _number(row.get("season"))
        name = str(row.get("name") or row.get("release_name") or "")
        if number:
            strength = 3 if number == episode and (not row_season or season is None or row_season == season) else -1
        else:
            all_numbered = False
            strength = releases.episode_match(name, season, episode)
        if strength <= 0:
            continue
        key = (strength, releases.score(video, name), str(row.get("format") or "").lower() == "srt")
        if best_key is None or key > best_key:
            best, best_key = row, key
    return best, best is None and all_numbered


HI_ALL, HI_HIDE, HI_ONLY = 0, 1, 2


def build_entries(rows: Iterable[dict], wanted: Sequence[str], video: str = "",
                  target: Optional[Tuple[Optional[int], int]] = None,
                  include_packs: bool = True, hearing_impaired: int = HI_ALL) -> List[Entry]:
    """Rows for Kodi, best first.

    ``wanted`` is the SubDL codes in the viewer's order (preferred language first),
    ``video`` the playing file's release name, ``target`` the (season, episode) of an
    episode or None for a film. ``hearing_impaired`` repeats the filter the search
    already asked SubDL for, in case a season pack mixes both kinds.
    """
    entries: List[Entry] = []
    seen = set()
    for order, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        code, other = _listed_language(row, wanted)
        path = api.strip_api_key(str(row.get("url") or ""))
        if not code or not api.is_download_path(path):
            continue
        release = str(row.get("release_name") or row.get("name") or "").strip()
        names = [release] + [str(name) for name in row.get("releases") or [] if isinstance(name, str)]
        entry = Entry(code, release, path, bool(row.get("hi")), secondary=other, order=order)

        if target is not None:
            season, episode = target
            row_season = _number(row.get("season"))
            if row_season and season is not None and row_season != season:
                continue
            if _is_pack(row):
                if not include_packs:
                    continue
                found, ruled_out = _pick_pack_file(row.get("unpack_files") or [], target, video)
                if ruled_out:
                    continue
                if found is not None:
                    file_name = str(found.get("name") or "")
                    entry.path = api.strip_api_key(str(found["url"]))
                    entry.pack_file = True
                    entry.format = str(found.get("format") or "").lower()
                    entry.hearing_impaired = entry.hearing_impaired or bool(found.get("hi"))
                    entry.release = releases.strip_extension(file_name) or release
                    names = [str(found.get("release_name") or ""), file_name] + names
                else:
                    entry.pack = True
            else:
                row_episode = _number(row.get("episode"))
                if row_episode and row_episode != episode:
                    continue
                # A release name that names another episode is wrong whatever the
                # metadata says.
                if releases.episode_match(release, season, episode) < 0:
                    continue

        if hearing_impaired == HI_HIDE and entry.hearing_impaired:
            continue
        if hearing_impaired == HI_ONLY and not entry.hearing_impaired:
            continue
        if entry.path in seen:
            continue
        seen.add(entry.path)
        entry.score = releases.best_score(video, names)
        entry.sync = entry.score >= SYNC_SCORE
        entries.append(entry)

    return sorted(entries, key=lambda e: _rank(e, wanted))


def _rank(entry: Entry, wanted: Sequence[str]) -> tuple:
    language_rank = min(
        (index for index, code in enumerate(wanted)
         if code == entry.language or languages.same_language(code, entry.language)),
        default=len(wanted),
    )
    return language_rank, not entry.sync, -entry.score, entry.pack, entry.order


def has_sync(entries: Iterable[Entry]) -> bool:
    return any(entry.sync for entry in entries)


def ordered_codes(languages_wanted: Sequence[str], preferred: Sequence[str]) -> List[str]:
    """The viewer's SubDL codes with the preferred language's codes first."""
    ordered: List[str] = [code for code in preferred if code in languages_wanted]
    ordered += [code for code in languages_wanted if code not in ordered]
    return ordered


def page_count(body: Dict) -> int:
    return _number(body.get("totalPages")) or 1
