"""Dialog helper utilities for progress tracking and user interaction."""
from __future__ import annotations

from typing import Optional, Union
import xbmc
import xbmcgui

_MONITOR = xbmc.Monitor()


class DialogProgress(xbmcgui.DialogProgress):
    """`xbmcgui.DialogProgress` that also reports Kodi shutdown as cancelled.

    Kodi's own `iscanceled()` tracks only the cancel button, so a loop polling it runs on
    through a shutdown and holds Kodi open until its work finishes.
    """

    def iscanceled(self) -> bool:
        """True if the user cancelled or Kodi is shutting down."""
        return _MONITOR.abortRequested() or super().iscanceled()


class ProgressDialog:
    """Context-managed progress dialog that picks `DialogProgress` or `DialogProgressBG` and
    clamps percent."""

    def __init__(self, use_background: bool = False, heading: str = "Processing",
                 fg_message_prefix: str = ""):
        self.use_background = use_background
        self.heading = heading
        self.fg_message_prefix = fg_message_prefix
        self.dialog: Optional[Union[xbmcgui.DialogProgress, xbmcgui.DialogProgressBG]] = None
        self.last_percent = -1
        self.throttle_enabled = False
        self.monitor = xbmc.Monitor()

    def create(self, message: str = "") -> None:
        """Create and show the dialog. Closes any existing dialog first."""
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
        """Update dialog percent/message; skips no-op updates when throttling on unless `force`."""
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
        """Close the progress dialog."""
        if self.dialog:
            try:
                self.dialog.close()
            except Exception:
                pass
            finally:
                self.dialog = None
                self.last_percent = -1

    def is_cancelled(self) -> bool:
        """True if the user cancelled the dialog or Kodi requested abort."""
        if self.monitor.abortRequested():
            return True

        if not self.dialog:
            return False

        if isinstance(self.dialog, xbmcgui.DialogProgress):
            return self.dialog.iscanceled()

        return False

    def enable_throttling(self) -> None:
        """Enable update throttling to skip updates when percent hasn't changed."""
        self.throttle_enabled = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class BackgroundNotice:
    """Background progress bar shown on demand, for slow work that only sometimes runs.

    Pass `start` as an on-demand callback so the bar appears only when the work fires
    (e.g. a dataset download that's skipped when the cache is current).
    """

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
    """Show notification dialog."""
    xbmcgui.Dialog().notification(heading, message, icon, duration)


def show_ok(heading: str, message: str) -> None:
    """Show OK dialog."""
    xbmcgui.Dialog().ok(heading, message)


def show_yesno(
    heading: str,
    message: str,
    nolabel: str | None = None,
    yeslabel: str | None = None
) -> bool:
    """Show yes/no dialog."""
    kwargs = {}
    if nolabel is not None:
        kwargs['nolabel'] = nolabel
    if yeslabel is not None:
        kwargs['yeslabel'] = yeslabel
    return xbmcgui.Dialog().yesno(heading, message, **kwargs)


def show_yesnocustom(heading: str, message: str, customlabel: str,
                     nolabel: str = "", yeslabel: str = "") -> int:
    """Show yes/no/custom dialog. Returns `0`=No, `1`=Yes, `2`=Custom, `-1`=Cancelled."""
    return xbmcgui.Dialog().yesnocustom(
        heading,
        message,
        customlabel=customlabel,
        nolabel=nolabel or "No",
        yeslabel=yeslabel or "Yes"
    )


def show_textviewer(heading: str, text: str, use_mono: bool = False) -> None:
    """Show text viewer dialog. `use_mono` for reports whose columns or rules need to line up."""
    xbmcgui.Dialog().textviewer(heading, text, usemono=use_mono)


def show_select(
    heading: str,
    options: list[str],
    preselect: int = -1
) -> int:
    """Show select dialog."""
    return xbmcgui.Dialog().select(heading, options, preselect=preselect)  # type: ignore[arg-type]


