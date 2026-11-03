"""Window property manipulation utilities for skin integration."""
from typing import Final

import xbmc

from lib.kodi.utilities import clear_window_prop, parse_pipe_list, read_labels, set_window_prop


_LABEL_CHUNK: Final = 1000


def _copy_or_clear(prop_name: str, value: str, window: str) -> None:
    """Set the property to a non-empty value, else clear it."""
    if value:
        set_window_prop(prop_name, value, window)
    else:
        clear_window_prop(prop_name, window)


def copy_container_item(container, infolabels='', artwork='', prefix='', window='home'):
    """Copy a container's focused item infolabels and art to `SkinInfo.Selected.*` props."""
    if not container:
        return

    container_prefix = f'Container({container}).ListItem'
    prop_base = f'SkinInfo.Selected.{prefix}' if prefix else 'SkinInfo.Selected'
    names = parse_pipe_list(infolabels) + [f'Art({art})' for art in parse_pipe_list(artwork)]
    values = read_labels(f'{container_prefix}.{name}' for name in names)
    for name in names:
        _copy_or_clear(f'{prop_base}.{name}', values[f'{container_prefix}.{name}'], window)


def aggregate_container_labels(container, infolabel, separator=' / ',
                               prefix='SkinInfo', window='home'):
    """Join a label's unique values across a container into a property named for the label."""
    if not container or not infolabel:
        return

    num_items_label = f'Container({container}).NumItems'
    num_items_str = read_labels((num_items_label,))[num_items_label]
    try:
        num_items = int(num_items_str) if num_items_str else 0
    except (ValueError, TypeError):
        num_items = 0

    if num_items == 0:
        set_window_prop(f'{prefix}.{infolabel}s', '', window)
        return

    labels = [f'Container({container}).ListItem({i}).{infolabel}' for i in range(num_items)]
    values = []
    seen = set()
    for start in range(0, num_items, _LABEL_CHUNK):
        chunk = labels[start:start + _LABEL_CHUNK]
        result = read_labels(chunk)
        for label in chunk:
            value = result[label]
            if value and value not in seen:
                values.append(value)
                seen.add(value)

    aggregated = separator.join(values) if values else ''
    prop_name = f'{prefix}.{infolabel}s'
    set_window_prop(prop_name, aggregated, window)


def refresh_counter(uid, prefix='SkinInfo'):
    """Increment a Home counter property, which a widget URL can carry to force a refresh."""
    window = 'home'
    prop_name = f'{prefix}.{uid}'
    current = xbmc.getInfoLabel(f'Window({window}).Property({prop_name})')

    try:
        value = int(current) if current else 0
    except (ValueError, TypeError):
        value = 0

    value += 1

    set_window_prop(prop_name, value, window)
