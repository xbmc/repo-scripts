from pprint import pprint, pformat
import sys

import xbmc

from typing import Any
# noinspection PyPackages
from .constants import ADDON_NAME, ADDON_VERSION, KODI_VERSION, KODI_MAJOR_VERSION, ADDON_ARGUMENTS, \
    BOSSANOVA808_VERSION, OS_PLATFORM

# xbmc.getUserAgent() always returns a non-empty string inside real Kodi, and is used here purely
# as a cheap "are we actually running inside Kodi" probe - it returns falsy under the lightweight
# xbmc stubs used when unit testing a module outside Kodi. Computed once, since this can't change
# part-way through a running addon process.
_IN_KODI = bool(xbmc.getUserAgent())


def _debug_logging_enabled() -> bool:
    """
    Whether debug logging is currently active - true if either Settings > System > Logging >
    'Enable debug logging' is on, or the active profile's advancedsettings.xml sets an explicit
    <loglevel> of 1 or higher. The latter can enable debug logging while the GUI setting above
    still reads False, since advancedsettings.xml overrides it without changing that setting.
    """
    if xbmc.getCondVisibility("System.GetBool(debug.showloginfo)"):
        return True
    # Local import: utilities.py imports Logger from this module, so importing it at module level
    # here would be circular. By the time this runs, module loading has long finished, so it's safe.
    from .utilities import get_advancedsetting
    loglevel = get_advancedsetting('loglevel')
    try:
        return bool(loglevel) and int(loglevel) >= 1
    except ValueError:
        return False


class Logger:

    @staticmethod
    def log(message: Any, level: int = xbmc.LOGDEBUG) -> None:
        """
        Logs a message using the Kodi logging system. If the user agent is unavailable
        (e.g. during unit testing), it will print the message to the console using pprint.

        :param message: The message to be logged. If the message is not a string, it will
            be formatted using `pformat` before logging.
        :param level: The log level for the message, default `xbmc.LOGDEBUG`.
        """
        if _IN_KODI:
            prefix = f'### {ADDON_NAME.replace("Kodi ","")} {ADDON_VERSION}: '
            if isinstance(message, str):
                xbmc.log(prefix + message, level)
            else:
                xbmc.log(prefix + pformat(message), level)
        else:
            # ONLY USED WHEN UNIT TESTING A MODULE!
            pprint(message)

    @staticmethod
    def info(*messages: Any) -> None:
        """
        Log messages to the Kodi log file at the INFO level.

        :param messages: The messages to log
        """
        for message in messages:
            Logger.log(message, xbmc.LOGINFO)

    @staticmethod
    def warning(*messages: Any) -> None:
        """
        Log messages to the Kodi log file at the WARNING level.

        :param messages: The messages to log
        """
        for message in messages:
            Logger.log(message, xbmc.LOGWARNING)

    @staticmethod
    def error(*messages: Any) -> None:
        """
        Log messages to the Kodi log file at the ERROR level.

        :param messages: The messages to log
        """
        for message in messages:
            Logger.log(message, xbmc.LOGERROR)

    @staticmethod
    def debug(*messages: Any) -> None:
        """
        Log messages to the Kodi log file at DEBUG level.

        :param messages: The message(s) to log
        """
        for message in messages:
            Logger.log(message, xbmc.LOGDEBUG)

    @staticmethod
    def start(*extra_messages: Any) -> None:
        """
        Log key information at the start of an addon run.

        :param extra_messages: Any extra things to log, such as "(Service)" or "(Plugin)" if it helps to identify component elements.
        """
        Logger.info(f'Start {ADDON_NAME}')
        if extra_messages:
            Logger.info(*extra_messages)
        Logger.info(f'Kodi {KODI_VERSION} (Major version {KODI_MAJOR_VERSION})')
        Logger.info(f'OS: {OS_PLATFORM}')
        Logger.info(f'Python {sys.version}')
        Logger.info(f'script.module.bossanova808 version: {BOSSANOVA808_VERSION}')
        Logger.info(f'Kodi debug logging enabled: {_debug_logging_enabled()}')
        if ADDON_ARGUMENTS != "['']":
            Logger.info(f'Run {ADDON_ARGUMENTS}')
        else:
            Logger.info('No arguments supplied to addon')

    @staticmethod
    def stop(*extra_messages: Any) -> None:
        """
        Log key information at the end of an addon run.

        :param extra_messages: Any extra things to log, such as "(Service)" or "(Plugin)" if it helps to identify component elements.
        """
        Logger.info(f'Finish {ADDON_NAME}')
        if extra_messages:
            Logger.info(*extra_messages)
