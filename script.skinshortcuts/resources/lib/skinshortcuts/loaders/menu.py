"""Menu loader."""

from __future__ import annotations

from pathlib import Path

from ..exceptions import MenuConfigError
from ..log import notify
from ..models.menu import (
    Action,
    Content,
    ContextMenu,
    ContextMenuButton,
    DefaultAction,
    IconOverrides,
    IconSource,
    IncludeRef,
    Input,
    Menu,
    MenuAllow,
    MenuConfig,
    MenuDefaults,
    MenuItem,
    OnCloseAction,
    Protection,
    Shortcut,
    ShortcutGroup,
    SubDialog,
    display_action,
)
from ..models.override import Override
from .base import (
    get_attr,
    get_bool,
    get_text,
    parse_content,
    parse_xml,
    report_missing,
    warn_duplicate_names,
)


def load_menus(path: str | Path) -> MenuConfig:
    """Load menu configuration from menus.xml, all but the shortcut groupings."""
    path = Path(path)
    if not path.exists():
        return MenuConfig()

    root = parse_xml(path, "menus", MenuConfigError)

    icon_sources = _parse_icons(root)
    icon_overrides = _parse_icon_overrides(root)

    menus = _parse_menus(root, str(path), icon_overrides)
    subdialogs = _parse_dialogs(root)
    action_overrides = _parse_overrides(root)
    context_menu = _parse_context_menu(root)
    submenu_path_all = _parse_submenu_path(root)

    return MenuConfig(
        menus=menus,
        icon_sources=icon_sources,
        subdialogs=subdialogs,
        action_overrides=action_overrides,
        icon_overrides=icon_overrides,
        context_menu=context_menu,
        submenu_path_all=submenu_path_all,
    )


def _parse_menus(root, path: str, icon_overrides: IconOverrides | None = None) -> list[Menu]:
    """Parse the top-level menu and submenu elements."""
    overrides = icon_overrides or IconOverrides()
    menus = []

    for elem in root.findall("menu"):
        menu = _parse_menu(elem, path, is_submenu=False, icon_overrides=overrides)
        if menu:
            menus.append(menu)

    for elem in root.findall("submenu"):
        menu = _parse_menu(elem, path, is_submenu=True, icon_overrides=overrides)
        if menu:
            menus.append(menu)

    warn_duplicate_names((m.name for m in menus), "menu", path)

    return menus


def _parse_icons(root) -> list[IconSource]:
    """Parse icon sources from <icons> element."""
    icons_elem = root.find("icons")
    if icons_elem is None:
        return []

    sources = []

    source_elems = icons_elem.findall("source")
    if source_elems:
        for source_elem in source_elems:
            label = get_attr(source_elem, "label") or ""
            path = (source_elem.text or "").strip()
            if path:
                sources.append(IconSource(
                    label=label,
                    path=path,
                    condition=get_attr(source_elem, "condition") or "",
                    visible=get_attr(source_elem, "visible") or "",
                    icon=get_attr(source_elem, "icon") or "",
                ))
    else:
        path = (icons_elem.text or "").strip()
        if path:
            sources.append(IconSource(label="", path=path))

    return sources


def _parse_context_menu(root) -> ContextMenu:
    """On/off, the controls the context action fires on, and the rows it lists; reports bad text."""
    elem = root.find("contextmenu")
    if elem is None:
        return ContextMenu()

    text = (elem.text or "").strip().lower()
    if text and text not in ("true", "false"):
        notify(
            "Context Menu Error",
            f"'{text}' is not true or false",
            f"menus.xml: <contextmenu> holds '{text}'; treated as true; write true or false",
        )

    return ContextMenu(
        enabled=text != "false",
        enable_on=_parse_enable_on(get_attr(elem, "enableOn")),
        buttons=_parse_context_buttons(elem.findall("button")),
    )


def _parse_context_buttons(rows) -> list[ContextMenuButton]:
    """The rows a skin lists, in the order written, reporting one with no numeric id."""
    buttons = []
    for child in rows:
        button_id = get_attr(child, "id")
        if not button_id.isdecimal():
            notify(
                "Context Menu Error",
                f"'{button_id}' is not a control id" if button_id else "button missing 'id'",
                f'menus.xml: <contextmenu> <button id="{button_id}"> needs a numeric id; row '
                "skipped; use the id of the dialog control",
            )
            continue

        buttons.append(ContextMenuButton(
            button_id=int(button_id),
            label=get_attr(child, "label"),
            condition=get_attr(child, "condition"),
            visible=get_attr(child, "visible"),
        ))

    return buttons


