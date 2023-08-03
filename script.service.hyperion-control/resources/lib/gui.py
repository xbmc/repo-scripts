"""Kodi GUI handler."""
from __future__ import annotations

import xbmcaddon
import xbmcgui

from resources.lib import ssdp
from resources.lib.interfaces import SettingsManager


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

    def do_ssdp_discovery(self) -> None:
        """Perform the SSDP discovery and lets the user choose the service."""
        servers = ssdp.discover()

        if not servers:
            self._dialog.ok("Hyperion Control", self._get_localized_string(32104))
            return
        # if there is more than one entry the user should select one
        if len(servers) > 1:
            selection_idx = self._dialog.select(
                self._get_localized_string(32102), build_select_list(servers)
            )
            selected_server = servers[selection_idx] if selection_idx > -1 else None
        else:
            selected_server = servers[0]
            self._dialog.ok(
                "Hyperion Control",
                f'{self._get_localized_string(32103)}[CR]{selected_server["ip"]}:{selected_server["port"]}',
            )

        if selected_server:
            self._settings.address = selected_server["ip"]
            self._settings.port = selected_server["port"]

    def do_initial_wizard(self) -> None:
        """Displays the initial wizard."""
        if self._dialog.yesno(
            "Hyperion Control",
            f"{self._get_localized_string(32100)}[CR]{self._get_localized_string(32101)}",
        ):
            self.do_ssdp_discovery()
            self._addon.openSettings()

    def do_changelog_display(self) -> None:
        """Displays the changelog."""
        if self._settings.current_version != self._addon.getAddonInfo("version"):
            self._dialog.textviewer(
                "Hyperion Control - Changelog", self._addon.getAddonInfo("changelog")
            )


def build_select_list(data: list[dict[str, str | int | None]]) -> list[str]:
    return [f"{item['ip']}:{item['port']}" for item in data]
