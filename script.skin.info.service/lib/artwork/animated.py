"""Find and add animated GIF posters to library items."""
from __future__ import annotations

import os
import xbmc
import xbmcvfs
from lib.infrastructure.dialogs import show_textviewer, show_select, show_notification, show_yesno
import xbmcgui
from typing import Optional, Dict, List
from datetime import datetime

from lib.kodi.client import request, log, ADDON, extract_result, MEDIA_TYPE_SPECS
from lib.infrastructure import tasks as task_manager
from lib.infrastructure.dialogs import ProgressDialog
from lib.infrastructure.menus import Menu, MenuItem
from lib.data.database import init_database
from lib.data.database.workflow import save_operation_stats, get_last_operation_stats
from lib.data.database import gif as gif_db


def run_scanner(scope: Optional[str] = None, scan_mode: Optional[str] = None) -> None:
    """Run gif poster scanner. None values prompt via dialog or fall back to addon settings."""
    init_database()

    last_stats = get_last_operation_stats('gif_scan')

    items = [MenuItem(ADDON.getLocalizedString(32540), lambda: _run_scan(scope, scan_mode))]
    if last_stats:
        items.append(
            MenuItem(ADDON.getLocalizedString(32086), lambda: _view_report(last_stats), loop=True)
        )

    items.extend([
        MenuItem(ADDON.getLocalizedString(32541), _view_cache_stats, loop=True),
        MenuItem(ADDON.getLocalizedString(32542), _clear_cache, loop=True)
    ])

    menu = Menu(ADDON.getLocalizedString(32192), items)
    menu.show()


def _format_gif_scan_report(stats: dict, timestamp: str, scope: Optional[str]) -> str:
    """Format a gif-scan operation result for textviewer display."""
    try:
        formatted_time = datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        formatted_time = timestamp

    lines = ["[B]Operation: Scan for Animated Posters[/B]"]
    if scope:
        scope_label = scope.title() if scope != 'all' else 'All'
        lines.append(f"Scope: {scope_label}")
    lines.append(f"Completed: {formatted_time}")
    lines.append("")

    scan_mode = stats.get('scan_mode', 'incremental')
    lines.append(f"Mode: {'Full' if scan_mode == 'full' else 'Incremental'}")
    lines.append(f"Items Scanned: {stats.get('scanned_count', 0)}")
    lines.append("")

    found = stats.get('found_count', 0)
    skipped_cached = stats.get('skipped_cached', stats.get('skipped_count', 0))
    skipped_existing = stats.get('skipped_existing', 0)

    lines.append("[B]Results:[/B]")
    lines.append(f"  New GIFs Added: {found}")
    lines.append(f"  Cached (Unchanged): {skipped_cached}")
    lines.append(f"  Already Set: {skipped_existing}")
    lines.append(f"  Total Processed: {found + skipped_cached + skipped_existing}")

    if stats.get('cancelled'):
        lines.append("")
        lines.append("[B]Status: Cancelled[/B]")

    return "[CR]".join(lines)


def _view_report(last_stats: Dict) -> None:
    """Display the last scan report."""
    report_text = _format_gif_scan_report(
        last_stats['stats'],
        last_stats['timestamp'],
        last_stats.get('scope'),
    )
    show_textviewer(ADDON.getLocalizedString(32543), report_text)


def _view_cache_stats() -> None:
    """Display cache statistics."""
    cache = gif_db.get_all_cached_gifs()

    if not cache:
        show_notification(
            ADDON.getLocalizedString(32547),
            ADDON.getLocalizedString(32073),
            xbmcgui.NOTIFICATION_INFO,
            3000
        )
        return

    lines = []
    lines.append(f"[B]{ADDON.getLocalizedString(32544)}[/B]")
    lines.append("")
    lines.append(ADDON.getLocalizedString(32588).format(len(cache)))
    lines.append("")

    if cache:
        sorted_gifs = sorted(cache.items(), key=lambda x: x[1].get('scanned_at', ''), reverse=True)

        lines.append(f"[B]{ADDON.getLocalizedString(32589).format(20)}[/B]")
        for path, metadata in sorted_gifs[:20]:
            scanned_at = metadata.get('scanned_at', xbmc.getLocalizedString(13205))
            filename = (
                path.split('/')[-1] if '/' in path
                else path.split('\\')[-1] if '\\' in path
                else path
            )
            lines.append(f"  {filename}")
            lines.append(f"    Scanned: {scanned_at}")

        if len(cache) > 20:
            lines.append(f"  {ADDON.getLocalizedString(32590).format(len(cache) - 20)}")

    text = "\n".join(lines)
    show_textviewer(ADDON.getLocalizedString(32544), text)


