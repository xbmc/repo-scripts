"""
IMDb rating source backed by Kodi's shared script.module.imdbratings.

The module keeps IMDb's daily ratings dataset in a sqlite store shared between
add-ons. It does its own HTTP (urllib), so these calls bypass providers/http.py
and no circuit breaker applies. Only prepare() should update the store, because
it passes the scan's abort callback. From module 1.1.0 lookups use its
lookup(), which never downloads and raises StoreError when the store cannot
answer. Module 1.0.0 has only get_rating(), which may update the store itself
and answers None for a store error too, so a None there is checked against
dataset_date(). addon.xml still accepts 1.0.0 until 1.1.0 is in Kodi's
official repository.

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

from typing import Any, Callable

from resources.lib.utils import TransientProviderError, get_logger

log = get_logger('imdb_ratings')

_unavailable_logged = False


def _module() -> Any | None:
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


def lookup(imdb_id: str) -> tuple[float, int] | None:
    """Return (rating, votes), or None when IMDb has no rating for the title.

    Raises TransientProviderError when the module is missing, the store cannot
    be read, or no dataset is loaded yet, so the maturity clock does not count
    a lookup that never happened.
    """
    mod = _module()
    if mod is None:
        raise TransientProviderError("script.module.imdbratings is not installed")
    store_lookup = getattr(mod, "lookup", None)
    if store_lookup is None:
        return _lookup_module_1_0(mod, imdb_id)
    try:
        return store_lookup(imdb_id)
    except mod.StoreError as exc:
        raise TransientProviderError(f"IMDb ratings store: {exc}") from exc


def _lookup_module_1_0(mod: Any, imdb_id: str) -> tuple[float, int] | None:
    """Module 1.0.0: get_rating's None is a real answer only while a dataset is loaded."""
    result = mod.get_rating(imdb_id)
    if result is not None:
        return result
    if mod.dataset_date() is None:
        raise TransientProviderError("IMDb ratings store is not loaded")
    return None
