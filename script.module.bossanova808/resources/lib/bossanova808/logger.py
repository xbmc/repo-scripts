# -*- coding: utf-8 -*-

import xbmc
from .constants import *


class Logger:

    @staticmethod
    def log(message, level=xbmc.LOGDEBUG):
        """
        Log a message to the Kodi log file.
        If we're unit testing a module outside Kodi, print to the console instead.

        :param message: the message to log
        :param level: the kodi log level to log at, default xbmc.LOGDEBUG
        :return:
        """
        #
        if xbmc.getUserAgent():
            xbmc.log(f'### {ADDON_NAME} {ADDON_VERSION}: {str(message)}', level)
        else:
            print(str(message))

    @staticmethod
    def info(message):
        """
        Log a message to the Kodi log file at INFO level.

        :param message: the message to log
        :return:
        """
        Logger.log(message, xbmc.LOGINFO)

    @staticmethod
    def warning(message):
        """
        Log a message to the Kodi log file at WARNING level.

        :param message: the message to log
        :return:
        """
        Logger.log(message, xbmc.LOGWARNING)

    @staticmethod
    def error(message):
        """
        Log a message to the Kodi log file at ERROR level.

        :param message: the message to log
        :return:
        """
        Logger.log(message, xbmc.LOGERROR)

    @staticmethod
    def debug(*messages):
        """
        Log messages to the Kodi log file at DEBUG level.

        :param messages: the message(s) to log
        :return:
        """
        for message in messages:
            Logger.log(message, xbmc.LOGDEBUG)

