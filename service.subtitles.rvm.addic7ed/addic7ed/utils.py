# Copyright (C) 2016, Roman Miroshnychenko aka Roman V.M.
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
import logging
import os

import xbmc

from addic7ed.addon import ADDON_ID, ADDON_VERSION
from addic7ed.exception_logger import format_exception, format_trace

__all__ = [
    'initialize_logging',
    'get_now_played',
]

logger = logging.getLogger(__name__)


class KodiLogHandler(logging.Handler):
    """
    Logging handler that writes to the Kodi log with correct levels

    It also adds {addon_id} and {addon_version} variables available to log format.
    """
    LOG_FORMAT = '[{addon_id} v.{addon_version}] {filename}:{lineno} - {message}'
    LEVEL_MAP = {
        logging.NOTSET: xbmc.LOGNONE,
        logging.DEBUG: xbmc.LOGDEBUG,
        logging.INFO: xbmc.LOGINFO,
        logging.WARN: xbmc.LOGWARNING,
        logging.WARNING: xbmc.LOGWARNING,
        logging.ERROR: xbmc.LOGERROR,
        logging.CRITICAL: xbmc.LOGFATAL,
    }

    def emit(self, record):
        record.addon_id = ADDON_ID
        record.addon_version = ADDON_VERSION
        extended_trace_info = getattr(self, 'extended_trace_info', False)
        if extended_trace_info:
            if record.exc_info is not None:
                record.exc_text = format_exception(record.exc_info[1])
            if record.stack_info is not None:
                record.stack_info = format_trace(7)
        message = self.format(record)
        kodi_log_level = self.LEVEL_MAP.get(record.levelno, xbmc.LOGDEBUG)
        xbmc.log(message, level=kodi_log_level)


def initialize_logging(extended_trace_info=True):
    """
    Initialize the root logger that writes to the Kodi log

    After initialization, you can use Python logging facilities as usual.

    :param extended_trace_info: write extended trace info when exc_info=True
        or stack_info=True parameters are passed to logging methods.
    """
    handler = KodiLogHandler()
    # pylint: disable=attribute-defined-outside-init
    handler.extended_trace_info = extended_trace_info
    logging.basicConfig(
        format=KodiLogHandler.LOG_FORMAT,
        style='{',
        level=logging.DEBUG,
        handlers=[handler],
        force=True
    )


def get_now_played():
    """
    Get info about the currently played file via JSON-RPC

    :return: currently played item's data
    :rtype: dict
    """
    request = json.dumps({
        'jsonrpc': '2.0',
        'method': 'Player.GetItem',
        'params': {
            'playerid': 1,
            'properties': ['showtitle', 'season', 'episode']
         },
        'id': '1'
    })
    response = xbmc.executeJSONRPC(request)
    item = json.loads(response)['result']['item']
    path = xbmc.getInfoLabel('Window(10000).Property(videoinfo.current_path)')
    if path:
        item['file'] = os.path.basename(path)
        logger.debug("Using file path from addon: %s", item['file'])
    else:
        item['file'] = xbmc.Player().getPlayingFile()  # It provides more correct result
    return item
