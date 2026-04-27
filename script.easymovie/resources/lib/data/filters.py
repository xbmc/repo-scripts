"""
Movie filter engine.

Applies user-configured filters to a list of movie dicts from
Kodi's JSON-RPC API. All filtering is client-side after an
initial bulk query.

Logging:
    Logger: 'data'
    Key events:
        - filter.step (DEBUG): Per-step remaining count after each filter
        - filter.apply (DEBUG): Filters applied with result count
    See LOGGING.md for full guidelines.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from resources.lib.constants import WATCHED_BOTH, WATCHED_UNWATCHED, WATCHED_WATCHED
from resources.lib.utils import get_logger

log = get_logger('data')


@dataclass
class FilterConfig:
    """Configuration for movie filtering."""
    ignore_genres: Optional[List[str]] = None
    ignore_genre_match_and: bool = False  # False = OR, True = AND
    genres: Optional[List[str]] = None
    genre_match_and: bool = False  # False = OR, True = AND
    watched: int = WATCHED_BOTH  # 0=unwatched, 1=watched, 2=both
    mpaa_ratings: Optional[List[str]] = None
    runtime_min: int = 0  # minutes, 0 = no minimum
    runtime_max: int = 0  # minutes, 0 = no maximum
    year_from: int = 0  # 0 = no lower bound
    year_to: int = 0  # 0 = no upper bound
    min_score: int = 0  # 0-100 (divide by 10 for comparison)
    exclude_ids: Optional[List[int]] = field(default_factory=list)


def apply_filters(
    movies: List[Dict[str, Any]], config: FilterConfig,
    reason: str = "final",
) -> List[Dict[str, Any]]:
    """Apply all configured filters to a list of movies.

    Args:
        movies: List of movie dicts from Kodi JSON-RPC.
        config: Filter configuration.
        reason: Why filters are being applied. "final" logs per-step detail,
            "cumulative_count" logs only the summary.

    Returns:
        Filtered list of movie dicts.
    """
    result = movies
    verbose = reason == "final"

    # Exclude specific movie IDs (previously suggested, blacklisted)
    if config.exclude_ids:
        exclude_set = set(config.exclude_ids)
        result = [m for m in result if m.get("movieid", 0) not in exclude_set]
        if verbose:
            log.debug("Filter step", event="filter.step",
                      step="exclude_ids", remaining=len(result))

    # Ignore genres filter (exclude matching movies)
    if config.ignore_genres:
        ignore_set = set(config.ignore_genres)
        if config.ignore_genre_match_and:
            # AND: only exclude if ALL ignored genres present
            result = [m for m in result
                      if not ignore_set.issubset(set(m.get("genre", [])))]
        else:
            # OR: exclude if ANY ignored genre present
            result = [m for m in result
                      if not ignore_set.intersection(set(m.get("genre", [])))]
        if verbose:
            log.debug("Filter step", event="filter.step",
                      step="ignore_genres", remaining=len(result))

    # Genre filter
    if config.genres:
        genre_set = set(config.genres)
        if config.genre_match_and:
            result = [m for m in result if genre_set.issubset(set(m.get("genre", [])))]
        else:
            result = [m for m in result if genre_set.intersection(set(m.get("genre", [])))]
        if verbose:
            log.debug("Filter step", event="filter.step",
                      step="genre", remaining=len(result))

    # Watched status
    if config.watched == WATCHED_UNWATCHED:
        result = [m for m in result if m.get("playcount", 0) == 0]
        if verbose:
            log.debug("Filter step", event="filter.step",
                      step="watched", remaining=len(result))
    elif config.watched == WATCHED_WATCHED:
        result = [m for m in result if m.get("playcount", 0) > 0]
        if verbose:
            log.debug("Filter step", event="filter.step",
                      step="watched", remaining=len(result))
    # WATCHED_BOTH: no filter

    # MPAA rating
    if config.mpaa_ratings:
        mpaa_set = set(config.mpaa_ratings)
        result = [m for m in result if m.get("mpaa", "") in mpaa_set]
        if verbose:
            log.debug("Filter step", event="filter.step",
                      step="mpaa", remaining=len(result))

    # Runtime (Kodi stores in seconds, config uses minutes)
    if config.runtime_min > 0:
        min_seconds = config.runtime_min * 60
        result = [m for m in result if m.get("runtime", 0) >= min_seconds]
        if verbose:
            log.debug("Filter step", event="filter.step",
                      step="runtime_min", remaining=len(result))
    if config.runtime_max > 0:
        max_seconds = config.runtime_max * 60
        result = [m for m in result if m.get("runtime", 0) <= max_seconds]
        if verbose:
            log.debug("Filter step", event="filter.step",
                      step="runtime_max", remaining=len(result))

    # Year
    if config.year_from > 0:
        result = [m for m in result if m.get("year", 0) >= config.year_from]
        if verbose:
            log.debug("Filter step", event="filter.step",
                      step="year_from", remaining=len(result))
    if config.year_to > 0:
        result = [m for m in result if m.get("year", 0) <= config.year_to]
        if verbose:
            log.debug("Filter step", event="filter.step",
                      step="year_to", remaining=len(result))

    # Score (config stores 0-100, Kodi rating is 0.0-10.0)
    if config.min_score > 0:
        min_rating = config.min_score / 10.0
        result = [m for m in result if m.get("rating", 0.0) >= min_rating]
        if verbose:
            log.debug("Filter step", event="filter.step",
                      step="score", remaining=len(result))

    log.debug("Filters applied", event="filter.apply",
              reason=reason, input_count=len(movies), result_count=len(result))
    return result


def filter_by_playlist_ids(
    movies: List[Dict[str, Any]], playlist_ids: Set[int],
) -> List[Dict[str, Any]]:
    """Filter movies to only those present in a smart playlist.

    Args:
        movies: Full movie list from library query.
        playlist_ids: Set of movie IDs from the smart playlist.

    Returns:
        Movies whose movieid is in playlist_ids.
    """
    return [m for m in movies if m.get("movieid", 0) in playlist_ids]


def extract_unique_genres(movies: List[Dict[str, Any]]) -> List[str]:
    """Extract and sort all unique genres from a movie list."""
    genres = set()
    for movie in movies:
        for genre in movie.get("genre", []):
            genres.add(genre)
    return sorted(genres)


def extract_unique_mpaa(movies: List[Dict[str, Any]]) -> List[str]:
    """Extract and sort all unique MPAA ratings from a movie list."""
    ratings = set()
    for movie in movies:
        mpaa = movie.get("mpaa", "")
        if mpaa:
            ratings.add(mpaa)
    return sorted(ratings)


def extract_decade_buckets(movies: List[Dict[str, Any]]) -> List[tuple]:
    """Extract decade buckets with counts from a movie list.

    Returns list of (decade_start, count, label) tuples, sorted descending.
    Example: [(2020, 331, "2020s"), (1990, 3, "1990s")]
    """
    from collections import Counter
    decades = Counter((m.get("year", 0) // 10) * 10 for m in movies if m.get("year", 0) > 0)
    buckets = []
    for decade, count in sorted(decades.items(), reverse=True):
        label = f"{decade}s"
        buckets.append((decade, count, label))
    return buckets
