# -*- coding: utf-8 -*-
"""Log handler for Kodi"""

from __future__ import absolute_import, division, unicode_literals

import logging

import xbmc
import xbmcaddon


class KodiLogHandler(logging.StreamHandler):
    """A log handler for Kodi"""

    def __init__(self):
        logging.StreamHandler.__init__(self)
        addon_id = xbmcaddon.Addon().getAddonInfo("id")
        formatter = logging.Formatter("[{}] [%(name)s] %(message)s".format(addon_id))
        self.setFormatter(formatter)

    def emit(self, record):
        """Emit a log message"""
        levels = {
            logging.CRITICAL: xbmc.LOGFATAL,
            logging.ERROR: xbmc.LOGERROR,
            logging.WARNING: xbmc.LOGWARNING,
            logging.INFO: xbmc.LOGINFO,
            logging.DEBUG: xbmc.LOGDEBUG,
            logging.NOTSET: xbmc.LOGNONE,
        }
        try:
            xbmc.log(self.format(record), levels[record.levelno])
        except UnicodeEncodeError:
            xbmc.log(self.format(record).encode('utf-8', 'ignore'), levels[record.levelno])

    def flush(self):
        """Flush the messages"""


def config():
    """Setup the logger with this handler"""
    logger = logging.getLogger()
    logger.addHandler(KodiLogHandler())
    logger.setLevel(logging.DEBUG)
