"""Template builder for Skin Shortcuts v3.

Builds Kodi include XML from templates.xml and menu data.
"""

from __future__ import annotations

import copy
import re
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

from ..conditions import evaluate_condition
from ..constants import extract_path_from_action
from ..expressions import process_if_expressions, process_math_expressions
from ..loaders.base import NO_SUFFIX_PROPERTIES, apply_suffix_to_from, apply_suffix_transform
from ..log import get_logger
from ..models.template import BuildMode, TemplateProperty

log = get_logger("TemplateBuilder")

if TYPE_CHECKING:
    from ..models import Menu, MenuItem
    from ..models.property import PropertySchema
    from ..models.template import (
        ItemsDefinition,
        Preset,
        PresetGroupReference,
        PresetReference,
        PropertyGroup,
        SubmenuTemplate,
        Template,
        TemplateOutput,
        TemplateSchema,
        TemplateVar,
        VariableDefinition,
        VariableGroupReference,
    )

_PROPERTY_PATTERN = re.compile(r"\$PROPERTY\[([^\]]+)\]")
_PARENT_PATTERN = re.compile(r"\$PARENT\[([^\]]+)\]")
_EXP_PATTERN = re.compile(r"\$EXP\[([^\]]+)\]")
_INCLUDE_PATTERN = re.compile(r"\$INCLUDE\[([^\]]+)\]")