def _clear_cache() -> None:
    """Clear the GIF cache after confirmation."""
    cache = gif_db.get_all_cached_gifs()
    count = len(cache)

    if count == 0:
        show_notification(
            ADDON.getLocalizedString(32547),
            ADDON.getLocalizedString(32549),
            xbmcgui.NOTIFICATION_INFO,
            3000
        )
        return

    confirmed = show_yesno(
        ADDON.getLocalizedString(32542),
        ADDON.getLocalizedString(32546).format(count)
    )

    if not confirmed:
        return

    removed = gif_db.clear_gif_cache()
    show_notification(
        ADDON.getLocalizedString(32547),
        ADDON.getLocalizedString(32548).format(removed),
        xbmcgui.NOTIFICATION_INFO,
        4000
    )


def _run_scan(scope: Optional[str], scan_mode: Optional[str]) -> None:
    """Execute the GIF scan with the given scope and mode."""
    if scope is None:
        scope = _select_scope()
        if scope is None:
            return

    scope = scope.lower()
    valid_scopes = ("movies", "tvshows", "all")
    if scope not in valid_scopes:
        log(
            "Artwork",
            f"Invalid scope '{scope}' for gif scanner. Expected one of: {', '.join(valid_scopes)}",
            xbmc.LOGWARNING,
        )
        show_notification(
            ADDON.getLocalizedString(32192),
            ADDON.getLocalizedString(32575).format(scope),
            xbmcgui.NOTIFICATION_WARNING,
            4000
        )
        return

    if scan_mode is None:
        scan_mode = _get_scan_mode_from_setting()
        if scan_mode is None:
            return

    scan_mode = scan_mode.lower()
    valid_modes = ("incremental", "full")
    if scan_mode not in valid_modes:
        log(
            "Artwork",
            f"Invalid scan mode '{scan_mode}'. Expected one of: {', '.join(valid_modes)}",
            xbmc.LOGWARNING,
        )
        show_notification(
            ADDON.getLocalizedString(32192),
            ADDON.getLocalizedString(32576).format(scan_mode),
            xbmcgui.NOTIFICATION_WARNING,
            4000
        )
        return

    from lib.infrastructure.menus import run_with_mode_choice

    run_with_mode_choice(
        ADDON.getLocalizedString(32192),
        lambda bg: _run_gif_scan(scope, scan_mode, use_background=bg),
    )


def _run_gif_scan(scope: str, scan_mode: str, use_background: bool) -> None:
    """Open a task context and run the GIF scan in the chosen mode."""
    try:
        with task_manager.TaskContext(ADDON.getLocalizedString(32192)) as ctx:
            progress = ProgressDialog(
                use_background=use_background, heading=ADDON.getLocalizedString(32192))
            if use_background:
                progress.create(ADDON.getLocalizedString(32577))
            else:
                progress.create(
                    f"[B]{ADDON.getLocalizedString(32574).upper()}[/B][CR]"
                    f"{ADDON.getLocalizedString(32278)}")
            try:
                _run_scan_operation(scope, scan_mode, progress, task_context=ctx)
            finally:
                progress.close()
    except Exception as e:
        log("Artwork", f"Animated scan failed: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(
            ADDON.getLocalizedString(32192), f"{ADDON.getLocalizedString(32274)}:[CR]{str(e)}")


def _run_scan_operation(
    scope: str,
    scan_mode: str,
    progress: ProgressDialog,
    task_context=None
) -> bool:
    """Execute the gif scan. Returns True if cancelled."""
    patterns_setting = ADDON.getSetting("gif_patterns")
    if patterns_setting:
        patterns = [p.strip() for p in patterns_setting.split(",") if p.strip()]
    else:
        patterns = ["poster.gif", "animatedposter.gif"]

    force_full_rescan = (scan_mode == "full")

    scanner = ArtworkAnimated(patterns, force_full_rescan, progress, task_context)

    if scope in ("movies", "all"):
        scanner.scan_movies()
        if scanner.cancelled:
            return True

    if scope in ("tvshows", "all"):
        scanner.scan_tvshows()
        if scanner.cancelled:
            return True

    if not scanner.cancelled and scope == "all":
        stale_removed = scanner.cleanup_stale_cache()
        log("Artwork", f"Cleaned {stale_removed} stale GIF cache entries", xbmc.LOGDEBUG)

    scanner.show_summary()

    stats = {
        'found_count': scanner.found_count,
        'scanned_count': scanner.scanned_count,
        'skipped_cached': scanner.skipped_cached,
        'skipped_existing': scanner.skipped_existing,
        'scan_mode': scan_mode,
        'cancelled': scanner.cancelled
    }

    save_operation_stats('gif_scan', stats, scope=scope)

    return scanner.cancelled


