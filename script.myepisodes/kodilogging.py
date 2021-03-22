# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import logging

import xbmc
import xbmcaddon


class KodiLogHandler(logging.StreamHandler):
    def __init__(self):
        logging.StreamHandler.__init__(self)
        addon_id = xbmcaddon.Addon().getAddonInfo("id")
        format = f"### [addon_id] - [%(filename)s:%(lineno)s - %(funcName)20s() ] %(name)s: %(message)s"
        formatter = logging.Formatter(format)
        self.setFormatter(formatter)

    def emit(self, record):
        levels = {
            logging.CRITICAL: xbmc.LOGFATAL,
            logging.ERROR: xbmc.LOGERROR,
            logging.WARNING: xbmc.LOGWARNING,
            logging.INFO: xbmc.LOGINFO,
            logging.DEBUG: xbmc.LOGDEBUG,
            logging.NOTSET: xbmc.LOGNONE,
        }

        xbmc.log(self.format(record), levels[record.levelno])

    def flush(self):
        pass


def config():
    logger = logging.getLogger()
    logger.addHandler(KodiLogHandler())
    logger.setLevel(logging.DEBUG)
