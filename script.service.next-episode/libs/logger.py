# coding: utf-8
# Author: Roman Miroshnychenko aka Roman V.M.
# E-mail: roman1972@gmail.com
# License: GPL v. 3 <http://www.gnu.org/licenses/gpl-3.0.en.html>

from __future__ import absolute_import, unicode_literals
import os
from inspect import currentframe
from kodi_six import xbmc
from .addon import addon_id, addon_version

__all__ = ['log_debug', 'log_error', 'log_notice', 'log_warning']

FORMAT = '{id} [v.{version}] - {filename}:{lineno} - {message}'


def log_message(msg, level=xbmc.LOGDEBUG):
    curr_frame = currentframe()
    xbmc.log(
        FORMAT.format(
            id=addon_id,
            version=addon_version,
            filename=os.path.basename(curr_frame.f_back.f_back.f_code.co_filename),
            lineno=curr_frame.f_back.f_back.f_lineno,
            message=msg
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