def _select_scope() -> Optional[str]:
    """Show dialog to select scan scope."""
    options = [
        ("all", ADDON.getLocalizedString(32579)),
        ("movies", ADDON.getLocalizedString(32580)),
        ("tvshows", ADDON.getLocalizedString(32581))
    ]

    labels = [label for _, label in options]
    choice = show_select(ADDON.getLocalizedString(32552), labels)

    if choice == -1:
        return None

    return options[choice][0]


def _get_scan_mode_from_setting() -> Optional[str]:
    """Get scan mode from setting, prompting if set to 'always_ask'."""
    setting_value = ADDON.getSetting("gif_scan.scan_mode")

    if setting_value == "always_ask":
        cache = gif_db.get_all_cached_gifs()
        cache_info = (
            f" ({ADDON.getLocalizedString(32586).format(len(cache))})" if cache
            else f" ({ADDON.getLocalizedString(32587)})"
        )

        options = [
            (
                "incremental",
                f"{ADDON.getLocalizedString(32582)}{cache_info}",
                ADDON.getLocalizedString(32583),
            ),
            ("full", ADDON.getLocalizedString(32584), ADDON.getLocalizedString(32585))
        ]

        labels = []
        for _, label, desc in options:
            labels.append(f"{label}\n{desc}")

        choice = show_select(ADDON.getLocalizedString(32553), labels)

        if choice == -1:
            return None

        return options[choice][0]

    if setting_value in ("incremental", "full"):
        return setting_value

    return "incremental"


