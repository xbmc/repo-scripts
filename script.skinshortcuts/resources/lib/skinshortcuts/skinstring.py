"""Standalone picker for storing results in skin strings."""

from __future__ import annotations

from pathlib import Path

try:
    import xbmc
    import xbmcgui

    IN_KODI = True
except ImportError:
    IN_KODI = False

from .dialog.pickers import PickersMixin
from .loaders.menu import load_menus
from .loaders.widget import load_widgets
from .localize import LANGUAGE, resolve_label
from .log import get_logger
from .models import MenuItem

log = get_logger("SkinString")


class _StandalonePicker(PickersMixin):
    """Minimal adapter for PickersMixin outside the management dialog."""

    def __init__(
        self, shortcuts_path: str, icon_overrides: dict[str, str] | None = None
    ) -> None:
        self.shortcuts_path = shortcuts_path
        self.manager = None  # type: ignore[assignment]
        self.menu_id = ""
        self.items: list[MenuItem] = []
        self._overrides = icon_overrides or {}

    def _icon_overrides(self) -> dict[str, str]:
        return self._overrides

    def _get_selected_item(self) -> MenuItem | None:
        return None

    def _get_item_properties(self, _item: MenuItem) -> dict[str, str]:
        return {}

    def _refresh_selected_item(self) -> None:
        pass

    def _log(self, msg: str) -> None:
        log.debug(msg)


def pick_widget_skinstring(shortcuts_path: str, params: dict[str, str]) -> None:
    """Open widget picker and store result in skin strings.

    Args:
        shortcuts_path: Path to skin's shortcuts folder
        params: Dict with skin string names:
            skinPath - Skin string for widget path
            skinLabel - Skin string for widget label
            skinType - Skin string for widget type
            skinTarget - Skin string for widget target
    """
    if not IN_KODI:
        return

    widget_config = load_widgets(Path(shortcuts_path) / "widgets.xml")
    menu_config = load_menus(Path(shortcuts_path) / "menus.xml")
    picker = _StandalonePicker(shortcuts_path, menu_config.icon_overrides)

    if widget_config.groupings:
        result = picker._pick_widget_from_groups(widget_config.groupings, {})
    elif widget_config.widgets:
        flat = [(w.name, w.label, w.icon) for w in widget_config.widgets]
        result = picker._pick_widget_flat(flat, {})
    else:
        xbmcgui.Dialog().notification(LANGUAGE(32147), LANGUAGE(32148))
        return

    if result is None:
        return

    skin_path = params.get("skinPath", "")
    skin_label = params.get("skinLabel", "")
    skin_type = params.get("skinType", "")
    skin_target = params.get("skinTarget", "")

    if result is False:
        for key in (skin_path, skin_label, skin_type, skin_target):
            if key:
                xbmc.executebuiltin(f"Skin.Reset({key})")
        return

    if skin_path and result.path:
        xbmc.executebuiltin(f"Skin.SetString({skin_path},{result.path})")
    if skin_label and result.label:
        xbmc.executebuiltin(
            f"Skin.SetString({skin_label},{resolve_label(result.label)})"
        )
    if skin_type and result.type:
        xbmc.executebuiltin(f"Skin.SetString({skin_type},{result.type})")
    if skin_target and result.target:
        xbmc.executebuiltin(f"Skin.SetString({skin_target},{result.target})")
