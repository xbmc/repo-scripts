# SPDX-License-Identifier: GPL-2.0-only
"""The single boundary between this addon and Kodi.

Everything else takes a KodiApi, so the logic is testable as plain Python. The one admitted
exception is PlaybackMonitor and ServiceMonitor, which must subclass xbmc.Player and
xbmc.Monitor to receive callbacks at all; they forward immediately and hold no logic.

Keep this module free of decisions: it translates, it does not choose. topmost_dialog_id
returns a raw id rather than a "busy" verdict for exactly that reason.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol

from resources.lib.constants import ADDON_ID
from resources.lib.log import get_logger

if TYPE_CHECKING:
    from resources.lib.ui.list_window import ListRequest, ListResult, ListState
    from resources.lib.ui.rating import RateRequest
    from resources.lib.ui.viewers_window import ViewersRequest, ViewersResult
    from resources.lib.ui.who_watched import WhoWatchedRequest

_log = get_logger("ui")

# xbmc/guilib/WindowIDs.h:12. GetTopmostModalDialog returns this when no modal is open.
WINDOW_INVALID = 9999

MAX_SETTINGS_FILE_BYTES = 256 * 1024


class KodiApi(Protocol):
    def jsonrpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]: ...
    def setting(self, key: str) -> str: ...
    def setting_bool(self, key: str) -> bool: ...
    def setting_int(self, key: str) -> int: ...
    def set_setting(self, key: str, value: str) -> None: ...
    def addon_version(self) -> str: ...
    def info_label(self, key: str) -> str: ...
    def translate(self, path: str) -> str: ...
    def read_text(self, path: str, max_bytes: int = MAX_SETTINGS_FILE_BYTES) -> str | None: ...
    def is_playing(self) -> bool: ...
    def player_times(self) -> tuple[int | None, int | None]: ...
    def topmost_dialog_id(self) -> int: ...
    def who_watched(self, request: WhoWatchedRequest) -> tuple[str, ...] | None: ...
    def confirm_window(self, heading: str, message: str) -> bool: ...
    def rate(self, request: RateRequest) -> int | None: ...
    def set_user_rating(self, media_type: str, library_id: int, value: int) -> bool: ...
    def list_window(self, request: ListRequest, state: ListState) -> ListResult: ...
    def remembered_window(self, request: ListRequest, state: ListState) -> ListResult: ...
    def viewers_window(self, request: ViewersRequest, key: str) -> ViewersResult: ...
    def text_input(self, heading: str, default: str = "") -> str: ...
    def confirm(self, heading: str, message: str, autoclose: int = 0) -> bool: ...
    def notify(self, heading: str, message: str) -> None: ...
    def ok(self, heading: str, message: str) -> None: ...
    def localised(self, string_id: int) -> str: ...
    def log(self, message: str, level: int) -> None: ...


class KodiRpcError(RuntimeError):
    def __init__(self, method: str, error: Any) -> None:
        super().__init__(f"{method}: {error}")
        self.method = method
        self.error = error


class KodiRuntime:
    """KodiApi backed by the real xbmc modules.

    The player is held, not constructed per call: building an xbmc.Player registers a
    callback target on a process-global list the application thread walks under lock.
    """

    def __init__(self, player: Any = None) -> None:
        import xbmc
        import xbmcaddon
        import xbmcgui
        import xbmcvfs

        self._xbmc = xbmc
        self._xbmcgui = xbmcgui
        self._xbmcvfs = xbmcvfs
        self._addon = xbmcaddon.Addon()
        self._player = player if player is not None else xbmc.Player()
        # Kodi's add-on rules allow only the debug level for routine output, so INFO lines
        # show in kodi.log only with Kodi's debug logging on; warnings and errors always do.
        self._levels = {10: xbmc.LOGDEBUG, 20: xbmc.LOGDEBUG, 30: xbmc.LOGWARNING, 40: xbmc.LOGERROR}

    def jsonrpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
        body = json.loads(self._xbmc.executeJSONRPC(json.dumps(request)))
        if "error" in body:
            raise KodiRpcError(method, body["error"])
        result = body.get("result")
        return result if isinstance(result, dict) else {"result": result}

    def setting(self, key: str) -> str:
        return str(self._addon.getSetting(key) or "")

    def setting_bool(self, key: str) -> bool:
        return bool(self._addon.getSettingBool(key))

    def setting_int(self, key: str) -> int:
        return int(self._addon.getSettingInt(key))

    def set_setting(self, key: str, value: str) -> None:
        """Saved at once, unless this add-on's settings screen is open.

        Then Kodi only updates the value on that screen (xbmc/interfaces/legacy/Addon.cpp,
        UpdateSettingInActiveDialog), and saves it, and tells the service, when the screen
        closes.
        """
        self._addon.setSetting(key, value)

    def addon_version(self) -> str:
        return str(self._addon.getAddonInfo("version") or "")

    def info_label(self, key: str) -> str:
        return str(self._xbmc.getInfoLabel(key) or "")

    def translate(self, path: str) -> str:
        return self._xbmcvfs.translatePath(path)

    def read_text(self, path: str, max_bytes: int = MAX_SETTINGS_FILE_BYTES) -> str | None:
        try:
            if not self._xbmcvfs.exists(path):
                return None
            # The cap is passed to Kodi rather than applied by slicing afterwards
            # (xbmcvfs File.h:110-112). Slicing reads the whole file first, and slices
            # characters rather than bytes, so the declared bound is not a bound at all.
            with self._xbmcvfs.File(path) as handle:
                return str(handle.read(max_bytes))
        except Exception:
            return None

    def is_playing(self) -> bool:
        try:
            return bool(self._player.isPlaying())
        except Exception:
            return False

    def player_times(self) -> tuple[int | None, int | None]:
        """Position and duration, read independently.

        Both raise when playback has stopped, and they can stop between the two calls. A
        failed duration read must not discard a good position: the stop event is built from
        the last sample.
        """
        position: int | None = None
        duration: int | None = None
        try:
            # Clamped: at the instant onAVStarted fires getTime() can return a small
            # negative, and a negative position is not a state the player can be in. It
            # would otherwise reach the wire and become a negative resume point.
            position = max(0, int(self._player.getTime() * 1000))
        except Exception:
            position = None
        try:
            total = int(self._player.getTotalTime() * 1000)
            duration = total if total > 0 else None
        except Exception:
            duration = None
        return position, duration

    def topmost_dialog_id(self) -> int:
        return int(self._xbmcgui.getCurrentWindowDialogId())

    def _modal(self, name: str, make: Callable[[str], Any]) -> Any:
        """Open a CrossWatch window modally; None when it could not be built or failed.

        One rule for every custom window: a failure is a cancel, logged once, with no
        fallback to a standard dialog (most CrossWatch windows have none).
        """
        try:
            from resources.lib.ui import skin_fonts

            # KODI-FONT-WORKAROUND: see the deletion guide in skin_fonts.
            dialog = make(skin_fonts.ensure_generated(ADDON_ID))
            try:
                dialog.doModal()
            finally:
                dialog.stop()
            return dialog
        except Exception as exc:
            _log.warning("ui.window_failed", window=name, error_type=type(exc).__name__)
            return None

    def who_watched(self, request: WhoWatchedRequest) -> tuple[str, ...] | None:
        """The ticked names, () for Done with nobody ticked or Forget, None for any cancel."""

        def make(path: str) -> Any:
            # Imported here so an import failure is a logged cancel like any other, and so
            # nothing that imports this module pays for the window classes.
            from resources.lib.ui import window

            dialog = window.WhoWatchedDialog(window.WHO_WATCHED_XML, path, "Default", "1080i")
            dialog.prepare(request, self.localised, self.is_playing, self._xbmc.Monitor().waitForAbort)
            return dialog

        dialog = self._modal("who_watched", make)
        return dialog.result if dialog is not None else None

    def rate(self, request: RateRequest) -> int | None:
        """1 to 10 a score, 0 Remove, None for Skip, Back, the countdown or playback starting,
        and RATE_FAILED for a window that could not be shown."""
        from resources.lib.ui.rating import RATE_FAILED

        def make(path: str) -> Any:
            from resources.lib.ui import window

            dialog = window.RatingDialog(window.RATING_XML, path, "Default", "1080i")
            dialog.prepare(request, self.localised, self.is_playing, self._xbmc.Monitor().waitForAbort)
            return dialog

        dialog = self._modal("rating", make)
        if dialog is None or dialog.close_reason == "error":
            return RATE_FAILED
        return dialog.result

    def set_user_rating(self, media_type: str, library_id: int, value: int) -> bool:
        """Kodi's own user rating for a library item, which every profile on a shared library sees."""
        method, key = (
            ("VideoLibrary.SetEpisodeDetails", "episodeid")
            if media_type == "episode"
            else ("VideoLibrary.SetMovieDetails", "movieid")
        )
        try:
            self.jsonrpc(method, {key: library_id, "userrating": value})
        except Exception as exc:
            _log.warning(
                "rating.library_write_failed", media_type=media_type, library_id=library_id, error_type=type(exc).__name__
            )
            return False
        return True

    def confirm_window(self, heading: str, message: str) -> bool:
        """True only for Yes; No, Back and a failed window all leave things as they are."""

        def make(path: str) -> Any:
            from resources.lib.ui import window

            dialog = window.ConfirmDialog(window.CONFIRM_XML, path, "Default", "1080i")
            dialog.prepare(heading, message, self.localised)
            return dialog

        dialog = self._modal("confirm", make)
        return dialog is not None and dialog.result is True

    def list_window(self, request: ListRequest, state: ListState) -> ListResult:
        """What the household did; Back and a failed window both close, keeping the state."""
        from resources.lib.ui.list_window import ListResult

        def make(path: str) -> Any:
            from resources.lib.ui import window

            dialog = window.PickListDialog(window.LIST_XML, path, "Default", "1080i")
            dialog.prepare(request, state, self.localised)
            return dialog

        dialog = self._modal("pick_list", make)
        if dialog is None or dialog.result is None:
            return ListResult("close", state)
        return dialog.result

    def remembered_window(self, request: ListRequest, state: ListState) -> ListResult:
        """What the household did; Back and a failed window both close, keeping the state."""
        from resources.lib.ui.list_window import ListResult

        def make(path: str) -> Any:
            from resources.lib.ui import window

            dialog = window.RememberedDialog(window.REMEMBERED_XML, path, "Default", "1080i")
            dialog.prepare(request, state, self.localised)
            return dialog

        dialog = self._modal("remembered", make)
        if dialog is None or dialog.result is None:
            return ListResult("close", state)
        return dialog.result

    def viewers_window(self, request: ViewersRequest, key: str) -> ViewersResult:
        """What the household did; Back and a failed window both close, on the same viewer."""
        from resources.lib.ui.viewers_window import ViewersResult

        def make(path: str) -> Any:
            from resources.lib.ui import window

            dialog = window.ViewersDialog(window.VIEWERS_XML, path, "Default", "1080i")
            dialog.prepare(request, key, self.localised)
            return dialog

        dialog = self._modal("viewers", make)
        if dialog is None or dialog.result is None:
            return ViewersResult("close", key)
        return dialog.result

    def text_input(self, heading: str, default: str = "") -> str:
        return str(self._xbmcgui.Dialog().input(heading, default) or "")

    def confirm(self, heading: str, message: str, autoclose: int = 0) -> bool:
        """autoclose is in seconds; a dialog that closes itself counts as No."""
        return bool(self._xbmcgui.Dialog().yesno(heading, message, autoclose=autoclose * 1000))

    def notify(self, heading: str, message: str) -> None:
        """A toast on the household's own screen.

        This is the one channel that may carry a playlist name. Kodi's shared log gets
        attached to bug reports; the screen in the living room does not.
        """
        try:
            self._xbmcgui.Dialog().notification(heading, message)
        except Exception:
            # Cosmetic. A skin that refuses to draw a toast must not take the service down.
            pass

    def ok(self, heading: str, message: str) -> None:
        """A message that wraps and waits to be read.

        For anything longer than a toast holds: Estuary's toast cuts long text off rather
        than wrapping it.
        """
        self._xbmcgui.Dialog().ok(heading, message)

    def localised(self, string_id: int) -> str:
        try:
            return str(self._addon.getLocalizedString(string_id) or "")
        except Exception:
            return ""

    def log(self, message: str, level: int) -> None:
        self._xbmc.log(message, self._levels.get(level, self._xbmc.LOGDEBUG))
