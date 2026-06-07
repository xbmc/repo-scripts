"""Property Schema models for Skin Shortcuts."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IconVariant:
    """Icon with optional condition."""

    path: str
    condition: str = ""  # Condition for when to use this icon


@dataclass
class SchemaOption:
    """Option for a schema property."""

    value: str
    label: str
    condition: str = ""
    icons: list[IconVariant] = field(default_factory=list)


@dataclass
class ButtonMapping:
    """Button to property mapping from buttons section."""

    button_id: int
    property_name: str
    suffix: bool = False  # If True, append property_suffix to property name at runtime
    title: str = ""
    show_none: bool = True
    show_icons: bool = True  # Show icons in select dialog (useDetails=True)
    type: str = ""  # "widget", "background", "toggle", "text", "number", or "select"
    requires: str = ""  # Property name that must have a value for button to be active


@dataclass
class SchemaProperty:
    """Property definition from schema."""

    name: str
    template_only: bool = False
    requires: str = ""  # Property name that must have a value
    options: list[SchemaOption] = field(default_factory=list)
    type: str = ""  # "widget", "background", "toggle", or "options"
    value: str = ""  # For toggle: custom value instead of "True"


@dataclass
class FallbackRule:
    """A single fallback rule with condition."""

    value: str
    condition: str = ""  # Empty = default


@dataclass
class PropertyFallback:
    """Fallback configuration for a property."""

    property_name: str
    rules: list[FallbackRule] = field(default_factory=list)


@dataclass
class PropertySchema:
    """Complete property schema."""

    properties: dict[str, SchemaProperty] = field(default_factory=dict)
    fallbacks: dict[str, PropertyFallback] = field(default_factory=dict)
    buttons: dict[int, ButtonMapping] = field(default_factory=dict)  # button_id -> mapping

    def get_property(self, name: str) -> SchemaProperty | None:
        """Get property by name."""
        return self.properties.get(name)

    def get_button(self, button_id: int) -> ButtonMapping | None:
        """Get button mapping by ID."""
        return self.buttons.get(button_id)

    def get_property_for_button(
        self, button_id: int
    ) -> tuple[SchemaProperty | None, ButtonMapping | None]:
        """Get property and button mapping for a button ID.

        Args:
            button_id: The button control ID

        Returns:
            Tuple of (property, button_mapping) or (None, None) if not found.
            Always returns the base property - suffix is applied at runtime
            by the caller when getting/setting values.
        """
        button = self.buttons.get(button_id)
        if not button:
            return None, None

        prop = self.properties.get(button.property_name)
        return prop, button
