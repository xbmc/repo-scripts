"""
Rating resolution for MetaMender.

Builds the Kodi named-slot ratings map from the TMDB and IMDb ratings under
the user's rating_source preference: Follow the scraper (the default),
Prefer TMDB, Prefer IMDb, TMDB only, IMDb only.

Follow the scraper keeps the rating Kodi shows where the scraper put it: the
item's default slot decides which of our sources is preferred, and the
default flag itself never moves while the item has one.

Logging:
    Logger: 'resolve'
    Key events:
        - resolve.ratings (DEBUG): Ratings map built
"""
from __future__ import annotations

from typing import Any

from resources.lib.engine.protect import fingerprint
from resources.lib.utils import get_logger

log = get_logger('resolve')

# rating_source values, matching the settings.xml integer options
PREFER_TMDB = 0
PREFER_IMDB = 1
TMDB_ONLY = 2
IMDB_ONLY = 3
FOLLOW_SCRAPER = 4


def rating_sources(rating_pref: int) -> tuple[bool, bool]:
    """(consults TMDB, consults IMDb) under a rating_source preference.
    Follow the scraper consults both: any item may have an IMDb default."""
    return (
        rating_pref in (PREFER_TMDB, PREFER_IMDB, TMDB_ONLY, FOLLOW_SCRAPER),
        rating_pref in (PREFER_TMDB, PREFER_IMDB, IMDB_ONLY, FOLLOW_SCRAPER),
    )


def _default_slot(current: dict[str, Any]) -> str | None:
    return next(
        (name for name, entry in current.items()
         if isinstance(entry, dict) and entry.get("default")),
        None,
    )


def effective_rating_pref(rating_pref: int, current_ratings: dict[str, Any]) -> int:
    """The fixed preference an item is handled under. Follow the scraper
    resolves per item from the slot Kodi marks as default: an IMDb default
    prefers IMDb; any other default (TMDB, or a source metamender does not
    fetch, such as trakt or tvdb) or none prefers TMDB. Fixed options pass
    through unchanged."""
    if rating_pref != FOLLOW_SCRAPER:
        return rating_pref
    if _default_slot(current_ratings or {}) == _IMDB_SLOT:
        return PREFER_IMDB
    return PREFER_TMDB


# Kodi rating slot names for our two managed providers. Kodi's TMDB movie
# scraper names its slot "themoviedb" and its TMDB TV scraper "tmdb"; both
# hold the TMDB rating, so an item that already has either keeps that name.
_TMDB_SLOT = "themoviedb"
_TMDB_SLOT_ALIASES = (_TMDB_SLOT, "tmdb")
_IMDB_SLOT = "imdb"

# Decimal places used to compare ratings (Kodi stores its own float; compare
# with tolerance so provider 7.28 vs stored 7.28000020980835 is "unchanged").
_RATING_PRECISION = 2


def _norm_rating(value: Any) -> float | None:
    """Round a rating for comparison/storage, or None if not a valid number."""
    try:
        return round(float(value), _RATING_PRECISION)
    except (TypeError, ValueError):
        return None