def _parse_enable_on(value: str) -> list[int]:
    """Control IDs the context action fires on, listed with commas; reports bad or missing IDs."""
    ids = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdecimal():
            notify(
                "Context Menu Error",
                f"'{part}' is not a control id",
                f'menus.xml: <contextmenu enableOn="{value}"> lists \'{part}\'; it is skipped; '
                "list numeric control ids",
            )
            continue
        ids.append(int(part))

    if value and not ids:
        notify(
            "Context Menu Error",
            "enableOn has no control id",
            f'menus.xml: <contextmenu enableOn="{value}"> has no control id; the context menu '
            "opens on every control; list numeric control ids",
        )

    return ids


def _parse_submenu_path(root) -> bool:
    """Parse <submenuPath>; True when "all" opts every widget submenu into the .N tail."""
    elem = root.find("submenuPath")
    if elem is None:
        return False
    return (elem.text or "").strip().lower() == "all"


def _parse_dialogs(root) -> list[SubDialog]:
    """Parse subdialog definitions from <dialogs> element, reporting skips and bad setFocus."""
    dialogs_elem = root.find("dialogs")
    if dialogs_elem is None:
        return []

    subdialogs = []
    for elem in dialogs_elem.findall("subdialog"):
        button_id_str = get_attr(elem, "buttonID")
        written = f'<subdialog buttonID="{button_id_str}">'
        if not button_id_str:
            report_missing("Subdialog Error", "menus.xml", elem, "buttonID", key="buttonID")
            continue
        if not button_id_str.isdecimal():
            notify(
                "Subdialog Error",
                f"'{button_id_str}' is not a control id",
                f"menus.xml: {written} is not a number; subdialog skipped; "
                "use the id of the dialog control",
            )
            continue
        button_id = int(button_id_str)

        mode = get_attr(elem, "mode") or ""
        menu = get_attr(elem, "menu") or ""
        onclose_actions = _parse_onclose(elem)

        if not mode and not menu and not onclose_actions:
            notify(
                "Subdialog Error",
                f"'{button_id}' does nothing",
                f"menus.xml: {written} has no mode, menu or <onclose>; subdialog skipped; "
                'add mode="..."',
            )
            continue

        setfocus = None
        setfocus_str = get_attr(elem, "setFocus")
        if setfocus_str.isdecimal():
            setfocus = int(setfocus_str)
        elif setfocus_str:
            notify(
                "Subdialog Error",
                f"'{setfocus_str}' is not a control id",
                f'menus.xml: <subdialog buttonID="{button_id}" setFocus="{setfocus_str}"> needs a '
                "numeric setFocus; setFocus ignored; use the id of the dialog control",
            )

        suffix = get_attr(elem, "suffix") or ""

        subdialogs.append(
            SubDialog(
                button_id=button_id,
                mode=mode,
                menu=menu,
                setfocus=setfocus,
                suffix=suffix,
                onclose=onclose_actions,
            )
        )

    return subdialogs


def _parse_onclose(subdialog_elem) -> list[OnCloseAction]:
    """Parse onclose actions from a subdialog element, reporting one with no action."""
    actions = []
    for elem in subdialog_elem.findall("onclose"):
        action = get_attr(elem, "action")
        if not action:
            report_missing("Subdialog Error", "menus.xml", elem, "action", key="action")
            continue

        actions.append(
            OnCloseAction(
                action=action,
                menu=get_attr(elem, "menu") or "",
                condition=get_attr(elem, "condition") or "",
            )
        )

    return actions


def _parse_overrides(root) -> list[Override]:
    """Parse action overrides from <overrides> element, reporting one with no replace or text."""
    overrides_elem = root.find("overrides")
    if overrides_elem is None:
        return []

    overrides = []
    for elem in overrides_elem.findall("action"):
        replace = get_attr(elem, "replace")
        action = (elem.text or "").strip()

        if not replace:
            report_missing("Override Error", "menus.xml", elem, "replace", key="replace")
        elif not action:
            notify(
                "Override Error",
                f"'{replace}' has no action",
                f'menus.xml: <action replace="{replace}"> has no text; override skipped; '
                "write the new action as its text",
            )
        else:
            overrides.append(Override(replace=replace, value=action))

    return overrides


