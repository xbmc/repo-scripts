"""Configuration file loaders."""

from __future__ import annotations

from ..conditions import evaluate_condition, expand_compact_or
from .background import load_backgrounds
from .base import apply_suffix_to_from, apply_suffix_transform
from .menu import load_groupings, load_menus
from .property import PropertyLoader, load_properties
from .template import TemplateLoader, load_templates
from .views import load_views
from .widget import load_widgets

__all__ = [
    "load_views",
    "load_widgets",
    "load_backgrounds",
    "load_menus",
    "load_groupings",
    "load_properties",
    "PropertyLoader",
    "evaluate_condition",
    "expand_compact_or",
    "apply_suffix_transform",
    "apply_suffix_to_from",
    "load_templates",
    "TemplateLoader",
]
