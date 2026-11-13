"""Per-field provider chain.

Steps run lazily in priority order. The chain stops at the first usable value
or at the first transient failure: a transient step must not let a lower
priority (for example English fallback) step win, because the preferred
provider may answer correctly next time.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List

from .textrules import is_empty_text

# Returned by a step when its provider could not give an answer (unreachable,
# not loaded, breaker open, auth disabled). Distinct from None, which means the
# provider answered and has nothing.
TRANSIENT = object()


@dataclass(frozen=True)
class Step:
    fetch: Callable[[], Any]
    fallback: bool


@dataclass(frozen=True)
class FieldOutcome:
    transient: bool
    # None when nothing should be written.
    value: Any
    from_fallback: bool


_ANSWERED_EMPTY = FieldOutcome(transient=False, value=None, from_fallback=False)


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return is_empty_text(value)
    # Non-text values (genre lists and similar) are real unless an empty list.
    try:
        return len(value) == 0
    except TypeError:
        return False


def run_chain(steps: List[Step], current_value: Any) -> FieldOutcome:
    """Resolve one field. A fallback value is only used to fill an empty or
    placeholder current value, never to replace real text."""
    for step in steps:
        if step.fallback and not _is_empty(current_value):
            # A fallback only fills an empty or placeholder value, so its
            # result (or transient failure) could never matter.
            continue
        value = step.fetch()
        if value is TRANSIENT:
            return FieldOutcome(transient=True, value=None, from_fallback=False)
        if _is_empty(value):
            continue
        return FieldOutcome(transient=False, value=value, from_fallback=step.fallback)
    return _ANSWERED_EMPTY
