# coding: utf-8
# Author: Roman Miroshnychenko aka Roman V.M.
# E-mail: roman1972@gmail.com
# License: GPL v. 3 <http://www.gnu.org/licenses/gpl-3.0.en.html>

import os
from inspect import currentframe
import xbmc
from xbmcaddon import Addon

__all__ = ['log_debug', 'log_error', 'log_notice', 'log_warning']

FORMAT = '{id} [v.{version}] - {filename}:{lineno} - {message}'
addon = Addon('script.service.next-episode')
addon_id = addon.getAddonInfo('id')
addon_version = addon.getAddonInfo('version')


def encode(msg):
    if isinstance(msg, unicode):
        msg = msg.encode('utf-8')
    return msg


def log_message(msg, level=xbmc.LOGDEBUG):
    curr_frame = currentframe()
    xbmc.log(
        FORMAT.format(
            id=addon_id,
            version=addon_version,
            filename=os.path.basename(curr_frame.f_back.f_back.f_code.co_filename),
            lineno=curr_frame.f_back.f_back.f_lineno,
            message=encode(msg)
        ),
        level
    )


def log_notice(msg):
    log_message(msg, xbmc.LOGNOTICE)


def log_warning(msg):
    log_message(msg, xbmc.LOGWARNING)


def log_error(msg):
    log_message(msg, xbmc.LOGERROR)


def log_debug(msg):
    log_message(msg, xbmc.LOGDEBUG)
