"""Pure per-field maturity decisions (Phase 7c).

Maturity is computed from facts, never stored. A field is FINAL once its content
is past the stability age; before that it is sampled on the refetch schedule.
A value only the fallback language supplied is not final until it has had
FALLBACK_RECHECKS answered re-checks, about a month apart, so a later
folder-language value can replace it.

Logging: none (pure computation).
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from resources.lib.constants import FALLBACK_RECHECK_DAYS, FALLBACK_RECHECKS

FETCH_NOW = "fetch_now"
SKIP_NOT_DUE = "skip_not_due"
FINAL = "final"


def decide_field(
    content_age_days: int | None,
    fetch_count: int,
    next_retry: str | None,
    today: str,
    threshold_days: int,
) -> str:
    """Decide what to do with a field this scan, before any API call."""
    if fetch_count == 0:
        return FETCH_NOW
    if content_age_days is not None and content_age_days >= threshold_days:
        return FINAL
    # young / unknown-age content, still volatile: fetch when due
    if next_retry is not None and next_retry <= today:
        return FETCH_NOW
    return SKIP_NOT_DUE


def apply_fallback_recheck(
    decision: str,
    from_fallback: bool,
    fallback_checks: int,
    next_retry: str | None,
    today: str,
) -> str:
    """Hold back FINAL for a fallback-language value with re-checks left.

    Composed after decide_field, which stays a function of fetch_count and
    content age only. Such a field is due on its next_retry date, which a
    fallback-sourced sample sets with fallback_recheck_due; a row without a
    date is due now.
    """
    if decision != FINAL or not from_fallback or fallback_checks >= FALLBACK_RECHECKS:
        return decision
    if next_retry is None or next_retry <= today:
        return FETCH_NOW
    return SKIP_NOT_DUE


def fallback_recheck_due(next_due: str | None, today: str) -> str:
    """Next sample of a field still holding a fallback value: the regular
    schedule date when that comes within FALLBACK_RECHECK_DAYS, otherwise
    FALLBACK_RECHECK_DAYS from today. A missing or past schedule date (old
    content's settle date) gives the monthly date."""
    cap = (date.fromisoformat(today) + timedelta(days=FALLBACK_RECHECK_DAYS)).isoformat()
    if next_due is None or next_due <= today or next_due > cap:
        return cap
    return next_due


def compute_next_due(
    fetch_count: int,
    schedule: tuple[int, ...],
    premiered: str | None,
    threshold_days: int,
    today: str,
    jitter: int = -1,
) -> str | None:
    """Date of the next sample for a field that stays volatile after a fetch.

    On the schedule: today + schedule[fetch_count-1] + jitter. After the schedule
    is exhausted: the settle-capture at premiered + threshold_days. Returns None
    if the settle date cannot be computed (no premiered date)."""
    today_d = date.fromisoformat(today)
    if fetch_count <= len(schedule):
        base = schedule[fetch_count - 1]
        j = random.randint(0, max(1, base // 4)) if jitter < 0 else jitter
        return (today_d + timedelta(days=base + j)).isoformat()
    # settle-capture: due when content crosses the stability age
    if not premiered:
        return None
    try:
        prem_d = date.fromisoformat(premiered)
    except ValueError:
        return None
    return (prem_d + timedelta(days=threshold_days)).isoformat()


def decide_certification(
    fetch_count: int,
    from_fallback: bool,
    fallback_checks: int,
    next_retry: str | None,
    today: str,
) -> str:
    """The maturity decision for `mpaa`, which does not follow content age.

    A certification from a real source (TMDB or the site for the configured
    country, or one the item already had in that system) never changes, so it
    is FINAL after one answer. A derived one, or "none found", is held like a
    fallback value: re-checked when due, up to FALLBACK_RECHECKS times, then
    FINAL.
    """
    if fetch_count == 0:
        return FETCH_NOW
    if not from_fallback or fallback_checks >= FALLBACK_RECHECKS:
        return FINAL
    if next_retry is None or next_retry <= today:
        return FETCH_NOW
    return SKIP_NOT_DUE
