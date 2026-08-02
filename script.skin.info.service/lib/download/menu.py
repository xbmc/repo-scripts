"""Download artwork menu UI handlers."""
from __future__ import annotations

import xbmc
from typing import Optional, List

from lib.infrastructure.dialogs import show_ok, show_textviewer
from lib.artwork.config import REVIEW_MEDIA_FILTERS, REVIEW_SCOPE_LABELS

from lib.data import database as db
from lib.download.workflows import (
    LOG_DIR,
    download_scope_artwork,
    format_folder_section,
    format_mismatch_section,
)
from lib.kodi.client import ADDON


def show_download_report() -> None:
    """Show the last download report from operation history."""
    last_report = db.get_last_operation_stats('artwork_download')

    if not last_report:
        show_ok(
            ADDON.getLocalizedString(32040),
            ADDON.getLocalizedString(32041)
        )
        return

    stats = last_report['stats']
    scope = last_report.get('scope', 'unknown')
    timestamp = last_report['timestamp']

    scope_label = REVIEW_SCOPE_LABELS.get(scope, scope.title())

    downloaded = stats.get('downloaded', 0)
    skipped = stats.get('skipped', 0)
    failed = stats.get('failed', 0)
    total_jobs = stats.get('total_jobs', 0)
    total_items = stats.get('total_items', 0)
    bytes_downloaded = stats.get('bytes_downloaded', 0)
    cancelled = stats.get('cancelled', False)
    mismatch_counts = stats.get('mismatch_counts', {})

    mb = bytes_downloaded / (1024 * 1024) if bytes_downloaded > 0 else 0

    status = ADDON.getLocalizedString(32042) if cancelled else ADDON.getLocalizedString(32121)

    lines = [
        f"[B]Artwork Download Report - {status}[/B]",
        "",
        f"Scope: {scope_label}",
        f"Timestamp: {timestamp}",
        "",
        f"Library items scanned: {total_items}",
        f"Total artwork URLs: {total_jobs}",
        f"Downloaded: {downloaded}",
        f"Skipped (already exists): {skipped}",
        f"Failed: {failed}",
        "",
        f"Total size: {mb:.2f} MB",
    ]
    lines.extend(format_folder_section(stats.get('folder_counts', {})))
    lines.extend(format_mismatch_section(mismatch_counts))
    lines.extend([
        "",
        "",
        f"Log files location: {LOG_DIR}",
        "(Most recent downloads saved to artwork_download.log)",
    ])

    show_textviewer(ADDON.getLocalizedString(32520), "\n".join(lines))


def run_download_menu() -> None:
    """Show the download menu: scope-pick + download, plus a report viewer if history exists."""
    from lib.infrastructure.menus import Menu, MenuItem

    db.init_database()

    items = [
        MenuItem(ADDON.getLocalizedString(32290), _handle_download, loop=True),
    ]

    if db.get_last_operation_stats('artwork_download'):
        items.append(MenuItem(ADDON.getLocalizedString(32086), show_download_report, loop=True))

    menu = Menu(ADDON.getLocalizedString(32522), items)
    menu.show()


def _handle_download():
    """Show the scope-selection menu (all / movies / tvshows / music)."""
    from lib.infrastructure.menus import Menu, MenuItem

    scope_menu = Menu(ADDON.getLocalizedString(32523), [
        MenuItem(xbmc.getLocalizedString(593), lambda: _select_mode('all', None)),
        MenuItem(xbmc.getLocalizedString(342),
                 lambda: _select_mode('movies', REVIEW_MEDIA_FILTERS.get('movies'))),
        MenuItem(xbmc.getLocalizedString(20343),
                 lambda: _select_mode('tvshows', REVIEW_MEDIA_FILTERS.get('tvshows'))),
        MenuItem(xbmc.getLocalizedString(2),
                 lambda: _select_mode('music', REVIEW_MEDIA_FILTERS.get('music'))),
    ])
    return scope_menu.show()


def _select_mode(scope: str, media_filter: Optional[List[str]]):
    """Show foreground/background run-mode menu, then kick off the download."""
    from lib.infrastructure.menus import run_with_mode_choice

    return run_with_mode_choice(
        "Download Artwork",
        lambda bg: download_scope_artwork(
            scope=scope, media_filter=media_filter, use_background=bg),
    )
