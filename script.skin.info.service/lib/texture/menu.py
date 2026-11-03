"""Texture cache management UI and menu handlers."""
from __future__ import annotations

import xbmc
import xbmcgui
from datetime import datetime
from typing import Optional, List, Union, Dict, Any, Final

from lib.data.database._infrastructure import init_database
from lib.data.database.workflow import save_operation_stats, get_last_operation_stats
from lib.infrastructure.dialogs import show_ok, show_textviewer, ProgressDialog, DialogProgress
from lib.infrastructure.workers import STALL_TIMEOUT_SECONDS

_RESUME_HINT: Final = "[B]CANCEL TO RESUME LATER[/B]"
from lib.kodi.client import log, ADDON
from lib.kodi.settings import KodiSettings
from lib.texture.cache import (
    precache_library_artwork,
    precache_and_download_artwork,
    cleanup_orphaned_textures,
)
from lib.texture.library import get_cached_textures, remove_texture
from lib.texture.stats import calculate_texture_statistics, format_statistics_report
from lib.texture.utilities import report_url_lines


def run_texture_maintenance() -> None:
    """Show the texture cache manager menu (precache, cleanup, stats, last report)."""
    from lib.infrastructure.menus import Menu, MenuItem

    init_database()

    precache_stats = get_last_operation_stats('texture_precache')
    cleanup_stats = get_last_operation_stats('texture_cleanup')

    last_stats = None
    if precache_stats and cleanup_stats:
        precache_time = datetime.fromisoformat(precache_stats['timestamp'])
        cleanup_time = datetime.fromisoformat(cleanup_stats['timestamp'])
        last_stats = precache_stats if precache_time > cleanup_time else cleanup_stats
    elif precache_stats:
        last_stats = precache_stats
    elif cleanup_stats:
        last_stats = cleanup_stats

    items = [
        MenuItem(ADDON.getLocalizedString(32083), _handle_precache, loop=True),
    ]

    if KodiSettings.enable_combo_workflows():
        items.append(
            MenuItem(ADDON.getLocalizedString(32440), _handle_precache_download, loop=True)
        )

    items.extend([
        MenuItem(ADDON.getLocalizedString(32087), _show_cleanup_menu, loop=True),
        MenuItem(ADDON.getLocalizedString(32085), _handle_stats, loop=True),
    ])

    if last_stats:
        items.append(MenuItem(ADDON.getLocalizedString(32086), _show_last_report, loop=True))

    menu = Menu(ADDON.getLocalizedString(32082), items)
    menu.show()


def _handle_precache():
    """Handle pre-cache: pick a library scope, then a mode."""
    from lib.infrastructure.menus import Menu, MenuItem

    scope_menu = Menu(ADDON.getLocalizedString(32441), [
        MenuItem(xbmc.getLocalizedString(593), lambda: _run_precache(None, False)),
        MenuItem(xbmc.getLocalizedString(342), lambda: _run_precache(["movie"], False)),
        MenuItem(xbmc.getLocalizedString(20343), lambda: _run_precache(["tvshow"], False)),
        MenuItem(xbmc.getLocalizedString(33054), lambda: _run_precache(["season"], False)),
        MenuItem(xbmc.getLocalizedString(20360), lambda: _run_precache(["episode"], False)),
        MenuItem(xbmc.getLocalizedString(20389), lambda: _run_precache(["musicvideo"], False)),
        MenuItem(xbmc.getLocalizedString(20434), lambda: _run_precache(["set"], False)),
        MenuItem(xbmc.getLocalizedString(133), lambda: _run_precache(["artist"], False)),
        MenuItem(xbmc.getLocalizedString(132), lambda: _run_precache(["album"], False)),
    ])
    return scope_menu.show()


