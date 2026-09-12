"""Move stored names a skin retired, so userdata keeps matching the skin."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .log import get_logger
from .models.background import Background, BackgroundConfig, BackgroundGroup
from .models.override import Override
from .models.property import PropertySchema
from .models.widget import Widget, WidgetConfig, WidgetGroup
from .userdata import MenuItemOverride, UserData

log = get_logger("Migrations")

WIDGET_SIBLINGS = ("Label", "Path", "Type", "Target", "Source")
BACKGROUND_SIBLINGS = ("Label", "Path", "Type", "PlaylistType")
# baked onto a widget the user added, never derived back, so not siblings to drop
WIDGET_EXTRAS = ("Limit", "SortBy", "SortOrder")

# keys the widget and background machinery writes; renaming one strips a user's stored pick
RESERVED = (
    {"widget", "background", "customWidget"}
    | {f"widget{part}" for part in WIDGET_SIBLINGS + WIDGET_EXTRAS}
    | {f"background{part}" for part in BACKGROUND_SIBLINGS}
)

MAX_PASSES = 5


def apply_overrides(
    userdata: UserData,
    property_schema: PropertySchema,
    widgets: WidgetConfig,
    backgrounds: BackgroundConfig,
) -> int:
    """Rewrite userdata for every retired name, returning the number of changes."""
    known_properties = set(property_schema.properties) | {
        b.property_name for b in property_schema.buttons.values() if b.property_name
    }
    known_widgets = {
        w.name: w for w in _leaves(widgets.widgets, widgets.groupings, Widget, WidgetGroup)
    }
    known_backgrounds = {
        b.name: b
        for b in _leaves(
            backgrounds.backgrounds, backgrounds.groupings, Background, BackgroundGroup
        )
    }

    plan = (
        [(o, "property", known_properties) for o in property_schema.overrides]
        + [(o, "widget", known_widgets) for o in widgets.overrides]
        + [(o, "background", known_backgrounds) for o in backgrounds.overrides]
    )
    plan = [entry for entry in plan if _usable(*entry)]

    total = 0
    for _ in range(MAX_PASSES):
        changed = sum(_apply_one(userdata, override, kind, known) for override, kind, known in plan)
        total += changed
        if not changed:
            return total

    log.error(f"Overrides did not settle after {MAX_PASSES} passes, check for a circular rename")
    return total


def _usable(override: Override, kind: str, known: Any) -> bool:
    """Reject an override that would rewrite userdata to something the skin cannot use."""
    if not override.replace:
        return False

    if override.value == override.replace:
        log.error(f"{kind} override '{override.replace}' replaces itself, ignored")
        return False

    if override.value and override.value not in known:
        log.error(
            f"{kind} override '{override.replace}' targets undefined '{override.value}', ignored"
        )
        return False

    if kind == "property" and (
        override.replace.partition(".")[0] in RESERVED
        or override.value.partition(".")[0] in RESERVED
    ):
        log.error(f"property override '{override.replace}' names a script-owned key, ignored")
        return False

    if override.replace in known:
        log.error(f"{kind} override '{override.replace}' is still defined by the skin, ignored")
        return False

    return True


def _apply_one(userdata: UserData, override: Override, kind: str, known: Any) -> int:
    """Apply one override across every stored menu."""
    count = 0
    for menu in userdata.menus.values():
        for item in menu.items:
            if kind == "property":
                count += _move_keys(item, override)
            else:
                count += _move_values(item, override, kind, known)

    if count:
        became = f"'{override.value}'" if override.value else "cleared"
        log.info(f"{kind} '{override.replace}' -> {became} on {count} item(s)")
    return count


def _leaves(flat: list, groupings: list, leaf_type: type, group_type: type) -> Iterator[Any]:
    """Every leaf, top level and nested inside groups."""
    yield from flat
    stack = list(groupings)
    while stack:
        node = stack.pop()
        if isinstance(node, group_type):
            stack.extend(node.items)
        elif isinstance(node, leaf_type):
            yield node


def _slot_keys(properties: dict[str, str], name: str) -> list[str]:
    """The property key plus its numbered slots, so widget also covers widget.2.

    The slot must be a number, or background.2Label would read as a slot of background.
    """
    return [k for k in properties if k == name or _slot_of(k, name).isdigit()]


def _slot_of(key: str, name: str) -> str:
    """The slot number a key carries for this name, empty when it is not one."""
    if not key.startswith(f"{name}."):
        return ""
    return key[len(name) + 1:]


def _sibling_names(kind: str, key: str) -> list[str]:
    """The baked keys the dialog writes beside a stored widget or background name."""
    base, _, slot = key.partition(".")
    tail = f".{slot}" if slot else ""
    parts = BACKGROUND_SIBLINGS if kind == "background" else WIDGET_SIBLINGS
    return [f"{base}{part}{tail}" for part in parts]


def _move_keys(item: MenuItemOverride, override: Override) -> int:
    """Rename a stored property, or drop it when the skin retired it outright."""
    changed = 0
    for key in _slot_keys(item.properties, override.replace):
        suffix = key[len(override.replace):]
        if not override.value or override.value + suffix in item.properties:
            del item.properties[key]
        else:
            item.properties[override.value + suffix] = item.properties.pop(key)
        changed += 1

    for name in list(item.removed_properties):
        if name != override.replace and not name.startswith(f"{override.replace}."):
            continue
        item.removed_properties.remove(name)
        renamed = override.value + name[len(override.replace):] if override.value else ""
        if renamed and renamed not in item.removed_properties:
            item.removed_properties.append(renamed)
        changed += 1

    # a name in both lists loses its value at merge, so the stored value wins
    for name in list(item.removed_properties):
        if name in item.properties:
            item.removed_properties.remove(name)

    return changed


def _stale_siblings(kind: str, key: str, element: Any) -> list[str]:
    """Baked keys the new definition supplies again; a user-set label is not one of them.

    A user's own path is stored under a picker-generated name no override matches, so a
    slot naming a skin element only holds what the picker put there.
    """
    base, _, slot = key.partition(".")
    tail = f".{slot}" if slot else ""

    if kind == "background":
        parts = ["Type"] + (["Path", "PlaylistType"] if element.path else [])
    else:
        parts = ["Path", "Type", "Target", "Source"]

    return [f"{base}{part}{tail}" for part in parts]


def _move_values(item: MenuItemOverride, override: Override, kind: str, known: Any) -> int:
    """Point a stored widget or background name at its replacement, or clear it."""
    changed = 0
    for key in _slot_keys(item.properties, kind):
        if item.properties[key] != override.replace:
            continue

        if override.value:
            item.properties[key] = override.value
            for name in _stale_siblings(kind, key, known[override.value]):
                item.properties.pop(name, None)
        else:
            del item.properties[key]
            for name in _sibling_names(kind, key):
                item.properties.pop(name, None)

        changed += 1
    return changed
