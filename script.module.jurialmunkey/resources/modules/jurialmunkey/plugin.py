import xbmc
from xbmcaddon import Addon as KodiAddon


class KodiPlugin():
    def __init__(self, addon_id):
        self._addon_id = addon_id
        self._addon = KodiAddon(addon_id)
        self._addon_name = self._addon.getAddonInfo('name')
        self._addon_path = self._addon.getAddonInfo('path')
        self._addon_getsettingroute = {
            'bool': self._addon.getSettingBool,
            'int': self._addon.getSettingInt,
            'str': self._addon.getSettingString}
        self._addon_setsettingroute = {
            'bool': self._addon.setSettingBool,
            'int': self._addon.setSettingInt,
            'str': self._addon.setSettingString}

    def get_setting(self, setting, mode='bool'):
        return self._addon_getsettingroute[mode](setting)

    def set_setting(self, setting, data, mode='bool'):
        return self._addon_setsettingroute[mode](setting, data)

    def get_localized(self, localize_int=0):
        if localize_int < 30000 or localize_int >= 33000:
            return xbmc.getLocalizedString(localize_int)
        return self._addon.getLocalizedString(localize_int)


def format_name(cache_name, *args, **kwargs):
    # Define a type whitelist to avoiding adding non-basic types like classes to cache name
    permitted_types = (int, float, str, bool, bytes)
    for arg in args:
        if not isinstance(arg, permitted_types):
            continue
        cache_name = f'{cache_name}/{arg}' if cache_name else f'{arg}'
    for key, value in sorted(kwargs.items()):
        if not isinstance(value, permitted_types):
            continue
        cache_name = f'{cache_name}&{key}={value}' if cache_name else f'{key}={value}'
    return cache_name


def format_folderpath(path, content='videos', affix='return', info=None, play='PlayMedia'):
    if not path:
        return
    if info == 'play':
        return f'{play}({path})'
    if xbmc.getCondVisibility("Window.IsMedia") and xbmc.getInfoLabel("System.CurrentWindow").lower() == content:
        return f'Container.Update({path})'
    return f'ActivateWindow({content},{path},{affix})'


def set_kwargattr(obj, kwargs):
    for k, v in kwargs.items():
        setattr(obj, k, v)