def _handle_precache_download():
    """Handle pre-cache plus download: pick a library scope, then a mode."""
    from lib.infrastructure.menus import Menu, MenuItem

    scope_menu = Menu(ADDON.getLocalizedString(32451), [
        MenuItem(xbmc.getLocalizedString(593), lambda: _run_precache(None, True)),
        MenuItem(xbmc.getLocalizedString(342), lambda: _run_precache(["movie"], True)),
        MenuItem(xbmc.getLocalizedString(20343), lambda: _run_precache(["tvshow"], True)),
        MenuItem(xbmc.getLocalizedString(33054), lambda: _run_precache(["season"], True)),
        MenuItem(xbmc.getLocalizedString(20360), lambda: _run_precache(["episode"], True)),
        MenuItem(xbmc.getLocalizedString(20389), lambda: _run_precache(["musicvideo"], True)),
        MenuItem(xbmc.getLocalizedString(20434), lambda: _run_precache(["set"], True)),
        MenuItem(xbmc.getLocalizedString(133), lambda: _run_precache(["artist"], True)),
        MenuItem(xbmc.getLocalizedString(132), lambda: _run_precache(["album"], True)),
    ])
    return scope_menu.show()


def _run_precache(selected_types: Optional[List[str]], enable_download: bool):
    """Run pre-cache for the scope once the user picks foreground or background."""
    from lib.infrastructure.menus import run_with_mode_choice

    return run_with_mode_choice(
        ADDON.getLocalizedString(32455),
        lambda bg: _execute_precache(selected_types, enable_download, bg),
    )


def _execute_precache(selected_types: Optional[List[str]], enable_download: bool,
                      use_background: bool) -> None:
    """Execute pre-cache as a task with progress, then show and save its report."""
    from lib.infrastructure import tasks as task_manager

    progress: Optional[ProgressDialog] = None
    dialog = xbmcgui.Dialog()

    operation_name = ADDON.getLocalizedString(32455)

    try:
        with task_manager.TaskContext(operation_name) as ctx:
            progress = ProgressDialog(
                use_background=use_background,
                heading=operation_name,
                fg_message_prefix=_RESUME_HINT,
            )
            progress.create(ADDON.getLocalizedString(32336))

            if enable_download:
                stats = precache_and_download_artwork(
                    progress_dialog=progress, media_types=selected_types, task_context=ctx
                )
            else:
                stats = precache_library_artwork(
                    progress_dialog=progress, media_types=selected_types, task_context=ctx
                )

            progress.close()

        cancelled = stats.get('cancelled', False)
        stalled = stats.get('stalled', False)

        if enable_download:
            total = stats['total_urls']
            cached = stats['cached']
            downloaded = stats['downloaded']
            skipped = stats['download_skipped']
            cache_failed = stats['cache_failed']
            download_failed = stats['download_failed']
            mb = stats['bytes_downloaded'] / (1024 * 1024) if stats['bytes_downloaded'] > 0 else 0

            title = (ADDON.getLocalizedString(32459) if cancelled or stalled
                     else ADDON.getLocalizedString(32460))

            message_parts = [
                ADDON.getLocalizedString(32463).format(total),
                ADDON.getLocalizedString(32464).format(cached),
                ADDON.getLocalizedString(32465).format(downloaded, mb),
                ADDON.getLocalizedString(32286).format(skipped)
            ]

            if cache_failed > 0 or download_failed > 0:
                message_parts.append(
                    ADDON.getLocalizedString(32467).format(cache_failed, download_failed)
                )
        else:
            save_operation_stats('texture_precache', {
                'cached_count': stats['already_cached'] + stats['successfully_cached'],
                'total_count': stats.get('total_urls', 0),
                'new_count': stats['successfully_cached'],
                'failed_count': stats.get('failed', 0),
                'cancelled': cancelled
            })

            total = stats['total_urls']
            already = stats['already_cached']
            newly = stats['successfully_cached']

            title = (ADDON.getLocalizedString(32459) if cancelled
                     else ADDON.getLocalizedString(32460))

            message_parts = [
                ADDON.getLocalizedString(32463).format(total),
                ADDON.getLocalizedString(32468).format(already),
                ADDON.getLocalizedString(32469).format(newly)
            ]

            if stats['failed'] > 0:
                message_parts.append(ADDON.getLocalizedString(32470).format(stats['failed']))

        if stalled:
            message_parts.append("")
            message_parts.append(f"[B]{ADDON.getLocalizedString(32066)}[/B]")
            message_parts.append(
                ADDON.getLocalizedString(32067).format(STALL_TIMEOUT_SECONDS)
            )
        elif cancelled:
            message_parts.append("")
            message_parts.append(f"[B]{ADDON.getLocalizedString(32471)}[/B]")

        message = "[CR]".join(message_parts)
        dialog.ok(title, message)

        failed_urls = stats.get('failed_urls', [])
        if failed_urls and dialog.yesno(
            ADDON.getLocalizedString(32460),
            ADDON.getLocalizedString(32498).format(len(failed_urls))
        ):
            report_lines = report_url_lines(sorted(failed_urls))
            show_textviewer(ADDON.getLocalizedString(32499), "\n".join(report_lines))

    except Exception as e:
        if progress:
            try:
                progress.close()
            except Exception:
                pass
        log("Texture", f"Pre-cache failed: {str(e)}", xbmc.LOGERROR)
        dialog.ok(operation_name, f"{ADDON.getLocalizedString(32170)}:[CR]{str(e)}")


