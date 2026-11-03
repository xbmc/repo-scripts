"""Plugin list built from a numbered set of infolabels, one item per index."""
from __future__ import annotations

import re
from typing import Dict, Final, List, Optional

import xbmc
import xbmcgui
import xbmcplugin

from lib.kodi.client import log
from lib.kodi.utilities import int_param, parse_pipe_list, read_labels

INDEX_CHUNK: Final = 100
_NUMBER: Final = re.compile(r'\s*([+-]?)(\d{1,3}(?:[.,]\d{3})+(?!\d)|\d+)(?:[.,](\d+))?')


def handle_infolabel_list(handle: int, params: dict) -> None:
    """Plugin entry for a numbered infolabel set as ListItems, each field a property of its name."""
    template = params.get('template', [''])[0]
    fields = parse_pipe_list(params.get('fields', [''])[0], ',')
    if '{n}' not in template or '{field}' not in template or not fields:
        log("Plugin", f"Infolabel list: needs fields and a template with {{n}} and {{field}}: "
            f"{template}", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    rows = _read_rows(template, fields, int_param(params, 'from', 1), int_param(params, 'to', 100))
    floor = min(max(int_param(params, 'floor', 0), 0), 100)
    for group in parse_pipe_list(params.get('scale', [''])[0], ','):
        _scale(rows, [name for name in group.split() if name in fields], floor)

    items = []
    for row in rows:
        listitem = xbmcgui.ListItem(row[fields[0]], offscreen=True)
        for name, value in row.items():
            listitem.setProperty(name, value)
        items.append(('', listitem, False))
    xbmcplugin.addDirectoryItems(handle, items, len(items))
    xbmcplugin.endOfDirectory(handle, succeeded=True)


def _read_rows(template: str, fields: List[str], first: int, last: int) -> List[Dict[str, str]]:
    """Read the fields per index in chunks, up to the first index whose first field is empty."""
    rows = []
    for start in range(first, last + 1, INDEX_CHUNK):
        indexes = range(start, min(start + INDEX_CHUNK, last + 1))
        labels = {(n, name): template.replace('{n}', str(n)).replace('{field}', name)
                  for n in indexes for name in fields}
        values = read_labels(labels.values())
        for n in indexes:
            row = {name: values[labels[(n, name)]] for name in fields}
            if not row[fields[0]]:
                return rows
            rows.append(row)
    return rows


def _scale(rows: List[Dict[str, str]], names: List[str], floor: int) -> None:
    """Add a 0-100 `<field>.Scaled` to each numeric value, the named fields sharing one range."""
    numbers = {(i, name): _parse_number(row[name]) for i, row in enumerate(rows) for name in names}
    found = [number for number in numbers.values() if number is not None]
    if not found:
        return
    low, high = min(found), max(found)
    for (i, name), number in numbers.items():
        if number is not None:
            share = (number - low) / (high - low) if high > low else 0.5
            rows[i][f'{name}.Scaled'] = str(round(floor + share * (100 - floor)))


def _parse_number(value: str) -> Optional[float]:
    """Parse a label's leading number; a separator before exactly three digits marks thousands."""
    match = _NUMBER.match(value)
    if not match:
        return None
    sign, whole, fraction = match.groups()
    number = float(re.sub(r'[.,]', '', whole) + '.' + (fraction or '0'))
    return -number if sign == '-' else number
