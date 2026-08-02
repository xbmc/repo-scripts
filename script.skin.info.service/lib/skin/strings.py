"""String manipulation utilities for skin integration."""
import urllib.parse
import xbmc


def split_string(string, separator='|', prefix='', window='home'):
    """Split `string` and write `SkinInfo.Split[.{prefix}].{Count, 1, 2, ...}` window properties."""
    prop_base = f'SkinInfo.Split.{prefix}' if prefix else 'SkinInfo.Split'

    if not string:
        xbmc.executebuiltin(f'SetProperty({prop_base}.Count,0,{window})')
        return

    parts = string.split(separator)
    xbmc.executebuiltin(f'SetProperty({prop_base}.Count,{len(parts)},{window})')

    for idx, part in enumerate(parts, start=1):
        xbmc.executebuiltin(f'SetProperty({prop_base}.{idx},{part.strip()},{window})')


def urlencode(string, prefix='', window='home'):
    """URL-encode `string` and write to `SkinInfo.Encoded[.{prefix}]`."""
    prop_name = f'SkinInfo.Encoded.{prefix}' if prefix else 'SkinInfo.Encoded'

    if not string:
        xbmc.executebuiltin(f'ClearProperty({prop_name},{window})')
        return

    encoded = urllib.parse.quote(string)
    xbmc.executebuiltin(f'SetProperty({prop_name},{encoded},{window})')


def urldecode(string, prefix='', window='home'):
    """URL-decode `string` and write to `SkinInfo.Decoded[.{prefix}]`."""
    prop_name = f'SkinInfo.Decoded.{prefix}' if prefix else 'SkinInfo.Decoded'

    if not string:
        xbmc.executebuiltin(f'ClearProperty({prop_name},{window})')
        return

    decoded = urllib.parse.unquote(string)
    xbmc.executebuiltin(f'SetProperty({prop_name},{decoded},{window})')
