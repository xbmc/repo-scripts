"""Merge ratings from several providers and shape them for Kodi."""
from __future__ import annotations

import xbmc
from typing import Dict, List, Optional, Any, Set
from lib.kodi.client import log

# only breaks a tie on vote count; a rating's owner already wins via _RATING_ORIGIN
DEFAULT_SOURCE_PRIORITY: Dict[str, int] = {
    "imdb_dataset": 110,
    "tmdb": 100,
    "trakt": 100,
    "mdblist": 90,
    "omdb": 50,
}

# movie scrapers write "themoviedb", TV scrapers "tmdb"; skins may read either key
_KEY_ALIASES: Dict[str, str] = {
    "themoviedb": "tmdb",
    "tmdb": "themoviedb",
}


# the provider a rating belongs to; a downstream copy cannot lead it
_RATING_ORIGIN: Dict[str, str] = {
    "imdb": "imdb_dataset",
    "trakt": "trakt",
    "tmdb": "tmdb",
    "themoviedb": "tmdb",
}


def rating_owner(name: str) -> Optional[str]:
    """Provider a rating belongs to, None for one no provider owns."""
    return _RATING_ORIGIN.get(name)


def _display_tenths(rating: float) -> int:
    """Rating in tenths, rounding half up so this matches SQLite's ROUND."""
    return int(rating * 10 + 0.5)


def rating_display_changed(old_rating: Optional[float], new_rating: float) -> bool:
    """True when the rating moves at the one decimal Kodi displays."""
    if old_rating is None:
        return True
    return _display_tenths(old_rating) != _display_tenths(new_rating)


def format_rating_change(source: str, old_rating: Optional[float], old_votes: int,
                         new_rating: float, new_votes: int) -> str:
    """Format the rating and vote movement for a log line; the arrow shows only on a real change."""
    old_rating = old_rating or 0.0
    rating = (f"{old_rating:.1f} -> {new_rating:.1f}"
              if rating_display_changed(old_rating, new_rating) else f"{old_rating:.1f}")
    if old_votes:
        swing = (new_votes - old_votes) / old_votes * 100
        return f"{source} {rating}, votes {old_votes} -> {new_votes} ({swing:+.1f}%)"
    return f"{source} {rating}, votes {new_votes}"


def merge_ratings(sources_ratings: List[Dict[str, Any]],
                  source_priority: Optional[Dict[str, int]] = None
                  ) -> Dict[str, Dict[str, float]]:
    """Best entry per rating key: the owning provider, else the highest vote count."""
    if source_priority is None:
        source_priority = DEFAULT_SOURCE_PRIORITY

    merged: Dict[str, Dict[str, float]] = {}
    source_origins: Dict[str, str] = {}

    for source_data in sources_ratings:
        if not source_data:
            continue

        data_source = source_data.get("_source", "unknown")
        data_priority = source_priority.get(data_source, 0)

        for source_name, rating_data in source_data.items():
            if source_name == "_source":
                continue

            if not isinstance(rating_data, dict):
                continue

            rating = rating_data.get("rating")
            votes = rating_data.get("votes")

            if rating is None or votes is None:
                continue

            existing = merged.get(source_name)
            if existing is None:
                merged[source_name] = {"rating": rating, "votes": votes}
                source_origins[source_name] = data_source
            else:
                existing_source = source_origins.get(source_name, "unknown")
                existing_priority = source_priority.get(existing_source, 0)
                existing_votes = existing.get("votes", 0)

                origin = _RATING_ORIGIN.get(source_name)
                incoming_is_origin = origin is not None and origin == data_source
                existing_is_origin = origin is not None and origin == existing_source

                should_replace = False
                if incoming_is_origin != existing_is_origin:
                    should_replace = incoming_is_origin
                elif votes > existing_votes:
                    should_replace = True
                elif votes == existing_votes and data_priority > existing_priority:
                    should_replace = True

                if should_replace:
                    merged[source_name] = {"rating": rating, "votes": votes}
                    source_origins[source_name] = data_source

    return merged


def prepare_kodi_ratings(merged_ratings: Dict[str, Dict[str, float]],
                         default_source: str = "imdb",
                         supplied: Optional[Set[str]] = None
                         ) -> Dict[str, Dict[str, bool | int | float]]:
    """Convert merged ratings into Kodi's `Set*Details.ratings` shape, clamped to 0-10."""
    kodi_ratings = {}
    if default_source not in merged_ratings and _KEY_ALIASES.get(default_source) in merged_ratings:
        default_source = _KEY_ALIASES[default_source]

    for source_name, rating_data in merged_ratings.items():
        rating = rating_data["rating"]
        votes = rating_data["votes"]

        if not (0.0 <= rating <= 10.0):
            log(
                "Ratings",
                f"CRITICAL - Rating out of valid range for '{source_name}': {rating:.2f} "
                f"(Kodi requires 0-10 scale). This indicates a normalization bug in rating source. "
                f"Clamping to valid range to prevent database corruption.",
                xbmc.LOGERROR,
            )
            rating = max(0.0, min(10.0, rating))

        kodi_ratings[source_name] = {
            "rating": rating,
            "votes": int(votes),
            "default": source_name == default_source
        }

    for src, alias in _KEY_ALIASES.items():
        if src not in kodi_ratings:
            continue
        if alias not in kodi_ratings:
            kodi_ratings[alias] = {
                "rating": kodi_ratings[src]["rating"],
                "votes": kodi_ratings[src]["votes"],
                "default": False,
            }
        elif supplied and src in supplied:
            kodi_ratings[alias]["rating"] = kodi_ratings[src]["rating"]
            kodi_ratings[alias]["votes"] = kodi_ratings[src]["votes"]

    return kodi_ratings


def default_moved(existing: Dict[str, Dict[str, Any]],
                  kodi_ratings: Dict[str, Dict[str, Any]]) -> bool:
    """True when the ratings flag a default that Kodi does not hold as its default."""
    new_default = next((name for name, data in kodi_ratings.items() if data["default"]), None)
    return new_default is not None and not (existing.get(new_default) or {}).get("default")


def has_alias_drift(ratings: Dict[str, Dict[str, Any]], supplied: Set[str]) -> bool:
    """True when the two names for one rating hold different numbers."""
    for src, alias in _KEY_ALIASES.items():
        if src not in supplied:
            continue
        first, second = ratings.get(src), ratings.get(alias)
        if not isinstance(first, dict) or not isinstance(second, dict):
            continue
        if first.get("rating") is None or second.get("rating") is None:
            continue
        if abs(first["rating"] - second["rating"]) > 0.01:
            return True
    return False