def _ratings_equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Compare two ratings maps by slot set, normalized rating, votes, default."""
    if set(a.keys()) != set(b.keys()):
        return False
    for name, ea in a.items():
        eb = b[name]
        if _norm_rating(ea.get("rating")) != _norm_rating(eb.get("rating")):
            return False
        if int(ea.get("votes") or 0) != int(eb.get("votes") or 0):
            return False
        if bool(ea.get("default")) != bool(eb.get("default")):
            return False
    return True


def slot_fingerprint(entry: dict[str, Any]) -> str:
    """Fingerprint of a rating slot's value (rating and votes, not `default`).

    The default flag is excluded because moving it is not a change of what the
    slot says, and the rating is rounded so Kodi's float round trip does not
    alter the digest (see protect.fingerprint).
    """
    return fingerprint({
        "rating": _norm_rating(entry.get("rating")),
        "votes": int(entry.get("votes") or 0),
    })


def _tmdb_slot(current: dict[str, Any]) -> str:
    """The slot the TMDB rating goes into: the first TMDB slot the item
    already has, else _TMDB_SLOT."""
    return next((s for s in _TMDB_SLOT_ALIASES if s in current), _TMDB_SLOT)


def build_ratings(
    tmdb_data: dict[str, Any],
    imdb_rating: tuple[float, int] | None,
    current_ratings: dict[str, Any] | None,
    rating_pref: int,
    nfo_managed: bool = False,
    owned_slots: dict[str, str] | None = None,
    keep_default_mark: bool = False,
) -> tuple[dict[str, Any] | None, str | None, int | None, dict[str, str]]:
    """Build the Kodi ratings map to write.

    Returns (map, default_source, default_votes, slot_fingerprints); the map is
    None when nothing changes. Writes the TMDB rating into the item's TMDB
    slot (`themoviedb`, or the `tmdb` slot Kodi's TV scraper made) and the IMDb (rating, votes) into the `imdb` slot (subject to
    rating_pref), preserves all other existing slots (e.g. trakt, user), and
    sets `default` on the preferred source's slot. Kodi rejects ratings <= 0 or
    > 10, so those candidates are dropped. The map is the full merge (for a
    merging SetXDetails call); default_source and its votes feed
    field_status/staleness; slot_fingerprints cover the slots written, for the
    caller to store as provenance.

    On an NFO-managed item the `default` flags are left exactly as they are
    (the NFO decides which rating Kodi shows), and a slot is written only when
    it is absent or still fingerprints to owned_slots[slot], the value
    metamender last wrote there. A slot that came from the NFO, or that the
    user edited, is never modified. default_source and its votes are None.
    The exception is an NFO item with no ratings at all: nothing there says
    which rating to show, so the default follows rating_pref, as without an
    NFO, instead of leaving Kodi to pick one.

    With keep_default_mark (Follow the scraper) an item that has a default
    slot keeps every default flag as it is, NFO or not; without an NFO,
    default_source is then that slot when this call wrote it, else None. An item without a
    default slot gets one by rating_pref, as usual.
    """
    current = current_ratings or {}
    owned = owned_slots or {}
    held_default = _default_slot(current)
    # Whether existing default flags stand: an NFO item's do, unless it has
    # no ratings to hold one; under Follow the scraper, whenever one is set.
    keep_defaults = (nfo_managed and bool(current)) or (
        keep_default_mark and held_default is not None
    )

    # Collect in-range candidates honoring the preference's source filter
    use_tmdb, use_imdb = rating_sources(rating_pref)
    tmdb_slot = _tmdb_slot(current)
    candidates: dict[str, tuple[float, int]] = {}
    if use_tmdb:
        r = _norm_rating(tmdb_data.get("rating"))
        if r is not None and 0 < r <= 10:
            candidates[tmdb_slot] = (r, int(tmdb_data.get("votes") or 0))
    if use_imdb and imdb_rating is not None:
        r = _norm_rating(imdb_rating[0])
        if r is not None and 0 < r <= 10:
            candidates[_IMDB_SLOT] = (r, int(imdb_rating[1] or 0))

    if nfo_managed:
        # Drop the slots that are not ours to write.
        candidates = {
            name: rv for name, rv in candidates.items()
            if name not in current or slot_fingerprint(current[name]) == owned.get(name)
        }

    if not candidates:
        return (None, None, None, {})

    # Build the new map: copy existing slots, then overlay ours. An NFO-managed
    # item keeps its default flags; otherwise the default moves to our slot.
    new_map: dict[str, Any] = {}
    for name, entry in current.items():
        new_map[name] = {
            "rating": entry.get("rating"),
            "votes": int(entry.get("votes") or 0),
            "default": bool(entry.get("default")) if keep_defaults else False,
        }
    for name, (r, v) in candidates.items():
        keep_default = keep_defaults and bool(current.get(name, {}).get("default"))
        new_map[name] = {"rating": r, "votes": v, "default": keep_default}

    default_source: str | None = None
    if keep_default_mark and not nfo_managed and held_default in candidates:
        default_source = held_default
    if not keep_defaults:
        # Choose the default slot by preference, falling back to whichever exists
        order = [_IMDB_SLOT, tmdb_slot] if rating_pref in (PREFER_IMDB, IMDB_ONLY) \
            else [tmdb_slot, _IMDB_SLOT]
        default_source = next((s for s in order if s in candidates), None)
        if default_source is not None:
            new_map[default_source]["default"] = True

    if _ratings_equal(new_map, current):
        return (None, None, None, {})

    chosen_votes = new_map[default_source]["votes"] if default_source else None
    written = {name: slot_fingerprint(new_map[name]) for name in candidates}
    log.debug(
        "Ratings map built",
        event="resolve.ratings",
        default_source=default_source,
        nfo_managed=nfo_managed,
        slots=sorted(new_map.keys()),
    )
    return (new_map, default_source, chosen_votes, written)
