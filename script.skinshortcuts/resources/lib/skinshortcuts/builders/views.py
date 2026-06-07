"""View expression builder."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

from ..log import get_logger

if TYPE_CHECKING:
    from ..models.views import ViewConfig, ViewContent
    from ..userdata import UserData

log = get_logger("ViewBuilder")


class ViewExpressionBuilder:
    """Builds Kodi visibility expressions for view locking.

    Generates minimal expressions:
        - {prefix}{ViewId} - Combined visibility for each view
        - {prefix}{ViewId}_Include - Whether view is used at all
        - {prefix}{Content}_HasPluginOverride - Only when plugin overrides exist
        - {prefix}{Content}_IsGenericPlugin - Only when plugin overrides exist
    """

    def __init__(self, config: ViewConfig, userdata: UserData):
        self.config = config
        self.userdata = userdata
        self.prefix = config.prefix
        self._view_conditions: dict[str, list[str]] = {}
        self._content_has_overrides: set[str] = set()

    def build(self) -> list[ET.Element]:
        """Build all view expressions."""
        if not self.config.content_rules:
            return []

        expressions: list[ET.Element] = []
        self._view_conditions = {v.id: [] for v in self.config.views}
        self._content_has_overrides.clear()

        for content in self.config.content_rules:
            plugin_overrides = self._get_effective_plugin_overrides(content)
            if plugin_overrides:
                content_name = _sanitize_name(content.name)
                self._content_has_overrides.add(content_name)
                expressions.extend(self._build_plugin_helpers(content_name, plugin_overrides))

            self._collect_view_conditions(content, plugin_overrides)

        for view in self.config.views:
            expressions.append(self._build_view_expression(view.id))

        for view in self.config.views:
            expressions.append(self._build_include_expression(view.id))

        return expressions

    def _build_plugin_helpers(
        self, content_name: str, overrides: dict[str, str]
    ) -> list[ET.Element]:
        """Build plugin override helper expressions."""
        expressions: list[ET.Element] = []

        elem = ET.Element("expression")
        elem.set("name", f"{self.prefix}{content_name}_HasPluginOverride")
        conditions = [
            f"String.IsEqual(Container.PluginName,{plugin_id})"
            for plugin_id in sorted(overrides.keys())
        ]
        elem.text = " | ".join(conditions)
        expressions.append(elem)

        elem = ET.Element("expression")
        elem.set("name", f"{self.prefix}{content_name}_IsGenericPlugin")
        elem.text = (
            f"!String.IsEmpty(Container.PluginName) + "
            f"!$EXP[{self.prefix}{content_name}_HasPluginOverride]"
        )
        expressions.append(elem)

        return expressions

    def _collect_view_conditions(
        self, content: ViewContent, plugin_overrides: dict[str, str]
    ) -> None:
        """Collect visibility conditions for each view from this content type."""
        content_name = _sanitize_name(content.name)
        visible = content.visible

        library_view = self._get_effective_library_view(content)
        generic_plugin_view = self._get_effective_generic_plugin_view(content)

        if library_view in self._view_conditions:
            if library_view == generic_plugin_view and not plugin_overrides:
                # Same view for both, no overrides - just use content visible
                self._view_conditions[library_view].append(f"[{visible}]")
            else:
                # Different views or has overrides - need source check
                self._view_conditions[library_view].append(
                    f"[{visible} + String.IsEmpty(Container.PluginName)]"
                )

        if generic_plugin_view in self._view_conditions:
            if library_view == generic_plugin_view and not plugin_overrides:
                pass  # Already added above
            elif plugin_overrides:
                self._view_conditions[generic_plugin_view].append(
                    f"[{visible} + $EXP[{self.prefix}{content_name}_IsGenericPlugin]]"
                )
            else:
                self._view_conditions[generic_plugin_view].append(
                    f"[{visible} + !String.IsEmpty(Container.PluginName)]"
                )

        for plugin_id, view_id in plugin_overrides.items():
            if view_id in self._view_conditions:
                self._view_conditions[view_id].append(
                    f"[{visible} + String.IsEqual(Container.PluginName,{plugin_id})]"
                )

    def _build_view_expression(self, view_id: str) -> ET.Element:
        """Build the combined visibility expression for a view."""
        elem = ET.Element("expression")
        elem.set("name", f"{self.prefix}{view_id}")

        conditions = self._view_conditions.get(view_id, [])
        elem.text = " | ".join(conditions) if conditions else "False"
        return elem

    def _build_include_expression(self, view_id: str) -> ET.Element:
        """Build the _Include expression for conditional view loading."""
        elem = ET.Element("expression")
        elem.set("name", f"{self.prefix}{view_id}_Include")
        has_conditions = bool(self._view_conditions.get(view_id))
        elem.text = "True" if has_conditions else "False"
        return elem

    def _get_effective_library_view(self, content: ViewContent) -> str:
        """Get the effective library view (user selection or default)."""
        user_view = self.userdata.get_view("library", content.name)
        if user_view and user_view in content.views:
            return user_view
        return content.library_default

    def _get_effective_generic_plugin_view(self, content: ViewContent) -> str:
        """Get the effective generic plugin view (user selection or default)."""
        user_view = self.userdata.get_view("plugins", content.name)
        if user_view and user_view in content.views:
            return user_view
        return content.plugin_default or content.library_default

    def _get_effective_plugin_overrides(self, content: ViewContent) -> dict[str, str]:
        """Get plugin-specific view overrides, filtering invalid selections."""
        valid_views = set(content.views)
        overrides = {}
        for plugin_id, view_id in self.userdata.get_addon_overrides(content.name).items():
            if view_id in valid_views:
                overrides[plugin_id] = view_id
        return overrides


def _sanitize_name(name: str) -> str:
    """Sanitize a content name for use in expression names."""
    if not name:
        return name
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    return sanitized[0].upper() + sanitized[1:]
