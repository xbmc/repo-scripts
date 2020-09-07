# coding: utf-8
# Author: Roman Miroshnychenko aka Roman V.M.
# E-mail: roman1972@gmail.com
# License: GPL v. 3 <http://www.gnu.org/licenses/gpl-3.0.en.html>

from __future__ import absolute_import, unicode_literals
import os
from inspect import currentframe
from kodi_six import xbmc
from .addon import ADDON_ID, ADDON_VERSION

__all__ = ['log_debug', 'log_error', 'log_info', 'log_warning']

FORMAT = '{id} [v.{version}] - {filename}:{lineno} - {message}'


def log_message(msg, level=xbmc.LOGDEBUG):
    curr_frame = currentframe()
    xbmc.log(
        FORMAT.format(
            id=ADDON_ID,
            version=ADDON_VERSION,
            filename=os.path.basename(curr_frame.f_back.f_back.f_code.co_filename),
            lineno=curr_frame.f_back.f_back.f_lineno,
            message=msg
        ),
        level
    )


def log_info(msg):
    log_message(msg, xbmc.LOGINFO)


def log_warning(msg):
    log_message(msg, xbmc.LOGWARNING)


def log_error(msg):
    log_message(msg, xbmc.LOGERROR)


def log_debug(msg):
    log_message(msg, xbmc.LOGDEBUG)
