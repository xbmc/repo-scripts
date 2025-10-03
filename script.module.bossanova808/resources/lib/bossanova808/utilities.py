import json
import re
import xbmc
import xbmcgui
import xbmcvfs
import xml.etree.ElementTree as ElementTree
from urllib.parse import unquote
from typing import Any

# noinspection PyPackages
from .constants import ADDON
# noinspection PyPackages
from .logger import Logger


def set_property(window: xbmcgui.Window, name: str, value: str | None = None) -> None:
    """
    Set a property on a window.
    To clear a property use clear_property()

    :param window: The Kodi window on which to set the property.
    :param name:Name of the property.
    :param value: Optional (default None).  Set the property to this value.  An empty string, or None, clears the property, but better to use clear_property().
    """
    if value is None:
        window.clearProperty(name)
        return

    value = str(value)
    if value:
        Logger.debug(f'Setting window property {name} to value {value}')
        window.setProperty(name, value)
    else:
        clear_property(window, name)


def clear_property(window: xbmcgui.Window, name: str) -> None:
    """
    Clear a property on a window.

    :param window:
    :param name:
    """
    Logger.debug(f'Clearing window property {name}')
    window.clearProperty(name)


def get_property(window: xbmcgui.Window, name: str) -> str | None:
    """
    Return the value of a window property

    :param window: the Kodi window to get the property value from
    :param name: the name of the property to get
    :return: the value of the window property, or None if not set
    """
    value = window.getProperty(name)
    return value if value != "" else None


def get_property_as_bool(window: xbmcgui.Window, name: str) -> bool | None:
    """
    Return the value of a window property as a boolean

    :param window: the Kodi window to get the property value from
    :param name: the name of the property to get
    :return: the value of the window property in boolean form, or None if not set
    """
    value = get_property(window, name)
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in ("true", "1", "yes", "on"):
        return True
    if lowered in ("false", "0", "no", "off"):
        return False
    return None


def send_kodi_json(human_description: str, json_dict_or_string: str | dict) -> dict | None:
    """
    Send a JSON command to Kodi, logging the human description, command, and result as returned.

    :param human_description: A textual description of the command being sent to KODI. Helpful for debugging.
    :param json_dict_or_string: The JSON RPC command to be sent to KODI, as a dict or string
    :return: Parsed KODI JSON response as a dict. Returns None only if parsing fails. On RPC errors, a dict containing an "error" key is returned.
    """
    Logger.debug(f'KODI JSON RPC command: {human_description}', json_dict_or_string)
    if isinstance(json_dict_or_string, dict):
        json_dict_or_string = json.dumps(json_dict_or_string)
    result = xbmc.executeJSONRPC(json_dict_or_string)
    try:
        result = json.loads(result)
    except json.JSONDecodeError:
        Logger.error('Unable to parse JSON RPC result from KODI:', result)
        return None

    if isinstance(result, dict) and 'error' in result:
        Logger.error(f'KODI JSON RPC error for {human_description}:', result)
        return result
    Logger.debug('KODI JSON RPC result:', result)
    return result


def get_setting(setting: str) -> str | None:
    """
    Helper function to get an addon setting

    :param setting: The addon setting to return
    :return: the setting value, or None if not found
    """
    value = ADDON.getSetting(setting).strip()
    return value or None


def get_setting_as_bool(setting: str) -> bool | None:
    """
    Helper function to get bool type from settings

    :param setting: The addon setting to return
    :return: the setting value as boolean, or None if not found
    """
    value = get_setting(setting)
    if value is None:
        return None
    lowered = value.lower()
    if lowered in ("true", "1", "yes", "on"):
        return True
    if lowered in ("false", "0", "no", "off"):
        return False
    return None


def get_kodi_setting(setting: str) -> Any | None:
    """
    Get a Kodi setting value - for settings, see https://github.com/xbmc/xbmc/blob/18f70e7ac89fd502b94b8cd8db493cc076791f39/system/settings/settings.xml

    :param setting: the Kodi setting to return
    :return: The value of the Kodi setting (remember to cast this to the appropriate type before use!)
    """
    json_dict = {"jsonrpc":"2.0", "method":"Settings.GetSettingValue", "params":{"setting":setting}, "id":1}
    properties_json = send_kodi_json(f'Get Kodi setting {setting}', json_dict)
    if not properties_json:
        Logger.error(f"Settings.GetSettingValue returned no response for [{setting}]")
        return None
    if 'error' in properties_json:
        Logger.error(f"Settings.GetSettingValue returned error for [{setting}]:", properties_json['error'])
        return None
    if 'result' not in properties_json:
        Logger.error(f"Settings.GetSettingValue returned no result for [{setting}]")
        return None
    return properties_json['result'].get('value')


def get_advancedsetting(setting_path: str) -> str | None:
    """
    Helper function to extract a setting from Kodi's advancedsettings.xml file,
    Remember: cast the result appropriately and provide the Kodi default value as a fallback if the setting is not found.
    E.g.::
        Store.ignore_seconds_at_start = int(get_advancedsetting('./video/ignoresecondsatstart')) or 180

    :param setting_path: The advanced setting, in 'section/setting' (i.e. path) form, to look for (e.g. video/ignoresecondsatstart)
    :return: The setting value if found, None if not found/advancedsettings.xml doesn't exist
    """
    advancedsettings_file = xbmcvfs.translatePath("special://profile/advancedsettings.xml")

    if not xbmcvfs.exists(advancedsettings_file):
        return None

    root = None
    try:
        root = ElementTree.parse(advancedsettings_file).getroot()
        Logger.info("Found and parsed advancedsettings.xml")

    except IOError:
        Logger.warning("Found, but could not read advancedsettings.xml")
    except ElementTree.ParseError:
        Logger.warning("Found, but could not parse advancedsettings.xml")
        return None

    # If we couldn't obtain a root element, bail out safely
    if root is None:
        return None
    # Normalise: accept either 'section/setting' or './section/setting'
    normalised_path = setting_path if setting_path.startswith('.') else f'./{setting_path.lstrip("./")}'
    setting_element = root.find(normalised_path)

    if setting_element is not None:
        text = (setting_element.text or "").strip()
        return text or None

    Logger.debug(f"Setting [{setting_path}] not found in advancedsettings.xml")
    return None


def clean_art_url(kodi_url: str) -> str:
    """
    Return a cleaned, HTML-unquoted version of the art url, removing any pre-pended Kodi stuff and any trailing slash

    :param kodi_url:
    :return: cleaned url string
    """
    cleaned_url = unquote(kodi_url).replace("image://", "").rstrip("/")
    cleaned_url = re.sub(r'^.*?@', '', cleaned_url)  # pre-pended video@, pvrchannel_tv@, pvrrecording@ etc
    return cleaned_url


def is_playback_paused() -> bool:
    """
    Helper function to return Kodi player state.
    (Odd that this is needed, it should be a testable state on Player really...)

    :return: Boolean indicating the player paused state
    """
    return bool(xbmc.getCondVisibility("Player.Paused"))


def footprints(startup: bool = True) -> None:
    """
    TODO - this has moved to Logger - update all addons to use Logger.start/.stop directly, then ultimately remove this!
    Log the startup/exit of an addon and key Kodi details that are helpful for debugging

    :param startup: Optional, default True.  If true, log the startup of an addon, otherwise log the exit.
    """
    if startup:
        Logger.start()
    else:
        Logger.stop()