def _parse_icon_overrides(root) -> IconOverrides:
    """Parse icon overrides from <overrides><icons>; its source is opt-in, not the root <icons>."""
    overrides_elem = root.find("overrides")
    if overrides_elem is None:
        return IconOverrides()

    icons_elem = overrides_elem.find("icons")
    if icons_elem is None:
        return IconOverrides()

    source_elem = icons_elem.find("source")
    source = (source_elem.text or "").strip() if source_elem is not None else ""
    # an expression carries its own trailing slash, its value is unknown here
    if source and not source.endswith("/") and not source.startswith("$"):
        source += "/"

    explicit: dict[str, str] = {}
    for icon_elem in icons_elem.findall("icon"):
        replace = get_attr(icon_elem, "replace")
        value = (icon_elem.text or "").strip()
        if not replace:
            report_missing("Override Error", "menus.xml", icon_elem, "replace", key="replace")
            continue
        written = f'<icon replace="{replace}">'
        if not value:
            notify(
                "Override Error",
                f"'{replace}' has no icon",
                f"menus.xml: {written} has no path; icon skipped; write the icon path as its text",
            )
        elif "://" in value or value.startswith("/"):
            explicit[replace] = value
        elif source:
            explicit[replace] = source + value
        else:
            notify(
                "Override Error",
                f"'{replace}' has a relative path",
                f"menus.xml: {written} has the relative path '{value}' and <icons> has no "
                "<source>; icon skipped; add <source> or use a full path",
            )

    return IconOverrides(source=source, explicit=explicit)


def _parse_menu(
    elem,
    path: str,
    is_submenu: bool = False,
    icon_overrides: IconOverrides | None = None,
) -> Menu | None:
    """Parse menu or submenu with items, defaults, allow rules; reports no name or a repeat item."""
    menu_name = get_attr(elem, "name")
    if not menu_name:
        report_missing("Menu Error", path, elem, "name")
        return None

    menu_type = get_attr(elem, "type") or None
    is_widget_submenu = menu_type == "widgets"
    overrides = icon_overrides or IconOverrides()

    items = []
    for item_elem in elem.findall("item"):
        item = _parse_item(item_elem, menu_name, path, is_widget_submenu, overrides)
        if item:
            items.append(item)
    warn_duplicate_names((i.name for i in items), "item", path, f"menu '{menu_name}'")

    defaults = _parse_defaults(elem.find("defaults"))
    allow = _parse_allow(elem.find("allow"))
    container = get_attr(elem, "container") or None
    controltype = get_attr(elem, "controlType") or ""
    icons = get_bool(elem, "icons", True)
    startid_str = get_attr(elem, "id") or ""
    startid = int(startid_str) if startid_str.isdecimal() else 1
    template_only = get_attr(elem, "templateOnly") or ""
    build = (get_attr(elem, "build") or "true").lower()
    action = get_attr(elem, "action") or ""
    standalone = get_bool(elem, "standalone", True)
    submenu_path = get_attr(elem, "submenuPath").lower()

    return Menu(
        name=menu_name,
        items=items,
        defaults=defaults,
        allow=allow,
        container=container,
        is_submenu=is_submenu,
        menu_type=menu_type,
        controltype=controltype,
        icons=icons,
        startid=startid,
        template_only=template_only,
        build=build,
        action=action,
        standalone=standalone,
        submenu_path=submenu_path,
    )