class ArtworkAnimated:
    """Scans for animated gif posters and updates Kodi's art database."""

    def __init__(
        self,
        patterns: List[str],
        force_full_rescan: bool,
        progress: ProgressDialog,
        task_context=None
    ):
        self.patterns = patterns
        self.force_full_rescan = force_full_rescan
        self.progress = progress
        self.task_context = task_context
        self.found_count = 0
        self.scanned_count = 0
        self.skipped_cached = 0
        self.skipped_existing = 0
        self.cancelled = False
        self.accessed_paths = set()

    def scan_movies(self) -> None:
        """Scan all movies for gif posters."""
        self._scan('movie')

    def scan_tvshows(self) -> None:
        """Scan all TV shows for gif posters."""
        self._scan('tvshow')

    def _scan(self, media_type: str) -> None:
        spec = MEDIA_TYPE_SPECS[media_type]
        resp = request(spec.library_method, {"properties": ["file", "art", "dateadded"]})
        if not resp:
            log("Artwork", f"Failed to get {spec.library_key} list", xbmc.LOGWARNING)
            return

        items = extract_result(resp, spec.library_key, [])
        if not items:
            return

        total = len(items)
        for idx, item in enumerate(items):
            if (
                (self.task_context and self.task_context.abort_flag.is_requested())
                or self.progress.is_cancelled()
            ):
                self.cancelled = True
                break

            self.scanned_count += 1
            item_id = item.get(spec.id_key)
            title = item.get("label", xbmc.getLocalizedString(13205))
            file_path = item.get("file", "")
            current_art = item.get("art", {})

            percent = int((idx / total) * 100)
            message = (
                f"Scanning: {title}\n"
                f"Progress: {idx + 1}/{total} | Found: {self.found_count} | "
                f"Cached: {self.skipped_cached} | Existing: {self.skipped_existing}"
            )
            self.progress.update(percent, message)
            if self.task_context is not None:
                self.task_context.mark_progress()

            if not item_id or not file_path:
                continue

            gif_path = self._find_gif(file_path)

            if gif_path:
                self.accessed_paths.add(gif_path)

                if not self.force_full_rescan and self._should_skip_gif(gif_path):
                    self.skipped_cached += 1
                    log(
                        "Artwork",
                        f"GIF scan: Skipped cached GIF for {spec.id_key}={item_id} "
                        f"({title}): {gif_path}",
                        xbmc.LOGDEBUG,
                    )
                    continue

                log(
                    "Artwork",
                    f"GIF scan: Setting GIF for {spec.id_key}={item_id} ({title}): {gif_path}",
                    xbmc.LOGDEBUG,
                )
                if self._set_art(media_type, item_id, title, gif_path):
                    self._update_cache(gif_path)
                    self.found_count += 1
                else:
                    log(
                        "Artwork",
                        f"GIF scan: Failed to apply GIF for {spec.id_key}={item_id} ({title})",
                        xbmc.LOGWARNING,
                    )
            else:
                if current_art.get("animatedposter"):
                    self.skipped_existing += 1
                else:
                    log(
                        "Artwork",
                        f"GIF scan: No matching GIF found for {spec.id_key}={item_id} "
                        f"({title}), folder={os.path.dirname(file_path)}",
                        xbmc.LOGDEBUG,
                    )


    def _find_gif(self, file_path: str) -> Optional[str]:
        """Look for gif files in the media file's folder.

        Matching: exact match first, then suffix match (e.g. "movie.poster.gif"),
        preferring shortest filename when multiple match.
        """
        if not file_path:
            return None

        try:
            if file_path.startswith("stack://"):
                stack_content = file_path.replace("stack://", "")
                if " , " in stack_content:
                    file_path = stack_content.split(" , ")[0]
                else:
                    file_path = stack_content.split(",")[0].strip()

            if file_path.startswith("bluray://"):
                import urllib.parse
                hostname = file_path[9:]
                if "/" in hostname:
                    hostname = hostname.split("/")[0]
                hostname = urllib.parse.unquote(hostname)
                if hostname.startswith("udf://"):
                    file_path = urllib.parse.unquote(hostname[6:])
                else:
                    file_path = hostname

            file_path = xbmcvfs.translatePath(file_path)

            folder = os.path.dirname(file_path)

            if not os.path.isdir(folder):
                return None

            for pattern in self.patterns:
                gif_path = os.path.join(folder, pattern)
                if os.path.isfile(gif_path):
                    return gif_path

            try:
                files = os.listdir(folder)
            except OSError as e:
                log("Artwork", f"Cannot list directory '{folder}': {str(e)}", xbmc.LOGWARNING)
                return None

            matches = []
            for pattern in self.patterns:
                pattern_lower = pattern.lower()
                pattern_base, pattern_ext = os.path.splitext(pattern_lower)

                if pattern_ext != '.gif':
                    pattern_base = pattern_lower

                for filename in files:
                    file_base, file_ext = os.path.splitext(filename)

                    if file_ext.lower() == '.gif' and file_base.lower().endswith(pattern_base):
                        matches.append((filename, len(filename)))

            # shortest match is the most specific
            if matches:
                matches.sort(key=lambda x: x[1])
                return os.path.join(folder, matches[0][0])

            return None

        except Exception as e:
            log("Artwork", f"Error finding gif for '{file_path}': {str(e)}", xbmc.LOGERROR)
            return None

    def _set_art(self, media_type: str, item_id: int, title: str, gif_path: str) -> bool:
        """Set animatedposter art on a movie or tvshow via JSON-RPC."""
        spec = MEDIA_TYPE_SPECS[media_type]
        try:
            if not xbmcvfs.exists(gif_path):
                log(
                    "Artwork",
                    f"GIF file does not exist for {spec.id_key}={item_id} ({title}): {gif_path}",
                    xbmc.LOGWARNING,
                )
                return False

            resp = request(
                spec.set_method,
                {spec.id_key: item_id, "art": {"animatedposter": gif_path}},
            )
            if resp is None:
                log(
                    "Artwork",
                    f"JSON-RPC returned None for {spec.id_key}={item_id} ({title}), "
                    f"path={gif_path}",
                    xbmc.LOGWARNING,
                )
                return False

            log(
                "Artwork",
                f"Successfully set animatedposter for {spec.id_key}={item_id} ({title}), "
                f"response: {resp}",
                xbmc.LOGDEBUG,
            )
            return True
        except Exception as e:
            log(
                "Artwork",
                f"Exception setting art for {spec.id_key}={item_id} ({title}), "
                f"path={gif_path}: {str(e)}",
                xbmc.LOGERROR,
            )
            return False

    def _should_skip_gif(self, gif_path: str) -> bool:
        """True if GIF is cached and unchanged (safe to skip in incremental mode)."""
        cached_entry = gif_db.get_cached_gif(gif_path)
        if not cached_entry:
            return False

        cached_mtime = cached_entry.get("mtime")
        if cached_mtime is None:
            return False

        try:
            current_mtime = os.path.getmtime(gif_path)
            # Compare mtimes (allow 1 second tolerance for filesystem precision)
            if abs(current_mtime - float(cached_mtime)) < 1.0:
                return True
        except (OSError, ValueError):
            return False

        return False

    def _update_cache(self, gif_path: str) -> None:
        """Update cache entry for a GIF file."""
        try:
            mtime = os.path.getmtime(gif_path)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            gif_db.update_gif_cache(gif_path, mtime, current_time)
        except OSError:
            pass

    def cleanup_stale_cache(self) -> int:
        """Remove cache entries for GIF files not found during this scan."""
        return gif_db.cleanup_stale_gifs(self.accessed_paths)

    def show_summary(self) -> None:
        """Show completion notification."""
        if self.cancelled:
            message = ADDON.getLocalizedString(32593).format(
                self.found_count, self.skipped_cached, self.skipped_existing
            )
        else:
            message = ADDON.getLocalizedString(32594).format(
                self.found_count, self.skipped_cached, self.skipped_existing
            )

        show_notification(
            ADDON.getLocalizedString(32192),
            message,
            xbmcgui.NOTIFICATION_INFO,
            5000
        )
