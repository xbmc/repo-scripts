"""Property loader, parsing properties.xml with Kodi-style includes and suffix transforms."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from ..conditions import suffix_condition
from ..exceptions import PropertyConfigError
from ..log import notify
from ..models.property import (
    ButtonMapping,
    FallbackRule,
    IconVariant,
    PropertyFallback,
    PropertySchema,
    SchemaOption,
    SchemaProperty,
)
from .base import (
    get_attr,
    get_bool,
    keep_first,
    parse_name_overrides,
    parse_xml,
    report_missing,
)


class PropertyLoader:
    """Loads property schema from properties.xml."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._includes: dict[str, list[ET.Element]] = {}

    def load(self) -> PropertySchema:
        """Load and parse the property schema."""
        if not self.path.exists():
            return PropertySchema()

        root = parse_xml(self.path, "properties", PropertyConfigError)
        self._parse_includes(root)

        properties = {}
        for elem in root.findall("property"):
            prop = self._parse_property(elem)
            if prop:
                keep_first(properties, prop.name, prop, "property", self.path)

        fallbacks = {}
        fallbacks_elem = root.find("fallbacks")
        if fallbacks_elem is not None:
            for fb_elem in fallbacks_elem.findall("fallback"):
                fb = self._parse_fallback(fb_elem)
                if fb:
                    keep_first(fallbacks, fb.property_name, fb, "fallback", self.path)

        buttons = {}
        buttons_elem = root.find("buttons")
        if buttons_elem is not None:
            default_suffix = get_bool(buttons_elem, "suffix")
            for child in buttons_elem:
                if child.tag == "button":
                    btn = self._parse_button(child, default_suffix)
                    if btn:
                        keep_first(buttons, btn.button_id, btn, "button", self.path)
                elif child.tag == "group":
                    group_suffix = get_bool(child, "suffix", default_suffix)
                    for btn_elem in child.findall("button"):
                        btn = self._parse_button(btn_elem, group_suffix)
                        if btn:
                            keep_first(buttons, btn.button_id, btn, "button", self.path)

        self._check_rename_buttons(properties, buttons)

        return PropertySchema(
            properties=properties,
            fallbacks=fallbacks,
            buttons=buttons,
            overrides=parse_name_overrides(root, "property", self.path),
        )

    def _check_rename_buttons(
        self, properties: dict[str, SchemaProperty], buttons: dict[int, ButtonMapping]
    ) -> None:
        """Check for buttons where rename="true" is a no-op, once buttons and properties are in."""
        for button in buttons.values():
            if not button.rename:
                continue
            prop = properties.get(button.property_name)
            effective_type = button.type or (prop.type if prop else "")
            if effective_type != "widget":
                notify(
                    "Property Button Error",
                    f"'{button.button_id}' rename needs a widget",
                    f'{self.path}: <button id="{button.button_id}" rename="true"> has type '
                    f"'{effective_type or 'unset'}'; rename ignored; rename applies to "
                    'type="widget" only',
                )

    def _parse_includes(self, root: ET.Element) -> None:
        """Parse include definitions from <includes> section."""
        includes_section = root.find("includes")
        if includes_section is None:
            return
        for include_elem in includes_section.findall("include"):
            name = get_attr(include_elem, "name")
            if not name:
                report_missing("Property Error", self.path, include_elem, "name")
                continue
            keep_first(self._includes, name, list(include_elem), "property include", self.path)

    def _expand_include(self, include_elem: ET.Element) -> list[ET.Element]:
        """Expand an include to suffixed element copies, reporting one unnamed or undefined."""
        content_name = get_attr(include_elem, "content")
        suffix = include_elem.get("suffix") or ""
        if not content_name:
            report_missing("Property Error", self.path, include_elem, "content", key="content")
            return []
        if content_name not in self._includes:
            notify(
                "Property Error",
                f"include '{content_name}' not defined",
                f'{self.path}: <include content="{content_name}"> names no include in '
                "<includes>; nothing included; define the include, or correct the name",
            )
            return []
        return [
            self._copy_element_with_suffix(elem, suffix)
            for elem in self._includes[content_name]
        ]

    def _copy_element_with_suffix(self, elem: ET.Element, suffix: str) -> ET.Element:
        """Deep copy element, applying suffix transform to conditions."""
        new_elem = ET.Element(elem.tag, elem.attrib.copy())
        new_elem.text = elem.text
        new_elem.tail = elem.tail

        if suffix and "condition" in new_elem.attrib:
            new_elem.attrib["condition"] = suffix_condition(
                new_elem.attrib["condition"], suffix
            )

        for child in elem:
            new_child = self._copy_element_with_suffix(child, suffix)
            new_elem.append(new_child)

        return new_elem

    def _parse_property(self, elem: ET.Element) -> SchemaProperty | None:
        """Parse a property element, reporting one with no name."""
        name = get_attr(elem, "name")
        if not name:
            report_missing("Property Error", self.path, elem, "name")
            return None

        template_only = get_bool(elem, "templateOnly")
        prop_type = get_attr(elem, "type")

        requires = get_attr(elem, "requires")
        if not requires:
            requires_elem = elem.find("requires")
            if requires_elem is not None:
                requires = get_attr(requires_elem, "property")

        options = []
        options_elem = elem.find("options")
        if options_elem is not None:
            options = self._parse_options(options_elem)

        value = get_attr(elem, "value")

        return SchemaProperty(
            name=name,
            template_only=template_only,
            requires=requires,
            options=options,
            type=prop_type,
            value=value,
        )

    def _parse_button(
        self, elem: ET.Element, default_suffix: bool = False
    ) -> ButtonMapping | None:
        """Parse a button element, reporting one with no numeric id or no property."""
        button_id_str = get_attr(elem, "id")
        if not button_id_str:
            report_missing("Property Button Error", self.path, elem, "id", key="id")
            return None

        if not button_id_str.isdecimal():
            notify(
                "Property Button Error",
                f"'{button_id_str}' is not a control id",
                f'{self.path}: <button id="{button_id_str}"> is not a number; button skipped; '
                "use the id of the dialog control",
            )
            return None
        button_id = int(button_id_str)

        property_name = get_attr(elem, "property")
        if not property_name:
            report_missing("Property Button Error", self.path, elem, "property", key="id")
            return None

        suffix = get_bool(elem, "suffix", default_suffix)
        heading = get_attr(elem, "heading")
        show_none = get_bool(elem, "showNone", True)
        show_icons = get_bool(elem, "showIcons", True)
        prop_type = get_attr(elem, "type")
        requires = get_attr(elem, "requires")
        rename = get_bool(elem, "rename")

        return ButtonMapping(
            button_id=button_id,
            property_name=property_name,
            suffix=suffix,
            heading=heading,
            show_none=show_none,
            show_icons=show_icons,
            type=prop_type,
            requires=requires,
            rename=rename,
        )

    def _parse_options(self, options_elem: ET.Element) -> list[SchemaOption]:
        """Parse options element, expanding includes."""
        result = []

        for child in options_elem:
            if child.tag == "include":
                expanded = self._expand_include(child)
                for exp_child in expanded:
                    if exp_child.tag == "option":
                        result.append(self._parse_option(exp_child))
            elif child.tag == "option":
                result.append(self._parse_option(child))

        return result

    def _parse_option(self, elem: ET.Element) -> SchemaOption:
        """Parse an option with its property condition, Kodi visibility condition and icons."""
        value = get_attr(elem, "value")
        label = get_attr(elem, "label")
        condition = get_attr(elem, "condition")
        visible = get_attr(elem, "visible")

        icons = []
        for icon_elem in elem.findall("icon"):
            icon_path = (icon_elem.text or "").strip()
            icon_condition = get_attr(icon_elem, "condition")
            if icon_path:
                icons.append(IconVariant(path=icon_path, condition=icon_condition))

        return SchemaOption(
            value=value,
            label=label,
            condition=condition,
            visible=visible,
            icons=icons,
        )

    def _parse_fallback(self, elem: ET.Element) -> PropertyFallback | None:
        """Parse a fallback element, reporting one with no property."""
        property_name = get_attr(elem, "property")
        if not property_name:
            report_missing("Property Error", self.path, elem, "property", key="property")
            return None

        rules = []

        expanded_children = []
        for child in elem:
            if child.tag == "include":
                expanded = self._expand_include(child)
                expanded_children.extend(expanded)
            else:
                expanded_children.append(child)

        for child in expanded_children:
            if child.tag == "when":
                condition = child.get("condition", "").strip()
                value = (child.text or "").strip()
                rules.append(FallbackRule(value=value, condition=condition))
            elif child.tag == "default":
                value = (child.text or "").strip()
                rules.append(FallbackRule(value=value, condition=""))

        return PropertyFallback(property_name=property_name, rules=rules)


def load_properties(path: str | Path) -> PropertySchema:
    """Load property schema from file."""
    loader = PropertyLoader(path)
    return loader.load()
