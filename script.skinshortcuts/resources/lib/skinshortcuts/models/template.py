"""Template models for Skin Shortcuts v3."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum


class BuildMode(Enum):
    """Template build mode."""

    MENU = "menu"  # Iterate menu items (default)
    RAW = "true"  # Raw output, no iteration


@dataclass
class Expression:
    """Reusable condition expression."""

    value: str
    nosuffix: bool = False


@dataclass
class TemplateParam:
    """Parameter for parameterized includes or raw templates."""

    name: str
    default: str = ""


@dataclass
class TemplateProperty:
    """Property assignment in a template."""

    name: str
    value: str = ""
    from_source: str = ""  # Built-in or item property name
    condition: str = ""


@dataclass
class TemplateVar:
    """Multi-conditional property for internal template resolution."""

    name: str
    values: list[TemplateProperty] = field(default_factory=list)


@dataclass
class PresetValues:
    """A single row in a preset lookup table."""

    condition: str = ""
    values: dict[str, str] = field(default_factory=dict)


@dataclass
class Preset:
    """Lookup table returning multiple values based on conditions."""

    name: str
    rows: list[PresetValues] = field(default_factory=list)


@dataclass
class PropertyGroup:
    """Reusable property group definition."""

    name: str
    properties: list[TemplateProperty] = field(default_factory=list)
    vars: list[TemplateVar] = field(default_factory=list)


@dataclass
class PropertyGroupReference:
    """Reference to a property group."""

    name: str
    suffix: str = ""  # Suffix for property transforms (e.g., ".2")
    condition: str = ""


@dataclass
class PresetReference:
    """Reference to a preset for direct property resolution."""

    name: str
    suffix: str = ""  # Suffix for condition transforms (e.g., ".2")
    condition: str = ""


@dataclass
class PresetGroupChild:
    """Child element in a presetGroup - either a preset reference or inline values."""

    preset_name: str = ""  # mutually exclusive with values
    values: dict[str, str] = field(default_factory=dict)
    condition: str = ""


@dataclass
class PresetGroup:
    """Conditional preset selection group, evaluated in order with the first match winning."""

    name: str
    children: list[PresetGroupChild] = field(default_factory=list)


@dataclass
class PresetGroupReference:
    """Reference to a presetGroup from a template."""

    name: str
    suffix: str = ""  # Suffix for condition transforms (e.g., ".2")
    condition: str = ""


@dataclass
class IncludeDefinition:
    """Reusable control include, inserted via <skinshortcuts include="name"/>."""

    name: str
    controls: ET.Element | None = None  # Raw XML for control content


@dataclass
class VariableDefinition:
    """Kodi variable definition."""

    name: str
    condition: str = ""  # Only build if item matches (evaluated per-item)
    output: str = ""  # Override output name pattern
    content: ET.Element | None = None  # The <variable> XML content


@dataclass
class VariableReference:
    """Reference to a variable definition within a variableGroup."""

    name: str
    condition: str = ""  # Only build if item matches this condition


@dataclass
class VariableGroupReference:
    """Reference to a variable group, from a template or from another group."""

    name: str
    suffix: str = ""
    condition: str = ""


@dataclass
class VariableGroup:
    """Group of variable references for reuse across templates."""

    name: str
    references: list[VariableReference] = field(default_factory=list)
    group_refs: list[VariableGroupReference] = field(default_factory=list)


@dataclass
class TemplateOutput:
    """Output configuration, letting one template build an include per suffix."""

    include: str  # Output include name
    id_prefix: str = ""  # For computed control IDs
    suffix: str = ""  # Suffix to apply to all conditions/references


@dataclass
class ItemsDefinition:
    """Definition for items insertion within a template."""

    name: str
    source: str = ""
    condition: str = ""
    filter: str = ""
    properties: list[TemplateProperty] = field(default_factory=list)
    vars: list[TemplateVar] = field(default_factory=list)
    preset_refs: list[PresetReference] = field(default_factory=list)
    property_groups: list[PropertyGroupReference] = field(default_factory=list)
    variable_groups: list[VariableGroupReference] = field(default_factory=list)
    controls: ET.Element | None = None

    def get_source(self) -> str:
        """Get the submenu source, defaulting to name if not specified."""
        return self.source or self.name


@dataclass
class Template:
    """Main template definition, iterating menu items or emitting raw output."""

    include: str = ""  # Output include name, unless outputs are declared
    build: BuildMode = BuildMode.MENU
    id_prefix: str = ""  # For computed control IDs
    template_only: str = ""  # "true"=never generate, "auto"=skip if unassigned
    menu: str = ""  # Filter to specific menu (e.g., "mainmenu")

    outputs: list[TemplateOutput] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)  # ANDed together
    params: list[TemplateParam] = field(default_factory=list)  # For build="true"
    properties: list[TemplateProperty] = field(default_factory=list)
    vars: list[TemplateVar] = field(default_factory=list)  # Internal context resolution
    property_groups: list[PropertyGroupReference] = field(default_factory=list)
    preset_refs: list[PresetReference] = field(default_factory=list)
    preset_group_refs: list[PresetGroupReference] = field(default_factory=list)
    controls: ET.Element | None = None  # Raw XML for controls output
    variables: list[VariableDefinition] = field(default_factory=list)
    variable_groups: list[VariableGroupReference] = field(default_factory=list)

    @property
    def has_transformations(self) -> bool:
        """Whether this template defines any property transformations."""
        return bool(
            self.properties
            or self.vars
            or self.preset_refs
            or self.preset_group_refs
            or self.property_groups
        )

    def get_outputs(self) -> list[TemplateOutput]:
        """Get output configurations."""
        if self.outputs:
            return self.outputs
        if self.include:
            return [TemplateOutput(include=self.include, id_prefix=self.id_prefix)]
        return []


@dataclass
class SubmenuTemplate:
    """Submenu template definition."""

    include: str = ""
    level: int = 0
    name: str = ""

    properties: list[TemplateProperty] = field(default_factory=list)
    vars: list[TemplateVar] = field(default_factory=list)
    property_groups: list[PropertyGroupReference] = field(default_factory=list)
    controls: ET.Element | None = None


@dataclass
class TemplateSchema:
    """Complete template schema from templates.xml."""

    expressions: dict[str, Expression] = field(default_factory=dict)
    property_groups: dict[str, PropertyGroup] = field(default_factory=dict)
    includes: dict[str, IncludeDefinition] = field(default_factory=dict)  # For controls
    presets: dict[str, Preset] = field(default_factory=dict)
    preset_groups: dict[str, PresetGroup] = field(default_factory=dict)
    variable_definitions: dict[str, VariableDefinition] = field(default_factory=dict)
    variable_groups: dict[str, VariableGroup] = field(default_factory=dict)
    items_templates: dict[str, ItemsDefinition] = field(default_factory=dict)
    templates: list[Template] = field(default_factory=list)
    submenus: list[SubmenuTemplate] = field(default_factory=list)

    def get_expression(self, name: str) -> Expression | None:
        """Get expression by name."""
        return self.expressions.get(name)

    def get_property_group(self, name: str) -> PropertyGroup | None:
        """Get property group by name."""
        return self.property_groups.get(name)

    def get_include(self, name: str) -> IncludeDefinition | None:
        """Get include definition by name (for controls)."""
        return self.includes.get(name)

    def get_preset(self, name: str) -> Preset | None:
        """Get preset by name."""
        return self.presets.get(name)

    def get_preset_group(self, name: str) -> PresetGroup | None:
        """Get preset group by name."""
        return self.preset_groups.get(name)

    def get_variable_definition(self, name: str) -> VariableDefinition | None:
        """Get variable definition by name."""
        return self.variable_definitions.get(name)

    def get_variable_group(self, name: str) -> VariableGroup | None:
        """Get variable group by name."""
        return self.variable_groups.get(name)

    def get_items_template(self, name: str) -> ItemsDefinition | None:
        """Get items template by name."""
        return self.items_templates.get(name)
