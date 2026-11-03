"""Base classes for the info dialogs."""
from __future__ import annotations

from typing import Dict, Final
import xbmcgui

from lib.kodi.client import ADDON
from lib.kodi.utilities import clear_window_prop


ADDON_PATH = ADDON.getAddonInfo('path')

_TOP_PROP: Final = 'SkinInfo.DialogTopId'
_CLOSE_ACTIONS = (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU)


class DialogBase(xbmcgui.WindowXMLDialog):
    """Shared close handling and property setting for the addon's XML dialogs."""

    def set_properties(self, props: Dict[str, str]) -> None:
        """Set each property, skipping empty values."""
        for key, value in props.items():
            if value:
                self.setProperty(key, str(value))

    def is_close_action(self, action: xbmcgui.Action) -> bool:
        """Whether the action is Back or Menu."""
        return action.getId() in _CLOSE_ACTIONS

    def onAction(self, action: xbmcgui.Action) -> None:
        """Close on the back and menu actions."""
        if self.is_close_action(action):
            self.close()


class InfoDialogBase(DialogBase):
    """Base for the info dialogs, adding topmost tracking and off-thread blur."""

    def __init__(self, *args, **kwargs):
        self._parent_win: str = ''
        self._closing = False
        super().__init__(*args, **kwargs)

    def mark_topmost(self) -> None:
        """Flag this dialog as topmost (`istop`), remembering the prior holder for close."""
        import xbmcgui
        home = xbmcgui.Window(10000)
        self._parent_win = home.getProperty(_TOP_PROP)
        if self._parent_win:
            clear_window_prop('istop', self._parent_win)
        home.setProperty(_TOP_PROP, str(xbmcgui.getCurrentWindowDialogId()))
        self.setProperty('istop', '1')

    def _start_blur(self, pairs) -> None:
        """Blur `(property_key, source_image)` pairs off-thread into properties on this dialog."""
        sources = [(key, src) for key, src in pairs if src]
        if not sources:
            return
        import threading
        threading.Thread(target=self._blur_worker, args=(sources,), daemon=True).start()

    def _blur_worker(self, sources) -> None:
        """Set each blurred image as it finishes, stopping once the dialog closes."""
        from lib.infrastructure.blur import blur_image
        for key, src in sources:
            if self._closing:
                return
            blurred = blur_image(src)
            if blurred and not self._closing:
                try:
                    self.setProperty(key, blurred)
                except Exception:
                    pass

    def close(self) -> None:
        """Hand topmost back to the previous dialog and stop the blur before closing."""
        self._closing = True
        import xbmc
        import xbmcgui
        xbmcgui.Window(10000).setProperty(_TOP_PROP, self._parent_win)
        if self._parent_win:
            xbmc.executebuiltin(f'SetProperty(istop,1,{self._parent_win})')
        super().close()
