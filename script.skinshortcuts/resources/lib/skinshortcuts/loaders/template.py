"""Template loader, parsing templates.xml expressions, includes, presets and templates."""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TypeVar

from ..exceptions import TemplateConfigError
from ..log import notify
from ..models.template import (
    BuildMode,
    Expression,
    IncludeDefinition,
    ItemsDefinition,
    Preset,
    PresetGroup,
    PresetGroupChild,
    PresetGroupReference,
    PresetReference,
    PresetValues,
    PropertyGroup,
    PropertyGroupReference,
    SubmenuTemplate,
    Template,
    TemplateOutput,
    TemplateProperty,
    TemplateSchema,
    TemplateVar,
    VariableDefinition,
    VariableGroup,
    VariableGroupReference,
    VariableReference,
)
from .base import get_attr, get_bool, keep_first, parse_xml, report_missing

R = TypeVar(
    "R", PropertyGroupReference, PresetReference, PresetGroupReference, VariableGroupReference
)

_SUBMENU_UNSUPPORTED = {
    "propertyGroup": "move its values into <property> elements",
    "preset": "use <property> or <var> elements",
    "presetGroup": "use <property> or <var> elements",
    "variableGroup": "build the variables from a menu template",
    "variables": "build the variables from a menu template",
    "condition": "put a condition on each <property> instead",
}
_SUBMENU_TEXT_FIXES = {
    "$IF": "use a Kodi $VAR with conditions",
    "$PARENT": "read the main item with Container(<main list>).ListItem.Property(...)",
}


def _drop_include_markers(controls: ET.Element | None) -> list[str]:
    """Drop each <skinshortcuts include> marker from the tree, returning their names."""
    dropped: list[str] = []
    for parent in list(controls.iter()) if controls is not None else []:
        for child in list(parent):
            if child.tag == "skinshortcuts" and child.get("include"):
                dropped.append(child.get("include") or "")
                parent.remove(child)
    return dropped


def _drop_duplicate_definitions(elem: ET.Element, heading: str, written: str) -> None:
    """Drop and report each <var>, or <property> after a <var>, reusing a name; the first stays."""
    property_names: set[str] = set()
    var_names: set[str] = set()
    for child in list(elem):
        name = get_attr(child, "name").lower()
        if child.tag not in ("property", "var") or not name:
            continue
        if name in var_names or (child.tag == "var" and name in property_names):
            notify(
                heading,
                f"'{child.get('name')}' defined twice",
                f"templates.xml: {written} defines '{child.get('name')}' again with "
                f"<{child.tag}>; the first definition is used; keep one <var>, or only "
                "<property> elements",
            )
            elem.remove(child)
        elif child.tag == "var":
            var_names.add(name)
        else:
            property_names.add(name)


