# -*- coding: utf-8 -*-

import json
from .constants import *
from .logger import Logger


def set_property(window, name, value=""):
    """
    Set a property on a window.
    To clear a property, provide an empty string

    :param window: Required.  The Kodi window on which to set the property.
    :param name: Required.  Name of the property.
    :param value: Optional (defaults to "").  Set the property to this value.  An empty string clears the property.
    """
    if value is None:
        window.clearProperty(name)

    value = str(value)
    if value:
        Logger.debug(f'Setting window property {name} to value {value}')
        window.setProperty(name, value)
    else:
        Logger.debug(f'Clearing window property {name}')
        window.clearProperty(name)


def get_property(window, name):
    """
    Return the value of a window property

    :param window: the Kodi window to get the property value from
    :param name: the name of the property to get
    :return: the value of the window property
    """
    return window.getProperty(name)


def get_property_as_bool(window, name):
    """
    Return the value of a window property as a boolean

    :param window: the Kodi window to get the property value from
    :param name: the name of the property to get
    :return: the value of the window property in boolean form
    """
    return window.getProperty(name).lower() == "true"


def send_kodi_json(human_description, json_string):
    """
    Send a JSON command to Kodi, logging the human description, command, and result as returned.

    :param human_description: Required. A human sensible description of what the command is aiming to do/retrieve.
    :param json_string: Required. The json command to send.
    :return: the json object loaded from the result string
    """
    Logger.debug(f'KODI JSON RPC command: {human_description} [{json_string}]')
    result = xbmc.executeJSONRPC(json_string)
    Logger.debug(f'KODI JSON RPC result: {result}')
    return json.loads(result)


def get_setting(setting):
    """
    Helper function to get string type from settings

    :param setting: The addon setting to return
    :return: the setting value
    """
    return ADDON.getSetting(setting).strip()


def get_setting_as_bool(setting):
    """
    Helper function to get bool type from settings

    :param setting: The addon setting to return
    :return: the setting value as boolean
    """
    return get_setting(setting).lower() == "true"


def is_playback_paused():
    """
    Helper function to return Kodi player state.
    (Odd this is needed, it should be a testable state on Player really...)

    :return: boolean indicating player paused state
    """
    return bool(xbmc.getCondVisibility("Player.Paused"))


def footprints(startup=True):
    """
    Log the startup/exit of an addon, and key Kodi details that are helpful for debugging

    :param startup: optional, default True.  If true, log the startup of an addon, otherwise log the exit.
    """
    if startup:
        Logger.info(f'Start.')
        Logger.info(f'Kodi {KODI_VERSION}')
        Logger.info(f'Python {sys.version}')
        Logger.info(f'Run {ADDON_ARGUMENTS}')
    else:
        Logger.info(f'Finish.')
