"""
IMDb rating source backed by Kodi's shared script.module.imdbratings.

The module keeps IMDb's daily ratings dataset in a sqlite store shared between
add-ons. It does its own HTTP (urllib), so these calls bypass providers/http.py
and no circuit breaker applies; `dataset_date()` being None is the signal that
the store is not usable.

The module is imported lazily so a missing install never breaks importing the
scan code; the rating then reads as transient rather than as "no rating".

Logging:
    Logger: 'imdb_ratings'
    Key events:
        - imdb_ratings.unavailable: module not installed (logged once per process)
        - imdb_ratings.refresh_failed: refresh raised; a previously loaded
          dataset is still used
"""
from __future__ import annotations

from typing import Any, Callable, Optional, Tuple

from resources.lib.utils import TransientProviderError, get_logger

log = get_logger('imdb_ratings')

_unavailable_logged = False


def _module() -> Optional[Any]:
    """Return the imdbratings module, or None (with one warning) when absent."""
    global _unavailable_logged
    try:
        import imdbratings
    except ImportError:
        if not _unavailable_logged:
            _unavailable_logged = True
            log.warning(
                "script.module.imdbratings is not installed",
                event="imdb_ratings.unavailable",
            )
        return None
    return imdbratings


def prepare(abort: Callable[[], bool]) -> bool:
    """Refresh the shared store when due; True when a dataset is loaded.

    `abort` is polled by the module during a download. A refresh failure is
    logged and the answer follows whatever dataset is already loaded, since an
    old dataset is still usable.
    """
    mod = _module()
    if mod is None:
        return False
    try:
        mod.refresh(abort=abort)
    except Exception:
        log.exception(
            "IMDb ratings refresh failed",
            event="imdb_ratings.refresh_failed",
        )
    return mod.dataset_date() is not None


def lookup(imdb_id: str) -> Optional[Tuple[float, int]]:
    """Return (rating, votes), or None when IMDb has no rating for the title.

    The module returns None both for "absent" and for a store error, so a None
    is only a real answer while the dataset is still readable. Raises
    TransientProviderError when the module is missing or the store is failing.
    """
    mod = _module()
    if mod is None:
        raise TransientProviderError("script.module.imdbratings is not installed")
    result = mod.get_rating(imdb_id)
    if result is not None:
        return result
    if mod.dataset_date() is None:
        raise TransientProviderError("IMDb ratings store is not loaded")
    return None
