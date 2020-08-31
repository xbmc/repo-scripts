# -*- coding: utf-8 -*-

# Handy utility functions for Kodi Addons
# By bossanova808
# Free in all senses....
# VERSION 0.1.3 2020-08-31
# (For Kodi Matrix & later)

import xbmc
import xbmcgui
import xbmcaddon
import sys
import traceback

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_AUTHOR = ADDON.getAddonInfo('author')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_ARGUMENTS = str(sys.argv)
CWD = ADDON.getAddonInfo('path')
LANGUAGE = ADDON.getLocalizedString
PROFILE = xbmc.translatePath(ADDON.getAddonInfo('profile'))
KODI_VERSION = xbmc.getInfoLabel('System.BuildVersion')
USER_AGENT = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.6"
WEATHER_WINDOW = xbmcgui.Window(12600)


def log(message, exception_instance=None, level=xbmc.LOGDEBUG):
    """
    Log a message to the Kodi debug log, if debug logging is turned on.

    :param message: required, the message to log
    :param exception_instance: optional, an instance of some Exception
    :param level: optional, the Kodi log level to use, default LOGDEBUG
    """

    message = f'### {ADDON_NAME} {ADDON_VERSION} - {message}'
    message_with_exception = message + f' ### Exception: {traceback.format_exc(exception_instance)}'

    if exception_instance is None:
        xbmc.log(message, level)
    else:
        xbmc.log(message_with_exception, level)


def log_info(message, exception_instance=None):
    """
    Log a message at the LOGINFO level, i.e. even if Kodi debugging is not turned on. Use sparingly.

    :param message: required, the message to log
    :param exception_instance: optional, an instance of some Exception
    """

    log(message, exception_instance, level=xbmc.LOGINFO)


def footprints(startup=True):
    """
    Log the startup of an addon, and key Kodi details that are helpful for debugging

    :param startup: optional, default True.  If true, log the startup of an addon, otherwise log the exit.
    """
    if startup:
        log_info(f'Starting...')
        log_info(f'Kodi Version: {KODI_VERSION}')
        log_info(f'Addon arguments: {ADDON_ARGUMENTS}')
    else:
        log_info(f'Exiting...')


def set_property(window, name, value=""):
    """
    Set a property on a window.
    To clear a property, provide an empty string

    :param window: Required.  The Kodi window on which to set the property.
    :param name: Required.  Name of the property.
    :param value: Optional (defaults to "").  Set the property to this value.  An empty string clears the property.
    """
    window.setProperty(name, value)
    # if value and value != False and value != 'na.png':
    #     log(f'Set window property: [{name}] - value: [{value}]')


def send_kodi_json(human_description, json_string):
    """
    Send a JSON command to Kodi, logging the human description, command, and result returned.

    :param human_description: Required. A human sensible description of what the command is aiming to do/retrieve.
    :param json_string: Required. The json command to send.
    """
    log(f'KODI JSON RPC command: {human_description} [{json_string}]')
    result = xbmc.executeJSONRPC(json_string)
    log(f'KODI JSON RPC result: {str(result)}')


def get_setting(setting):
    """
    Helper function to get string type from settings

    @param setting:
    @return: setting value
    """
    return ADDON.getSetting(setting).strip()


def get_setting_as_bool(setting):
    """
    Helper function to get bool type from settings

    @param setting:
    @return: setting value as boolen
    """
    return get_setting(setting).lower() == "true"
