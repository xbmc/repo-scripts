"""File system utilities for skin integration."""
import xbmc
import xbmcvfs


def _set_not_found(prop_base: str, window: str) -> None:
    """Set Exists=false and clear Path."""
    xbmc.executebuiltin(f'SetProperty({prop_base}.Exists,false,{window})')
    xbmc.executebuiltin(f'ClearProperty({prop_base}.Path,{window})')


def check_file_exists(paths, separator='|', prefix='', window='home'):
    """Set `SkinInfo.File[.{prefix}].{Exists,Path}` for the first existing path in `paths`."""
    prop_base = f'SkinInfo.File.{prefix}' if prefix else 'SkinInfo.File'

    if not paths:
        _set_not_found(prop_base, window)
        return

    for path in (p.strip() for p in paths.split(separator) if p.strip()):
        if xbmcvfs.exists(path):
            xbmc.executebuiltin(f'SetProperty({prop_base}.Exists,true,{window})')
            xbmc.executebuiltin(f'SetProperty({prop_base}.Path,{path},{window})')
            return

    _set_not_found(prop_base, window)