def _parse_item(
    elem,
    menu_name: str,
    path: str,
    is_widget_submenu: bool = False,
    icon_overrides: IconOverrides | None = None,
) -> MenuItem | None:
    """Parse an item element: label, icon, actions, includes, properties and protection."""
    overrides = icon_overrides or IconOverrides()
    item_name = get_attr(elem, "name")
    label = get_text(elem, "label")
    scope = f"menu '{menu_name}'"
    if not item_name:
        report_missing("Menu Error", path, elem, "name", scope=scope)
        return None
    if not label:
        report_missing("Menu Error", path, elem, "<label>", scope=scope)
        return None

    actions = []
    includes = []
    seen_action = False

    for child in elem:
        if child.tag == "action" and child.text:
            seen_action = True
            actions.append(Action(
                action=child.text.strip(),
                condition=get_attr(child, "condition") or "",
            ))
        elif child.tag == "skinshortcuts":
            include_name = get_attr(child, "include")
            if include_name:
                includes.append(IncludeRef(
                    name=include_name,
                    condition=get_attr(child, "condition") or "",
                    after_onclick=seen_action,
                ))

    properties = {}
    for prop_elem in elem.findall("property"):
        prop_name = get_attr(prop_elem, "name")
        if prop_name and prop_elem.text:
            properties[prop_name] = prop_elem.text.strip()

    if is_widget_submenu and "widgetLabel" not in properties:
        properties["widgetLabel"] = label

    visible_parts = [v.text.strip() for v in elem.findall("visible") if v.text]
    visible = " + ".join(visible_parts) if visible_parts else ""

    widget_attr = get_attr(elem, "widget")
    if widget_attr:
        properties["widget"] = widget_attr
    background_attr = get_attr(elem, "background")
    if background_attr:
        properties["background"] = background_attr

    protection = None
    protect_elem = elem.find("protect")
    if protect_elem is not None:
        protection = Protection(
            type=get_attr(protect_elem, "type", "all"),
            heading=get_attr(protect_elem, "heading", ""),
            message=get_attr(protect_elem, "message", ""),
        )

    dialog_visible = get_attr(elem, "visible") or ""

    return MenuItem(
        name=item_name,
        label=label,
        actions=actions,
        label2=get_text(elem, "label2"),
        icon=get_text(elem, "icon") or overrides.get("DefaultShortcut.png", "DefaultShortcut.png"),
        thumb=get_text(elem, "thumb"),
        visible=visible,
        dialog_visible=dialog_visible,
        disabled=get_text(elem, "disabled", "false").lower() == "true",
        required=get_bool(elem, "required"),
        protection=protection,
        properties=properties,
        submenu=get_attr(elem, "submenu"),
        original_action=display_action(actions),
        includes=includes,
    )


def _parse_defaults(elem) -> MenuDefaults:
    """Parse a defaults element: properties, actions and includes every item in the menu gets."""
    if elem is None:
        return MenuDefaults()

    properties = {}
    for prop_elem in elem.findall("property"):
        name = get_attr(prop_elem, "name")
        if name and prop_elem.text:
            properties[name] = prop_elem.text.strip()

    widget_attr = get_attr(elem, "widget")
    if widget_attr:
        properties["widget"] = widget_attr
    background_attr = get_attr(elem, "background")
    if background_attr:
        properties["background"] = background_attr

    actions = []
    includes = []
    seen_action = False

    for child in elem:
        if child.tag == "action" and child.text:
            seen_action = True
            actions.append(DefaultAction(
                action=child.text.strip(),
                when=get_attr(child, "when") or "before",
                condition=get_attr(child, "condition") or "",
            ))
        elif child.tag == "skinshortcuts":
            include_name = get_attr(child, "include")
            if include_name:
                includes.append(IncludeRef(
                    name=include_name,
                    condition=get_attr(child, "condition") or "",
                    after_onclick=seen_action,
                ))

    return MenuDefaults(
        properties=properties,
        actions=actions,
        includes=includes,
    )


def _parse_allow(elem) -> MenuAllow:
    """Parse an allow element: which features the menu lets the user edit."""
    if elem is None:
        return MenuAllow()

    return MenuAllow(
        widgets=get_bool(elem, "widgets", True),
        backgrounds=get_bool(elem, "backgrounds", True),
        submenus=get_bool(elem, "submenus", True),
    )


def load_groupings(
    path: str | Path, menu_id: str = ""
) -> list[Shortcut | ShortcutGroup | Content | Input]:
    """Load shortcut groupings for a menu from menus.xml, with the skin's icon overrides applied."""
    path = Path(path)
    if not path.exists():
        return []

    root = parse_xml(path, "menus", MenuConfigError)
    return _parse_shortcut_groupings(root, str(path), menu_id, _parse_icon_overrides(root))


def _parse_shortcut_groupings(
    root,
    path: str,
    menu_id: str = "",
    icon_overrides: IconOverrides | None = None,
) -> list[Shortcut | ShortcutGroup | Content | Input]:
    """Parse the groupings a menu gets: its own <groupings menu>, else the default one."""
    overrides = icon_overrides or IconOverrides()
    default_elem = None
    menu_elem = None

    for elem in root.findall("groupings"):
        menu_attr = get_attr(elem, "menu") or ""
        if menu_attr and menu_id and menu_attr == menu_id:
            menu_elem = elem
            break
        if not menu_attr and default_elem is None:
            default_elem = elem

    groupings_elem = menu_elem if menu_elem is not None else default_elem
    if groupings_elem is None:
        return []

    items: list[Shortcut | ShortcutGroup | Content | Input] = []
    for child in groupings_elem:
        if child.tag == "group":
            group = _parse_shortcut_group(child, path, overrides)
            if group:
                items.append(group)
        elif child.tag == "shortcut":
            shortcut = _parse_shortcut(child, path, overrides)
            if shortcut:
                items.append(shortcut)
        elif child.tag == "content":
            content = parse_content(child, path, "Shortcut Error")
            if content:
                items.append(content)
        elif child.tag == "input":
            input_item = _parse_input(child, path, overrides)
            if input_item:
                items.append(input_item)

    return items


