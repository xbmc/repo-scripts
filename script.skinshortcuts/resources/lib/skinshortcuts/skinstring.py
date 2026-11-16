"""Standalone picker for storing results in skin strings."""

from __future__ import annotations

from pathlib import Path

try:
    import xbmc
    import xbmcgui

    IN_KODI = True
except ImportError:
    IN_KODI = False

from .constants import MENUS_FILE, WIDGETS_FILE
from .dialog.pickers import PickersMixin
from .loaders.menu import load_menus
from .loaders.widget import load_widgets
from .localize import LANGUAGE, resolve_label
from .log import get_logger
from .models.menu import IconOverrides, MenuItem

log = get_logger("SkinString")


class _StandalonePicker(PickersMixin):
    """Minimal adapter for PickersMixin outside the management dialog."""

    def __init__(
        self, shortcuts_path: str, icon_overrides: IconOverrides | None = None
    ) -> None:
        self.shortcuts_path = shortcuts_path
        self.manager = None  # type: ignore[assignment]
        self.menu_id = ""
        self.items: list[MenuItem] = []
        self._overrides = icon_overrides or IconOverrides()

    def _icon_overrides(self) -> IconOverrides:
        """Overrides handed in by the caller."""
        return self._overrides

    def _get_selected_item(self) -> MenuItem | None:
        """No item is selected outside the management dialog."""
        return None

    def _get_item_properties(self, _item: MenuItem) -> dict[str, str]:
        """No item properties to test picker conditions against."""
        return {}

    def _refresh_selected_item(self) -> None:
        """Nothing to refresh without a list control."""
        pass

    def _log(self, msg: str) -> None:
        """Log through this module's logger."""
        log.debug(msg)


def pick_widget_skinstring(shortcuts_path: str, params: dict[str, str]) -> None:
    """Pick a widget and store the result in skin strings."""
    if not IN_KODI:
        return

    widget_config = load_widgets(Path(shortcuts_path) / WIDGETS_FILE)
    menu_config = load_menus(Path(shortcuts_path) / MENUS_FILE)
    picker = _StandalonePicker(shortcuts_path, menu_config.icon_overrides)

    if not widget_config.groupings:
        xbmcgui.Dialog().notification(LANGUAGE(32147), LANGUAGE(32148))
        return

    result = picker._pick_widget_from_groups(widget_config.groupings, {})
    if result is None:
        return

    keys = [params.get(k, "") for k in ("skinPath", "skinLabel", "skinType", "skinTarget")]
    if result is False:
        values = ["", "", "", ""]
    else:
        values = [result.path, resolve_label(result.label), result.type, result.target]

    for key, value in zip(keys, values, strict=True):
        if not key:
            continue
        if value:
            quoted = value.replace("\\", "\\\\").replace('"', '\\"')
            xbmc.executebuiltin(f'Skin.SetString({key},"{quoted}")')
        else:
            xbmc.executebuiltin(f"Skin.Reset({key})")
