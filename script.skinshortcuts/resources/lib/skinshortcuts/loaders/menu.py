"""Menu loader."""

from __future__ import annotations

from pathlib import Path

from ..exceptions import MenuConfigError
from ..models.menu import (
    Action,
    ActionOverride,
    Content,
    DefaultAction,
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
)
from ..log import get_logger, notify
from .base import get_attr, get_bool, get_text, parse_content, parse_xml

log = get_logger("MenuLoader")


def load_menus(path: str | Path) -> MenuConfig:
    """Load complete menu configuration from menus.xml.

    Returns:
        MenuConfig containing menus, groupings, icon sources, subdialogs, and settings.
    """
    path = Path(path)
    if not path.exists():
        return MenuConfig()

    root = parse_xml(path, "menus", MenuConfigError)
    path_str = str(path)

    icon_sources = _parse_icons(root)
    icon_overrides = _parse_icon_overrides(root, icon_sources)

    menus = _parse_menus(root, path_str, icon_overrides)
    groupings = _parse_shortcut_groupings(root, path_str, icon_overrides=icon_overrides)
    subdialogs = _parse_dialogs(root)
    action_overrides = _parse_overrides(root)
    show_context_menu = _parse_context_menu(root)
    submenu_path_all = _parse_submenu_path(root)

    return MenuConfig(
        menus=menus,
        groupings=groupings,
        icon_sources=icon_sources,
        subdialogs=subdialogs,
        action_overrides=action_overrides,
        icon_overrides=icon_overrides,
        show_context_menu=show_context_menu,
        submenu_path_all=submenu_path_all,
    )


def _parse_menus(root, path: str, icon_overrides: dict[str, str] | None = None) -> list[Menu]:
    """Parse menu and submenu elements from root."""
    overrides = icon_overrides or {}
    menus = []

    for elem in root.findall("menu"):
        menu = _parse_menu(elem, path, is_submenu=False, icon_overrides=overrides)
        menus.append(menu)

    for elem in root.findall("submenu"):
        menu = _parse_menu(elem, path, is_submenu=True, icon_overrides=overrides)
        menus.append(menu)

    return menus


def _parse_icons(root) -> list[IconSource]:
    """Parse icon sources from <icons> element.

    Supports two formats:
    1. Simple: <icons>path/to/icons/</icons>
    2. Advanced: <icons><source label="..." condition="...">path</source>...</icons>
    """
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


def _parse_context_menu(root) -> bool:
    """Parse contextmenu setting from <contextmenu> element.

    Returns True (show context menu) by default unless explicitly set to false.
    """
    elem = root.find("contextmenu")
    if elem is None:
        return True

    text = (elem.text or "").strip().lower()
    return text not in ("false", "0", "no", "")


def _parse_submenu_path(root) -> bool:
    """Parse the global submenuPath setting from <submenuPath>.

    Returns True when set to "all": emit the numbered submenuPath.N tail for
    every widget submenu. Off unless explicitly enabled.
    """
    elem = root.find("submenuPath")
    if elem is None:
        return False
    return (elem.text or "").strip().lower() == "all"