def _parse_shortcut_group(
    elem,
    path: str,
    icon_overrides: IconOverrides | None = None,
) -> ShortcutGroup | None:
    """Parse a shortcut group element (supports nested groups, shortcuts, content, and inputs)."""
    overrides = icon_overrides or IconOverrides()
    group_name = get_attr(elem, "name")
    label = get_attr(elem, "label")
    flat = get_bool(elem, "flat")

    if not group_name:
        report_missing("Shortcut Group Error", path, elem, "name")
        return None
    if not label and not flat:
        notify(
            "Shortcut Group Error",
            f"'{group_name}' missing label",
            f"{path}: <group name=\"{group_name}\"> has no label and is not flat; group "
            "skipped; add label=\"...\" or flat=\"true\"",
        )
        return None

    condition = get_attr(elem, "condition") or ""
    icon = get_attr(elem, "icon") or ""
    items: list[Shortcut | ShortcutGroup | Content | Input] = []

    for child in elem:
        if child.tag == "shortcut":
            shortcut = _parse_shortcut(child, path, overrides)
            if shortcut:
                items.append(shortcut)
        elif child.tag == "group":
            nested = _parse_shortcut_group(child, path, overrides)
            if nested:
                items.append(nested)
        elif child.tag == "content":
            content = parse_content(child, path, "Shortcut Error")
            if content:
                items.append(content)
        elif child.tag == "input":
            input_item = _parse_input(child, path, overrides)
            if input_item:
                items.append(input_item)

    visible = get_attr(elem, "visible") or ""
    return ShortcutGroup(
        name=group_name,
        label=label,
        condition=condition,
        visible=visible,
        icon=icon,
        items=items,
        flat=flat,
    )


def _parse_shortcut(
    elem,
    path: str,
    icon_overrides: IconOverrides | None = None,
) -> Shortcut | None:
    """Parse a shortcut element, reporting one with no name, label, or action or browse path."""
    overrides = icon_overrides or IconOverrides()
    shortcut_name = get_attr(elem, "name")
    label = get_attr(elem, "label")
    if not shortcut_name or not label:
        report_missing("Shortcut Error", path, elem, "label" if shortcut_name else "name")
        return None

    actions = []
    primary_action = ""
    for a in elem.findall("action"):
        action_text = (a.text or "").strip()
        if not action_text:
            continue
        actions.append(Action(action=action_text, condition=get_attr(a, "condition") or ""))
        if get_bool(a, "primary"):
            primary_action = action_text

    shortcut_path = get_text(elem, "path") or ""
    browse = get_attr(elem, "browse") or ""

    if not actions and not (browse and shortcut_path):
        notify(
            "Shortcut Error",
            f"'{shortcut_name}' has no action",
            f'{path}: <shortcut name="{shortcut_name}"> has no <action> and no browse <path>; '
            "shortcut skipped; add an <action>",
        )
        return None

    visible_parts = [v.text.strip() for v in elem.findall("visible") if v.text]
    item_visible = " + ".join(visible_parts) if visible_parts else ""

    return Shortcut(
        name=shortcut_name,
        label=label,
        actions=actions,
        primary_action=primary_action,
        path=shortcut_path,
        browse=browse,
        type=get_attr(elem, "type") or "",
        icon=get_attr(elem, "icon") or overrides.get("DefaultShortcut.png", "DefaultShortcut.png"),
        condition=get_attr(elem, "condition") or "",
        visible=get_attr(elem, "visible") or "",
        item_visible=item_visible,
    )


def _parse_input(elem, path: str, icon_overrides: IconOverrides | None = None) -> Input | None:
    """Parse an input element, reporting one with no label."""
    overrides = icon_overrides or IconOverrides()
    label = get_attr(elem, "label")
    if not label:
        report_missing("Shortcut Error", path, elem, "label", key="label")
        return None

    return Input(
        label=label,
        type=get_attr(elem, "type") or "text",
        for_=get_attr(elem, "for") or "action",
        condition=get_attr(elem, "condition") or "",
        visible=get_attr(elem, "visible") or "",
        icon=get_attr(elem, "icon") or overrides.get("DefaultFile.png", "DefaultFile.png"),
    )


