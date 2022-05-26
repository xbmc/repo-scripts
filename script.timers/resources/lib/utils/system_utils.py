import xbmc
from resources.lib.utils.jsonrpc_utils import json_rpc


def is_fullscreen() -> bool:

    return xbmc.getCondVisibility("System.IsFullscreen")


def set_powermanagement_displaysoff(value: int) -> None:

    json_rpc("Settings.SetSettingValue", {
        "setting": "powermanagement.displaysoff", "value": value})


def set_windows_unlock(value: bool) -> bool:

    if xbmc.getCondVisibility("system.platform.windows"):
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(
            0x80000002 if value else 0x80000000)

    return value
