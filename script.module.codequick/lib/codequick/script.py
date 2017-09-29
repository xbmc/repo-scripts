# -*- coding: utf-8 -*-
from __future__ import absolute_import

# Standard Library Imports
import logging
import os

# Kodi imports
import xbmcaddon
import xbmcgui
import xbmc

# Package imports
from codequick.utils import CacheProperty, ensure_unicode, ensure_native_str, safe_path
from codequick.support import dispatcher, script_data, addon_data, logger_id
import urlquick

__all__ = ["Script", "Settings"]

# Logger used by the addons
addon_logger = logging.getLogger(logger_id)


class Settings(object):
    """Settings class to handle the getting and setting of addon settings."""

    def __getitem__(self, key):
        """
        Returns the value of a setting as a unicode string.

        :param str key: Id of the setting to access.

        :return: Setting as a unicode string.
        :rtype: unicode
        """
        return addon_data.getSetting(key)

    def __setitem__(self, key, value):
        """
        Set an add-on setting.

        :param str key: Id of the setting.
        :param value: Value of the setting.
        :type value: str or unicode
        """
        # noinspection PyTypeChecker
        addon_data.setSetting(key, ensure_unicode(value))

    @staticmethod
    def get_string(key, addon_id=None):
        """
        Returns the value of a setting as a unicode string.

        :param str key: Id of the setting to access.
        :param str addon_id: [opt] Id of another addon to extract settings from.

        :raises RuntimeError: If addon_id is given and there is no addon with given id.

        :return: Setting as a unicode string.
        :rtype: unicode
        """
        if addon_id:
            return xbmcaddon.Addon(addon_id).getSetting(key)
        else:
            return addon_data.getSetting(key)

    @staticmethod
    def get_boolean(key, addon_id=None):
        """
        Returns the value of a setting as a boolean.

        :param str key: Id of the setting to access.
        :param str addon_id: [opt] Id of another addon to extract settings from.

        :raises RuntimeError: If addon_id is given and there is no addon with given id.

        :return: Setting as a boolean.
        :rtype: bool
        """
        setting = Settings.get_string(key, addon_id).lower()
        return setting == u"true" or setting == u"1"

    @staticmethod
    def get_int(key, addon_id=None):
        """
        Returns the value of a setting as a integer.

        :param str key: Id of the setting to access.
        :param str addon_id: [opt] Id of another addon to extract settings from.

        :raises RuntimeError: If addon_id is given and there is no addon with given id.

        :return: Setting as a integer.
        :rtype: int
        """
        return int(Settings.get_string(key, addon_id))

    @staticmethod
    def get_number(key, addon_id=None):
        """
        Returns the value of a setting as a float.

        :param str key: Id of the setting to access.
        :param str addon_id: [opt] Id of another addon to extract settings from.

        :raises RuntimeError: If addon_id is given and there is no addon with given id.

        :return: Setting as a float.
        :rtype: float
        """
        return float(Settings.get_string(key, addon_id))