def _show_cleanup_menu():
    """Show the cleanup menu: orphaned textures or the advanced options."""
    from lib.infrastructure.menus import Menu, MenuItem

    menu = Menu(ADDON.getLocalizedString(32087), [
        MenuItem(ADDON.getLocalizedString(32088), _handle_standard_cleanup, loop=True),
        MenuItem(ADDON.getLocalizedString(32089), _handle_age_cleanup, loop=True),
    ])
    return menu.show()


def _handle_standard_cleanup():
    """Handle orphaned texture cleanup once the user picks a mode."""
    from lib.infrastructure.menus import run_with_mode_choice

    return run_with_mode_choice(
        ADDON.getLocalizedString(32334),
        _execute_standard_cleanup,
    )


def _execute_standard_cleanup(use_background: bool) -> None:
    """Execute orphaned texture cleanup as a task, then save its stats and show the result."""
    from lib.infrastructure import tasks as task_manager

    progress: Optional[ProgressDialog] = None
    dialog = xbmcgui.Dialog()

    try:
        with task_manager.TaskContext(ADDON.getLocalizedString(32334)) as ctx:
            progress = ProgressDialog(
                use_background=use_background,
                heading=ADDON.getLocalizedString(32334),
            )
            progress.create(ADDON.getLocalizedString(32335))
            stats = cleanup_orphaned_textures(
                progress_dialog=progress, media_types=None, task_context=ctx
            )
            progress.close()

        save_operation_stats('texture_cleanup', {
            'cached_count': stats['total_library'],
            'total_count': stats['total_cached'],
            'removed_count': stats['removed'],
            'orphaned_count': stats['orphaned_found'],
            'cancelled': stats.get('cancelled', False)
        })

        total_cached = stats['total_cached']
        library = stats['total_library']
        orphaned_found = stats['orphaned_found']
        removed = stats['removed']
        cancelled = stats.get('cancelled', False)

        if cancelled:
            title = ADDON.getLocalizedString(32461)
        else:
            title = ADDON.getLocalizedString(32462)

        message_parts = [
            ADDON.getLocalizedString(32496).format(total_cached, library),
            ADDON.getLocalizedString(32497).format(orphaned_found, removed)
        ]

        if stats['failed'] > 0:
            message_parts.append(ADDON.getLocalizedString(32470).format(stats['failed']))

        if cancelled:
            message_parts.append(ADDON.getLocalizedString(32471))

        message = "[CR]".join(message_parts)
        dialog.ok(title, message)

    except Exception as e:
        if progress:
            try:
                progress.close()
            except Exception:
                pass
        log("Texture", f"Cleanup failed: {str(e)}", xbmc.LOGERROR)
        dialog.ok(ADDON.getLocalizedString(32087),
                  f"{ADDON.getLocalizedString(32170)}:[CR]{str(e)}")


