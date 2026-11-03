"""String manipulation utilities for skin integration."""
import xbmc

from lib.kodi.utilities import set_window_prop, clear_window_prop


def split_string(string, separator='|', prefix='', window='home'):
    """Split a string into `SkinInfo.Split[.prefix].*` properties: the count, then 1, 2 and on."""
    prop_base = f'SkinInfo.Split.{prefix}' if prefix else 'SkinInfo.Split'
    previous = xbmc.getInfoLabel(f'Window({window}).Property({prop_base}.Count)')
    parts = string.split(separator) if string else []

    set_window_prop(f'{prop_base}.Count', len(parts), window)
    for idx, part in enumerate(parts, start=1):
        set_window_prop(f'{prop_base}.{idx}', part.strip(), window)
    for idx in range(len(parts) + 1, int(previous) + 1 if previous.isdigit() else 0):
        clear_window_prop(f'{prop_base}.{idx}', window)


def urlencode(string, prefix='', window='home', doneaction='', json_escape=False):
    """URL-encode a string into `SkinInfo.Encoded[.prefix]` and the builtin's `{value}`."""
    prop_name = f'SkinInfo.Encoded.{prefix}' if prefix else 'SkinInfo.Encoded'

    if not string:
        clear_window_prop(prop_name, window)
        return

    from urllib.parse import quote
    if json_escape:
        import json
        string = json.dumps(string, ensure_ascii=False)[1:-1]
    encoded = quote(string)
    set_window_prop(prop_name, encoded, window)
    if doneaction:
        from lib.skin.dialogs import _execute_builtin_list
        _execute_builtin_list(doneaction.replace('{value}', encoded))


def urldecode(string, prefix='', window='home'):
    """URL-decode a string into `SkinInfo.Decoded[.prefix]`."""
    prop_name = f'SkinInfo.Decoded.{prefix}' if prefix else 'SkinInfo.Decoded'

    if not string:
        clear_window_prop(prop_name, window)
        return

    from urllib.parse import unquote
    decoded = unquote(string)
    set_window_prop(prop_name, decoded, window)
