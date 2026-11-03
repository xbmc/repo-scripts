"""Kodi dialog wrappers: progress bars, notifications and prompts."""
from __future__ import annotations

import threading
from typing import Optional, Sequence, Union
import xbmc
import xbmcgui

_MONITOR: Optional[xbmc.Monitor] = None


def _shutdown_monitor() -> xbmc.Monitor:
    """Shared monitor behind `DialogProgress.iscanceled()`'s shutdown check."""
    global _MONITOR
    if _MONITOR is None:
        _MONITOR = xbmc.Monitor()
    return _MONITOR


class DialogProgress(xbmcgui.DialogProgress):
    """`xbmcgui.DialogProgress` whose `iscanceled()` is also true once Kodi is shutting down."""

    def iscanceled(self) -> bool:
        """True if the user cancelled or Kodi is shutting down."""
        return _shutdown_monitor().abortRequested() or super().iscanceled()


class ProgressDialog:
    """Foreground or background progress dialog with clamped percent and optional throttling."""

    def __init__(self, heading: str, use_background: bool = False, fg_message_prefix: str = ""):
        self.use_background = use_background
        self.heading = heading
        self.fg_message_prefix = fg_message_prefix
        self.dialog: Optional[Union[xbmcgui.DialogProgress, xbmcgui.DialogProgressBG]] = None
        self.last_percent = -1
        self.throttle_enabled = False
        self.monitor = xbmc.Monitor()

    def create(self, message: str = "") -> None:
        """Create and show the progress dialog, closing any already open."""
        if self.dialog:
            try:
                self.dialog.close()
            except Exception:
                pass

        if self.use_background:
            self.dialog = xbmcgui.DialogProgressBG()
            self.dialog.create(self.heading, message)
        else:
            self.dialog = DialogProgress()
            self.dialog.create(self.heading, message)

        self.last_percent = -1

    def update(self, percent: int, message: str = "", force: bool = False) -> None:
        """Update percent and message; throttling skips an unchanged percent unless forced."""
        if not self.dialog:
            return

        percent = max(0, min(100, percent))

        if self.throttle_enabled and not force:
            if percent == self.last_percent:
                return

        self.last_percent = percent

        if self.use_background:
            assert isinstance(self.dialog, xbmcgui.DialogProgressBG)
            self.dialog.update(percent, self.heading, message)
        else:
            assert isinstance(self.dialog, xbmcgui.DialogProgress)
            full_message = (
                f"{self.fg_message_prefix}[CR]{message}"
                if self.fg_message_prefix and message
                else message
            )
            self.dialog.update(percent, full_message)

    def close(self) -> None:
        """Close the progress dialog if one is open."""
        if self.dialog:
            try:
                self.dialog.close()
            except Exception:
                pass
            finally:
                self.dialog = None
                self.last_percent = -1

    def is_cancelled(self) -> bool:
        """True if the user cancelled the progress dialog or Kodi is shutting down."""
        if self.monitor.abortRequested():
            return True

        if not self.dialog:
            return False

        if isinstance(self.dialog, xbmcgui.DialogProgress):
            return self.dialog.iscanceled()

        return False

    def enable_throttling(self) -> None:
        """Enable throttling, which skips updates that leave the percent unchanged."""
        self.throttle_enabled = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class BackgroundNotice:
    """Background progress bar that appears only once `start` is called."""

    def __init__(self, heading: str, message: str):
        self.heading = heading
        self.message = message
        self._dialog: Optional[xbmcgui.DialogProgressBG] = None

    def start(self) -> None:
        """Show the bar if not already shown."""
        if self._dialog is None:
            self._dialog = xbmcgui.DialogProgressBG()
            self._dialog.create(self.heading, self.message)

    def close(self) -> None:
        """Close the bar if it was shown."""
        if self._dialog is not None:
            try:
                self._dialog.close()
            except Exception:
                pass
            self._dialog = None


def show_notification(
    heading: str,
    message: str,
    icon: str = xbmcgui.NOTIFICATION_INFO,
    duration: int = 3000
) -> None:
    """Show a Kodi toast notification."""
    xbmcgui.Dialog().notification(heading, message, icon, duration)


def notify_when_idle(heading: str, message: str, monitor: xbmc.Monitor,
                     abort: Optional[threading.Event] = None) -> None:
    """Show a notification, holding it back until video playback stops; dropped on abort."""
    while xbmc.getCondVisibility("Player.HasVideo"):
        if monitor.waitForAbort(30):
            return
        if abort is not None and abort.is_set():
            return
    show_notification(heading, message)


def show_ok(heading: str, message: str) -> None:
    """Show an OK dialog and wait for it to close."""
    xbmcgui.Dialog().ok(heading, message)


def show_yesno(
    heading: str,
    message: str,
    nolabel: str | None = None,
    yeslabel: str | None = None
) -> bool:
    """Show a yes/no dialog; True when Yes is chosen."""
    kwargs = {}
    if nolabel is not None:
        kwargs['nolabel'] = nolabel
    if yeslabel is not None:
        kwargs['yeslabel'] = yeslabel
    return xbmcgui.Dialog().yesno(heading, message, **kwargs)


def show_yesnocustom(heading: str, message: str, customlabel: str,
                     nolabel: str = "", yeslabel: str = "") -> int:
    """Show a yes/no/custom dialog; 0 No, 1 Yes, 2 custom, -1 cancelled."""
    return xbmcgui.Dialog().yesnocustom(
        heading, message, customlabel=customlabel, nolabel=nolabel, yeslabel=yeslabel)


def show_textviewer(heading: str, text: str, use_mono: bool = False) -> None:
    """Show a text viewer, monospaced for reports whose columns need to line up."""
    xbmcgui.Dialog().textviewer(heading, text, usemono=use_mono)


def show_select(
    heading: str,
    options: Sequence[Union[str, xbmcgui.ListItem]],
    preselect: int = -1,
    use_details: bool = False
) -> int:
    """Show a select dialog, optionally detailed with art; the chosen index, -1 when cancelled."""
    return xbmcgui.Dialog().select(
        heading, list(options), preselect=preselect, useDetails=use_details)
