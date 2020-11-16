# coding: utf-8
"""Mimics built-in logging module"""

from __future__ import unicode_literals
import sys
from traceback import format_exc
import xbmc

__all__ = ['Logger', 'getLogger']

PY2 = sys.version_info[0] == 2


def encode(string):
    if PY2 and isinstance(string, unicode):
        string = string.encode('utf-8')
    return string


class Logger(object):
    def __init__(self, name=''):
        self._name = name

    def info(self, msg):
        xbmc.log(encode('{}: {}'.format(self._name, msg)), xbmc.LOGINFO)

    def error(self, msg):
        xbmc.log(encode('{}: {}'.format(self._name, msg)), xbmc.LOGERROR)

    def exception(self, msg):
        self.error(msg)
        xbmc.log(format_exc(), xbmc.LOGERROR)

    def debug(self, msg):
        xbmc.log(encode('{}: {}'.format(self._name, msg)), xbmc.LOGDEBUG)

    def critical(self, msg):
        xbmc.log(encode('{}: {}'.format(self._name, msg)), xbmc.LOGFATAL)


def getLogger(name):
    return Logger(name)