def _parse_dialogs(root) -> list[SubDialog]:
    """Parse subdialog definitions from <dialogs> element.

    Schema:
        <dialogs>
            <subdialog buttonID="800" mode="widget1" setfocus="309">
                <prompt>
                    <option label="Choose Widget" action="subdialog"/>
                    <option label="Edit Custom" action="menu" menu="{item}.customwidget"
                            condition="String.IsEqual(widgetType,custom)"/>
                    <option label="Clear"
                            onclick="RunScript(script.skinshortcuts,type=clear...)"
                            condition="String.IsEqual(widgetType,custom)"/>
                </prompt>
            </subdialog>
        </dialogs>
    """
    dialogs_elem = root.find("dialogs")
    if dialogs_elem is None:
        return []

    subdialogs = []
    for elem in dialogs_elem.findall("subdialog"):
        button_id_str = get_attr(elem, "buttonID")
        if not button_id_str:
            continue

        try:
            button_id = int(button_id_str)
        except ValueError:
            continue

        mode = get_attr(elem, "mode") or ""
        menu = get_attr(elem, "menu") or ""
        onclose_actions = _parse_onclose(elem)

        if not mode and not menu and not onclose_actions:
            continue

        setfocus = None
        setfocus_str = get_attr(elem, "setfocus")
        if setfocus_str and setfocus_str.isdigit():
            setfocus = int(setfocus_str)

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
    """Parse onclose actions from a subdialog element.

    <onclose condition="widgetType=custom" action="menu" menu="{item}.customwidget"/>
    <onclose condition="widgetType.2=custom" action="menu" menu="{item}.customwidget.2"/>
    """
    actions = []
    for elem in subdialog_elem.findall("onclose"):
        action = get_attr(elem, "action")
        if not action:
            continue

        actions.append(
            OnCloseAction(
                action=action,
                menu=get_attr(elem, "menu") or "",
                condition=get_attr(elem, "condition") or "",
            )
        )

    return actions


def _parse_overrides(root) -> list[ActionOverride]:
    """Parse action overrides from <overrides> element.

    Schema:
        <overrides>
            <action replace="ActivateWindow(favourites)">ActivateWindow(favouritesbrowser)</action>
        </overrides>
    """
    overrides_elem = root.find("overrides")
    if overrides_elem is None:
        return []

    overrides = []
    for elem in overrides_elem.findall("action"):
        replace = get_attr(elem, "replace")
        action = (elem.text or "").strip()

        if replace and action:
            overrides.append(ActionOverride(replace=replace, action=action))

    return overrides


def _check_visible(visible: str) -> bool:
    if not visible:
        return True
    try:
        import xbmc

        return bool(xbmc.getCondVisibility(visible))
    except Exception:
        return True


def _list_default_pngs(path: str) -> list[str]:
    """List Default*.png basenames in path; empty on error."""
    try:
        import xbmcvfs

        _dirs, files = xbmcvfs.listdir(path)
        return [f for f in files if f.startswith("Default") and f.endswith(".png")]
    except Exception:
        return []


def _parse_icon_overrides(root, _picker_sources: list[IconSource]) -> dict[str, str]:
    """Parse icon overrides from <overrides><icons>.

    Schema:
        <overrides>
            <icons>
                <source visible="...">special://skin/extras/icons-dark/</source>
                <source>special://skin/extras/icons-light/</source>
                <icon replace="DefaultFolder.png">files.png</icon>
            </icons>
        </overrides>

    Source is opt-in (not inherited from the root <icons>): the picker source
    is often a flat icon library, not a substitution map.
    """
    overrides_elem = root.find("overrides")
    if overrides_elem is None:
        return {}

    icons_elem = overrides_elem.find("icons")
    if icons_elem is None:
        return {}

    active_path = ""
    for source_elem in icons_elem.findall("source"):
        visible = get_attr(source_elem, "visible") or ""
        if _check_visible(visible):
            active_path = (source_elem.text or "").strip()
            break

    if active_path and not active_path.endswith("/"):
        active_path = active_path + "/"

    overrides: dict[str, str] = {}

    if active_path:
        for png in _list_default_pngs(active_path):
            overrides[png] = active_path + png

    for icon_elem in icons_elem.findall("icon"):
        replace = get_attr(icon_elem, "replace")
        value = (icon_elem.text or "").strip()
        if not replace or not value:
            log.warning("Icon override missing 'replace' attribute or value, skipping")
            continue
        if "://" in value or value.startswith("/"):
            overrides[replace] = value
        elif active_path:
            overrides[replace] = active_path + value
        else:
            log.warning(
                f"Icon override '{replace}' has relative path '{value}' but no <source> declared"
            )

    return overrides


