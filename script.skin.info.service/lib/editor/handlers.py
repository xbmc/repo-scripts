"""Field type handlers for metadata editor."""
from __future__ import annotations

from typing import Any, Callable, TypeVar, Final

import xbmc
import xbmcgui

from lib.infrastructure.dialogs import show_select, show_yesno
from lib.kodi.client import ADDON
from lib.kodi.formatters import format_rating
from lib.editor.config import TVSHOW_STATUS_VALUES
from lib.editor.operations import fetch_library_values_for_field
from lib.editor.utilities import (
    format_duration_for_edit,
    format_runtime_for_edit,
    parse_duration_from_edit,
    parse_rating,
    parse_runtime_from_edit,
    normalize_date,
    validate_date,
    validate_duration,
    validate_rating,
    validate_runtime,
    validate_top250,
    validate_year,
)

# xbmc.Keyboard truncates the pre-filled default past 100 chars
MAX_KEYBOARD_DEFAULT_LEN: Final = 100

_T = TypeVar("_T")


def _edit_heading(field_name: str) -> str:
    """Get the localized edit dialog heading for a field."""
    return ADDON.getLocalizedString(32557).format(field_name)


def handle_text(
    field_name: str, current_value: str | None
) -> tuple[str | None, bool]:
    """Handle text input, newlines shown as [CR] in the keyboard."""
    heading = _edit_heading(field_name)
    default = current_value or ""

    # xbmc.Keyboard can't take newlines
    default_display = default.replace('\r\n', '[CR]').replace('\n', '[CR]').replace('\r', '[CR]')

    if len(default_display) > MAX_KEYBOARD_DEFAULT_LEN:
        xbmcgui.Dialog().notification(
            ADDON.getLocalizedString(32258),
            ADDON.getLocalizedString(32987),
            xbmcgui.NOTIFICATION_WARNING,
            3000
        )

    kb = xbmc.Keyboard(default_display, heading)
    kb.doModal()

    if not kb.isConfirmed():
        return None, True

    result = kb.getText().replace('[CR]', '\n')
    return result, False


_INTEGER_VALIDATORS = {
    "year": validate_year,
    "top250": validate_top250,
}


def handle_integer(
    field_name: str, current_value: int | None, validator: str | None = None
) -> tuple[int | None, bool]:
    """Handle integer input, checked by the field's validator when it has one."""
    validator_fn = _INTEGER_VALIDATORS.get(validator) if validator else None
    return _prompt_until_valid(
        _edit_heading(field_name), str(current_value) if current_value else "", int,
        validator_fn or (lambda _value: (True, "")), 32254, xbmcgui.INPUT_NUMERIC)


def _handle_seconds(
    field_name: str, current_value: int | None, *, unit: str, fmt, parse, validate,
    input_type: int = xbmcgui.INPUT_ALPHANUM,
) -> tuple[int | None, bool]:
    """Prompt for a seconds-backed field in its display unit, storing the parsed seconds."""
    heading = f"{_edit_heading(field_name)} ({unit})"
    return _prompt_until_valid(
        heading, fmt(current_value or 0), parse, validate, 32254, input_type)


def handle_runtime(
    field_name: str, current_value: int | None
) -> tuple[int | None, bool]:
    """Handle runtime input (edit in minutes, store in seconds)."""
    return _handle_seconds(
        field_name, current_value, unit="minutes", fmt=format_runtime_for_edit,
        parse=parse_runtime_from_edit, validate=validate_runtime,
        input_type=xbmcgui.INPUT_NUMERIC)


def handle_duration(
    field_name: str, current_value: int | None
) -> tuple[int | None, bool]:
    """Handle duration input (edit in MM:SS format, store in seconds)."""
    return _handle_seconds(
        field_name, current_value, unit="MM:SS", fmt=format_duration_for_edit,
        parse=parse_duration_from_edit, validate=validate_duration)


def _prompt_until_valid(
    heading: str, value: str, parse: Callable[[str], _T],
    validate: Callable[[_T], tuple[bool, str]], error_heading: int,
    input_type: int = xbmcgui.INPUT_ALPHANUM
) -> tuple[_T | None, bool]:
    """Prompt, reopening with the entry kept, until the value validates or is cancelled."""
    while True:
        result = xbmcgui.Dialog().input(heading, value, type=input_type)
        if not result:
            return None, True
        parsed = parse(result)
        valid, error = validate(parsed)
        if valid:
            return parsed, False
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(error_heading), error)
        value = result


