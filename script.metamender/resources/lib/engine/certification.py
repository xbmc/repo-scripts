"""Certification values: Kodi's `mpaa` field in and out, and title matching
for the certification sites.

Kodi stores a certification as free text: "NL:12" with a country prefix,
"Rated PG-13" (the form Kodi's TMDB scraper writes for the US), or a bare
"16". Everything here is pure; the scan decides what to do with the verdicts.

Logging:
    None (pure functions).
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable

from resources.lib.engine.protect import is_blank
from resources.lib.utils import TransientProviderError

_COUNTRY_PREFIX = re.compile(r"^\s*([A-Za-z]{2,3}):\s*")
_RATED_PREFIX = re.compile(r"^\s*rated\s+", re.IGNORECASE)
_US_RATED = "Rated "
_SUBTITLE_SEPARATORS = (":", "-")
# rating_prefix is free text in the settings; anything longer is a mistake.
_MAX_PREFIX_LENGTH = 8

BLANK = "blank"
PLACEHOLDER = "placeholder"
OWN = "own"
FOREIGN = "foreign"


def parse_mpaa(value: str) -> tuple[str, str]:
    """(prefix, bare) of a Kodi certification. The prefix is a country code
    with its colon, upper-cased ("NL:"), or "Rated " (the US form), or ""."""
    text = value or ""
    match = _COUNTRY_PREFIX.match(text)
    if match:
        return match.group(1).upper() + ":", text[match.end():].strip()
    match = _RATED_PREFIX.match(text)
    if match:
        return _US_RATED, text[match.end():].strip()
    return "", text.strip()


def format_mpaa(bare: str, prefix: str) -> str:
    """The value written to Kodi: the prefix exactly as configured, then the
    bare rating."""
    return prefix + bare


def classify_current(
    value: str,
    valid: frozenset[str],
    own_prefix: str,
    own_country: str,
    placeholder: bool,
    canonical: Callable[[str], str] = str.strip,
) -> str:
    """BLANK, PLACEHOLDER, OWN or FOREIGN for the certification Kodi holds.

    ``placeholder`` is the caller's verdict that the value is metamender's own
    not-found value (its provenance says so). OWN is a rating from the
    configured country's list with that country's prefix, the configured
    prefix, or none; anything else that is not blank is FOREIGN.
    ``canonical`` turns another spelling of a rating into the list's own
    (Preset.canonical).
    """
    if placeholder:
        return PLACEHOLDER
    if is_blank(value):
        return BLANK
    stripped = value.strip()
    custom = own_prefix.strip()
    if (custom and stripped.lower().startswith(custom.lower())
            and canonical(stripped[len(custom):]) in valid):
        return OWN
    prefix, bare = parse_mpaa(value)
    own_forms = {"", own_prefix, own_country.upper() + ":"}
    if own_country.upper() == "US":
        own_forms.add(_US_RATED)
    if canonical(bare) in valid and prefix in own_forms:
        return OWN
    return FOREIGN


def normalize_title(text: str) -> str:
    """Casefolded, without diacritics, whitespace collapsed."""
    decomposed = unicodedata.normalize("NFD", text or "")
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(stripped.casefold().split())


def titles_match(site_title: str, item_title: str) -> bool:
    """The site's title names the item: equal, or the site title continues
    the item title with a subtitle after ":" or "-" ("Alien: Romulus",
    "Avatar - Aufbruch nach Pandora" for "Avatar"), never the reverse. A plain
    space is not enough: "Dark Blue" is another show than "Dark"."""
    site = normalize_title(site_title)
    item = normalize_title(item_title)
    if not site or not item:
        return False
    if site == item:
        return True
    return site.startswith(item) and site[len(item):].lstrip().startswith(_SUBTITLE_SEPARATORS)


def years_match(site_year: int | None, item_year: int | None) -> bool:
    """Within one year when both are known; an unknown year does not
    contradict."""
    if site_year is None or item_year is None:
        return True
    return abs(site_year - item_year) <= 1


def sanitize_prefix(value: str, default: str) -> str:
    """``value`` when it is a usable prefix, else ``default``: at most
    _MAX_PREFIX_LENGTH characters and no control characters."""
    if len(value) > _MAX_PREFIX_LENGTH or any(ord(c) < 32 or ord(c) == 127 for c in value):
        return default
    return value


# A site's search result: its titles (localized, original, ...), its year
# when known, and its bare rating.
Candidate = tuple[tuple[str, ...], int | None, str]


def best_match(
    item_titles: tuple[str, ...], item_year: int | None, candidates: list[Candidate],
) -> str | None:
    """The rating of the candidate that names the item, or None.

    Sites search their full text and list sequels and namesakes, so an exact
    title (normalized) within a year comes first, in the site's order. The
    prefix form of titles_match ("Alien: Romulus" for "Alien") counts only
    when both years are known and agree. Without an item year only exact
    titles count, and only when they all carry the same rating.
    """
    wanted = {normalize_title(t) for t in item_titles if t}
    wanted.discard("")
    if not wanted:
        return None

    def exact(titles: tuple[str, ...]) -> bool:
        return any(normalize_title(t) in wanted for t in titles)

    hits = [c for c in candidates if exact(c[0]) and years_match(c[1], item_year)]
    if item_year is None:
        ratings = {c[2] for c in hits}
        return ratings.pop() if len(ratings) == 1 else None
    if hits:
        return hits[0][2]
    for titles, year, rating in candidates:
        if year is not None and years_match(year, item_year) and any(
            titles_match(t, w) for t in titles for w in item_titles if w
        ):
            return rating
    return None


def no_pace() -> bool:
    """The pace of a lookup made outside a scan (tests, verify.py): go now."""
    return True


def paced(pace: Callable[[], bool]) -> None:
    """Ask the scan's site gate before a request; it raises when the request
    must not go out (Kodi shutting down, the cycle's budget spent)."""
    if not pace():
        raise TransientProviderError("certification request not allowed now")


def other_title(title: str, original_title: str) -> str | None:
    """The original title when it differs from the item's title: the second
    search a site gets when the first finds nothing."""
    if original_title and normalize_title(original_title) != normalize_title(title):
        return original_title
    return None
