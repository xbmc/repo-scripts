"""Template loader for Skin Shortcuts v3.

Parses templates.xml with support for expressions, includes, presets, and templates.
"""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from pathlib import Path

from ..exceptions import TemplateConfigError
from ..log import get_logger
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
    TemplateParam,
    TemplateProperty,
    TemplateSchema,
    TemplateVar,
    VariableDefinition,
    VariableGroup,
    VariableGroupReference,
    VariableReference,
)
from .base import apply_suffix_to_from, apply_suffix_transform, get_bool

log = get_logger("TemplateLoader")


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

        try:
            tree = ET.parse(str(self.path))
            root = tree.getroot()
        except ET.ParseError as e:
            raise TemplateConfigError(str(self.path), f"XML parse error: {e}", e.position[0]) from e
        except Exception as e:
            raise TemplateConfigError(str(self.path), f"Failed to load file: {e}") from e

        if root.tag != "templates":
            raise TemplateConfigError(
                str(self.path), f"Root element must be <templates>, got <{root.tag}>"
            )

        self._parse_expressions_section(root)
        self._parse_presets_section(root)
        self._parse_preset_groups_section(root)
        self._parse_property_groups_section(root)
        self._parse_variables_section(root)
        self._parse_includes_section(root)

        templates = []
        for elem in root.findall("template"):
            items_name = (elem.get("items") or "").strip()
            if items_name:
                items_def = self._parse_items_template(elem, items_name)
                if items_def:
                    self._items_templates[items_name] = items_def
            else:
                template = self._parse_template(elem)
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
        """Parse <expressions> section."""
        section = root.find("expressions")
        if section is None:
            return
        for elem in section.findall("expression"):
            name = (elem.get("name") or "").strip()
            if not name:
                log.warning(f"{self.path}: <{elem.tag}> definition missing 'name' attribute, skipping")
                continue
            value = (elem.text or "").strip()
            nosuffix = get_bool(elem, "nosuffix")
            self._expressions[name] = Expression(value=value, nosuffix=nosuffix)

    def _parse_presets_section(self, root: ET.Element) -> None:
        """Parse <presets> section."""
        section = root.find("presets")
        if section is None:
            return
        for elem in section.findall("preset"):
            preset = self._parse_preset(elem)
            self._presets[preset.name] = preset

    def _parse_preset_groups_section(self, root: ET.Element) -> None:
        """Parse <presetGroups> section."""
        section = root.find("presetGroups")
        if section is None:
            return
        for elem in section.findall("presetGroup"):
            group = self._parse_preset_group(elem)
            if group:
                self._preset_groups[group.name] = group

    def _parse_preset_group(self, elem: ET.Element) -> PresetGroup | None:
        """Parse a presetGroup element.

        Children can be <preset content="name"/> or <values attr="val"/>.
        First matching condition wins (document order).
        """
        name = (elem.get("name") or "").strip()
        if not name:
            log.warning(f"{self.path}: <{elem.tag}> missing 'name' attribute, skipping")
            return None

        children = []
        for child in elem:
            if child.tag == "preset":
                preset_name = (child.get("content") or "").strip()
                if preset_name:
                    condition = (child.get("condition") or "").strip()
                    children.append(
                        PresetGroupChild(
                            preset_name=preset_name,
                            condition=condition,
                        )
                    )
                else:
                    log.warning(
                        f"{self.path}: <preset> in <presetGroup> missing 'content' attribute, skipping"
                    )
            elif child.tag == "values":
                condition = (child.get("condition") or "").strip()
                values = {k: v for k, v in child.attrib.items() if k != "condition"}
                children.append(
                    PresetGroupChild(
                        values=values,
                        condition=condition,
                    )
                )

        return PresetGroup(name=name, children=children)

    def _parse_property_groups_section(self, root: ET.Element) -> None:
        """Parse <propertyGroups> section."""
        section = root.find("propertyGroups")
        if section is None:
            return
        for elem in section.findall("propertyGroup"):
            name = (elem.get("name") or "").strip()
            if not name:
                log.warning(f"{self.path}: <{elem.tag}> definition missing 'name' attribute, skipping")
                continue

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

            self._property_groups[name] = PropertyGroup(
                name=name,
                properties=properties,
                vars=vars_list,
            )

    def _parse_variables_section(self, root: ET.Element) -> None:
        """Parse <variables> section for global variable definitions and groups."""
        section = root.find("variables")
        if section is None:
            return

        for elem in section.findall("variable"):
            var_def = self._parse_variable_definition(elem)
            if var_def:
                self._variable_definitions[var_def.name] = var_def

        for elem in section.findall("variableGroup"):
            group = self._parse_variable_group(elem)
            if group:
                self._variable_groups[group.name] = group

    def _parse_variable_group(self, elem: ET.Element) -> VariableGroup | None:
        """Parse a variableGroup element."""
        name = (elem.get("name") or "").strip()
        if not name:
            log.warning(f"{self.path}: <{elem.tag}> missing 'name' attribute, skipping")
            return None

        references = []
        for var_elem in elem.findall("variable"):
            ref = self._parse_variable_reference(var_elem)
            if ref:
                references.append(ref)

        group_refs = []
        for group_elem in elem.findall("variableGroup"):
            group_name = (group_elem.get("content") or "").strip()
            if group_name:
                group_refs.append(VariableGroupReference(name=group_name))
            else:
                log.warning(
                    f"{self.path}: nested <variableGroup> missing 'content' attribute, skipping"
                )

        return VariableGroup(name=name, references=references, group_refs=group_refs)

    def _parse_variable_reference(self, elem: ET.Element) -> VariableReference | None:
        """Parse a variable reference within a variableGroup.

        Uses content="" attribute (v4 syntax) for the reference name.
        """
        name = (elem.get("content") or "").strip()
        if not name:
            log.warning(f"{self.path}: <{elem.tag}> reference missing 'content' attribute, skipping")
            return None
        condition = (elem.get("condition") or "").strip()
        return VariableReference(name=name, condition=condition)

    def _parse_includes_section(self, root: ET.Element) -> None:
        """Parse <includes> section for control includes."""
        section = root.find("includes")
        if section is None:
            return
        for elem in section.findall("include"):
            name = (elem.get("name") or "").strip()
            if not name:
                log.warning(f"{self.path}: <{elem.tag}> definition missing 'name' attribute, skipping")
                continue

            self._includes[name] = IncludeDefinition(
                name=name,
                controls=copy.deepcopy(elem) if len(elem) > 0 else None,
            )

    def _parse_param(self, elem: ET.Element) -> TemplateParam | None:
        """Parse a param element."""
        name = (elem.get("name") or "").strip()
        if not name:
            log.warning(f"{self.path}: <{elem.tag}> missing 'name' attribute, skipping")
            return None
        default = (elem.get("default") or "").strip()
        return TemplateParam(name=name, default=default)

    def _parse_property(self, elem: ET.Element, suffix: str = "") -> TemplateProperty | None:
        """Parse a property element."""
        name = (elem.get("name") or "").strip()
        if not name:
            log.warning(f"{self.path}: <{elem.tag}> missing 'name' attribute, skipping")
            return None

        value = (elem.get("value") or elem.text or "").strip()
        from_source = (elem.get("from") or "").strip()
        condition = (elem.get("condition") or "").strip()

        if suffix:
            if from_source:
                from_source = apply_suffix_to_from(from_source, suffix)
            if condition:
                condition = apply_suffix_transform(condition, suffix)

        return TemplateProperty(
            name=name,
            value=value,
            from_source=from_source,
            condition=condition,
        )

    def _parse_var(self, elem: ET.Element, suffix: str = "") -> TemplateVar | None:
        """Parse a var element for internal template resolution."""
        name = (elem.get("name") or "").strip()
        if not name:
            log.warning(f"{self.path}: <{elem.tag}> missing 'name' attribute, skipping")
            return None

        values = []
        for value_elem in elem.findall("value"):
            value = (value_elem.text or "").strip()
            condition = (value_elem.get("condition") or "").strip()

            if suffix and condition:
                condition = apply_suffix_transform(condition, suffix)

            values.append(TemplateProperty(name=name, value=value, condition=condition))

        return TemplateVar(name=name, values=values)

    def _parse_preset(self, elem: ET.Element) -> Preset:
        """Parse a preset element."""
        name = (elem.get("name") or "").strip()
        if not name:
            raise TemplateConfigError(str(self.path), "Preset missing name attribute")

        rows = []
        for values_elem in elem.findall("values"):
            condition = (values_elem.get("condition") or "").strip()
            values = {k: v for k, v in values_elem.attrib.items() if k != "condition"}
            rows.append(PresetValues(condition=condition, values=values))

        return Preset(name=name, rows=rows)

    def _parse_template(self, elem: ET.Element) -> Template:
        """Parse a template element."""
        outputs: list[TemplateOutput] = []
        for output_elem in elem.findall("output"):
            output_include = (output_elem.get("include") or "").strip()
            if output_include:
                outputs.append(
                    TemplateOutput(
                        include=output_include,
                        id_prefix=(output_elem.get("idprefix") or "").strip(),
                        suffix=(output_elem.get("suffix") or "").strip(),
                    )
                )

        include = (elem.get("include") or "").strip()
        id_prefix = (elem.get("idprefix") or "").strip()

        if not outputs and not include:
            raise TemplateConfigError(
                str(self.path), "Template missing include attribute or output elements"
            )

        build_str = (elem.get("build") or "").strip().lower()
        if build_str == "true":
            build = BuildMode.RAW
        else:
            build = BuildMode.MENU

        template_only = (elem.get("templateonly") or "").strip().lower()
        menu = (elem.get("menu") or "").strip()

        conditions = []
        for cond_elem in elem.findall("condition"):
            cond_text = (cond_elem.text or "").strip()
            if cond_text:
                conditions.append(cond_text)

        params = []
        for param_elem in elem.findall("param"):
            param = self._parse_param(param_elem)
            if param:
                params.append(param)

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
                ref = self._parse_property_group_ref(child)
                if ref:
                    property_groups.append(ref)
            elif child.tag == "preset":
                ref = self._parse_preset_ref(child)
                if ref:
                    preset_refs.append(ref)
            elif child.tag == "presetGroup":
                ref = self._parse_preset_group_ref(child)
                if ref:
                    preset_group_refs.append(ref)
            elif child.tag == "variableGroup":
                ref = self._parse_variable_group_ref(child)
                if ref:
                    variable_groups.append(ref)

        variables_elem = elem.find("variables")
        if variables_elem is not None:
            for var_elem in variables_elem.findall("variable"):
                var_def = self._parse_variable_definition(var_elem)
                if var_def:
                    variables.append(var_def)

        controls = elem.find("controls")

        return Template(
            include=include,
            build=build,
            id_prefix=id_prefix,
            template_only=template_only,
            menu=menu,
            outputs=outputs,
            conditions=conditions,
            params=params,
            properties=properties,
            vars=vars_list,
            property_groups=property_groups,
            preset_refs=preset_refs,
            preset_group_refs=preset_group_refs,
            controls=copy.deepcopy(controls) if controls is not None else None,
            variables=variables,
            variable_groups=variable_groups,
        )

    def _parse_submenu(self, elem: ET.Element) -> SubmenuTemplate:
        """Parse a submenu element."""
        include = (elem.get("include") or "").strip()
        level_str = (elem.get("level") or "0").strip()
        try:
            level = int(level_str)
        except ValueError:
            level = 0
        name = (elem.get("name") or "").strip()

        properties = []
        vars_list = []
        property_groups = []

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
                ref = self._parse_property_group_ref(child)
                if ref:
                    property_groups.append(ref)

        controls = elem.find("controls")

        return SubmenuTemplate(
            include=include,
            level=level,
            name=name,
            properties=properties,
            vars=vars_list,
            property_groups=property_groups,
            controls=copy.deepcopy(controls) if controls is not None else None,
        )

    def _parse_items_template(self, elem: ET.Element, name: str) -> ItemsDefinition | None:
        """Parse <template items="X"> into an ItemsDefinition.

        Syntax:
            <template items="widgets" source="widgets" filter="widgetPath">
                <condition>widgetType=custom</condition>
                <property name="id" from="index" />
                <var name="style">...</var>
                <preset content="layoutDims" />
                <propertyGroup content="widgetProps" />
                <controls>
                    <control type="group">...</control>
                </controls>
            </template>
        """
        source = (elem.get("source") or "").strip()
        filter_cond = (elem.get("filter") or "").strip()

        condition = ""
        cond_elem = elem.find("condition")
        if cond_elem is not None:
            condition = (cond_elem.text or "").strip()

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
                ref = self._parse_preset_ref(child)
                if ref:
                    preset_refs.append(ref)
            elif child.tag == "propertyGroup":
                ref = self._parse_property_group_ref(child)
                if ref:
                    property_groups.append(ref)
            elif child.tag == "variableGroup":
                ref = self._parse_variable_group_ref(child)
                if ref:
                    variable_groups.append(ref)

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

    def _parse_property_group_ref(self, elem: ET.Element) -> PropertyGroupReference | None:
        """Parse a property group reference element.

        Uses content="" attribute (v4 syntax) for the reference name.
        """
        name = (elem.get("content") or "").strip()
        if not name:
            log.warning(f"{self.path}: <{elem.tag}> reference missing 'content' attribute, skipping")
            return None

        suffix = (elem.get("suffix") or "").strip()
        condition = (elem.get("condition") or "").strip()

        return PropertyGroupReference(
            name=name,
            suffix=suffix,
            condition=condition,
        )

    def _parse_preset_ref(self, elem: ET.Element) -> PresetReference | None:
        """Parse a preset reference element for direct property resolution.

        Uses content="" attribute (v4 syntax) for the reference name.
        """
        name = (elem.get("content") or "").strip()
        if not name:
            log.warning(f"{self.path}: <{elem.tag}> reference missing 'content' attribute, skipping")
            return None

        suffix = (elem.get("suffix") or "").strip()
        condition = (elem.get("condition") or "").strip()

        return PresetReference(
            name=name,
            suffix=suffix,
            condition=condition,
        )

    def _parse_preset_group_ref(self, elem: ET.Element) -> PresetGroupReference | None:
        """Parse a presetGroup reference element in a template.

        Uses content="" attribute (v4 syntax) for the reference name.
        """
        name = (elem.get("content") or "").strip()
        if not name:
            log.warning(f"{self.path}: <{elem.tag}> reference missing 'content' attribute, skipping")
            return None

        suffix = (elem.get("suffix") or "").strip()
        condition = (elem.get("condition") or "").strip()

        return PresetGroupReference(
            name=name,
            suffix=suffix,
            condition=condition,
        )

    def _parse_variable_group_ref(self, elem: ET.Element) -> VariableGroupReference | None:
        """Parse a variableGroup reference element in a template.

        Uses content="" attribute (v4 syntax) for the reference name.
        """
        name = (elem.get("content") or "").strip()
        if not name:
            log.warning(f"{self.path}: <{elem.tag}> reference missing 'content' attribute, skipping")
            return None

        suffix = (elem.get("suffix") or "").strip()
        condition = (elem.get("condition") or "").strip()

        return VariableGroupReference(
            name=name,
            suffix=suffix,
            condition=condition,
        )

    def _parse_variable_definition(self, elem: ET.Element) -> VariableDefinition | None:
        """Parse a variable definition inside a template's <variables> section."""
        name = (elem.get("name") or "").strip()
        if not name:
            log.warning(f"{self.path}: <{elem.tag}> missing 'name' attribute, skipping")
            return None

        condition = (elem.get("condition") or "").strip()
        output = (elem.get("output") or "").strip()

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
