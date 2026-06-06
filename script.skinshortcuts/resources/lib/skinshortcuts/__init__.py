"""Skin Shortcuts - Menu management for Kodi skins."""

from __future__ import annotations

from .builders import IncludesBuilder
from .config import SkinConfig
from .models import (
    Background,
    Menu,
    MenuItem,
    PropertySchema,
    SchemaProperty,
    Widget,
)

__version__ = "3.0.0-dev"
__all__ = [
    "__version__",
    "SkinConfig",
    "IncludesBuilder",
    "Menu",
    "MenuItem",
    "Widget",
    "Background",
    "PropertySchema",
    "SchemaProperty",
]
