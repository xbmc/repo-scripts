"""
Result selection and sorting.

Handles selecting N random movies from a filtered pool and
sorting them according to user preferences.

Logging:
    Logger: 'data'
    Key events:
        - results.generate (DEBUG): Result set generated with count and sort
    See LOGGING.md for full guidelines.
"""
import random
from typing import Dict, List, Any

from resources.lib.constants import (
    SORT_RANDOM, SORT_TITLE, SORT_YEAR, SORT_RATING,
    SORT_RUNTIME, SORT_DATE_ADDED, SORT_DESC,
)
from resources.lib.utils import get_logger

log = get_logger('data')


# Sort key functions mapped to sort option constants
_SORT_KEYS = {
    SORT_TITLE: lambda m: m.get("title", "").lower(),
    SORT_YEAR: lambda m: m.get("year", 0),
    SORT_RATING: lambda m: m.get("rating", 0.0),
    SORT_RUNTIME: lambda m: m.get("runtime", 0),
    SORT_DATE_ADDED: lambda m: m.get("dateadded", ""),
}


def select_and_sort_results(
    movies: List[Dict[str, Any]],
    count: int,
    sort_by: int,
    sort_dir: int,
) -> List[Dict[str, Any]]:
    """Select N movies and sort them.

    For SORT_RANDOM: randomly sample N, then return in random order.
    For other sorts: randomly sample N, then sort by the chosen key.

    Args:
        movies: Pool of filtered movies to select from.
        count: Maximum number of movies to return.
        sort_by: Sort option constant (SORT_RANDOM, SORT_TITLE, etc).
        sort_dir: Sort direction (SORT_ASC or SORT_DESC).

    Returns:
        Selected and sorted list of movie dicts.
    """
    # Sample from pool
    if len(movies) <= count:
        selected = list(movies)
    else:
        selected = random.sample(movies, count)

    # Sort
    if sort_by == SORT_RANDOM:
        random.shuffle(selected)
    elif sort_by in _SORT_KEYS:
        selected.sort(
            key=_SORT_KEYS[sort_by],
            reverse=(sort_dir == SORT_DESC),
        )

    log.debug("Results generated", event="results.generate",
              pool_size=len(movies), result_count=len(selected),
              sort_by=sort_by, sort_dir=sort_dir)
    return selected
