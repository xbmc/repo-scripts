"""Window property manipulation utilities for skin integration."""
import xbmc

from lib.kodi.client import request
from lib.kodi.utilities import parse_pipe_list


_LABEL_CHUNK = 1000


def _copy_or_clear(prop_name: str, value: str, window: str) -> None:
    """Set the property when `value` is truthy; clear it otherwise."""
    if value:
        xbmc.executebuiltin(f'SetProperty({prop_name},{value},{window})')
    else:
        xbmc.executebuiltin(f'ClearProperty({prop_name},{window})')


def copy_container_item(container, infolabels='', artwork='', prefix='', window='home'):
    """Copy `Container.ListItem` infolabels/`Art(...)` to `SkinInfo.Selected[.prefix].*` props."""
    if not container:
        return

    container_prefix = f'Container({container}).ListItem'
    prop_base = f'SkinInfo.Selected.{prefix}' if prefix else 'SkinInfo.Selected'

    if infolabels:
        for label in parse_pipe_list(infolabels):
            value = xbmc.getInfoLabel(f'{container_prefix}.{label}')
            _copy_or_clear(f'{prop_base}.{label}', value, window)

    if artwork:
        for art_type in parse_pipe_list(artwork):
            value = xbmc.getInfoLabel(f'{container_prefix}.Art({art_type})')
            _copy_or_clear(f'{prop_base}.Art({art_type})', value, window)


def aggregate_container_labels(container, infolabel, separator=' / ',
                               prefix='SkinInfo', window='home'):
    """Join unique `infolabel` values across all container items into `{prefix}.{infolabel}s`.

    Example: `aggregate_container_labels(50, "Genre")` -> `SkinInfo.Genres = "Action / Comedy"`.
    """
    if not container or not infolabel:
        return

    num_items_str = xbmc.getInfoLabel(f'Container({container}).NumItems')
    try:
        num_items = int(num_items_str) if num_items_str else 0
    except (ValueError, TypeError):
        num_items = 0

    if num_items == 0:
        xbmc.executebuiltin(f'SetProperty({prefix}.{infolabel}s,,{window})')
        return

    labels = [f'Container({container}).ListItem({i}).{infolabel}' for i in range(num_items)]
    values = []
    seen = set()
    for start in range(0, num_items, _LABEL_CHUNK):
        chunk = labels[start:start + _LABEL_CHUNK]
        response = request('XBMC.GetInfoLabels', {'labels': chunk})
        result = response.get('result', {}) if response else {}
        for label in chunk:
            value = result.get(label, '')
            if value and value not in seen:
                values.append(value)
                seen.add(value)

    aggregated = separator.join(values) if values else ''
    prop_name = f'{prefix}.{infolabel}s'
    xbmc.executebuiltin(f'SetProperty({prop_name},{aggregated},{window})')


def refresh_counter(uid, prefix='SkinInfo'):
    """Increment `{prefix}.{uid}` window prop. Useful to trigger widget refresh via URL params."""
    window = 'home'
    prop_name = f'{prefix}.{uid}'
    current = xbmc.getInfoLabel(f'Window({window}).Property({prop_name})')

    try:
        value = int(current) if current else 0
    except (ValueError, TypeError):
        value = 0

    value += 1

    xbmc.executebuiltin(f'SetProperty({prop_name},{value},{window})')
