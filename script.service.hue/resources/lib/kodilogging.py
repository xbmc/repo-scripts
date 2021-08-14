# -*- coding: utf-8 -*-

import logging
from logging.handlers import TimedRotatingFileHandler
import os

import xbmc

from . import ADDONID, ADDON, ADDONDIR

prefix = "[{}]".format(ADDONID)
formatter = logging.Formatter(prefix + '[%(module)s][%(funcName)s](%(lineno)d): %(message)s')
fileFormatter = logging.Formatter('%(asctime)s %(levelname)s [%(module)s][%(funcName)s](%(lineno)d): %(message)s')


class KodiLogHandler(logging.StreamHandler):

    def __init__(self):
        logging.StreamHandler.__init__(self)
        self.setFormatter(formatter)

    def emit(self, record):
        levels = {
            logging.DEBUG: xbmc.LOGDEBUG,
        }

        xbmc.log(self.format(record), levels[record.levelno])

        #=======================================================================
        # try:
        #     xbmc.log(self.format(record), levels[record.levelno])
        # except UnicodeEncodeError:
        #     xbmc.log(self.format(record).encode(
        #         'utf-8', 'ignore'), levels[record.levelno])
        #=======================================================================

    def flush(self):
        pass


def config():
    separateLogFile=ADDON.getSettingBool("separateLogFile")
    logger = logging.getLogger(ADDONID)

    if separateLogFile:
        if not os.path.isdir(ADDONDIR):
            #xbmc.log("Hue Service: profile directory doesn't exist: " + ADDONDIR + "   Trying to create.", level=xbmc.LOGDEBUG)
            try:
                os.mkdir(ADDONDIR)
                xbmc.log("Hue Service: profile directory created: " + ADDONDIR, level=xbmc.LOGDEBUG)
            except OSError as e:
                xbmc.log("Hue Service: Log: can't create directory: " + ADDONDIR, level=xbmc.LOGDEBUG)
                xbmc.log("Exception: {}".format(e.message), xbmc.LOGDEBUG)

        file_handler = TimedRotatingFileHandler(os.path.join(ADDONDIR, 'kodiHue.log'), when="midnight",  backupCount=2)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(fileFormatter)
        logger.addHandler(file_handler)

    logger.addHandler(KodiLogHandler())
    logger.setLevel(logging.DEBUG)