class Script(object):
    """
    This class is used to create Script callbacks. Script callbacks are callbacks that
    just execute code and return nothing.

    This class is also used as the base for all other types of callbacks i.e.
    :class:`Route<codequick.route.Route>` and :class:`Resolver<codequick.resolver.Resolver>`.
    """
    # Set the listitem types to that of a script
    is_playable = False
    is_folder = False

    # Logging Levels
    CRITICAL = 50
    WARNING = 30
    ERROR = 40
    DEBUG = 10
    INFO = 20

    # Notification icon options
    NOTIFY_WARNING = 'warning'
    NOTIFY_ERROR = 'error'
    NOTIFY_INFO = 'info'

    #: Underlining logger object, for advanced use.
    logger = addon_logger

    setting = Settings()
    """
    Dictionary like interface of add-on settings,
    See :class:`script.Settings<codequick.script.Settings>` for more details.
    """

    def __init__(self):
        self._title = dispatcher.support_params.get(u"_title_", u"")
        self.handle = dispatcher.handle
        self.params = dispatcher.params

    def _execute_route(self, callback):
        """
        Execute the callback function and process the results.

        :param callback: The callback func/class to register.
        :returns: The response from the callback func/class.
        """
        return callback(self, **dispatcher.callback_params)

    @classmethod
    def register(cls, callback):
        """
        Decorator used to register callback functions.

        :param callback: The callback function to register.
        :returns: The original callback function.
        """
        return dispatcher.register(callback, cls=cls)

    @staticmethod
    def register_metacall(func, *args, **kwargs):
        """
        Register a function that will be executed after kodi has finished listing all listitems.
        Sence the function is called after the listitems have been shown, it will not slow anything down.
        Very useful for fetching extra metadata without slowing down the listing of content.

        :param func: Function that will be called after endOfDirectory is called.
        :param args: Positional arguments that will be passed to function.
        :param kwargs: Keyword arguments that will be passed to function.
        """
        callback = (func, args, kwargs)
        dispatcher.metacalls.append(callback)

    @staticmethod
    def log(msg, args=None, lvl=10):
        """
        Logs a message with logging level of 'lvl'.

        Logging Levels.
            * :attr:`Script.DEBUG<codequick.script.Script.DEBUG>`
            * :attr:`Script.INFO<codequick.script.Script.INFO>`
            * :attr:`Script.WARNING<codequick.script.Script.WARNING>`
            * :attr:`Script.ERROR<codequick.script.Script.ERROR>`
            * :attr:`Script.CRITICAL<codequick.script.Script.CRITICAL>`

        :param msg: The message format string.
        :type args: list or tuple
        :param args: List of arguments which are merged into msg using the string formatting operator.
        :param lvl: The logging level to use. default => 10(Debug).

        .. Note::
            When a log level of 50(CRITICAL) is given, then all debug messages that were previously logged
            will now be logged as level 30(WARNING). This will allow for debug messages to show in the normal kodi
            log file when a CRITICAL error has occurred, without having to enable kodi's debug mode.
        """
        addon_logger.log(lvl, msg, *args)

    @staticmethod
    def notify(heading, message, icon=None, display_time=5000, sound=True):
        """
        Send a notification to kodi.

        Options for icon are.
            * :attr:`Script.NOTIFY_INFO<codequick.script.Script.NOTIFY_INFO>`
            * :attr:`Script.NOTIFY_ERROR<codequick.script.Script.NOTIFY_ERROR>`
            * :attr:`Script.NOTIFY_WARNING<codequick.script.Script.NOTIFY_WARNING>`

        :type heading: str or unicode
        :param heading: Dialog heading label.

        :type message: str or unicode
        :param message: Dialog message label.

        :type icon: str or unicode
        :param icon: [opt] Icon image to use. (default => 'add-on icon image')

        :param int display_time: [opt] Ttime in milliseconds to show dialog. (default => 5000)
        :param bool sound: [opt] Whether or not to play notification sound. (default => True)
        """
        # Ensure that heading, message and icon
        # is encoded into native str type
        heading = ensure_native_str(heading)
        message = ensure_native_str(message)
        icon = ensure_native_str(icon if icon else Script.get_info("icon"))

        dialog = xbmcgui.Dialog()
        dialog.notification(heading, message, icon, display_time, sound)

    @staticmethod
    def localize(string_id):
        """
        Returns an add-on's localized 'unicode string'.

        :param int string_id: The id or reference string to be localized.

        :returns: Localized unicode string.
        :rtype: unicode
        """
        if 30000 <= string_id <= 30999:
            return addon_data.getLocalizedString(string_id)
        elif 32000 <= string_id <= 32999:
            return script_data.getLocalizedString(string_id)
        else:
            return xbmc.getLocalizedString(string_id)

    @staticmethod
    def get_info(key, addon_id=None):
        """
        Returns the value of an addon property as a unicode string.

        Properties.
            * author
            * changelog
            * description
            * disclaimer
            * fanart
            * icon
            * id
            * name
            * path
            * profile
            * stars
            * summary
            * type
            * version

        :param str key: Id of the property to access.
        :param str addon_id: [opt] Id of another addon to extract properties from.

        :return: Add-on property as a unicode string.
        :rtype: unicode

        :raises RuntimeError: If addon_id is given and there is no add-on with given id.
        """
        if addon_id:
            # Extract property from a different add-on
            resp = xbmcaddon.Addon(addon_id).getAddonInfo(key)
        elif key == "path_global" or key == "profile_global":
            # Extract property from codequick addon
            resp = script_data.getAddonInfo(key[:key.find("_")])
        else:
            # Extract property from the running addon
            resp = addon_data.getAddonInfo(key)

        # Check if path needs to be translated first
        if resp[:10] == "special://":
            resp = xbmc.translatePath(resp)

        # Convert response to unicode
        resp = resp.decode("utf8") if isinstance(resp, bytes) else resp

        # Create any missing directory
        if key.startswith("profile"):
            path = safe_path(resp)
            if not os.path.exists(path):
                os.mkdir(path)

        return resp

    @CacheProperty
    def request(self):
        """
        A urlquick.session object.

        This is used for requesting online resources.
        It is very similar to requests.session but with built-in caching support.

        .. seealso:: The urlquick documentation can be found at.\n
                     http://urlquick.readthedocs.io/en/stable/

        :example:
            >>> from codequick import Route
            >>>
            >>> @Route.register
            >>> def root(plugin):
            >>>     html = plugin.request.get("http://example.com/index.html")
            >>>     root_element = html.parse()
            >>>     print(root_element)
            >>>     "xml.etree.ElementTree.Element"
        """
        return urlquick.Session()

    @CacheProperty
    def icon(self):
        """The add-on's icon image path."""
        return self.get_info("icon")

    @CacheProperty
    def fanart(self):
        """The add-on's fanart image path."""
        return self.get_info("fanart")

    @CacheProperty
    def profile(self):
        """The add-on's profile data directory path."""
        return self.get_info("profile")

    @CacheProperty
    def path(self):
        """The add-on's directory path."""
        return self.get_info("path")