class TemplateLoader:
    """Loads template schema from templates.xml."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._expressions: dict[str, Expression] = {}
        self._presets: dict[str, Preset] = {}
        self._preset_groups: dict[str, PresetGroup] = {}
        self._property_groups: dict[str, PropertyGroup] = {}
        self._variable_definitions: dict[str, VariableDefinition] = {}
        self._variable_groups: dict[str, VariableGroup] = {}
        self._includes: dict[str, IncludeDefinition] = {}
        self._items_templates: dict[str, ItemsDefinition] = {}

    def load(self) -> TemplateSchema:
        """Load and parse the template schema."""
        if not self.path.exists():
            return TemplateSchema()

        root = parse_xml(self.path, "templates", TemplateConfigError)
        self._parse_expressions_section(root)
        self._parse_presets_section(root)
        self._parse_preset_groups_section(root)
        self._parse_property_groups_section(root)
        self._parse_variables_section(root)
        self._parse_includes_section(root)

        templates = []
        for elem in root.findall("template"):
            items_name = get_attr(elem, "items")
            if items_name:
                items_def = self._parse_items_template(elem, items_name)
                if items_def:
                    keep_first(
                        self._items_templates, items_name, items_def, "items template", self.path
                    )
            else:
                template = self._parse_template(elem)
                if template:
                    templates.append(template)

        submenus = []
        for elem in root.findall("submenu"):
            submenu = self._parse_submenu(elem)
            submenus.append(submenu)

        return TemplateSchema(
            expressions=self._expressions,
            property_groups=self._property_groups,
            includes=self._includes,
            presets=self._presets,
            preset_groups=self._preset_groups,
            variable_definitions=self._variable_definitions,
            variable_groups=self._variable_groups,
            items_templates=self._items_templates,
            templates=templates,
            submenus=submenus,
        )

    def _parse_expressions_section(self, root: ET.Element) -> None:
        """Parse <expressions> section, bracketing each value so callers can compound it."""
        section = root.find("expressions")
        if section is None:
            return
        for elem in section.findall("expression"):
            name = get_attr(elem, "name")
            if not name:
                report_missing("Template Error", self.path, elem, "name")
                continue
            value = (elem.text or "").strip()
            nosuffix = get_bool(elem, "noSuffix")
            expression = Expression(value=f"[{value}]" if value else "", nosuffix=nosuffix)
            keep_first(self._expressions, name, expression, "expression", self.path)

    def _parse_presets_section(self, root: ET.Element) -> None:
        """Parse <presets> section, skipping a preset with no name."""
        section = root.find("presets")
        if section is None:
            return
        for elem in section.findall("preset"):
            preset = self._parse_preset(elem)
            if preset:
                keep_first(self._presets, preset.name, preset, "preset", self.path)

    def _parse_preset_groups_section(self, root: ET.Element) -> None:
        """Parse <presetGroups> section, reporting a repeated group name."""
        section = root.find("presetGroups")
        if section is None:
            return
        for elem in section.findall("presetGroup"):
            group = self._parse_preset_group(elem)
            if group:
                keep_first(self._preset_groups, group.name, group, "presetGroup", self.path)

    def _parse_preset_group(self, elem: ET.Element) -> PresetGroup | None:
        """Parse a presetGroup element into its preset and values children, in order."""
        name = get_attr(elem, "name")
        if not name:
            report_missing("Template Error", self.path, elem, "name")
            return None

        children = []
        for child in elem:
            if child.tag == "preset":
                preset_name = get_attr(child, "content")
                if preset_name:
                    condition = get_attr(child, "condition")
                    children.append(
                        PresetGroupChild(
                            preset_name=preset_name,
                            condition=condition,
                        )
                    )
                else:
                    report_missing(
                        "Template Error", self.path, child, "content", key="content",
                        scope=f"presetGroup '{name}'",
                    )
            elif child.tag == "values":
                condition = get_attr(child, "condition")
                values = {k: v for k, v in child.attrib.items() if k != "condition"}
                children.append(
                    PresetGroupChild(
                        values=values,
                        condition=condition,
                    )
                )

        return PresetGroup(name=name, children=children)

    def _parse_property_groups_section(self, root: ET.Element) -> None:
        """Parse <propertyGroups> section, dropping and reporting duplicate definitions."""
        section = root.find("propertyGroups")
        if section is None:
            return
        for elem in section.findall("propertyGroup"):
            name = get_attr(elem, "name")
            if not name:
                report_missing("Template Error", self.path, elem, "name")
                continue
            _drop_duplicate_definitions(elem, "Template Error", f'<propertyGroup name="{name}">')

            properties = []
            for prop_elem in elem.findall("property"):
                prop = self._parse_property(prop_elem)
                if prop:
                    properties.append(prop)

            vars_list = []
            for var_elem in elem.findall("var"):
                var = self._parse_var(var_elem)
                if var:
                    vars_list.append(var)

            group = PropertyGroup(name=name, properties=properties, vars=vars_list)
            keep_first(self._property_groups, name, group, "propertyGroup", self.path)

    def _parse_variables_section(self, root: ET.Element) -> None:
        """Parse <variables> section for global variable definitions and groups."""
        section = root.find("variables")
        if section is None:
            return

        for elem in section.findall("variable"):
            var_def = self._parse_variable_definition(elem)
            if var_def:
                keep_first(
                    self._variable_definitions, var_def.name, var_def, "variable", self.path
                )

        for elem in section.findall("variableGroup"):
            group = self._parse_variable_group(elem)
            if group:
                keep_first(self._variable_groups, group.name, group, "variableGroup", self.path)

    def _parse_variable_group(self, elem: ET.Element) -> VariableGroup | None:
        """Parse a variableGroup element: its variable references and nested group references."""
        name = get_attr(elem, "name")
        if not name:
            report_missing("Template Error", self.path, elem, "name")
            return None

        references = []
        for var_elem in elem.findall("variable"):
            ref = self._parse_variable_reference(var_elem)
            if ref:
                references.append(ref)

        group_refs = []
        for group_elem in elem.findall("variableGroup"):
            group_name = get_attr(group_elem, "content")
            if group_name:
                group_refs.append(VariableGroupReference(name=group_name))
            else:
                report_missing(
                    "Template Error", self.path, group_elem, "content", key="content",
                    scope=f"variableGroup '{name}'",
                )

        return VariableGroup(name=name, references=references, group_refs=group_refs)

    def _parse_variable_reference(self, elem: ET.Element) -> VariableReference | None:
        """Parse a variable reference within a variableGroup."""
        name = get_attr(elem, "content")
        if not name:
            report_missing("Template Error", self.path, elem, "content", key="content")
            return None
        condition = get_attr(elem, "condition")
        return VariableReference(name=name, condition=condition)

    def _parse_includes_section(self, root: ET.Element) -> None:
        """Parse <includes> section for control includes."""
        section = root.find("includes")
        if section is None:
            return
        for elem in section.findall("include"):
            name = get_attr(elem, "name")
            if not name:
                report_missing("Template Error", self.path, elem, "name")
                continue

            include = IncludeDefinition(
                name=name, controls=copy.deepcopy(elem) if len(elem) > 0 else None
            )
            keep_first(self._includes, name, include, "include", self.path)

    def _parse_property(self, elem: ET.Element) -> TemplateProperty | None:
        """Parse a property element, reporting one with no name."""
        name = get_attr(elem, "name")
        if not name:
            report_missing("Template Error", self.path, elem, "name")
            return None

        return TemplateProperty(
            name=name,
            value=(elem.get("value") or elem.text or "").strip(),
            from_source=get_attr(elem, "from"),
            condition=get_attr(elem, "condition"),
        )

    def _parse_var(self, elem: ET.Element) -> TemplateVar | None:
        """Parse a var element for internal template resolution."""
        name = get_attr(elem, "name")
        if not name:
            report_missing("Template Error", self.path, elem, "name")
            return None

        values = []
        for value_elem in elem.findall("value"):
            value = (value_elem.text or "").strip()
            condition = get_attr(value_elem, "condition")
            values.append(TemplateProperty(name=name, value=value, condition=condition))

        return TemplateVar(name=name, values=values)

    def _parse_preset(self, elem: ET.Element) -> Preset | None:
        """Parse a preset element, reporting one with no name."""
        name = get_attr(elem, "name")
        if not name:
            report_missing("Template Error", self.path, elem, "name")
            return None

        rows = []
        for values_elem in elem.findall("values"):
            condition = get_attr(values_elem, "condition")
            values = {k: v for k, v in values_elem.attrib.items() if k != "condition"}
            rows.append(PresetValues(condition=condition, values=values))

        return Preset(name=name, rows=rows)

    def _parse_template(self, elem: ET.Element) -> Template | None:
        """Parse a template, dropping duplicates, raw markers; reports no output, raw variables."""
        outputs: list[TemplateOutput] = []
        for output_elem in elem.findall("output"):
            output_include = get_attr(output_elem, "include")
            if output_include:
                outputs.append(
                    TemplateOutput(
                        include=output_include,
                        id_prefix=get_attr(output_elem, "idPrefix"),
                        suffix=get_attr(output_elem, "suffix"),
                    )
                )

        include = get_attr(elem, "include")
        id_prefix = get_attr(elem, "idPrefix")

        if not outputs and not include:
            report_missing("Template Error", self.path, elem, "include", key="include")
            return None

        build_str = get_attr(elem, "build").lower()
        if build_str == "true":
            build = BuildMode.RAW
        else:
            build = BuildMode.MENU

        template_only = get_attr(elem, "templateOnly").lower()
        menu = get_attr(elem, "menu")

        conditions = []
        for cond_elem in elem.findall("condition"):
            cond_text = (cond_elem.text or "").strip()
            if cond_text:
                conditions.append(cond_text)

        name = include or outputs[0].include
        _drop_duplicate_definitions(elem, "Template Error", f'<template include="{name}">')

        properties = []
        vars_list = []
        property_groups = []
        preset_refs = []
        preset_group_refs = []
        variable_groups = []
        variables = []

        for child in elem:
            if child.tag == "property":
                prop = self._parse_property(child)
                if prop:
                    properties.append(prop)
            elif child.tag == "var":
                var = self._parse_var(child)
                if var:
                    vars_list.append(var)
            elif child.tag == "propertyGroup":
                ref = self._parse_ref(child, PropertyGroupReference)
                if ref:
                    property_groups.append(ref)
            elif child.tag == "preset":
                ref = self._parse_ref(child, PresetReference)
                if ref:
                    preset_refs.append(ref)
            elif child.tag == "presetGroup":
                ref = self._parse_ref(child, PresetGroupReference)
                if ref:
                    preset_group_refs.append(ref)
            elif child.tag == "variableGroup":
                ref = self._parse_ref(child, VariableGroupReference)
                if ref:
                    variable_groups.append(ref)

        variables_elem = elem.find("variables")
        if variables_elem is not None:
            for var_elem in variables_elem.findall("variable"):
                var_def = self._parse_variable_definition(var_elem)
                if var_def:
                    variables.append(var_def)

        controls = elem.find("controls")
        controls = copy.deepcopy(controls) if controls is not None else None

        if build == BuildMode.RAW:
            for tag, declared in (("variables", variables), ("variableGroup", variable_groups)):
                if declared:
                    notify(
                        "Template Error",
                        f"raw template '{name}' has <{tag}>",
                        f"templates.xml: <template include=\"{name}\" build=\"true\"> declares "
                        f"<{tag}>, which raw templates do not build; move it to a menu template",
                    )
            for marker in _drop_include_markers(controls):
                notify(
                    "Template Error",
                    f"raw template '{name}' has <skinshortcuts include>",
                    f"templates.xml: <template include=\"{name}\" build=\"true\"> uses "
                    f"<skinshortcuts include=\"{marker}\"/>, which raw templates do not "
                    "expand; the marker is left out; use a Kodi <include>",
                )

        return Template(
            include=include,
            build=build,
            id_prefix=id_prefix,
            template_only=template_only,
            menu=menu,
            outputs=outputs,
            conditions=conditions,
            properties=properties,
            vars=vars_list,
            property_groups=property_groups,
            preset_refs=preset_refs,
            preset_group_refs=preset_group_refs,
            controls=controls,
            variables=variables,
            variable_groups=variable_groups,
        )

    def _parse_submenu(self, elem: ET.Element) -> SubmenuTemplate:
        """Parse a submenu, reporting unbuilt features, dropping duplicates and include markers."""
        include = get_attr(elem, "include")
        level_str = (elem.get("level") or "0").strip()
        try:
            level = int(level_str)
        except ValueError:
            level = 0
        name = get_attr(elem, "name")
        written = f'<submenu include="{include}">'
        _drop_duplicate_definitions(elem, "Submenu Template Error", written)

        properties = []
        vars_list = []
        ignored: list[str] = []

        for child in elem:
            if child.tag == "property":
                prop = self._parse_property(child)
                if prop:
                    properties.append(prop)
            elif child.tag == "var":
                var = self._parse_var(child)
                if var:
                    vars_list.append(var)
            elif child.tag in _SUBMENU_UNSUPPORTED and child.tag not in ignored:
                ignored.append(child.tag)

        for tag in ignored:
            notify(
                "Submenu Template Error",
                f"'{include}' uses <{tag}>",
                f"templates.xml: {written} contains <{tag}>, which submenu templates do not "
                f"build; it is ignored; {_SUBMENU_UNSUPPORTED[tag]}",
            )

        controls = elem.find("controls")
        controls = copy.deepcopy(controls) if controls is not None else None
        text = "" if controls is None else ET.tostring(controls, encoding="unicode")
        for token, fix in _SUBMENU_TEXT_FIXES.items():
            if f"{token}[" in text:
                notify(
                    "Submenu Template Error",
                    f"'{include}' uses {token}",
                    f"templates.xml: {written} uses {token}[...] in its controls, which "
                    f"submenu templates leave as written; {fix}",
                )
        for marker in _drop_include_markers(controls):
            notify(
                "Submenu Template Error",
                f"'{include}' uses <skinshortcuts include>",
                f"templates.xml: {written} uses <skinshortcuts include=\"{marker}\"/>, which "
                "submenu templates do not expand; the marker is left out; use a Kodi <include>",
            )

        return SubmenuTemplate(
            include=include,
            level=level,
            name=name,
            properties=properties,
            vars=vars_list,
            controls=controls,
        )

    def _parse_items_template(self, elem: ET.Element, name: str) -> ItemsDefinition | None:
        """Parse <template items="X">, reporting and dropping duplicates and suffix=."""
        source = get_attr(elem, "source")
        filter_cond = get_attr(elem, "filter")

        condition = ""
        cond_elem = elem.find("condition")
        if cond_elem is not None:
            condition = (cond_elem.text or "").strip()

        _drop_duplicate_definitions(elem, "Items Template Error", f'<template items="{name}">')

        properties = []
        vars_list = []
        preset_refs = []
        property_groups = []
        variable_groups = []

        for child in elem:
            if child.tag == "property":
                prop = self._parse_property(child)
                if prop:
                    properties.append(prop)
            elif child.tag == "var":
                var = self._parse_var(child)
                if var:
                    vars_list.append(var)
            elif child.tag == "preset":
                ref = self._parse_ref(child, PresetReference)
                if ref:
                    preset_refs.append(ref)
            elif child.tag == "propertyGroup":
                ref = self._parse_ref(child, PropertyGroupReference)
                if ref:
                    property_groups.append(ref)
            elif child.tag == "variableGroup":
                ref = self._parse_ref(child, VariableGroupReference)
                if ref:
                    variable_groups.append(ref)

        refs = (
            ("preset", preset_refs), ("propertyGroup", property_groups),
            ("variableGroup", variable_groups),
        )
        for tag, tag_refs in refs:
            for ref in tag_refs:
                if ref.suffix:
                    notify(
                        "Items Template Error",
                        f"'{name}' uses suffix=",
                        f'templates.xml: <template items="{name}"> has <{tag} '
                        f'content="{ref.name}" suffix="{ref.suffix}">; suffixes are ignored in '
                        "items templates, whose items have no slots; remove suffix=",
                    )
                    ref.suffix = ""

        controls = elem.find("controls")

        return ItemsDefinition(
            name=name,
            source=source,
            condition=condition,
            filter=filter_cond,
            properties=properties,
            vars=vars_list,
            preset_refs=preset_refs,
            property_groups=property_groups,
            variable_groups=variable_groups,
            controls=copy.deepcopy(controls) if controls is not None else None,
        )

    def _parse_ref(self, elem: ET.Element, cls: type[R]) -> R | None:
        """Parse a preset or group reference, reporting one with no content."""
        name = get_attr(elem, "content")
        if not name:
            report_missing("Template Error", self.path, elem, "content", key="content")
            return None

        suffix = get_attr(elem, "suffix")
        condition = get_attr(elem, "condition")

        return cls(name=name, suffix=suffix, condition=condition)

    def _parse_variable_definition(self, elem: ET.Element) -> VariableDefinition | None:
        """Parse a variable definition, global or a template's, reporting one with no name."""
        name = get_attr(elem, "name")
        if not name:
            report_missing("Template Error", self.path, elem, "name")
            return None

        condition = get_attr(elem, "condition")
        output = get_attr(elem, "output")

        return VariableDefinition(
            name=name,
            condition=condition,
            output=output,
            content=copy.deepcopy(elem),
        )


def load_templates(path: str | Path) -> TemplateSchema:
    """Load template schema from file."""
    loader = TemplateLoader(path)
    return loader.load()