def _handle_date_input(
    field_name: str, value: str, store=lambda date: date
) -> tuple[str | None, bool]:
    """Prompt for a date, reopening with the entry kept until it validates or is cancelled."""
    heading = f"{_edit_heading(field_name)} (YYYY-MM-DD)"
    date, cancelled = _prompt_until_valid(
        heading, value, normalize_date, validate_date, 32255)
    return (None, True) if cancelled or date is None else (store(date), False)


def _handle_rating_input(heading: str, value: str) -> tuple[float | None, bool]:
    """Prompt for a 0-10 rating, decimal point or comma both accepted."""
    return _prompt_until_valid(heading, value, parse_rating, validate_rating, 32256)


def handle_date(
    field_name: str, current_value: str | None
) -> tuple[str | None, bool]:
    """Handle date input (YYYY-MM-DD); reopens with the entry kept on a bad value."""
    return _handle_date_input(field_name, current_value or "")


def handle_lastplayed(
    field_name: str, current_value: str | None
) -> tuple[str | None, bool]:
    """Handle last-played as a date, stored at midnight since Kodi shows it date-only."""
    return _handle_date_input(
        field_name, (current_value or "").split(" ")[0], lambda date: f"{date} 00:00:00")


def handle_userrating(
    field_name: str, current_value: int | None
) -> tuple[int | None, bool]:
    """Handle 1-10 user rating selection, the first option clearing it."""
    options = [ADDON.getLocalizedString(32391)] + [str(i) for i in range(1, 11)]
    preselect = current_value if current_value else 0

    choice = show_select(
        ADDON.getLocalizedString(32556).format(field_name), options, preselect=preselect
    )

    if choice < 0:
        return None, True

    return choice, False


def handle_status(
    field_name: str, current_value: str | None
) -> tuple[str | None, bool]:
    """Handle TV show status selection."""
    options = [ADDON.getLocalizedString(32392)] + [s.title() for s in TVSHOW_STATUS_VALUES[1:]]

    preselect = 0
    if current_value:
        current_lower = current_value.lower()
        for i, status in enumerate(TVSHOW_STATUS_VALUES):
            if status == current_lower:
                preselect = i
                break

    choice = show_select(
        ADDON.getLocalizedString(32556).format(field_name), options, preselect=preselect
    )

    if choice < 0:
        return None, True

    return TVSHOW_STATUS_VALUES[choice], False


def handle_list(
    field_name: str,
    current_values: list[str] | None,
    media_type: str,
    field_key: str
) -> tuple[list[str] | None, bool]:
    """Handle list editing: quick edit, pick from the library, or add and remove."""
    values = list(current_values) if current_values else []

    current_display = ", ".join(values) if values else ADDON.getLocalizedString(32392)
    options = [
        ADDON.getLocalizedString(32395).format(current_display),
        ADDON.getLocalizedString(32396),
        ADDON.getLocalizedString(32397),
    ]

    choice = show_select(ADDON.getLocalizedString(32557).format(field_name), options)

    if choice < 0:
        return None, True

    if choice == 0:
        return _quick_edit_list(field_name, values)
    elif choice == 1:
        return _select_from_library(field_name, values, media_type, field_key)
    else:
        return _add_remove_items(field_name, values)


def _quick_edit_list(
    field_name: str, current: list[str]
) -> tuple[list[str] | None, bool]:
    """Edit list as comma-separated string."""
    current_str = ", ".join(current)
    heading = ADDON.getLocalizedString(32399).format(field_name)

    kb = xbmc.Keyboard(current_str, heading)
    kb.doModal()

    if not kb.isConfirmed():
        return None, True

    result = kb.getText()
    parsed = [x.strip() for x in result.split(",") if x.strip()]
    return parsed, False


