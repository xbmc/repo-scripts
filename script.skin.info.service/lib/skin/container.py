"""Container manipulation utilities for skin integration."""
from __future__ import annotations

from typing import Optional
import unicodedata
from urllib.parse import quote
import xbmc
import xbmcgui
import xbmcplugin

from lib.kodi.client import log, request


_SMS_MAP = {
    'A': 'jumpsms2', 'B': 'jumpsms2', 'C': 'jumpsms2',
    'D': 'jumpsms3', 'E': 'jumpsms3', 'F': 'jumpsms3',
    'G': 'jumpsms4', 'H': 'jumpsms4', 'I': 'jumpsms4',
    'J': 'jumpsms5', 'K': 'jumpsms5', 'L': 'jumpsms5',
    'M': 'jumpsms6', 'N': 'jumpsms6', 'O': 'jumpsms6',
    'P': 'jumpsms7', 'Q': 'jumpsms7', 'R': 'jumpsms7', 'S': 'jumpsms7',
    'T': 'jumpsms8', 'U': 'jumpsms8', 'V': 'jumpsms8',
    'W': 'jumpsms9', 'X': 'jumpsms9', 'Y': 'jumpsms9', 'Z': 'jumpsms9',
}

# Latin letters that don't NFKD-decompose; folded to the base letter Kodi sorts them under.
_LETTER_FOLD = {
    'Ø': 'O', 'ø': 'O', 'Æ': 'A', 'æ': 'A', 'Œ': 'O', 'œ': 'O',
    'ß': 'S', 'ẞ': 'S', 'Ð': 'D', 'ð': 'D', 'Đ': 'D', 'đ': 'D',
    'Þ': 'T', 'þ': 'T', 'Ł': 'L', 'ł': 'L', 'Ħ': 'H', 'ħ': 'H',
    'Ŧ': 'T', 'ŧ': 'T',
}


def _fold_letter(value: str) -> str:
    """Bucket a SortLetter into A-Z or '#', folding accents to their base letter.

    Matches Kodi's collation so the availability flag lines up with where the SMS jump lands.
    """
    if not value:
        return ''
    ch = value[0]
    if ch.isascii() and ch.isalpha():
        return ch.upper()
    mapped = _LETTER_FOLD.get(ch)
    if mapped:
        return mapped
    for base in unicodedata.normalize('NFKD', ch):
        if base.isascii() and base.isalpha():
            return base.upper()
    return '#'


def _evaluate_conditional_focus(blocks: list[str]) -> None:
    """Evaluate condition::focus_id blocks in order, focusing first match."""
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        if '::' in block:
            condition, fid = block.split('::', 1)
            condition = condition.strip()
            fid = fid.strip()
        else:
            condition = None
            fid = block.strip()

        if condition and not xbmc.getCondVisibility(condition):
            continue

        if fid:
            xbmc.executebuiltin(f'SetFocus({fid})', True)
            return


def move_to_position(
    main_focus: str,
    main_position: Optional[str] = None,
    main_action: Optional[str] = None,
    next_focus: Optional[str] = None,
    next_position: Optional[str] = None,
    next_action: Optional[str] = None
) -> None:
    """Move or focus containers to a target position; see DOCS/skin-utilities.md for the
    `container_move` RunScript API."""
    _move_main_containers(main_focus, main_position, main_action)
    _handle_next_focus(next_focus, next_position, next_action)


