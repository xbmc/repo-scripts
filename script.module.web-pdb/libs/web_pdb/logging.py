"""Mimics built-in logging module"""

from traceback import format_exc
import xbmc

__all__ = ['Logger', 'getLogger']


class Logger:
    def __init__(self, name=''):
        self._name = name

    def _log(self, msg, level):
        xbmc.log(f'{self._name}: {msg}', level)

    def info(self, msg):
        self._log(msg, xbmc.LOGINFO)

    def error(self, msg):
        self._log(msg, xbmc.LOGERROR)

    def exception(self, msg):
        self._log(msg, xbmc.LOGERROR)
        xbmc.log(format_exc(), xbmc.LOGERROR)

    def debug(self, msg):
        self._log(msg, xbmc.LOGDEBUG)

    def critical(self, msg):
        self._log(msg, xbmc.LOGFATAL)


def getLogger(name):
    return Logger(name)