def _select_from_library(
    field_name: str, current: list[str], media_type: str, field_key: str
) -> tuple[list[str] | None, bool]:
    """Show a multiselect of the library's values plus the item's own."""
    library_values = fetch_library_values_for_field(field_key, media_type)

    if not library_values:
        xbmcgui.Dialog().ok(
            ADDON.getLocalizedString(32390),
            ADDON.getLocalizedString(32726).format(field_name)
        )
        return None, True

    all_values: list[str] = list(library_values)
    for val in current:
        if val not in all_values:
            all_values.append(val)

    preselect = [i for i, v in enumerate(all_values) if v in current]

    result = xbmcgui.Dialog().multiselect(
        ADDON.getLocalizedString(32556).format(field_name),
        all_values,  # type: ignore[arg-type]
        preselect=preselect
    )

    if result is None:
        return None, True

    return [all_values[i] for i in result], False


def _add_remove_items(
    field_name: str, current: list[str]
) -> tuple[list[str] | None, bool]:
    """Add and remove items one at a time until the user saves or cancels."""
    items = list(current)
    monitor = xbmc.Monitor()

    while not monitor.abortRequested():
        options = [f"[+] {ADDON.getLocalizedString(32394).format(field_name)}"]
        for item in items:
            options.append(f"[-] {item}")
        options.append(f"[{ADDON.getLocalizedString(32393)}]")
        options.append(f"[{xbmc.getLocalizedString(222)}]")

        choice = show_select(ADDON.getLocalizedString(32557).format(field_name), options)

        if choice < 0 or choice == len(options) - 1:
            return None, True

        if choice == 0:
            new_item = xbmcgui.Dialog().input(ADDON.getLocalizedString(32394).format(field_name))
            if new_item and new_item.strip():
                items.append(new_item.strip())

        elif choice == len(options) - 2:
            return items, False

        else:
            item_index = choice - 1
            if 0 <= item_index < len(items):
                del items[item_index]

    return None, True


def handle_ratings(
    field_name: str, current_ratings: dict[str, Any] | None
) -> tuple[dict[str, Any] | None, bool]:
    """Handle external ratings editing, returning the edited map only when something changed."""
    # shared nested dicts would read as unchanged in _edit_field's equality check
    ratings = {source: dict(data) if isinstance(data, dict) else data
               for source, data in (current_ratings or {}).items()}
    modified = False
    monitor = xbmc.Monitor()

    while not monitor.abortRequested():
        options = []
        sources = list(ratings.keys())

        for source in sources:
            data = ratings[source]
            if isinstance(data, dict):
                rating = data.get("rating", 0)
                votes = data.get("votes", 0)
                default_mark = f" [{xbmc.getLocalizedString(571)}]" if data.get("default") else ""
                vote_text = ADDON.getLocalizedString(32727).format(f"{votes:,}")
                options.append(f"{source}: {format_rating(rating)} ({vote_text}){default_mark}")
            else:
                options.append(f"{source}: {data}")

        add_rating = ADDON.getLocalizedString(32394).format(xbmc.getLocalizedString(563))
        options.append(f"[+] {add_rating}")

        choice = show_select(ADDON.getLocalizedString(32557).format(field_name), options)

        if choice < 0:
            if modified:
                return ratings, False
            return None, True

        if choice == len(sources):
            if _add_rating_source(ratings):
                modified = True
        elif choice < len(sources):
            source = sources[choice]
            if _edit_single_rating(ratings, source):
                modified = True

    return None, True


def handle_uniqueids(
    field_name: str, current: dict[str, Any] | None, default_value: str | None = None
) -> tuple[dict[str, Any] | None, bool]:
    """Handle unique ID editing. Returns the full map, cleared entries as None."""
    original: dict[str, str] = {k: str(v) for k, v in (current or {}).items()}
    ids: dict[str, Any] = dict(original)
    # Kodi default id is imdbnumber
    default_key = next(
        (k for k, v in ids.items() if default_value and v == default_value), None)
    modified = False
    monitor = xbmc.Monitor()

    while not monitor.abortRequested():
        keys = list(ids.keys())
        options = []
        for key in keys:
            mark = f" [{xbmc.getLocalizedString(571)}]" if key == default_key else ""
            options.append(f"{key}: {ids[key]}{mark}")
        options.append(f"[+] {ADDON.getLocalizedString(32663)}")

        choice = show_select(ADDON.getLocalizedString(32557).format(field_name), options)

        if choice < 0:
            if not modified:
                return None, True
            payload: dict[str, Any] = dict(ids)
            for key in original:
                if key not in ids:
                    payload[key] = None
            return payload, False

        if choice == len(keys):
            modified = _add_uniqueid(ids) or modified
        elif choice < len(keys):
            modified = _edit_single_uniqueid(ids, keys[choice],
                                             keys[choice] == default_key) or modified

    return None, True


