"""Observer interface."""
from typing import Protocol


class Observer(Protocol):
    """Observer interface."""

    def notify(self, command: str) -> None:
        """Process the received command."""
        pass


class Logger(Protocol):
    """Logger interface."""

    def log(self, message: str, level: int = 0) -> None:
        """Logs a message."""

    def debug(self, message: str) -> None:
        """Writes a debug message to the log."""

    def info(self, message: str) -> None:
        """Writes an info message to the log."""

    def error(self, message: str) -> None:
        """Writes an error message to the log."""


class SettingsManager(Protocol):
    """Settings manager interface."""

    auth_token: str
    current_version: str
    address: str
    port: int
    video_mode_enabled: bool
    enable_hyperion: bool
    disable_hyperion: bool
    target_comp: str
    screensaver_enabled: bool
    video_enabled: bool
    audio_enabled: bool
    pause_enabled: bool
    menu_enabled: bool
    show_changelog_on_update: bool
    tasks: int
    debug: bool
    first_run: bool

    @property
    def should_display_changelog(self) -> bool:
        """Whether the changelog should be displayed."""
        pass

    @property
    def base_url(self) -> str:
        """Hyperion server JSON RPC base url."""
        pass

    def set_tasks(self, value: int) -> None:
        """Sets the tasks to run."""

    def set_addon_version(self, value: str) -> None:
        """Sets the current addon version for changelog checks."""

    def set_first_run_done(self) -> None:
        """Sets the first run settings to false."""

    def read_settings(self) -> None:
        """Read all settings."""


class GuiHandler(Protocol):
    """GUI handler interface."""

    def notify_label(self, label_id: int) -> None:
        """Displays a notification with the localized message."""

    def notify_text(self, message: str, time: int = 3000, icon: str = "info") -> None:
        """Displays a notification."""

    def do_ssdp_discovery(self) -> None:
        """Perform the SSDP discovery and lets the user choose the service."""

    def do_initial_wizard(self) -> None:
        """Displays the initial wizard."""

    def do_changelog_display(self) -> None:
        """Displays the changelog."""


class ApiClient(Protocol):
    """API client interface."""

    def send_component_state(self, component: str, state: bool) -> None:
        """Sends the component state."""

    def send_video_mode(self, mode: str) -> None:
        """Sends the current video mode."""
