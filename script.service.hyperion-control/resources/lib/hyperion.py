"""Hyperion Controller."""
from __future__ import annotations

from collections.abc import Callable

from resources.lib.interfaces import ApiClient
from resources.lib.interfaces import GuiHandler
from resources.lib.interfaces import Logger
from resources.lib.interfaces import SettingsManager


class Hyperion:
    """Main instance class."""

    def __init__(
        self,
        settings_manager: SettingsManager,
        logger: Logger,
        gui_handler: GuiHandler,
        api_client: ApiClient,
        get_video_mode_function: Callable[[], str],
        addon_version: str,
    ) -> None:
        self._prev_video_mode = "2D"

        self._addon_version = addon_version
        self._client = api_client
        self._settings = settings_manager
        self._logger = logger
        self._gui = gui_handler
        self._video_mode_fn = get_video_mode_function

        self._kodi_state: str = "menu"
        self._prev_comp_state: bool | None = None
        self._initialize()

    def _initialize(self) -> None:
        # check for changelog display, but not on first run
        settings = self._settings
        if settings.should_display_changelog:
            self._gui.do_changelog_display()

        # check for setup wizard
        if settings.first_run:
            # be sure to fill in the current version
            settings.set_addon_version(self._addon_version)
            self._gui.do_initial_wizard()

        if settings.enable_hyperion:
            self._client.send_component_state("ALL", True)
        settings.set_first_run_done()

    def notify(self, command: str) -> None:
        """Process the commands sent by the observables."""
        if self._settings.debug:
            self._logger.log(f"received command: {command}")
        if command == "updateSettings":
            self.update_settings()
        else:
            self._kodi_state = command
        self._update_state()

    def update_settings(self) -> None:
        """Update the settings."""
        settings = self._settings
        settings.read_settings()

        auth_token = settings.auth_token
        if auth_token and len(auth_token) != 36:
            self._gui.notify_label(32105)

        # Checkout Tasklist for pending tasks
        if settings.tasks == 1:
            settings.set_tasks(0)
            self._gui.do_ssdp_discovery()

    def _update_state(self) -> None:
        comp_state = self._get_comp_state()
        if self._prev_comp_state != comp_state:
            self._client.send_component_state(self._settings.target_comp, comp_state)
            self._prev_comp_state = comp_state

        # update stereoscopic mode always, better apis for detection available?
        # Bug: race condition, return of jsonapi has wrong gui state
        # after onPlayBackStopped after a 3D movie
        if self._settings.video_mode_enabled:
            new_mode = self._video_mode_fn()
            if self._prev_video_mode != new_mode:
                self._client.send_video_mode(new_mode)
                self._prev_video_mode = new_mode

    def _get_comp_state(self) -> bool:
        """Get the desired state of the target component based on kodi state."""
        settings = self._settings
        state = self._kodi_state
        if state == "screensaver":
            return settings.screensaver_enabled
        if state == "pause":
            return settings.pause_enabled
        if state == "playAudio":
            return settings.audio_enabled
        if state == "playVideo":
            return settings.video_enabled
        return settings.menu_enabled

    def stop(self) -> None:
        """Stops the hyperion control."""
        if self._settings.disable_hyperion:
            self._client.send_component_state("ALL", False)
        self._logger.log("Hyperion-control stopped")
