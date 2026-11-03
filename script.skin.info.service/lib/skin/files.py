"""File system utilities for skin integration."""
import xbmcvfs

from lib.kodi.utilities import set_window_prop, clear_window_prop


def _set_not_found(prop_base: str, window: str) -> None:
    """Set Exists=false and clear Path."""
    set_window_prop(f'{prop_base}.Exists', 'false', window)
    clear_window_prop(f'{prop_base}.Path', window)


def check_file_exists(paths, separator='|', prefix='', window='home'):
    """Check the paths in order, setting `SkinInfo.File[.prefix].*` for the first found."""
    prop_base = f'SkinInfo.File.{prefix}' if prefix else 'SkinInfo.File'

    if not paths:
        _set_not_found(prop_base, window)
        return

    for path in (p.strip() for p in paths.split(separator) if p.strip()):
        if xbmcvfs.exists(path):
            set_window_prop(f'{prop_base}.Exists', 'true', window)
            set_window_prop(f'{prop_base}.Path', path, window)
            return

    _set_not_found(prop_base, window)
