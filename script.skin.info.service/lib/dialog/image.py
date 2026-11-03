from __future__ import annotations

import threading
from typing import cast, Final
from urllib.parse import urlencode

import xbmc
import xbmcgui
import xbmcplugin

from lib.dialog.base import InfoDialogBase, ADDON_PATH

XML_FILE: Final = 'script-skin-info-service-DialogImageViewer.xml'

_IMAGES_CONTROL_ID: Final = 1520
_LOAD_POLLS: Final = 50
_TOGGLE_ACTIONS: Final = (xbmcgui.ACTION_SHOW_INFO, xbmcgui.ACTION_CONTEXT_MENU)


class DialogImageViewer(InfoDialogBase):
    """Image browser bound to a plugin path, opened at the chosen item."""

    def __init__(self, *args, **kwargs):
        self._images_path: str = kwargs.pop('images_path', '')
        self._selected_index: int = kwargs.pop('selected_index', 0)
        self._artwork_view: bool = kwargs.pop('artwork_view', False)
        super().__init__(*args, **kwargs)
        if self._images_path:
            self.setProperty('container.viewer.path', self._images_path)
        if self._artwork_view:
            self.setProperty('artwork_view', 'true')

    def is_close_action(self, action: xbmcgui.Action) -> bool:
        """Whether the action is Back or Menu, or Info or the context menu in an artwork view."""
        return super().is_close_action(action) or (
            self._artwork_view and action.getId() in _TOGGLE_ACTIONS)

    def onInit(self) -> None:
        """Mark topmost and jump the list to the item that was opened once it loads."""
        xbmc.executebuiltin('Dialog.Close(busydialognocancel,true)')
        self.mark_topmost()
        threading.Thread(target=self._select_when_loaded, daemon=True).start()

    def _select_when_loaded(self) -> None:
        """Select the opened item once the list has loaded, then flag the viewer ready."""
        monitor = xbmc.Monitor()
        loaded = (f'Integer.IsGreater(Container({_IMAGES_CONTROL_ID}).NumItems,0)'
                  f' + !Container({_IMAGES_CONTROL_ID}).IsUpdating')
        for _ in range(_LOAD_POLLS):
            if self._closing or monitor.abortRequested():
                return
            if xbmc.getCondVisibility(loaded):
                break
            monitor.waitForAbort(0.1)
        if self._selected_index:
            try:
                control = cast(xbmcgui.ControlList, self.getControl(_IMAGES_CONTROL_ID))
                control.selectItem(self._selected_index)
            except Exception:
                pass
            # selectItem only queues the move for the GUI thread
            moved = (f'Integer.IsEqual(Container({_IMAGES_CONTROL_ID}).CurrentItem,'
                     f'{self._selected_index + 1})')
            for _ in range(_LOAD_POLLS):
                if self._closing or monitor.abortRequested() or xbmc.getCondVisibility(moved):
                    break
                monitor.waitForAbort(0.02)
        self.setProperty('viewer_ready', 'true')


def open_image_viewer(
    images_path: str,
    selected_index: int = 0,
    artwork_view: bool = False,
) -> None:
    """Open the image viewer on a plugin path; an empty path opens nothing."""
    if not images_path:
        return

    dialog = DialogImageViewer(
        XML_FILE,
        ADDON_PATH,
        'default',
        '1080i',
        images_path=images_path,
        selected_index=selected_index,
        artwork_view=artwork_view,
    )
    dialog.doModal()
    del dialog


def open_artwork_viewer(url: str, dimensions: str = '', source: str = '') -> None:
    """Open the image viewer on one artwork image, full size."""
    query = urlencode({'action': 'artwork_viewer', 'url': url, 'dimensions': dimensions,
                       'source': source})
    open_image_viewer(f'plugin://script.skin.info.service/?{query}', artwork_view=True)


def handle_artwork_viewer(handle: int, params: dict) -> None:
    """Handle the artwork viewer path, listing the named image as one full-size item."""
    url = params.get('url', [''])[0]
    if url:
        item = xbmcgui.ListItem('1', offscreen=True)
        item.setArt({'thumb': url, 'icon': url})
        for key in ('dimensions', 'source'):
            value = params.get(key, [''])[0]
            if value:
                item.setProperty(key, value)
        xbmcplugin.addDirectoryItem(handle, url, item, isFolder=False)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