class TemplateBuilder:
    """Builds Kodi includes from v3 templates."""

    def __init__(
        self,
        schema: TemplateSchema,
        menus: list[Menu],
        property_schema: PropertySchema | None = None,
    ):
        self.schema = schema
        self.menus = menus
        self.property_schema = property_schema
        self._menu_map: dict[str, Menu] = {m.name: m for m in menus}
        self._assigned_templates: set[str] = self._collect_assigned_templates()

    def _collect_assigned_templates(self) -> set[str]:
        """Collect template include names that are actually assigned to menu items.

        Scans all menu item properties (widgetPath, widgetPath.2, etc.) for
        $INCLUDE[skinshortcuts-template-*] references.
        """
        assigned: set[str] = set()
        include_pattern = re.compile(r"\$INCLUDE\[skinshortcuts-template-([^\]]+)\]")

        for menu in self.menus:
            for item in menu.items:
                for _prop_name, prop_value in item.properties.items():
                    if not prop_value:
                        continue
                    for match in include_pattern.finditer(prop_value):
                        assigned.add(f"skinshortcuts-template-{match.group(1)}")

        return assigned

    def build(self) -> ET.Element:
        """Build all template includes and variables.

        Templates with the same include name are merged into a single include element.
        Variables with the same name are merged (children appended to existing).
        Variables are output at the root level (siblings to includes).
        """
        root = ET.Element("includes")

        include_map: dict[str, ET.Element] = {}
        variable_map: dict[str, ET.Element] = {}

        # templateonly: "true" = never generate, "auto" = skip if unassigned
        template_only_settings: dict[str, str] = {}

        for template in self.schema.templates:
            for output in template.get_outputs():
                include_name = f"skinshortcuts-template-{output.include}"

                if template.template_only:
                    template_only_settings[include_name] = template.template_only

                if include_name not in include_map:
                    include_elem = ET.Element("include")
                    include_elem.set("name", include_name)
                    include_map[include_name] = include_elem

                include_elem = include_map[include_name]
                if template.build == BuildMode.RAW:
                    self._build_raw_template(
                        template, output, include_elem, variable_map
                    )
                else:
                    self._build_template_into(
                        template, output, include_elem, variable_map
                    )

        for submenu_tpl in self.schema.submenus:
            self._build_submenu_template(submenu_tpl, include_map)

        for var_elem in variable_map.values():
            root.append(var_elem)

        for include_name, include_elem in include_map.items():
            setting = template_only_settings.get(include_name, "")
            if setting == "true":
                continue
            if setting == "auto" and include_name not in self._assigned_templates:
                continue
            if len(include_elem) == 0:
                desc = ET.SubElement(include_elem, "description")
                desc.text = "Automatically generated - no menu items matched this template"
            root.append(include_elem)

        return root

    def _build_submenu_template(
        self,
        submenu_tpl: SubmenuTemplate,
        include_map: dict[str, ET.Element],
    ) -> None:
        """Build a submenu template.

        Two modes:
        - name="menuname": Process controls once, with items insert for iteration
        - level=N: Process controls for each main menu item that has submenus
        """
        if not submenu_tpl.controls:
            return

        include_name = f"skinshortcuts-{submenu_tpl.include}"
        if include_name not in include_map:
            include_elem = ET.Element("include")
            include_elem.set("name", include_name)
            include_map[include_name] = include_elem
        include_elem = include_map[include_name]

        if submenu_tpl.name:
            menu = self._menu_map.get(submenu_tpl.name)
            if not menu:
                log.debug(f"Named menu '{submenu_tpl.name}' not found for submenu template")
                return
            self._build_submenu_named(submenu_tpl, menu, include_elem)
        elif submenu_tpl.level > 0:
            self._build_submenu_level(submenu_tpl, include_elem)

    def _build_submenu_named(
        self,
        submenu_tpl: SubmenuTemplate,
        menu: Menu,
        include_elem: ET.Element,
    ) -> None:
        """Build a named submenu template (e.g., powermenu).

        Processes controls once. Any <skinshortcuts insert="X"> inside
        triggers items iteration over the menu's items.
        """
        context: dict[str, str] = {"menu": menu.name}
        self._apply_submenu_transforms(submenu_tpl, context)
        self._emit_submenu_controls(submenu_tpl, context, menu, include_elem)

    def _build_submenu_level(
        self,
        submenu_tpl: SubmenuTemplate,
        include_elem: ET.Element,
    ) -> None:
        """Build a level-based submenu template.

        Iterates over main menu items and generates controls for each
        item that has a submenu at the specified level.
        """
        main_menu = self._menu_map.get("mainmenu")
        if not main_menu:
            log.debug("Main menu not found for level-based submenu template")
            return

        for idx, item in enumerate(main_menu.items, start=1):
            if item.disabled:
                continue

            submenu_key = f"{main_menu.name}/{item.name}"
            submenu = self._menu_map.get(submenu_key)
            if not submenu:
                continue

            context = self._build_submenu_level_context(item, idx, submenu)
            self._apply_submenu_transforms(submenu_tpl, context, item)
            self._emit_submenu_controls(submenu_tpl, context, submenu, include_elem, item)

    def _emit_submenu_controls(
        self,
        submenu_tpl: SubmenuTemplate,
        context: dict[str, str],
        menu: Menu,
        target: ET.Element,
        parent_item: MenuItem | None = None,
    ) -> None:
        """Process submenu template controls and append to target element."""
        if submenu_tpl.controls is None:
            return
        controls_copy = copy.deepcopy(submenu_tpl.controls)
        for child in list(controls_copy):
            processed = self._process_submenu_controls(child, context, menu, parent_item)
            if processed is not None:
                self._append_processed(target, processed)

    @staticmethod
    def _append_processed(parent: ET.Element, elem: ET.Element) -> None:
        """Append a processed element, unwrapping _container wrappers."""
        if elem.tag == "_container":
            for child in elem:
                parent.append(child)
        else:
            parent.append(elem)

    def _build_submenu_level_context(
        self,
        item: MenuItem,
        index: int,
        submenu: Menu,
    ) -> dict[str, str]:
        """Build context for a level-based submenu template."""
        context: dict[str, str] = {**item.properties}
        context["name"] = item.name
        context["label"] = item.label
        context["index"] = str(index)
        context["menu"] = submenu.name
        context["icon"] = item.icon
        context["action"] = item.action
        context["path"] = extract_path_from_action(item.action) if item.action else ""
        context["submenu"] = item.submenu or ""
        if "submenuVisibility" not in context:
            context["submenuVisibility"] = item.name
        self._apply_fallbacks(item, context)
        return context

    def _apply_submenu_transforms(
        self,
        submenu_tpl: SubmenuTemplate,
        context: dict[str, str],
        parent_item: MenuItem | None = None,
    ) -> None:
        """Apply property/var transformations from submenu template.

        For level-based submenu templates, parent_item is the main menu item
        being processed, allowing $PARENT[] substitution in property values.
        """
        parent_context = dict(context)

        for prop in submenu_tpl.properties:
            if prop.from_source:
                value = context.get(prop.from_source, "")
            elif prop.value:
                value = prop.value
                if "$PARENT[" in value and parent_item is not None:
                    value = self._substitute_parent_refs(value, parent_context, parent_item)
            else:
                value = ""
            if value:
                context[prop.name] = value

        for var in submenu_tpl.vars:
            for val in var.values:
                if val.condition:
                    if evaluate_condition(val.condition, context):
                        context[var.name] = val.value
                        break
                else:
                    context[var.name] = val.value
                    break

    def _process_submenu_controls(
        self,
        elem: ET.Element,
        context: dict[str, str],
        menu: Menu,
        parent_item: MenuItem | None = None,
    ) -> ET.Element | None:
        """Process controls from a submenu template."""
        result = copy.deepcopy(elem)

        if result.text:
            result.text = self._substitute_submenu_text(result.text, context)
        if result.tail:
            result.tail = self._substitute_submenu_text(result.tail, context)

        for attr_name, attr_value in list(result.attrib.items()):
            if attr_name.startswith("_"):
                continue
            result.set(attr_name, self._substitute_submenu_text(attr_value, context))

        insert_attr = result.get("_skinshortcuts_insert")
        if insert_attr or result.tag == "skinshortcuts":
            insert_name = insert_attr or result.get("insert", "")
            if insert_name:
                items_def = self.schema.get_items_template(insert_name)
                if items_def:
                    container = ET.Element("_container")
                    self._expand_submenu_items(items_def, menu, container, context, parent_item)
                    return container
            return None

        for child in list(result):
            processed = self._process_submenu_controls(child, context, menu, parent_item)
            result.remove(child)
            if processed is not None:
                self._append_processed(result, processed)

        return result

    def _substitute_submenu_text(self, text: str, context: dict[str, str]) -> str:
        """Substitute $PROPERTY[...] and $EXP[...] in submenu template text."""
        def replace_property(m: re.Match[str]) -> str:
            return context.get(m.group(1), "")

        def replace_exp(m: re.Match[str]) -> str:
            exp_name = m.group(1)
            expr = self.schema.get_expression(exp_name)
            if expr:
                return expr.value
            return m.group(0)

        text = _PROPERTY_PATTERN.sub(replace_property, text)
        text = _EXP_PATTERN.sub(replace_exp, text)
        text = process_math_expressions(text, context)
        return text

    def _expand_submenu_items(
        self,
        items_def: ItemsDefinition,
        menu: Menu,
        container: ET.Element,
        parent_context: dict[str, str] | None = None,
        parent_item: MenuItem | None = None,
    ) -> None:
        """Expand items iteration within a submenu template."""
        for idx, item in enumerate(menu.items, start=1):
            if item.disabled:
                continue

            sub_context = self._build_items_context(item, idx, menu)
            self._apply_items_transformations_from_definition(
                sub_context, item, items_def, parent_context, parent_item
            )

            if items_def.controls is not None:
                for child in items_def.controls:
                    cloned = copy.deepcopy(child)
                    self._process_items_element(
                        cloned, sub_context, parent_context or {}, item, parent_item
                    )
                    container.append(cloned)

    def _build_raw_template(
        self,
        template: Template,
        output: TemplateOutput,
        include: ET.Element,
        variable_map: dict[str, ET.Element],
    ) -> None:
        """Output template controls for build="true" mode.

        Without property definitions: outputs controls once with OR'd visibility
        across all matching items (fast path).

        With property definitions: resolves properties per item, groups items
        with identical resolved output, and emits one control per group with
        OR'd visibility within each group (dedup path). Mirrors v2 <other>
        template behavior.
        """
        if template.controls is None:
            return

        matching = self._collect_raw_matching_items(template)

        if not template.has_transformations:
            for child in template.controls:
                cloned = copy.deepcopy(child)
                self._resolve_raw_visibility(cloned, matching)
                include.append(cloned)
            return

        groups: dict[
            str,
            tuple[
                ET.Element,
                list[tuple[MenuItem, Menu, int]],
                dict[str, str],
                MenuItem,
            ],
        ] = {}

        for item, menu, idx in matching:
            context = self._build_context(template, output, item, idx, menu)

            resolved = copy.deepcopy(template.controls)
            self._substitute_raw_controls(resolved, context, item)

            key: str = ET.tostring(resolved, encoding="unicode")  # type: ignore[assignment]

            if key not in groups:
                groups[key] = (resolved, [], context, item)
            groups[key][1].append((item, menu, idx))

        for resolved_controls, items, context, representative in groups.values():
            for child in list(resolved_controls):
                self._resolve_raw_visibility(child, items)
                include.append(child)

            for var_def in template.variables:
                var_elem = self._build_variable(var_def, context, representative)
                if var_elem is not None:
                    self._add_variable(var_elem, variable_map)

            for group_ref in template.variable_groups:
                effective_suffix = self._combine_suffixes(output.suffix, group_ref.suffix)
                self._build_variable_group(
                    group_ref, context, representative, variable_map, effective_suffix
                )

    def _collect_raw_matching_items(
        self, template: Template
    ) -> list[tuple[MenuItem, Menu, int]]:
        """Collect menu items matching a raw template's filters."""
        matching: list[tuple[MenuItem, Menu, int]] = []
        for menu in self.menus:
            if template.menu and menu.name != template.menu:
                continue
            if not menu.container:
                # Only warn when the template explicitly targets this menu
                if template.menu:
                    log.warning(
                        f"<skinshortcuts>visibility in build=\"true\" template for "
                        f"menu '{menu.name}' but menu has no container attribute"
                    )
                continue
            for idx, item in enumerate(menu.items, start=1):
                if item.disabled:
                    continue
                if not self._check_conditions(template.conditions, item):
                    continue
                matching.append((item, menu, idx))
        return matching

    def _substitute_raw_controls(
        self,
        elem: ET.Element,
        context: dict[str, str],
        item: MenuItem,
    ) -> None:
        """Substitute $PROPERTY/$EXP/$MATH/$IF in raw template controls.

        Leaves <skinshortcuts>visibility</skinshortcuts> markers untouched
        for post-grouping resolution.
        """
        for child in elem:
            if (
                child.tag == "skinshortcuts"
                and child.text
                and child.text.strip() == "visibility"
            ):
                continue
            if child.text:
                child.text = self._substitute_text(child.text, context, item)
            if child.tail:
                child.tail = self._substitute_text(child.tail, context, item)
            for attr, value in list(child.attrib.items()):
                child.set(attr, self._substitute_text(value, context, item))
            self._substitute_raw_controls(child, context, item)

    def _resolve_raw_visibility(
        self,
        elem: ET.Element,
        items: list[tuple[MenuItem, Menu, int]],
    ) -> None:
        """Replace <skinshortcuts>visibility markers with OR'd conditions."""
        if elem.tag == "skinshortcuts" and elem.text and elem.text.strip() == "visibility":
            parts = [
                f"String.IsEqual(Container({menu.container})."
                f"ListItem.Property(name),{item.name})"
                for item, menu, _idx in items
            ]
            elem.tag = "visible"
            elem.text = " | ".join(parts) if parts else "false"
            return
        for child in elem:
            self._resolve_raw_visibility(child, items)

    def _build_template_into(
        self,
        template: Template,
        output: TemplateOutput,
        include: ET.Element,
        variable_map: dict[str, ET.Element],
    ) -> None:
        """Build template controls and variables for a specific output.

        Controls go into the include element.
        Variables go into the variable_map (merged by name, output at root level).

        The output's suffix is applied to all conditions and references,
        allowing one template to generate multiple includes.
        """
        for menu in self.menus:
            if template.menu and menu.name != template.menu:
                continue

            for idx, item in enumerate(menu.items, start=1):
                if item.disabled:
                    continue

                if not self._check_conditions(template.conditions, item, output.suffix):
                    continue

                if not self._has_required_submenus(template, item):
                    continue

                context = self._build_context(template, output, item, idx, menu)

                if template.controls is not None:
                    controls = self._process_controls(
                        template.controls, context, item, menu, variable_map, output.suffix
                    )
                    if controls is not None:
                        for child in controls:
                            include.append(child)

                for var_def in template.variables:
                    var_elem = self._build_variable(var_def, context, item)
                    if var_elem is not None:
                        self._add_variable(var_elem, variable_map)

                for group_ref in template.variable_groups:
                    effective_suffix = self._combine_suffixes(output.suffix, group_ref.suffix)
                    self._build_variable_group(
                        group_ref, context, item, variable_map, effective_suffix
                    )

    def _combine_suffixes(self, base_suffix: str, ref_suffix: str) -> str:
        """Combine output suffix with reference suffix.

        If ref already has a suffix, use it (explicit overrides output default).
        Otherwise, use the base output suffix.
        """
        return ref_suffix if ref_suffix else base_suffix

    def _build_context(
        self,
        template: Template,
        output: TemplateOutput,
        item: MenuItem,
        idx: int,
        menu: Menu,
    ) -> dict[str, str]:
        """Build property context for a menu item.

        The output's suffix is applied to all property/preset/variableGroup
        references, allowing one template to serve multiple widget slots.
        """
        context: dict[str, str] = {**menu.defaults.properties, **item.properties}

        context["index"] = str(idx)
        context["name"] = item.name
        context["menu"] = menu.name
        context["idprefix"] = output.id_prefix
        context["id"] = f"{output.id_prefix}{idx}" if output.id_prefix else str(idx)
        context["suffix"] = output.suffix or ""

        context["label"] = item.label
        context["label2"] = item.label2
        context["icon"] = item.icon
        context["visible"] = item.visible
        context["action"] = item.action
        context["path"] = extract_path_from_action(item.action) if item.action else ""

        context["submenuVisibility"] = item.name

        self._apply_fallbacks(item, context)

        # First match wins for same-named properties
        resolved_props: set[str] = set()
        for prop in template.properties:
            if prop.name in resolved_props:
                continue  # Already set by earlier match in this template
            value = self._resolve_property(prop, item, context, output.suffix)
            if value is not None:
                context[prop.name] = value
                resolved_props.add(prop.name)

        for var in template.vars:
            value = self._resolve_var(var, item, context, output.suffix)
            if value is not None:
                context[var.name] = value

        for ref in template.preset_refs:
            effective_suffix = self._combine_suffixes(output.suffix, ref.suffix)
            condition = ref.condition
            if condition:
                condition = self._expand_expressions(condition)
                if effective_suffix:
                    condition = self._apply_suffix_to_condition(condition, effective_suffix)
                if not self._eval_condition(condition, item, context):
                    continue
            self._apply_preset(ref, item, context, effective_suffix)

        for ref in template.preset_group_refs:
            effective_suffix = self._combine_suffixes(output.suffix, ref.suffix)
            condition = ref.condition
            if condition:
                condition = self._expand_expressions(condition)
                if effective_suffix:
                    condition = self._apply_suffix_to_condition(condition, effective_suffix)
                if not self._eval_condition(condition, item, context):
                    continue
            self._apply_preset_group(ref, item, context, effective_suffix)

        for ref in template.property_groups:
            effective_suffix = self._combine_suffixes(output.suffix, ref.suffix)
            condition = ref.condition
            if condition:
                condition = self._expand_expressions(condition)
                if effective_suffix:
                    condition = self._apply_suffix_to_condition(condition, effective_suffix)
                if not self._eval_condition(condition, item, context):
                    continue
            prop_group = self.schema.get_property_group(ref.name)
            if prop_group:
                self._apply_property_group(prop_group, item, context, effective_suffix)

        return context

    def _build_variable(
        self,
        var_def: VariableDefinition,
        context: dict[str, str],
        item: MenuItem,
        parent_context: dict[str, str] | None = None,
        parent_item: MenuItem | None = None,
    ) -> ET.Element | None:
        """Build a Kodi <variable> element from a variable definition.

        Checks the variable's condition, substitutes $PROPERTY[...] placeholders.
        When parent context/item are supplied (items-template scope), $PARENT[...]
        and $MATH[...] also resolve in the output name and content.
        """
        if var_def.condition:
            condition = self._expand_expressions(var_def.condition)
            if not self._eval_condition(condition, item, context):
                return None

        if var_def.content is None:
            return None
        var_elem = copy.deepcopy(var_def.content)

        raw_name = var_def.output or var_elem.get("name") or var_def.name
        if parent_item is not None:
            output_name = self._substitute_text(
                raw_name, context, item, None, parent_context, parent_item
            )
        else:
            output_name = self._substitute_property_refs(raw_name, item, context)

        var_elem.set("name", output_name)
        # output/condition are build-time directives; drop them so they don't leak into Kodi XML
        if "output" in var_elem.attrib:
            del var_elem.attrib["output"]
        if "condition" in var_elem.attrib:
            del var_elem.attrib["condition"]
        self._expand_iterate_values(var_elem, item, context)
        self._substitute_variable_content(
            var_elem, context, item, parent_context, parent_item
        )

        return var_elem

    def _expand_iterate_values(
        self,
        var_elem: ET.Element,
        item: MenuItem,
        context: dict[str, str],
    ) -> None:
        """Expand <value iterate="..." as="..."> into N <value> siblings.

        Numeric iterate yields slots 1..N. Identifier iterate scans item.properties
        for {id} and {id}.2..{id}.99, emitting one <value> per filled slot.
        Loop-local $PROPERTY[{as}Index] and $PROPERTY[{as}Suffix] resolve literally;
        other $PROPERTY[X] refs auto-gain the iteration's suffix.
        """
        new_children: list[ET.Element] = []
        for child in list(var_elem):
            if child.tag != "value" or "iterate" not in child.attrib:
                new_children.append(child)
                continue

            iterate_expr = child.attrib.pop("iterate")
            as_name = child.attrib.pop("as", "")
            if not as_name:
                log.warning(
                    f"<value iterate='{iterate_expr}'> is missing required 'as' "
                    "attribute; emitting value without iteration"
                )
                new_children.append(child)
                continue

            resolved = self._substitute_property_refs(iterate_expr, item, context).strip()
            suffixes = self._resolve_iterate_suffixes(resolved, item)

            for idx, suffix in enumerate(suffixes, start=1):
                expanded = copy.deepcopy(child)
                if expanded.text:
                    expanded.text = self._apply_iterate_to_text(expanded.text, suffix, idx, as_name)
                if "condition" in expanded.attrib:
                    expanded.attrib["condition"] = self._apply_iterate_to_text(
                        expanded.attrib["condition"], suffix, idx, as_name
                    )
                new_children.append(expanded)

        for old in list(var_elem):
            var_elem.remove(old)
        for new_child in new_children:
            var_elem.append(new_child)

    @staticmethod
    def _resolve_iterate_suffixes(expr: str, item: MenuItem) -> list[str]:
        """Return suffix list for an iterate expression."""
        if expr.isdigit():
            n = int(expr)
            return [""] + [f".{i}" for i in range(2, n + 1)]
        suffixes: list[str] = []
        if expr in item.properties:
            suffixes.append("")
        for i in range(2, 100):
            if f"{expr}.{i}" in item.properties:
                suffixes.append(f".{i}")
        return suffixes

    @staticmethod
    def _apply_iterate_to_text(text: str, suffix: str, index: int, as_name: str) -> str:
        """Resolve loop-locals and auto-suffix other $PROPERTY refs."""
        if not text:
            return text
        index_key = f"{as_name}Index"
        suffix_key = f"{as_name}Suffix"

        def replace(match: re.Match) -> str:
            name = match.group(1)
            if name == index_key:
                return str(index)
            if name == suffix_key:
                return suffix
            if name in NO_SUFFIX_PROPERTIES or not suffix:
                return match.group(0)
            return f"$PROPERTY[{name}{suffix}]"

        return _PROPERTY_PATTERN.sub(replace, text)

    def _add_variable(
        self,
        var_elem: ET.Element,
        variable_map: dict[str, ET.Element],
    ) -> None:
        """Add a variable to the map, merging if same name exists.

        If a variable with the same name already exists, append this variable's
        children to the existing one. Otherwise, add as new entry.
        """
        var_name = var_elem.get("name", "")
        if not var_name:
            return

        if var_name in variable_map:
            for child in var_elem:
                variable_map[var_name].append(child)
        else:
            variable_map[var_name] = var_elem

    def _build_variable_group(
        self,
        group_ref: VariableGroupReference,
        context: dict[str, str],
        item: MenuItem,
        variable_map: dict[str, ET.Element],
        override_suffix: str = "",
        parent_context: dict[str, str] | None = None,
        parent_item: MenuItem | None = None,
    ) -> None:
        """Build variables from a variableGroup reference.

        Looks up the group, iterates its variable references, applies suffix
        transforms, and builds each matching variable from global definitions.
        Handles nested group references recursively.

        override_suffix: If provided, overrides the group_ref's suffix.
        parent_context/parent_item: Items-template scope; enables $PARENT[...] in
        variable output and content.
        """
        if group_ref.condition:
            condition = self._expand_expressions(group_ref.condition)
            if not self._eval_condition(condition, item, context):
                return

        var_group = self.schema.get_variable_group(group_ref.name)
        if not var_group:
            return

        suffix = override_suffix if override_suffix else group_ref.suffix

        for nested_ref in var_group.group_refs:
            from ..models.template import VariableGroupReference

            nested_group_ref = VariableGroupReference(
                name=nested_ref.name, suffix=suffix, condition=""
            )
            self._build_variable_group(
                nested_group_ref, context, item, variable_map, "", parent_context, parent_item
            )

        for var_ref in var_group.references:
            condition = var_ref.condition
            if suffix and condition:
                condition = apply_suffix_transform(condition, suffix)

            if condition:
                condition = self._expand_expressions(condition)
                if not self._eval_condition(condition, item, context):
                    continue

            var_def = self.schema.get_variable_definition(var_ref.name)
            if not var_def:
                continue

            var_elem = self._build_variable(var_def, context, item, parent_context, parent_item)
            if var_elem is not None:
                self._add_variable(var_elem, variable_map)

    def _substitute_variable_content(
        self,
        elem: ET.Element,
        context: dict[str, str],
        item: MenuItem,
        parent_context: dict[str, str] | None = None,
        parent_item: MenuItem | None = None,
    ) -> None:
        """Substitute $EXP/$PROPERTY/$MATH/$IF in variable content recursively.

        $PARENT[...] also resolves when parent_item is supplied (items-template scope).
        """
        if elem.text:
            elem.text = self._substitute_text(
                elem.text, context, item, None, parent_context, parent_item
            )
        if elem.tail:
            elem.tail = self._substitute_text(
                elem.tail, context, item, None, parent_context, parent_item
            )
        for attr, value in list(elem.attrib.items()):
            elem.set(
                attr,
                self._substitute_text(value, context, item, None, parent_context, parent_item),
            )
        for child in elem:
            self._substitute_variable_content(
                child, context, item, parent_context, parent_item
            )

    def _resolve_property(
        self,
        prop: TemplateProperty,
        item: MenuItem,
        context: dict[str, str],
        suffix: str = "",
    ) -> str | None:
        """Resolve a property value.

        When suffix is provided, it's applied to condition property names.
        """
        if prop.condition:
            condition = self._expand_expressions(prop.condition)
            if suffix:
                condition = self._apply_suffix_to_condition(condition, suffix)
            if not self._eval_condition(condition, item, context):
                return None

        if prop.from_source:
            source = prop.from_source
            if suffix:
                source = apply_suffix_to_from(source, suffix)
            return self._get_from_source(source, item, context, suffix)

        value = prop.value
        if "$PROPERTY[" in value:
            value = self._substitute_property_refs(value, item, context)
        return value

    def _substitute_property_refs(
        self,
        text: str,
        item: MenuItem,
        context: dict[str, str],
    ) -> str:
        """Substitute $PROPERTY[...] in text during context building."""

        def replace_property(match: re.Match) -> str:
            name = match.group(1)
            if name in context:
                return context[name]
            if name in item.properties:
                return item.properties[name]
            return ""

        return _PROPERTY_PATTERN.sub(replace_property, text)

    def _substitute_parent_refs(
        self,
        text: str,
        parent_context: dict[str, str] | None,
        parent_item: MenuItem,
    ) -> str:
        """Substitute $PARENT[...] in text during items template processing."""

        def replace_parent(match: re.Match) -> str:
            name = match.group(1)
            if parent_context and name in parent_context:
                return parent_context[name]
            if name == "label":
                return parent_item.label
            if name == "name":
                return parent_item.name
            if name in parent_item.properties:
                return parent_item.properties[name]
            return ""

        return _PARENT_PATTERN.sub(replace_parent, text)

    def _resolve_var(
        self,
        var: TemplateVar,
        item: MenuItem,
        context: dict[str, str],
        suffix: str = "",
    ) -> str | None:
        """Resolve a var (first matching value wins).

        When suffix is provided, it's applied to condition property names.
        Substitutes $PROPERTY[...] references in the resolved value.
        """
        for val in var.values:
            if val.condition:
                condition = self._expand_expressions(val.condition)
                if suffix:
                    condition = self._apply_suffix_to_condition(condition, suffix)
                if not self._eval_condition(condition, item, context):
                    continue

            value = val.value
            if "$PROPERTY[" in value:
                value = self._substitute_property_refs(value, item, context)
            return value
        return None

    def _get_from_source(
        self,
        source: str,
        item: MenuItem,
        context: dict[str, str],
        suffix: str = "",
    ) -> str:
        """Get value from a source (built-in or item property)."""
        if source in ("index", "name", "menu", "id", "idprefix"):
            return context.get(source, "")
        if source in context:
            return context[source]
        return item.properties.get(source, "")

    def _apply_property_group(
        self,
        prop_group: PropertyGroup,
        item: MenuItem,
        context: dict[str, str],
        suffix: str = "",
    ) -> None:
        """Apply properties from a property group to context."""
        for prop in prop_group.properties:
            from_source = prop.from_source
            condition = prop.condition

            if suffix:
                if from_source:
                    from_source = apply_suffix_to_from(from_source, suffix)
                if condition:
                    condition = self._expand_expressions(condition)
                    condition = self._apply_suffix_to_condition(condition, suffix)

            modified_prop = TemplateProperty(
                name=prop.name,
                value=prop.value,
                from_source=from_source,
                condition=condition,
            )
            value = self._resolve_property(modified_prop, item, context)
            if value is not None and (from_source or prop.name not in context):
                context[prop.name] = value

        for var in prop_group.vars:
            value = self._resolve_var(var, item, context, suffix)
            if value is not None:
                context[var.name] = value

    def _apply_preset(
        self,
        ref: PresetReference,
        item: MenuItem,
        context: dict[str, str],
        override_suffix: str = "",
    ) -> None:
        """Apply preset values directly as properties.

        Evaluates preset conditions and sets all matched attributes as properties.
        Supports suffix transforms for Widget 1/2 reuse.

        The suffix is applied to CONDITIONS during evaluation, not to the preset name.
        This allows a single preset definition to be reused for Widget 1 and Widget 2
        by transforming conditions like 'widgetArt=Poster' to 'widgetArt.2=Poster'.

        override_suffix: If provided, overrides the ref's suffix.
        """
        preset = self.schema.get_preset(ref.name)
        if not preset:
            return

        suffix = override_suffix if override_suffix else ref.suffix

        for row in preset.rows:
            if row.condition:
                condition = self._expand_expressions(row.condition)
                if suffix:
                    condition = self._apply_suffix_to_condition(condition, suffix)
                if self._eval_condition(condition, item, context):
                    for attr_name, attr_value in row.values.items():
                        if attr_name not in context:
                            context[attr_name] = attr_value
                    return
            else:
                for attr_name, attr_value in row.values.items():
                    if attr_name not in context:
                        context[attr_name] = attr_value
                return

    def _apply_preset_group(
        self,
        ref: PresetGroupReference,
        item: MenuItem,
        context: dict[str, str],
        override_suffix: str = "",
    ) -> None:
        """Apply presetGroup - conditional preset selection.

        Evaluates children in document order, first matching condition wins.
        Children can be preset references or inline values.

        override_suffix: If provided, overrides the ref's suffix.
        """
        group = self.schema.get_preset_group(ref.name)
        if not group:
            return

        suffix = override_suffix if override_suffix else ref.suffix

        for child in group.children:
            if child.condition:
                condition = self._expand_expressions(child.condition)
                if suffix:
                    condition = self._apply_suffix_to_condition(condition, suffix)
                if not self._eval_condition(condition, item, context):
                    continue

            if child.preset_name:
                preset = self.schema.get_preset(child.preset_name)
                if preset:
                    values = self._get_preset_values(preset, item, context, suffix)
                    if values:
                        for attr_name, attr_value in values.items():
                            if attr_name not in context:
                                context[attr_name] = attr_value
                        return
            elif child.values:
                for attr_name, attr_value in child.values.items():
                    if attr_name not in context:
                        context[attr_name] = attr_value
                return

    def _get_preset_values(
        self,
        preset: Preset,
        item: MenuItem,
        context: dict[str, str],
        suffix: str = "",
    ) -> dict[str, str] | None:
        """Get matching values from a preset (first matching row)."""
        for row in preset.rows:
            if row.condition:
                condition = self._expand_expressions(row.condition)
                if suffix:
                    condition = self._apply_suffix_to_condition(condition, suffix)
                if self._eval_condition(condition, item, context):
                    return row.values
            else:
                return row.values
        return None

    def _apply_fallbacks(
        self,
        item: MenuItem,
        context: dict[str, str],
    ) -> None:
        """Apply property fallbacks for missing properties.

        Checks all defined fallbacks and applies values for properties
        that are not already set in the context or item properties.

        Also applies fallbacks for suffixed properties (e.g., widgetArt.2)
        by transforming conditions to use suffixed property names.
        """
        if not self.property_schema:
            return

        suffixes_in_use = {""}
        for prop_name in item.properties:
            if "." in prop_name:
                parts = prop_name.rsplit(".", 1)
                if parts[1].isdigit():
                    suffixes_in_use.add(f".{parts[1]}")

        for prop_name, fallback in self.property_schema.fallbacks.items():
            for suffix in suffixes_in_use:
                suffixed_prop = f"{prop_name}{suffix}" if suffix else prop_name

                if suffixed_prop in context or suffixed_prop in item.properties:
                    continue

                for rule in fallback.rules:
                    if rule.condition:
                        condition = rule.condition
                        if suffix:
                            condition = apply_suffix_transform(condition, suffix)
                        if self._eval_condition(condition, item, context):
                            context[suffixed_prop] = rule.value
                            break
                    else:
                        context[suffixed_prop] = rule.value
                        break

    def _apply_suffix_to_condition(self, condition: str, suffix: str) -> str:
        """Apply suffix to property names in a condition."""
        nosuffix_pattern = re.compile(r"\{NOSUFFIX:([^}]+)\}")
        preserved: list[str] = []

        def extract_nosuffix(match: re.Match) -> str:
            preserved.append(match.group(1))
            return f"__NOSUFFIX_{len(preserved) - 1}__"

        condition = nosuffix_pattern.sub(extract_nosuffix, condition)

        separators = {"=", "~", "|", "+", "[", "]", "!"}
        reserved = ("index", "name", "menu", "id", "idprefix", "suffix")

        result = []
        # After = or ~ we are consuming a value list; `|` continues the list,
        # but + [ ] ! start a new condition term with a fresh property name.
        in_value = False
        parts = re.split(r"([=~|+\[\]!])", condition)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if part in separators:
                if part in ("=", "~"):
                    in_value = True
                elif part in ("+", "[", "]", "!"):
                    in_value = False
                result.append(part)
                continue
            if part in reserved or part.startswith("__NOSUFFIX_"):
                result.append(part)
                continue
            if not in_value:
                part = f"{part}{suffix}"
            result.append(part)

        transformed = "".join(result)

        for i, content in enumerate(preserved):
            transformed = transformed.replace(f"__NOSUFFIX_{i}__", content)

        return transformed

    def _strip_nosuffix_markers(self, condition: str) -> str:
        """Strip {NOSUFFIX:...} markers, keeping only the content."""
        return re.sub(r"\{NOSUFFIX:([^}]+)\}", r"\1", condition)

    def _check_conditions(self, conditions: list[str], item: MenuItem, suffix: str = "") -> bool:
        """Check if all template conditions match.

        When suffix is provided, it's applied to property names in conditions
        (e.g., 'widgetPath' becomes 'widgetPath.2' with suffix='.2').
        """
        for cond in conditions:
            expanded = self._expand_expressions(cond)
            if suffix:
                expanded = self._apply_suffix_to_condition(expanded, suffix)
            if not self._eval_condition(expanded, item, {}):
                return False
        return True

    def _has_required_submenus(self, template: Template, item: MenuItem) -> bool:
        """Check if menu item has required submenus for template's items insertions.

        Scans template controls for <skinshortcuts insert="X"/> elements.
        Returns True if no insertions required, or if any referenced submenu has items.
        """
        if template.controls is None:
            return True

        insert_names = self._find_insert_names(template.controls)
        if not insert_names:
            return True

        for insert_name in insert_names:
            items_def = self.schema.get_items_template(insert_name)
            if not items_def:
                continue

            source = items_def.get_source()
            submenu_id = f"{item.name}.{source}"
            submenu = self._menu_map.get(submenu_id)

            if submenu and submenu.items:
                return True

        return False

    def _find_insert_names(self, elem: ET.Element) -> set[str]:
        """Find all skinshortcuts insert names in an element tree."""
        names: set[str] = set()

        for child in elem.iter():
            if child.tag == "skinshortcuts":
                insert_attr = child.get("insert")
                if insert_attr:
                    names.add(insert_attr)

        return names

    def _eval_condition(
        self,
        condition: str,
        item: MenuItem,
        context: dict[str, str],
    ) -> bool:
        """Evaluate a condition against a menu item.

        Uses the shared evaluate_condition from loaders/property.py.
        Adds expression expansion ($EXP[name]) before evaluation.
        """
        condition = self._expand_expressions(condition)
        condition = self._strip_nosuffix_markers(condition)

        properties = {**item.properties, **context}

        return evaluate_condition(condition, properties)

    def _expand_expressions(self, condition: str) -> str:
        """Expand $EXP[name] references in a condition.

        For nosuffix=True expressions, wraps the value in {NOSUFFIX:...} markers
        which _apply_suffix_to_condition will preserve unchanged.
        """

        def replace_exp(match: re.Match) -> str:
            name = match.group(1)
            expr = self.schema.get_expression(name)
            if expr:
                expanded = self._expand_expressions(expr.value)
                if expr.nosuffix:
                    return f"{{NOSUFFIX:{expanded}}}"
                return expanded
            return match.group(0)

        return _EXP_PATTERN.sub(replace_exp, condition)

    def _process_controls(
        self,
        controls: ET.Element,
        context: dict[str, str],
        item: MenuItem,
        menu: Menu,
        variable_map: dict[str, ET.Element] | None = None,
        output_suffix: str = "",
    ) -> ET.Element | None:
        """Process controls XML, applying substitutions."""
        result = copy.deepcopy(controls)
        self._process_element(result, context, item, menu, variable_map, output_suffix)
        self._remove_empty_elements(result)

        return result

    def _remove_empty_elements(self, elem: ET.Element) -> None:
        """Remove leaf elements with no text content and no attributes."""
        children_to_remove = []
        for child in elem:
            self._remove_empty_elements(child)
            if len(child) == 0 and not child.text and not child.attrib:
                children_to_remove.append(child)
        for child in children_to_remove:
            elem.remove(child)

    def _process_element(
        self,
        elem: ET.Element,
        context: dict[str, str],
        item: MenuItem,
        menu: Menu,
        variable_map: dict[str, ET.Element] | None = None,
        output_suffix: str = "",
    ) -> None:
        """Recursively process an element, applying substitutions."""
        if elem.tag == "skinshortcuts":
            if elem.text and elem.text.strip() == "visibility":
                if menu.container:
                    elem.tag = "visible"
                    elem.text = (
                        f"String.IsEqual(Container({menu.container})."
                        f"ListItem.Property(name),{item.name})"
                    )
                else:
                    log.warning(
                        f"<skinshortcuts>visibility in template for menu "
                        f"'{menu.name}' but menu has no container attribute"
                    )
            elif elem.text and elem.text.strip() == "onclick":
                elem.set("_skinshortcuts_onclick", "true")
                elem.text = ""
            include_name = elem.get("include")
            if include_name:
                condition = elem.get("condition")
                if condition and not self._eval_condition(condition, item, context):
                    elem.set("_skinshortcuts_remove", "true")
                    elem.attrib.pop("include", None)
                    elem.attrib.pop("condition", None)
                    elem.attrib.pop("wrap", None)
                    return

                include_def = self.schema.get_include(include_name)
                if include_def and include_def.controls is not None:
                    elem.set("_skinshortcuts_include", include_name)
                    wrap_attr = elem.get("wrap") or ""
                    wrap = wrap_attr.lower() == "true"
                    if wrap:
                        elem.set("_skinshortcuts_wrap", "true")
                    elem.attrib.pop("include", None)
                    elem.attrib.pop("condition", None)
                    elem.attrib.pop("wrap", None)

            insert_name = elem.get("insert")
            if insert_name:
                elem.set("_skinshortcuts_insert", insert_name)
                elem.attrib.pop("insert", None)
                return

        if elem.text:
            elem.text = self._substitute_text(elem.text, context, item, menu)
        if elem.tail:
            elem.tail = self._substitute_text(elem.tail, context, item, menu)
        for attr, value in list(elem.attrib.items()):
            elem.set(attr, self._substitute_text(value, context, item, menu))

        self._handle_include_substitution(elem)

        children_to_remove = []
        for child in elem:
            self._process_element(child, context, item, menu, variable_map, output_suffix)
            if child.get("_skinshortcuts_remove"):
                children_to_remove.append(child)

        self._handle_skinshortcuts_include(
            elem, context, item, menu, variable_map, output_suffix
        )
        self._handle_skinshortcuts_items(
            elem, context, item, menu, variable_map, output_suffix
        )
        self._handle_skinshortcuts_onclick(elem, item, menu)

        for child in children_to_remove:
            elem.remove(child)

    def _handle_include_substitution(self, elem: ET.Element) -> None:
        """Convert $INCLUDE[...] in element text to <include> child elements.

        When element text contains $INCLUDE[name], converts it to a Kodi
        <include>name</include> child element.
        """
        if elem.text:
            match = _INCLUDE_PATTERN.search(elem.text)
            if match:
                include_name = match.group(1)
                include_elem = ET.Element("include")
                include_elem.text = include_name
                include_elem.tail = elem.text[match.end() :]
                elem.text = elem.text[: match.start()]
                elem.insert(0, include_elem)

    def _handle_skinshortcuts_include(
        self,
        elem: ET.Element,
        context: dict[str, str],
        item: MenuItem,
        menu: Menu,
        variable_map: dict[str, ET.Element] | None = None,
        output_suffix: str = "",
    ) -> None:
        """Handle <skinshortcuts include="..."/> element replacements.

        Finds children marked with _skinshortcuts_include attribute and replaces
        them with the expanded include contents.

        If wrap="true" was specified, outputs as a Kodi <include> element.
        Otherwise, unwraps and inserts the include's children directly.
        """
        children_to_replace = []
        for i, child in enumerate(elem):
            include_name = child.get("_skinshortcuts_include")
            if include_name:
                wrap = child.get("_skinshortcuts_wrap") == "true"
                children_to_replace.append((i, child, include_name, wrap))

        for i, child, include_name, wrap in reversed(children_to_replace):
            include_def = self.schema.get_include(include_name)
            if include_def and include_def.controls is not None:
                expanded = self._process_controls(
                    include_def.controls, context, item, menu, variable_map, output_suffix
                )
                if expanded is not None:
                    tail = child.tail
                    elem.remove(child)

                    if wrap:
                        include_elem = ET.Element("include")
                        include_elem.set("name", include_name)
                        for inc_child in list(expanded):
                            include_elem.append(inc_child)
                        include_elem.tail = tail
                        elem.insert(i, include_elem)
                    else:
                        for j, inc_child in enumerate(list(expanded)):
                            elem.insert(i + j, inc_child)
                        if tail and len(expanded) > 0:
                            last_child = elem[i + len(expanded) - 1]
                            last_child.tail = (last_child.tail or "") + tail
            else:
                elem.remove(child)

    def _handle_skinshortcuts_items(
        self,
        elem: ET.Element,
        context: dict[str, str],
        item: MenuItem,
        _menu: Menu,
        variable_map: dict[str, ET.Element] | None = None,
        output_suffix: str = "",
    ) -> None:
        """Handle <skinshortcuts insert="X" /> submenu iteration.

        Finds children marked with _skinshortcuts_insert attribute, looks up
        the matching ItemsDefinition, and expands by iterating over submenu items.
        The submenu is looked up as {parent_item.name}.{items_def.source}.

        $PROPERTY[...] within the items controls references submenu item properties.
        $PARENT[...] references parent menu item properties.
        """
        children_to_replace: list[tuple[int, ET.Element, str]] = []
        for i, child in enumerate(elem):
            insert_name = child.get("_skinshortcuts_insert")
            if insert_name:
                children_to_replace.append((i, child, insert_name))

        for i, child, insert_name in reversed(children_to_replace):
            items_def = self.schema.get_items_template(insert_name)
            if not items_def:
                log.debug(f"Items definition '{insert_name}' not found")
                elem.remove(child)
                continue

            if items_def.condition and not self._eval_condition(
                items_def.condition, item, context
            ):
                elem.remove(child)
                continue

            source = items_def.get_source()
            submenu_id = f"{item.name}.{source}"
            submenu = self._menu_map.get(submenu_id)

            if not submenu:
                log.debug(f"Submenu '{submenu_id}' not found for items iteration")
                elem.remove(child)
                continue
            if not submenu.items:
                log.debug(f"Submenu '{submenu_id}' has no items")
                elem.remove(child)
                continue

            if items_def.controls is None:
                elem.remove(child)
                continue

            output_elems = list(items_def.controls)

            expanded_controls: list[ET.Element] = []
            for sub_idx, sub_item in enumerate(submenu.items, start=1):
                if sub_item.disabled:
                    continue

                if items_def.filter and not self._eval_condition(
                    items_def.filter, sub_item, {}
                ):
                    continue

                sub_context = self._build_items_context(sub_item, sub_idx, submenu)

                self._apply_items_transformations_from_definition(
                    sub_context, sub_item, items_def, context, item
                )

                if variable_map is not None:
                    for group_ref in items_def.variable_groups:
                        effective_suffix = self._combine_suffixes(output_suffix, group_ref.suffix)
                        self._build_variable_group(
                            group_ref,
                            sub_context,
                            sub_item,
                            variable_map,
                            effective_suffix,
                            parent_context=context,
                            parent_item=item,
                        )

                for out_elem in output_elems:
                    cloned = copy.deepcopy(out_elem)
                    self._process_items_element(
                        cloned, sub_context, context, sub_item, item
                    )
                    expanded_controls.append(cloned)

            tail = child.tail
            elem.remove(child)
            for j, ctrl in enumerate(expanded_controls):
                elem.insert(i + j, ctrl)
            if tail and expanded_controls:
                last = expanded_controls[-1]
                last.tail = (last.tail or "") + tail

    def _handle_skinshortcuts_onclick(
        self,
        elem: ET.Element,
        item: MenuItem,
        menu: Menu,
    ) -> None:
        """Handle <skinshortcuts>onclick</skinshortcuts> element replacement.

        Finds children marked with _skinshortcuts_onclick attribute and replaces
        them with onclick elements from the menu item's actions.

        Actions are ordered: before defaults -> conditional -> unconditional -> after defaults.
        Each onclick element preserves its condition attribute if present.
        """
        children_to_replace: list[tuple[int, ET.Element]] = []
        for i, child in enumerate(elem):
            if child.get("_skinshortcuts_onclick"):
                children_to_replace.append((i, child))

        for i, child in reversed(children_to_replace):
            before_actions = [a for a in menu.defaults.actions if a.when == "before"]
            after_actions = [a for a in menu.defaults.actions if a.when == "after"]
            conditional = [a for a in item.actions if a.condition]
            unconditional = [a for a in item.actions if not a.condition]

            all_actions = before_actions + conditional + unconditional + after_actions

            tail = child.tail
            elem.remove(child)

            for j, act in enumerate(all_actions):
                onclick = ET.Element("onclick")
                onclick.text = act.action
                if act.condition:
                    onclick.set("condition", act.condition)
                elem.insert(i + j, onclick)

            if tail and all_actions:
                last_onclick = elem[i + len(all_actions) - 1]
                last_onclick.tail = (last_onclick.tail or "") + tail

    def _apply_items_transformations_from_definition(
        self,
        sub_context: dict[str, str],
        sub_item: MenuItem,
        items_def: ItemsDefinition,
        parent_context: dict[str, str] | None = None,
        parent_item: MenuItem | None = None,
    ) -> None:
        """Apply property transformations from an ItemsDefinition."""
        resolved_props: set[str] = set()
        for prop in items_def.properties:
            if prop.name in resolved_props:
                continue
            value = self._resolve_property(prop, sub_item, sub_context, "")
            if value is not None:
                if "$PARENT[" in value and parent_item is not None:
                    value = self._substitute_parent_refs(value, parent_context, parent_item)
                sub_context[prop.name] = value
                resolved_props.add(prop.name)

        for var in items_def.vars:
            value = self._resolve_var(var, sub_item, sub_context, "")
            if value is not None:
                if "$PARENT[" in value and parent_item is not None:
                    value = self._substitute_parent_refs(value, parent_context, parent_item)
                sub_context[var.name] = value

        for ref in items_def.preset_refs:
            if ref.condition and not self._eval_condition(ref.condition, sub_item, sub_context):
                continue
            self._apply_preset(ref, sub_item, sub_context, "")

        for ref in items_def.property_groups:
            if ref.condition and not self._eval_condition(ref.condition, sub_item, sub_context):
                continue
            group = self.schema.get_property_group(ref.name)
            if group:
                self._apply_property_group(group, sub_item, sub_context, "")

    def _build_items_context(
        self,
        sub_item: MenuItem,
        sub_idx: int,
        submenu: Menu,
    ) -> dict[str, str]:
        """Build property context for a submenu item.

        Context contains submenu item properties plus built-ins.
        Parent properties are accessed via $PARENT[...], not included in context.
        """
        context: dict[str, str] = {**submenu.defaults.properties, **sub_item.properties}
        context["index"] = str(sub_idx)
        context["name"] = sub_item.name
        context["menu"] = submenu.name

        context["label"] = sub_item.label
        context["label2"] = sub_item.label2
        context["icon"] = sub_item.icon
        context["visible"] = sub_item.visible
        context["action"] = sub_item.action
        context["path"] = extract_path_from_action(sub_item.action) if sub_item.action else ""

        self._apply_fallbacks(sub_item, context)

        return context

    def _process_items_element(
        self,
        elem: ET.Element,
        sub_context: dict[str, str],
        parent_context: dict[str, str],
        sub_item: MenuItem,
        parent_item: MenuItem | None,
    ) -> None:
        """Process an element within items iteration, substituting both contexts.

        $PROPERTY[...] -> submenu item properties (sub_context)
        $PARENT[...] -> parent item properties (parent_context)
        """
        if elem.text:
            elem.text = self._substitute_text(
                elem.text, sub_context, sub_item,
                parent_context=parent_context, parent_item=parent_item
            )
        if elem.tail:
            elem.tail = self._substitute_text(
                elem.tail, sub_context, sub_item,
                parent_context=parent_context, parent_item=parent_item
            )
        for attr, value in list(elem.attrib.items()):
            elem.set(
                attr,
                self._substitute_text(
                    value, sub_context, sub_item,
                    parent_context=parent_context, parent_item=parent_item
                ),
            )

        self._handle_include_substitution(elem)

        for child in elem:
            self._process_items_element(
                child, sub_context, parent_context, sub_item, parent_item
            )

    def _substitute_text(
        self,
        text: str,
        context: dict[str, str],
        item: MenuItem,
        _menu: Menu | None = None,
        parent_context: dict[str, str] | None = None,
        parent_item: MenuItem | None = None,
    ) -> str:
        """Substitute $EXP, $PROPERTY, $MATH, and $IF expressions in text.

        Order of operations:
        1. $EXP[...] - expression references
        2. $PARENT[...] - parent item properties (if parent_item provided)
        3. $PROPERTY[...] - property substitution (so refs in $MATH get resolved)
        4. $MATH[...] - arithmetic expressions
        5. $IF[...] - conditional expressions

        Args:
            text: Text to process
            context: Property context for $PROPERTY substitution
            item: Menu item for property fallback
            _menu: Unused, kept for compatibility
            parent_context: Optional parent context for $PARENT substitution
            parent_item: Optional parent item for $PARENT substitution
        """
        if "$EXP[" in text:
            text = self._expand_expressions(text)
            text = self._strip_nosuffix_markers(text)

        if parent_item is not None:

            def replace_parent(match: re.Match) -> str:
                prop_name = match.group(1)
                if parent_context and prop_name in parent_context:
                    return parent_context[prop_name]
                if prop_name == "label":
                    return parent_item.label
                if prop_name == "name":
                    return parent_item.name
                if prop_name in parent_item.properties:
                    return parent_item.properties[prop_name]
                return ""

            text = _PARENT_PATTERN.sub(replace_parent, text)

        def replace_property(match: re.Match) -> str:
            name = match.group(1)
            if name in context:
                return context[name]
            if name in item.properties:
                return item.properties[name]
            return ""

        text = _PROPERTY_PATTERN.sub(replace_property, text)

        properties = {**item.properties, **context}
        if parent_context:
            properties = {**parent_context, **properties}
        if parent_item:
            properties = {**parent_item.properties, **properties}

        if "$MATH[" in text:
            text = process_math_expressions(text, properties)

        if "$IF[" in text:
            text = process_if_expressions(text, properties)

        return text

    def write(self, path: str, indent: bool = True) -> None:
        """Write template includes to file."""
        root = self.build()
        if indent:
            _indent_xml(root)
        tree = ET.ElementTree(root)
        tree.write(path, encoding="UTF-8", xml_declaration=True)


def _indent_xml(elem: ET.Element, level: int = 0) -> None:
    """Add indentation to XML tree."""
    indent = "\n" + "\t" * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "\t"
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
        for child in elem:
            _indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent
    elif level and (not elem.tail or not elem.tail.strip()):
        elem.tail = indent
