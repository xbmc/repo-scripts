"""Kodi GUI handler."""
from __future__ import annotations

import xbmcaddon
import xbmcgui
from resources.lib.settings import SettingsManager


class GuiHandler:
    """Kodi GUI handler."""

    def __init__(
        self, addon: xbmcaddon.Addon, settings_manager: SettingsManager
    ) -> None:
        self._addon = addon
        self._settings = settings_manager
        self._dialog = xbmcgui.Dialog()  # TODO: DI with embedded getlocalizedstring
        self._addon_name = addon.getAddonInfo("name")
        self._addon_icon = addon.getAddonInfo("icon")

    def _get_localized_string(self, label_id: int) -> str:
        """Returns the localized string of a label ID."""
        return self._addon.getLocalizedString(label_id)

    def notify_label(self, label_id: int) -> None:
        """Displays a notification with the localized message."""
        message = self._get_localized_string(label_id)
        self.notify_text(message, time=1000, icon=self._addon_icon)

    def notify_text(
        self, message: str, time: int = 3000, icon: str = xbmcgui.NOTIFICATION_INFO
    ) -> None:
        """Displays a notification."""
        self._dialog.notification(self._addon_name, message, icon, time)
