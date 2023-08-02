"""Settings manager."""
from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from resources.lib.interfaces import Logger

if TYPE_CHECKING:
    import xbmcaddon


INT_TO_COMP_STRING = {
    0: "GRABBER",
    1: "V4L",
    2: "AUDIO",
    3: "LEDDEVICE",
    4: "SMOOTHING",
    5: "BLACKBORDER",
    6: "FORWARDER",
    7: "BOBLIGHTSERVER",
    8: "ALL",
}


class SettingsManager:
    """Class which contains all addon settings."""

    def __init__(
        self, settings: xbmcaddon.Settings, logger: Logger, addon: xbmcaddon.Addon
    ) -> None:
        self._logger = logger
        self.rev = 0
        self._settings = settings
        self._addon = addon
        self.current_version: str = ""
        self._address: str = "localhost"
        self._port: int = 8090
        self._base_url = "http://localhost:8090/json-rpc"
        self.video_mode_enabled: bool
        self.enable_hyperion: bool
        self.disable_hyperion: bool
        self.auth_token: str
        self.target_comp: str
        self.screensaver_enabled: bool
        self.video_enabled: bool
        self.audio_enabled: bool
        self.pause_enabled: bool
        self.menu_enabled: bool
        self.show_changelog_on_update: bool
        self.tasks: int
        self.debug: bool
        self.first_run: bool
        self.read_settings()

    @property
    def address(self) -> str:
        """Hyperion server address."""
        return self._address

    @address.setter
    def address(self, value: str) -> None:
        """Hyperion server address."""
        self._address = value
        self._update_url()
        self._set_string("ip", value)

    @property
    def port(self) -> int:
        """Hyperion server port."""
        return self._port

    @port.setter
    def port(self, value: int) -> None:
        """Hyperion server port."""
        self._port = value
        self._update_url()
        self._set_int("port", value)

    def _update_url(self) -> None:
        self._base_url = f"http://{self._address}:{self._port}/json-rpc"

    @property
    def base_url(self) -> str:
        """Hyperion server JSON RPC base url."""
        return self._base_url

    @property
    def should_display_changelog(self) -> bool:
        """Whether the changelog should be displayed."""
        return self.show_changelog_on_update and not self.first_run

    def _set_string(self, name: str, value: str) -> None:
        self._addon.setSettingString(name, value)
        outcome = value == self._settings.getString(name)
        self._log_set_outcome(name, value, outcome)

    def _set_int(self, name: str, value: int) -> None:
        self._addon.setSettingInt(name, value)
        outcome = value == self._settings.getInt(name)
        self._log_set_outcome(name, value, outcome)

    def _set_bool(self, name: str, value: bool) -> None:
        self._addon.setSettingBool(name, value)
        outcome = value == self._settings.getBool(name)
        self._log_set_outcome(name, value, outcome)

    def _log_set_outcome(self, name: str, value: Any, outcome: bool) -> None:
        if not outcome:
            self._logger.error(f"Error setting {name} to {value} (outcome={outcome})")
        elif self.debug:
            self._logger.log(f"Set {name} to {value}")

    def set_tasks(self, value: int) -> None:
        """Sets the tasks to run."""
        self._set_int("tasks", value)
        self.tasks = value

    def set_addon_version(self, value: str) -> None:
        """Sets the current addon version for changelog checks."""
        self._set_string("currAddonVersion", value)
        self.current_version = value

    def set_first_run_done(self) -> None:
        """Sets the first run settings to false."""
        self._set_bool("firstRun", False)
        self.first_run = False

    def read_settings(self) -> None:
        """Read all settings."""
        settings = self._settings
        get_bool = settings.getBool
        get_string = settings.getString
        get_int = settings.getInt
        self._address = get_string("ip")
        self._port = get_int("port")
        self._update_url()
        self.auth_token = get_string("authToken")
        self.video_mode_enabled = get_bool("videoModeEnabled")
        self.enable_hyperion = get_bool("enableHyperion")
        self.disable_hyperion = get_bool("disableHyperion")
        self.show_changelog_on_update = get_bool("showChangelogOnUpdate")
        self.debug = get_bool("debug")
        self.first_run = get_bool("firstRun")
        self.current_version = get_string("currAddonVersion")

        self.target_comp = INT_TO_COMP_STRING.get(
            get_int("targetComponent"), "NOT_FOUND"
        )
        self.video_enabled = get_bool("videoEnabled")
        self.audio_enabled = get_bool("audioEnabled")
        self.pause_enabled = get_bool("pauseEnabled")
        self.menu_enabled = get_bool("menuEnabled")
        self.screensaver_enabled = get_bool("screensaverEnabled")
        self.tasks = get_int("tasks")
        self.rev += 1

        if self.debug:
            self._log_settings()

    def _log_settings(self) -> None:
        log = self._logger.log
        log("Settings updated!")
        log(f"Hyperion ip:           {self.address}")
        log(f"Hyperion port:         {self.port}")
        log(f"Enable H on start:     {self.enable_hyperion}")
        log(f"Disable H on stop:     {self.disable_hyperion}")
        log(f"VideoMode enabled:     {self.video_mode_enabled}")
        log(f"Hyperion target comp:  {self.target_comp}")
        log(f"Screensaver enabled:   {self.screensaver_enabled}")
        log(f"Video enabled:         {self.video_enabled}")
        log(f"Audio enabled:         {self.audio_enabled}")
        log(f"Pause enabled:         {self.pause_enabled}")
        log(f"Menu enabled:          {self.menu_enabled}")
        log(f"Debug enabled:         {self.debug}")
        log(f"ChangelogOnUpdate:     {self.show_changelog_on_update}")
        log(f"tasks:                 {self.tasks}")
        log(f"first run:             {self.first_run}")
        log(f"current version:       {self.current_version}")
