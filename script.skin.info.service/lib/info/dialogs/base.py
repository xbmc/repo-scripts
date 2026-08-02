from __future__ import annotations

from lib.dialog.base import DialogBase
from lib.kodi.client import ADDON


ADDON_PATH = ADDON.getAddonInfo('path')

_TOP_PROP = 'SkinInfo.DialogTopId'


class InfoDialogBase(DialogBase):

    def __init__(self, *args, **kwargs):
        self._parent_win: str = ''
        self._closing = False
        super().__init__(*args, **kwargs)

    def mark_topmost(self) -> None:
        """Flag this dialog as topmost (`istop`), remembering the prior holder to restore on
        close."""
        import xbmc
        import xbmcgui
        home = xbmcgui.Window(10000)
        self._parent_win = home.getProperty(_TOP_PROP)
        if self._parent_win:
            xbmc.executebuiltin(f'ClearProperty(istop,{self._parent_win})')
        home.setProperty(_TOP_PROP, str(xbmcgui.getCurrentWindowDialogId()))
        self.setProperty('istop', '1')

    def _start_blur(self, pairs) -> None:
        """Blur each `(property_key, source_image)` off-thread, scoped to this instance so stacked
        dialogs don't clash."""
        sources = [(key, src) for key, src in pairs if src]
        if not sources:
            return
        import threading
        threading.Thread(target=self._blur_worker, args=(sources,), daemon=True).start()

    def _blur_worker(self, sources) -> None:
        from lib.service.blur import blur_image
        radius = self._blur_radius()
        for key, src in sources:
            if self._closing:
                return
            blurred = blur_image(src, radius)
            if blurred and not self._closing:
                try:
                    self.setProperty(key, blurred)
                except Exception:
                    pass

    @staticmethod
    def _blur_radius() -> int:
        import xbmc
        value = xbmc.getInfoLabel("Skin.String(SkinInfo.BlurRadius)") or "40"
        try:
            radius = int(value)
        except (ValueError, TypeError):
            return 40
        return radius if radius >= 1 else 40

    def close(self) -> None:
        self._closing = True
        import xbmc
        import xbmcgui
        xbmcgui.Window(10000).setProperty(_TOP_PROP, self._parent_win)
        if self._parent_win:
            xbmc.executebuiltin(f'SetProperty(istop,1,{self._parent_win})')
        super().close()

    @staticmethod
    def create(xml_name: str, cls, **kwargs):
        return cls(
            xml_name,
            ADDON_PATH,
            'default',
            '1080i',
            **kwargs
        )