def _move_main_containers(main_focus: str, main_position: Optional[str],
                          main_action: Optional[str]) -> None:
    """Reset each visible control in `main_focus` to its target, skipping any already there.

    List containers guard on `CurrentItem`; buttons have no item position, so they guard on
    `HasFocus` instead.
    """
    main_ids = [cid.strip() for cid in main_focus.split('|')]
    main_action_list = [a.strip() for a in main_action.split('|')] if main_action else []
    has_pipe_main_action = main_action and '|' in main_action
    main_position_list = (
        [p.strip() for p in main_position.split('|')]
        if main_position and '|' in main_position else []
    )
    has_pipe_main_position = main_position and '|' in main_position

    for idx, cid in enumerate(main_ids):
        if not cid:
            continue
        if not xbmc.getCondVisibility(f'Control.IsVisible({cid})'):
            continue

        if has_pipe_main_position and idx < len(main_position_list):
            position_str = main_position_list[idx]
        else:
            position_str = main_position

        if position_str is None or position_str == "":
            position = 0
            target_1indexed = "1"
        else:
            try:
                position_int = int(position_str)
                position = 0 if position_int <= 0 else position_int - 1
                target_1indexed = "1" if position_int <= 0 else str(position_int)
            except (ValueError, TypeError):
                continue

        try:
            item_count = int(xbmc.getInfoLabel(f'Container({cid}).NumItems') or 0)
        except ValueError:
            item_count = 0

        if item_count > 0:
            should_move = (
                xbmc.getInfoLabel(f'Container({cid}).CurrentItem') != target_1indexed
            )
        else:
            should_move = not xbmc.getCondVisibility(f'Control.HasFocus({cid})')

        if should_move:
            xbmc.executebuiltin(f'Control.SetFocus({cid}, {position}, absolute)', True)

        if has_pipe_main_action and idx < len(main_action_list) and main_action_list[idx]:
            xbmc.executebuiltin(main_action_list[idx], True)
        elif not has_pipe_main_action and main_action:
            xbmc.executebuiltin(main_action, True)


def _handle_next_focus(next_focus: Optional[str], next_position: Optional[str],
                       next_action: Optional[str]) -> None:
    """Resolve next-focus from parameter (preferred), else `SkinInfo.CM_Focus.*` properties."""
    properties_found = []
    for i in range(1, 100):
        prop_value = xbmc.getInfoLabel(f'Window(home).Property(SkinInfo.CM_Focus.{i})')
        if prop_value:
            properties_found.append((i, prop_value))
        else:
            break

    if next_focus and properties_found:
        log(
            "ContainerMove",
            "Both next_focus parameter and CM_Focus properties set - "
            "using parameter, ignoring properties",
            xbmc.LOGWARNING,
        )
        _clear_cm_focus_props(properties_found)
        properties_found = []

    if next_focus:
        if '::' in next_focus:
            _evaluate_conditional_focus(next_focus.split('||'))
            return
        _focus_next_containers(next_focus, next_position, next_action)
    elif properties_found:
        _evaluate_conditional_focus([prop_value for _, prop_value in properties_found])
        _clear_cm_focus_props(properties_found)


def _focus_next_containers(next_focus: str, next_position: Optional[str],
                          next_action: Optional[str]) -> None:
    """Focus and optionally position each container in `next_focus` (pipe-separated IDs)."""
    next_ids = [fid.strip() for fid in next_focus.split('|')]
    next_action_list = [a.strip() for a in next_action.split('|')] if next_action else []
    has_pipe_next_action = next_action and '|' in next_action
    next_position_list = (
        [p.strip() for p in next_position.split('|')]
        if next_position and '|' in next_position else []
    )
    has_pipe_next_position = next_position and '|' in next_position

    for idx, fid in enumerate(next_ids):
        if not fid:
            continue

        xbmc.executebuiltin(f'SetFocus({fid})', True)

        if has_pipe_next_position and idx < len(next_position_list):
            position_str = next_position_list[idx]
        else:
            position_str = next_position

        if position_str:
            try:
                position_int = int(position_str)
                position = 0 if position_int <= 0 else position_int - 1
            except (ValueError, TypeError):
                continue
            xbmc.executebuiltin(f'Control.SetFocus({fid}, {position}, absolute)', True)

        if has_pipe_next_action and idx < len(next_action_list) and next_action_list[idx]:
            xbmc.executebuiltin(next_action_list[idx], True)
        elif not has_pipe_next_action and next_action:
            xbmc.executebuiltin(next_action, True)


def _clear_cm_focus_props(properties_found: list) -> None:
    """Clear `SkinInfo.CM_Focus.{i}` for each `(i, _)` in `properties_found`."""
    for i, _ in properties_found:
        xbmc.executebuiltin(f'ClearProperty(SkinInfo.CM_Focus.{i},home)', True)