def _handle_stats() -> None:
    """Show texture cache statistics."""
    dialog = xbmcgui.Dialog()
    progress = DialogProgress()
    progress.create(ADDON.getLocalizedString(32180), ADDON.getLocalizedString(32472))

    try:
        textures = get_cached_textures()
        stats = calculate_texture_statistics(textures, progress)
        progress.close()

        if stats:
            report = format_statistics_report(stats)
            dialog.textviewer(ADDON.getLocalizedString(32180), report, usemono=True)
        else:
            dialog.ok(ADDON.getLocalizedString(32180), ADDON.getLocalizedString(32181))
    except Exception as e:
        progress.close()
        log("Texture", f" Stats failed: {str(e)}", xbmc.LOGERROR)
        dialog.ok(ADDON.getLocalizedString(32180),
                  f"{ADDON.getLocalizedString(32170)}:[CR]{str(e)}")


def cleanup_textures_by_age(age_days: int,
                            progress_dialog: Optional[Union[xbmcgui.DialogProgress,
                                                            xbmcgui.DialogProgressBG]] = None,
                            task_context: Optional[Any] = None,
                            textures: Optional[List[Dict[str, Any]]] = None) -> Dict[str, int]:
    """Remove cached textures unused for the given days, fetching the list unless given one."""
    from datetime import datetime, timedelta

    stats = {
        'total_textures': 0,
        'old_textures': 0,
        'removed': 0,
        'failed': 0,
        'cancelled': False
    }

    try:
        if progress_dialog:
            progress_dialog.update(0, ADDON.getLocalizedString(32490))

        if textures is None:
            textures = get_cached_textures()
        stats['total_textures'] = len(textures)

        if not textures:
            return stats

        cutoff_date = datetime.now() - timedelta(days=age_days)
        old_textures = []

        if progress_dialog:
            progress_dialog.update(10, ADDON.getLocalizedString(32332).format(len(textures)))

        for i, texture in enumerate(textures):
            if task_context and task_context.abort_flag.is_requested():
                stats['cancelled'] = True
                return stats

            if progress_dialog and i % 100 == 0:
                if (isinstance(progress_dialog, xbmcgui.DialogProgress)
                        and progress_dialog.iscanceled()):
                    stats['cancelled'] = True
                    return stats
                progress_dialog.update(10 + int((i / len(textures)) * 40))

            sizes = texture.get('sizes', [])
            if not sizes:
                continue

            for size in sizes:
                lastusetime = size.get('lastused')
                if lastusetime:
                    try:
                        last_used = datetime.fromisoformat(lastusetime)
                        if last_used < cutoff_date:
                            old_textures.append(texture)
                            break
                    except Exception:
                        pass

        stats['old_textures'] = len(old_textures)

        if not old_textures:
            return stats

        if progress_dialog:
            progress_dialog.update(50, ADDON.getLocalizedString(32492).format(len(old_textures)))

        for i, texture in enumerate(old_textures):
            if task_context and task_context.abort_flag.is_requested():
                stats['cancelled'] = True
                return stats

            if progress_dialog and i % 10 == 0:
                if (isinstance(progress_dialog, xbmcgui.DialogProgress)
                        and progress_dialog.iscanceled()):
                    stats['cancelled'] = True
                    return stats
                progress_dialog.update(50 + int((i / len(old_textures)) * 50))

            texture_id = texture.get('textureid')
            if texture_id:
                if remove_texture(texture_id):
                    stats['removed'] += 1
                else:
                    stats['failed'] += 1

        if progress_dialog:
            progress_dialog.update(100, ADDON.getLocalizedString(32426))

    except Exception as e:
        log("Texture", f" Age cleanup failed: {str(e)}", xbmc.LOGERROR)
        raise

    return stats


def _handle_age_cleanup():
    """Handle age cleanup: pick how many days unused counts as old."""
    from lib.infrastructure.menus import Menu, MenuItem

    menu = Menu(ADDON.getLocalizedString(32473), [
        MenuItem(ADDON.getLocalizedString(32474), lambda: _execute_age_cleanup(30)),
        MenuItem(ADDON.getLocalizedString(32475), lambda: _execute_age_cleanup(60)),
        MenuItem(ADDON.getLocalizedString(32476), lambda: _execute_age_cleanup(90)),
        MenuItem(ADDON.getLocalizedString(32477), lambda: _execute_age_cleanup(180)),
        MenuItem(ADDON.getLocalizedString(32478), lambda: _execute_age_cleanup(365)),
    ])
    return menu.show()


