from pprint import pprint, pformat
import sys

import xbmc

from typing import Any
# noinspection PyPackages
from .constants import ADDON_NAME, ADDON_VERSION, KODI_VERSION, KODI_MAJOR_VERSION, ADDON_ARGUMENTS


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
        # (The below test will fail if we're unit testing a module)
        if xbmc.getUserAgent():
            if isinstance(message, str):
                xbmc.log(f'### {ADDON_NAME.replace("Kodi ","")} {ADDON_VERSION}: {message}', level)
            else:
                xbmc.log(pformat(message), level)
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
        Logger.info(f'Python {sys.version}')
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
