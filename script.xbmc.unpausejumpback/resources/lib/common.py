# -*- coding: utf-8 -*-
"""
Handy utility functions for Kodi Addons
By bossanova808
Free in all senses....
VERSION 0.2.3 2021-06-21
(For Kodi Matrix & later)
"""
import sys
import traceback

import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_AUTHOR = ADDON.getAddonInfo('author')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_ARGUMENTS = f'{sys.argv}'
CWD = ADDON.getAddonInfo('path')
LANGUAGE = ADDON.getLocalizedString
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
KODI_VERSION = xbmc.getInfoLabel('System.BuildVersion')
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36"
HOME_WINDOW = xbmcgui.Window(10000)
WEATHER_WINDOW = xbmcgui.Window(12600)


"""
Determine if we are unit testing outside of Kodi, or actually running within Kodi
Because we're using Kodi stubs https://romanvm.github.io/Kodistubs/ we can't rely on 'import xbmc' failing
So we use this hack - Kodi will return a user agent string, but Kodistrubs just returns and empty string.
If we are unit testing, change logs -> print

In other files, minimal code to make this work is:

# Small hack to allow for unit testing - see common.py for explanation
if not xbmc.getUserAgent():
    sys.path.insert(0, '../../..') # modify this depending on actual level - assumes resources/lib/something/file.py

from resources.lib.store import Store
from resources.lib.common import *
..etc

"""

unit_testing = False
if not xbmc.getUserAgent():

    xbmc = None
    unit_testing = True
    KODI_VERSION = 'N/A'

    print("\nNo user agent, must be unit testing.\n")

    def log(message, exception_instance=None, level=None):
        print(f'DEBUG: {message}')
        if exception_instance:
            print(f'EXCPT: {traceback.format_exc(exception_instance)}')


else:

    def log(message, exception_instance=None, level=xbmc.LOGDEBUG):
        """
        Log a message to the Kodi debug log, if debug logging is turned on.

        :param message: required, the message to log
        :param exception_instance: optional, an instance of some Exception
        :param level: optional, the Kodi log level to use, default LOGDEBUG but can override with level=xbmc.LOGINFO
        """

        message = f'### {ADDON_NAME} {ADDON_VERSION} - {message}'
        message_with_exception = message + f' ### Exception: {traceback.format_exc(exception_instance)}'

        if exception_instance is None:
            xbmc.log(message, level)
        else:
            xbmc.log(message_with_exception, level)

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
            log(f'Setting window property {name} to value {value}')
            window.setProperty(name, value)
        else:
            log(f'Clearing window property {name}')
            window.clearProperty(name)

    def get_property(window, name):
        """
        Return the value of a window property
        @param window:
        @param name:
        @return:
        """
        return window.getProperty(name)


    def get_property_as_bool(window, name):
        """
        Return the value of a window property as a boolean
        @param window:
        @param name:
        @return:
        """
        return window.getProperty(name).lower() == "true"


    def send_kodi_json(human_description, json_string):
        """
        Send a JSON command to Kodi, logging the human description, command, and result returned.

        :param human_description: Required. A human sensible description of what the command is aiming to do/retrieve.
        :param json_string: Required. The json command to send.
        """
        log(f'KODI JSON RPC command: {human_description} [{json_string}]')
        result = xbmc.executeJSONRPC(json_string)
        log(f'KODI JSON RPC result: {result}')
        return result


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


    def notify(message, notification_type=xbmcgui.NOTIFICATION_ERROR, duration=5000):
        """
        Send a notification to the user via the Kodi GUI

        @param message: the message to send
        @param notification_type: xbmcgui.NOTIFICATION_ERROR (default), xbmcgui.NOTIFICATION_WARNING, or xbmcgui.NOTIFICATION_INFO
        @param duration: time to display notification in milliseconds, default 5000
        @return: None
        """
        dialog = xbmcgui.Dialog()

        dialog.notification(ADDON_NAME,
                            message,
                            notification_type,
                            duration)


def footprints(startup=True):
    """
    Log the startup of an addon, and key Kodi details that are helpful for debugging

    :param startup: optional, default True.  If true, log the startup of an addon, otherwise log the exit.
    """
    if startup:
        log(f'Starting...', level=xbmc.LOGINFO)
        log(f'Kodi Version: {KODI_VERSION}', level=xbmc.LOGINFO)
        log(f'Addon arguments: {ADDON_ARGUMENTS}', level=xbmc.LOGINFO)
    else:
        log(f'Exiting...', level=xbmc.LOGINFO)


