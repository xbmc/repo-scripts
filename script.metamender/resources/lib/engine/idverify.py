"""
Show-title matching for verifying `unknown`-type uniqueids.

Kodi items scraped by some tools carry an id of type `unknown`, which in
practice is a TVDB id. Before such an id is used, the TVDB series it names must
be the same show: one of the series' names (primary, translations, aliases)
has to equal the Kodi title once both are normalized.

Normalization makes formatting differences irrelevant without making
different shows equal: case, diacritics, punctuation, articles, a trailing
"(year)" and the spelling of "and" across languages are ignored; every word
that remains must match. A year is compared separately: when both sides
have one (from a trailing "(year)" or passed in) they must be within a year
of each other, so a same-titled remake is not taken for the original. The
tolerance allows for a premiere that falls on either side of New Year in
different countries. A year mismatch is reported apart from a name mismatch,
because the scan can confirm such a show by its episode ids instead.

Logging:
    None (pure functions).
"""
from __future__ import annotations

import re
import unicodedata

# "and" in the languages of the library's sources. Unified rather than
# dropped, so "Tom en Jerry" equals "Tom & Jerry" but not "Tom Jerry".
_CONJUNCTIONS = frozenset({"and", "en", "und", "et", "y", "e", "og", "och"})
_AND = "and"

# Articles are dropped wherever they stand, which also covers the
# "Office, The" sort form. "a" is left alone: it is also a conjunction
# (Czech "Pat a Mat") and would otherwise make "Pat & Mat" equal "Pat Mat".
_ARTICLES = frozenset({
    "the", "an",
    "de", "het", "een",
    "der", "die", "das", "ein", "eine",
    "le", "la", "les", "l", "un", "une",
    "el", "los", "las",
    "il", "lo", "gli",
})

_TRAILING_YEAR = re.compile(r"\s*\((\d{4})\)\s*$")
_YEAR_TOLERANCE = 1
_APOSTROPHES = re.compile(r"['’‘`]")
_NON_WORD = re.compile(r"[^\w]+", re.UNICODE)


def normalize_title(text: str) -> str:
    """Return the comparison form of a show title."""
    text = _TRAILING_YEAR.sub("", text or "")
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in decomposed if not unicodedata.combining(c))
    text = text.replace("&", " {} ".format(_AND))
    text = _APOSTROPHES.sub("", text)
    words: list[str] = []
    for word in _NON_WORD.sub(" ", text).split():
        if word in _ARTICLES:
            continue
        words.append(_AND if word in _CONJUNCTIONS else word)
    return " ".join(words)


def _title_year(text: str) -> int | None:
    match = _TRAILING_YEAR.search(text or "")
    return int(match.group(1)) if match else None


def _years_agree(a: int | None, b: int | None) -> bool:
    return a is None or b is None or abs(a - b) <= _YEAR_TOLERANCE


NAME_MISMATCH = "name_mismatch"
YEAR_MISMATCH = "year_mismatch"


def show_mismatch(
    kodi_title: str,
    candidate_names: list[str],
    kodi_year: int | None = None,
    candidate_year: int | None = None,
) -> str | None:
    """Why the Kodi title does not name the candidate show, or None when it
    does.

    It does when the title equals one of the candidate names after
    normalization and the years agree where both sides have one. A year in
    the title wins over the passed year. YEAR_MISMATCH means a name matched
    but no matching name agreed on the year; NAME_MISMATCH means no name
    matched (an empty normalized title never does). The caller may confirm
    the id by other evidence either way.
    """
    wanted = normalize_title(kodi_title)
    if not wanted:
        return NAME_MISMATCH
    own_year = _title_year(kodi_title) or kodi_year
    reason = NAME_MISMATCH
    for name in candidate_names:
        if normalize_title(name) != wanted:
            continue
        if _years_agree(own_year, _title_year(name) or candidate_year):
            return None
        reason = YEAR_MISMATCH
    return reason


def show_matches(
    kodi_title: str,
    candidate_names: list[str],
    kodi_year: int | None = None,
    candidate_year: int | None = None,
) -> bool:
    """True when show_mismatch finds no reason the title does not match."""
    return show_mismatch(kodi_title, candidate_names, kodi_year, candidate_year) is None