def jump_letter(letter: str, container_id: Optional[str] = None) -> None:
    """Jump to an item starting with `letter` (A-Z or `#`) via Kodi's SMS actions."""
    if container_id:
        xbmc.executebuiltin(f'SetFocus({container_id})', True)

    letter_upper = letter.upper()

    if letter_upper == '#':
        is_descending = xbmc.getCondVisibility('Container.SortDirection(descending)')
        action = 'lastpage' if is_descending else 'firstpage'
        request('Input.ExecuteAction', {'action': action})
        return

    action = _SMS_MAP.get(letter_upper)
    if not action:
        return

    for _ in range(5):
        request('Input.ExecuteAction', {'action': action})
        xbmc.sleep(30)

        if _fold_letter(xbmc.getInfoLabel('ListItem.SortLetter')) == letter_upper:
            break


_SCAN_CHUNK = 1000

# Skip the scan above this count; each item permanently registers a GUIInfo entry against
# Kodi's ~60k global cap.
_MAX_AVAILABILITY_ITEMS = 10000


def _container_too_large(target: str) -> bool:
    """True when the target has too many items to scan for availability safely."""
    try:
        count = int(xbmc.getInfoLabel(f'Container({target}).NumItems') or 0)
    except ValueError:
        return False
    if count > _MAX_AVAILABILITY_ITEMS:
        log('SkinUtils', f'letter_jump: {count} items exceed availability cap; plain bar',
            xbmc.LOGINFO)
        return True
    return False


def _available_sort_letters(target: str) -> set[str]:
    """Folded jump letters (A-Z plus '#') present in the target container.

    Reads the live container, so active filters and the current sort are honoured.
    """
    try:
        all_count = int(xbmc.getInfoLabel(f'Container({target}).NumAllItems') or 0)
        count = int(xbmc.getInfoLabel(f'Container({target}).NumItems') or 0)
    except ValueError:
        return set()

    start_index = max(0, all_count - count)  # 1 when a ".." parent item leads the list

    found: set[str] = set()
    for start in range(start_index, all_count, _SCAN_CHUNK):
        labels = [
            f'Container({target}).ListItemAbsolute({i}).SortLetter'
            for i in range(start, min(start + _SCAN_CHUNK, all_count))
        ]
        response = request('XBMC.GetInfoLabels', {'labels': labels})
        for value in (response.get('result', {}) if response else {}).values():
            letter = _fold_letter(value)
            if letter:
                found.add(letter)
        if len(found) >= 27:
            break
    return found


def handle_letter_jump_list(handle: int, params: dict) -> None:
    """Return A-Z (plus '#') ListItems for container letter-jump; see DOCS/plugin/navigation.md
    for the full API."""
    target = params.get('target', ['50'])[0]
    showall = params.get('showall', ['true'])[0].lower() != 'false'
    want_available = params.get('available', ['false'])[0].lower() == 'true' or not showall

    if want_available and _container_too_large(target):
        want_available = False
        showall = True  # can't compact or dim without the scan; fall back to the full bar

    is_descending = xbmc.getCondVisibility(f'Container({target}).SortDirection(descending)')

    letters = 'ZYXWVUTSRQPONMLKJIHGFEDCBA#' if is_descending else 'ABCDEFGHIJKLMNOPQRSTUVWXYZ#'

    available = _available_sort_letters(target) if want_available else set()

    for letter in letters:
        is_available = letter in available
        if not showall and not is_available:
            continue

        listitem = xbmcgui.ListItem(letter, offscreen=True)

        if want_available and not is_available:
            url = ''  # no jump target, so the cell is inert
            listitem.setProperty('IsNotAvailable', 'true')
        else:
            url = (f'plugin://script.skin.info.service/?action=jump_letter_exec'
                   f'&letter={quote(letter, safe="")}&target={target}')

        xbmcplugin.addDirectoryItem(handle, url, listitem, False)

    xbmcplugin.setContent(handle, '')
    xbmcplugin.endOfDirectory(handle)


def handle_letter_jump_exec(handle: int, params: dict) -> None:
    """Execute letter jump from `?action=jump_letter_exec&letter=X&target=N`."""
    try:
        xbmcplugin.setResolvedUrl(handle, succeeded=False, listitem=xbmcgui.ListItem())
    except Exception:
        pass

    letter = params.get('letter', [''])[0]
    target = params.get('target', [''])[0]

    if not letter:
        return

    current = xbmc.getInfoLabel(f'Container({target}).ListItem.SortLetter')
    if letter.upper() == _fold_letter(current):
        return

    jump_letter(letter, target)