def _add_uniqueid(ids: dict[str, Any]) -> bool:
    """Add a new unique ID. Returns True if added."""
    id_type = xbmcgui.Dialog().input(ADDON.getLocalizedString(32664))
    if not id_type or not id_type.strip():
        return False

    id_type = id_type.strip().lower()
    if id_type in ids:
        xbmcgui.Dialog().ok(
            ADDON.getLocalizedString(32257), ADDON.getLocalizedString(32564).format(id_type)
        )
        return False

    value = xbmcgui.Dialog().input(ADDON.getLocalizedString(32665).format(id_type))
    if not value or not value.strip():
        return False

    ids[id_type] = value.strip()
    return True


def _edit_single_uniqueid(ids: dict[str, Any], id_type: str, is_default: bool) -> bool:
    """Edit or clear one unique ID. Returns True if modified."""
    value = xbmcgui.Dialog().input(
        ADDON.getLocalizedString(32665).format(id_type), ids[id_type]
    )
    if value is None:
        return False

    value = value.strip()
    if value == ids[id_type]:
        return False

    if value:
        ids[id_type] = value
        return True

    # Kodi won't remove the default id
    if is_default:
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(32257), ADDON.getLocalizedString(32666))
        return False

    if not show_yesno(ADDON.getLocalizedString(32257),
                      ADDON.getLocalizedString(32667).format(id_type)):
        return False

    del ids[id_type]
    return True


def _add_rating_source(ratings: dict[str, Any]) -> bool:
    """Add a new rating source. Returns True if added."""
    source = xbmcgui.Dialog().input(ADDON.getLocalizedString(32252))
    if not source or not source.strip():
        return False

    source = source.strip().lower()

    if source in ratings:
        xbmcgui.Dialog().ok(
            ADDON.getLocalizedString(32257), ADDON.getLocalizedString(32564).format(source)
        )
        return False

    rating, cancelled = _handle_rating_input(ADDON.getLocalizedString(32565), "0")
    if cancelled or rating is None:
        return False

    votes_str = xbmcgui.Dialog().input(
        ADDON.getLocalizedString(32253), "0", type=xbmcgui.INPUT_NUMERIC
    )
    votes = int(votes_str) if votes_str else 0

    is_default = not ratings
    ratings[source] = {"rating": rating, "votes": votes, "default": is_default}
    return True


def _edit_single_rating(ratings: dict[str, Any], source: str) -> bool:
    """Edit a single rating source. Returns True if modified."""
    options = [
        ADDON.getLocalizedString(32557).format(xbmc.getLocalizedString(563)),
        f"Edit {ADDON.getLocalizedString(32253)}",
        xbmc.getLocalizedString(40023),
        xbmc.getLocalizedString(1210),
    ]

    choice = show_select(ADDON.getLocalizedString(32557).format(source), options)

    if choice < 0:
        return False

    data = ratings[source]
    if not isinstance(data, dict):
        data = {"rating": float(data), "votes": 0, "default": False}
        ratings[source] = data

    if choice == 0:
        current = data.get("rating", 0)
        new_rating, cancelled = _handle_rating_input(
            ADDON.getLocalizedString(32565), format_rating(current))
        if not cancelled and new_rating is not None:
            data["rating"] = new_rating
            return True

    elif choice == 1:
        current = data.get("votes", 0)
        result = xbmcgui.Dialog().input(
            ADDON.getLocalizedString(32253), str(current), type=xbmcgui.INPUT_NUMERIC
        )
        if result:
            try:
                data["votes"] = int(result)
                return True
            except ValueError:
                pass

    elif choice == 2:
        for s in ratings:
            if isinstance(ratings[s], dict):
                ratings[s]["default"] = s == source
        return True

    elif choice == 3:
        if show_yesno(
            ADDON.getLocalizedString(32301), ADDON.getLocalizedString(32302).format(source)
        ):
            del ratings[source]
            return True

    return False