def _parse_menu(
    elem,
    path: str,
    is_submenu: bool = False,
    icon_overrides: dict[str, str] | None = None,
) -> Menu:
    menu_name = get_attr(elem, "name")
    if not menu_name:
        raise MenuConfigError(path, "Menu missing 'name' attribute")

    menu_type = get_attr(elem, "type") or None
    is_widget_submenu = menu_type == "widgets"
    overrides = icon_overrides or {}

    items = []
    for item_elem in elem.findall("item"):
        item = _parse_item(item_elem, menu_name, path, is_widget_submenu, overrides)
        items.append(item)

    defaults = _parse_defaults(elem.find("defaults"))
    allow = _parse_allow(elem.find("allow"))
    container = get_attr(elem, "container") or None
    controltype = get_attr(elem, "controltype") or ""
    startid_str = get_attr(elem, "id") or ""
    startid = int(startid_str) if startid_str.isdigit() else 1
    template_only = get_attr(elem, "template_only") or ""
    build = get_attr(elem, "build") or "true"
    action = get_attr(elem, "action") or ""
    standalone = (get_attr(elem, "standalone") or "true").lower() != "false"
    submenu_path = get_attr(elem, "submenuPath") or ""

    return Menu(
        name=menu_name,
        items=items,
        defaults=defaults,
        allow=allow,
        container=container,
        is_submenu=is_submenu,
        menu_type=menu_type,
        controltype=controltype,
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
    icon_overrides: dict[str, str] | None = None,
) -> MenuItem:
    overrides = icon_overrides or {}
    item_name = get_attr(elem, "name")
    if not item_name:
        raise MenuConfigError(path, f"Menu '{menu_name}' has item without 'name'")

    label = get_text(elem, "label")
    if not label:
        raise MenuConfigError(path, f"Item '{item_name}' missing <label>")

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
                position = "after-onclick" if seen_action else "before-onclick"
                includes.append(IncludeRef(
                    name=include_name,
                    condition=get_attr(child, "condition") or "",
                    position=position,
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
        includes=includes,
    )


def _parse_defaults(elem) -> MenuDefaults:
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
                position = "after-onclick" if seen_action else "before-onclick"
                includes.append(IncludeRef(
                    name=include_name,
                    condition=get_attr(child, "condition") or "",
                    position=position,
                ))

    return MenuDefaults(
        properties=properties,
        actions=actions,
        includes=includes,
    )


def _parse_allow(elem) -> MenuAllow:
    if elem is None:
        return MenuAllow()

    def parse_bool(value: str | None, default: bool = True) -> bool:
        if value is None:
            return default
        return value.lower() == "true"

    return MenuAllow(
        widgets=parse_bool(get_attr(elem, "widgets")),
        backgrounds=parse_bool(get_attr(elem, "backgrounds")),
        submenus=parse_bool(get_attr(elem, "submenus")),
    )


def load_groupings(
    path: str | Path, menu_id: str = ""
) -> list[Shortcut | ShortcutGroup | Content | Input]:
    """Load shortcut groupings from menus.xml file.

    Groupings define the available shortcuts for the picker dialog.
    They are stored inside a <groupings> element within <menus>.

    If menu_id is provided, a <groupings menu="menu_id"> element takes
    priority over the default (unnamed) <groupings>.

    Note: Consider using load_menus() instead which returns full MenuConfig.

    Schema:
        <menus>
          ...
          <groupings>
            <group name="..." label="..." icon="..." condition="...">
              <shortcut name="..." label="..." icon="..." type="..." condition="...">
                <action>...</action>
              </shortcut>
              <shortcut name="..." label="..." browse="videos">
                <path>videodb://movies/genres/</path>
              </shortcut>
              <content source="playlists" target="videos"/>
              <group name="...">...</group>  <!-- nested -->
            </group>
            <!-- Top-level items also supported -->
            <shortcut name="..." label="...">...</shortcut>
            <content source="..." target="..."/>
            <input label="..." type="text" for="action" />
          </groupings>
          <groupings menu="powermenu">
            <!-- Completely replaces default groupings for this menu -->
          </groupings>
        </menus>
    """
    path = Path(path)
    if not path.exists():
        return []

    root = parse_xml(path, "menus", MenuConfigError)
    return _parse_shortcut_groupings(root, str(path), menu_id)


def _parse_shortcut_groupings(
    root,
    path: str,
    menu_id: str = "",
    icon_overrides: dict[str, str] | None = None,
) -> list[Shortcut | ShortcutGroup | Content | Input]:
    """Parse groupings from root element.

    Supports all item types at the top level: groups, shortcuts, content, and inputs.
    If menu_id is provided, a menu-specific <groupings> replaces the default.
    """
    overrides = icon_overrides or {}
    default_elem = None
    menu_elem = None

    for elem in root.findall("groupings"):
        menu_attr = get_attr(elem, "menu") or ""
        if menu_attr and menu_id and menu_attr == menu_id:
            menu_elem = elem
            break
        if not menu_attr and default_elem is None:
            default_elem = elem

    groupings_elem = menu_elem or default_elem
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
            content = parse_content(child)
            if content:
                items.append(content)
        elif child.tag == "input":
            input_item = _parse_input(child, overrides)
            if input_item:
                items.append(input_item)

    return items


def _parse_shortcut_group(
    elem,
    path: str,
    icon_overrides: dict[str, str] | None = None,
) -> ShortcutGroup | None:
    """Parse a group element (supports nested groups, shortcuts, content refs, and inputs)."""
    overrides = icon_overrides or {}
    group_name = get_attr(elem, "name")
    label = get_attr(elem, "label")
    flat = get_bool(elem, "flat")

    if not group_name:
        log.warning(f"Shortcut group in {path} missing 'name' attribute")
        notify("Shortcut Group Error", "Group missing 'name' (see log)")
        return None
    if not label and not flat:
        log.warning(f"Shortcut group '{group_name}' in {path} missing 'label' (required when not flat)")
        notify("Shortcut Group Error", f"'{group_name}' missing label")
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
            content = parse_content(child)
            if content:
                items.append(content)
        elif child.tag == "input":
            input_item = _parse_input(child, overrides)
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
    _path: str,
    icon_overrides: dict[str, str] | None = None,
) -> Shortcut | None:
    """Parse a shortcut element.

    Supports two modes:
    1. Action mode: <action>ActivateWindow(...)</action>
    2. Browse mode: browse="videos" with <path>videodb://...</path>

    The visible="..." attribute hides the shortcut from the picker. A
    <visible> child element is baked into the resulting menu item when the
    shortcut is picked. Multiple <visible> children are joined with " + ".
    """
    overrides = icon_overrides or {}
    shortcut_name = get_attr(elem, "name")
    label = get_attr(elem, "label")
    if not shortcut_name or not label:
        log.warning(f"Shortcut in {_path} missing 'name' or 'label', skipping")
        return None

    actions = []
    primary_action = ""
    for a in elem.findall("action"):
        action_text = (a.text or "").strip()
        if not action_text:
            continue
        actions.append(action_text)
        if get_bool(a, "primary"):
            primary_action = action_text

    shortcut_path = get_text(elem, "path") or ""
    browse = get_attr(elem, "browse") or ""

    # Must have either action(s) or (browse + path)
    if not actions and not (browse and shortcut_path):
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


def _parse_input(elem, icon_overrides: dict[str, str] | None = None) -> Input | None:
    """Parse an input element.

    Schema: <input label="Custom action" type="text" for="action" />
    """
    overrides = icon_overrides or {}
    label = get_attr(elem, "label")
    if not label:
        log.warning("Input element missing 'label', skipping")
        return None

    return Input(
        label=label,
        type=get_attr(elem, "type") or "text",
        for_=get_attr(elem, "for") or "action",
        condition=get_attr(elem, "condition") or "",
        visible=get_attr(elem, "visible") or "",
        icon=get_attr(elem, "icon") or overrides.get("DefaultFile.png", "DefaultFile.png"),
    )