def _execute_age_cleanup(age_days: int) -> None:
    """Execute age cleanup: find textures unused past the cutoff, confirm, then pick a mode."""
    dialog = xbmcgui.Dialog()
    progress = DialogProgress()
    progress.create(ADDON.getLocalizedString(32330), ADDON.getLocalizedString(32331))

    try:
        from datetime import datetime, timedelta

        textures = get_cached_textures()
        total_textures = len(textures)

        if not textures:
            progress.close()
            dialog.ok(ADDON.getLocalizedString(32182), ADDON.getLocalizedString(32182))
            return

        cutoff_date = datetime.now() - timedelta(days=age_days)
        old_textures = []
        oldest_date = None

        progress.update(20, ADDON.getLocalizedString(32332).format(total_textures))

        for i, texture in enumerate(textures):
            if progress.iscanceled():
                progress.close()
                return

            if i % 100 == 0:
                progress.update(20 + int((i / total_textures) * 60))

            sizes = texture.get('sizes', [])
            if not sizes:
                continue

            for size in sizes:
                lastusetime = size.get('lastused')
                if lastusetime:
                    try:
                        last_used = datetime.fromisoformat(lastusetime)
                        if last_used < cutoff_date:
                            old_textures.append(texture)
                            if oldest_date is None or last_used < oldest_date:
                                oldest_date = last_used
                            break
                    except Exception:
                        pass

        progress.close()

        if not old_textures:
            dialog.ok(
                ADDON.getLocalizedString(32479),
                f"{ADDON.getLocalizedString(32480).format(age_days)}[CR][CR]"
                f"{ADDON.getLocalizedString(32481).format(total_textures)}"
            )
            return

        oldest_str = (oldest_date.strftime('%Y-%m-%d') if oldest_date
                      else xbmc.getLocalizedString(13205))

        confirm = dialog.yesno(
            ADDON.getLocalizedString(32482),
            f"{ADDON.getLocalizedString(32483).format(len(old_textures), age_days)}[CR]"
            f"{ADDON.getLocalizedString(32484).format(total_textures, oldest_str)}"
        )

        if not confirm:
            return

    except Exception as e:
        progress.close()
        log("Texture", f" Analysis failed: {str(e)}", xbmc.LOGERROR)
        dialog.ok(ADDON.getLocalizedString(32184),
                  f"{ADDON.getLocalizedString(32485)}:[CR]{str(e)}")
        return

    from lib.infrastructure.menus import run_with_mode_choice

    return run_with_mode_choice(
        ADDON.getLocalizedString(32333),
        lambda bg: _execute_age_cleanup_with_mode(age_days, bg, textures),
    )


def _execute_age_cleanup_with_mode(age_days: int, use_background: bool,
                                   textures: Optional[List[Dict[str, Any]]] = None) -> None:
    """Execute age cleanup as a task, then save its stats and show the result."""
    from lib.infrastructure import tasks as task_manager

    progress: Optional[Union[xbmcgui.DialogProgress, xbmcgui.DialogProgressBG]] = None
    dialog = xbmcgui.Dialog()

    try:
        with task_manager.TaskContext(ADDON.getLocalizedString(32333)) as ctx:
            if use_background:
                progress = xbmcgui.DialogProgressBG()
                progress.create(ADDON.getLocalizedString(32333), ADDON.getLocalizedString(32335))
            else:
                progress = DialogProgress()
                progress.create(ADDON.getLocalizedString(32333), ADDON.getLocalizedString(32335))
            stats = cleanup_textures_by_age(age_days, progress_dialog=progress, task_context=ctx,
                                            textures=textures)
            progress.close()

        save_operation_stats('texture_age_cleanup', {
            'age_days': age_days,
            'total_count': stats['total_textures'],
            'old_count': stats['old_textures'],
            'removed_count': stats['removed'],
            'cancelled': stats.get('cancelled', False)
        })

        total_textures = stats['total_textures']
        old_textures_count = stats['old_textures']
        removed = stats['removed']
        cancelled = stats.get('cancelled', False)

        if cancelled:
            title = ADDON.getLocalizedString(32461)
        else:
            title = ADDON.getLocalizedString(32462)

        message_parts = [
            ADDON.getLocalizedString(32493).format(total_textures),
            ADDON.getLocalizedString(32494).format(age_days, old_textures_count),
            ADDON.getLocalizedString(32495).format(removed)
        ]

        if stats['failed'] > 0:
            message_parts.append(ADDON.getLocalizedString(32470).format(stats['failed']))

        if cancelled:
            message_parts.append(ADDON.getLocalizedString(32471))

        message = "[CR]".join(message_parts)
        dialog.ok(title, message)

    except Exception as e:
        if progress:
            try:
                progress.close()
            except Exception:
                pass
        log("Texture", f" Age cleanup failed: {str(e)}", xbmc.LOGERROR)
        dialog.ok(ADDON.getLocalizedString(32087),
                  f"{ADDON.getLocalizedString(32170)}:[CR]{str(e)}")


