"""Tools menu entry that updates IMDb Top 250 rankings from Trakt's official list."""
from __future__ import annotations

import xbmc

from lib.infrastructure.dialogs import ProgressDialog, show_ok, show_yesno
from lib.infrastructure.tasks import MAX_REQUEST_SECONDS, ShutdownAbortFlag
from lib.kodi.client import ADDON, log
from lib.rating.top250 import apply_updates, compute_updates, fetch_ranks


def run_top250_update() -> None:
    """Update IMDb Top 250 rankings from Trakt's official list."""
    heading = ADDON.getLocalizedString(32600)

    try:
        with ProgressDialog(heading=heading) as progress:
            progress.create(ADDON.getLocalizedString(32601))
            ranks = fetch_ranks(ShutdownAbortFlag(MAX_REQUEST_SECONDS))
            if ranks is None:
                progress.close()
                show_ok(heading, ADDON.getLocalizedString(32607))
                return
            if progress.is_cancelled():
                return

            progress.update(25, ADDON.getLocalizedString(32602))
            computed = compute_updates(ranks)
            if computed is None:
                progress.close()
                show_ok(heading, ADDON.getLocalizedString(32608))
                return
            if progress.is_cancelled():
                return
            progress.update(50, ADDON.getLocalizedString(32603))

        updates, already_correct = computed

        if not updates:
            show_ok(
                ADDON.getLocalizedString(32605),
                ADDON.getLocalizedString(32606).format(0, 0, already_correct)
            )
            return

        set_count = sum(1 for _, rank, _ in updates if rank > 0)
        clear_count = len(updates) - set_count

        if not show_yesno(
            ADDON.getLocalizedString(32609),
            ADDON.getLocalizedString(32610).format(set_count, clear_count, already_correct)
        ):
            return

        with ProgressDialog(heading=heading) as progress:
            progress.create()
            stats = apply_updates(updates, already_correct, progress)

        if stats.cancelled:
            show_ok(
                heading,
                ADDON.getLocalizedString(32611).format(stats.updated, stats.cleared)
            )
        else:
            show_ok(
                ADDON.getLocalizedString(32605),
                ADDON.getLocalizedString(32606).format(
                    stats.updated, stats.cleared, stats.already_correct)
            )

    except Exception as e:
        log("General", f"Top 250 update error: {e}", xbmc.LOGERROR)
        show_ok(heading, str(e))
