"""
Movie set awareness logic.

Handles finding the correct movie within a set (first unwatched),
substituting random picks, and determining set continuations.

Logging:
    Logger: 'data'
    Key events:
        - results.set_substitute (DEBUG): Movie substituted for set-correct entry
        - results.set_dedup (DEBUG): Duplicate set member skipped
        - continuation.next_found (DEBUG): Next movie in set identified
    See LOGGING.md for full guidelines.
"""
from typing import Dict, List, Optional, Any

from resources.lib.utils import get_logger

log = get_logger('data')


def find_first_unwatched_in_set(
    set_details: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Find the first unwatched movie in a set (by release order).

    Args:
        set_details: MovieSetDetails response with movies sorted by year.

    Returns:
        First unwatched movie dict, or None if all watched.
    """
    for movie in set_details.get("movies", []):
        if movie.get("playcount", 0) == 0:
            return movie
    return None


def find_first_unwatched_before(
    set_details: Dict[str, Any],
    current_movie_id: int,
) -> Optional[Dict[str, Any]]:
    """Find the first unwatched movie that comes before the given movie in a set.

    Used by the background service to detect when a user starts playing
    a later movie in a set while an earlier one is still unwatched.

    Args:
        set_details: MovieSetDetails response with movies sorted by year.
        current_movie_id: The movie being played.

    Returns:
        First unwatched movie before current, or None if none exist
        or current movie is not in the set.
    """
    movies = set_details.get("movies", [])

    # Verify the current movie is actually in this set
    if not any(m.get("movieid") == current_movie_id for m in movies):
        return None

    for movie in movies:
        if movie.get("movieid") == current_movie_id:
            # Reached the current movie — no earlier unwatched found
            return None
        if movie.get("playcount", 0) == 0:
            return movie
    return None


def apply_set_substitutions(
    movies: List[Dict[str, Any]],
    set_cache: Dict[int, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Replace set-member movies with the first unwatched entry in their set.

    Also deduplicates: if multiple movies from the same set were picked,
    only the first occurrence (substituted) is kept.

    Args:
        movies: List of picked movie dicts.
        set_cache: Dict of setid -> GetMovieSetDetails response.

    Returns:
        New list with substitutions applied and set duplicates removed.
    """
    seen_sets = set()
    result = []

    for movie in movies:
        set_id = movie.get("setid", 0)

        if set_id and set_id in set_cache:
            # Skip if we already have a movie from this set
            if set_id in seen_sets:
                log.debug("Duplicate set member skipped",
                          event="results.set_dedup",
                          title=movie.get("title", ""),
                          set_name=movie.get("set", ""))
                continue
            seen_sets.add(set_id)

            # Find first unwatched in set
            first_unwatched = find_first_unwatched_in_set(set_cache[set_id])
            if first_unwatched is not None:
                # Copy the substitute and preserve set info
                substitute = dict(first_unwatched)
                substitute["set"] = movie.get("set", "")
                substitute["setid"] = set_id
                log.debug("Movie substituted for set-correct entry",
                          event="results.set_substitute",
                          original_title=movie.get("title", ""),
                          substitute_title=substitute.get("title", ""),
                          set_name=movie.get("set", ""))
                result.append(substitute)
            else:
                # All watched — keep original pick
                result.append(movie)
        else:
            result.append(movie)

    return result


def get_next_in_set(
    set_details: Dict[str, Any],
    current_movie_id: int,
) -> Optional[Dict[str, Any]]:
    """Get the next movie in a set after the given movie.

    Used for continuation prompts: "You just watched X,
    want to watch Y next?"

    Args:
        set_details: MovieSetDetails response with movies sorted by year.
        current_movie_id: The movie that was just watched.

    Returns:
        Next movie dict, or None if current is last or not found.
    """
    movies = set_details.get("movies", [])
    for i, movie in enumerate(movies):
        if movie.get("movieid") == current_movie_id:
            if i + 1 < len(movies):
                next_movie = movies[i + 1]
                log.debug("Next movie in set identified",
                          event="continuation.next_found",
                          current_title=movie.get("title", ""),
                          next_title=next_movie.get("title", ""))
                return next_movie
            return None
    return None
