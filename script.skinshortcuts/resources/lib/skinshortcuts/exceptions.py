"""Exception hierarchy for Skin Shortcuts."""

from __future__ import annotations


class SkinShortcutsError(Exception):
    """Base exception for all Skin Shortcuts errors."""


class ConfigError(SkinShortcutsError):
    """Error in configuration file."""

    def __init__(self, file_path: str, message: str, line: int | None = None):
        self.file_path = file_path
        self.line = line
        location = f"{file_path}:{line}" if line else file_path
        super().__init__(f"{location}: {message}")


class MenuConfigError(ConfigError):
    """Error in menus.xml."""


class WidgetConfigError(ConfigError):
    """Error in widgets.xml."""


class BackgroundConfigError(ConfigError):
    """Error in backgrounds.xml."""


class PropertyConfigError(ConfigError):
    """Error in properties.xml."""


class TemplateConfigError(ConfigError):
    """Error in templates.xml."""


class ViewConfigError(ConfigError):
    """Error in views.xml."""