def _format_completed_time(timestamp: str) -> str:
    """Best-effort ISO-string to `YYYY-MM-DD HH:MM`. Returns the input on parse failure."""
    try:
        return datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        return timestamp


def _format_precache_report(stats: dict, timestamp: str) -> str:
    """Format a `texture_precache` operation result for textviewer display."""
    lines = [
        "[B]Operation: Pre-Cache Library Artwork[/B]",
        f"Completed: {_format_completed_time(timestamp)}",
        (f"Cached: {stats.get('cached_count', 0)}/{stats.get('total_count', 0)} "
         f"({stats.get('new_count', 0)} new)"),
    ]
    failed = stats.get('failed_count', 0)
    if failed > 0:
        lines.append(f"Failed: {failed}")
    if stats.get('cancelled'):
        lines.append("[B]Status: Cancelled[/B]")
    return "[CR]".join(lines)


def _format_cleanup_report(stats: dict, timestamp: str) -> str:
    """Format a `texture_cleanup` operation result for textviewer display."""
    lines = [
        "[B]Operation: Clean Orphaned Textures[/B]",
        f"Completed: {_format_completed_time(timestamp)}",
        f"Cached: {stats.get('cached_count', 0)}/{stats.get('total_count', 0)} in library",
        f"Removed: {stats.get('removed_count', 0)}/{stats.get('orphaned_count', 0)} orphaned",
    ]
    if stats.get('cancelled'):
        lines.append("[B]Status: Cancelled[/B]")
    return "[CR]".join(lines)


def _format_age_cleanup_report(stats: dict, timestamp: str) -> str:
    """Format a `texture_age_cleanup` operation result for textviewer display."""
    lines = [
        f"[B]Operation: Clean Textures Unused for {stats.get('age_days', 0)} Days[/B]",
        f"Completed: {_format_completed_time(timestamp)}",
        (f"Removed: {stats.get('removed_count', 0)}/{stats.get('old_count', 0)} old "
         f"of {stats.get('total_count', 0)} cached"),
    ]
    if stats.get('cancelled'):
        lines.append("[B]Status: Cancelled[/B]")
    return "[CR]".join(lines)


_REPORT_FORMATTERS = {
    'texture_precache': _format_precache_report,
    'texture_cleanup': _format_cleanup_report,
    'texture_age_cleanup': _format_age_cleanup_report,
}


def _show_last_report() -> None:
    """Show the newest of the last pre-cache, cleanup and age cleanup reports."""
    runs = [run for run in map(get_last_operation_stats, _REPORT_FORMATTERS) if run]
    if runs:
        last = max(runs, key=lambda run: datetime.fromisoformat(run['timestamp']))
        report_text = _REPORT_FORMATTERS[last['operation']](last['stats'], last['timestamp'])
        show_textviewer(ADDON.getLocalizedString(32488), report_text)
        return

    show_ok(
        ADDON.getLocalizedString(32086),
        ADDON.getLocalizedString(32489)
    )
