# -*- coding: utf-8 -*-
"""

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

import re
import logging
import copy

try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

try:
    import xbmc
except ImportError:
    xbmc = None


def _mask(message):
    mask = '*' * 11
    masked_message = re.sub(r'((?:OAuth|Bearer)\s)[^\'"]+', r'\1' + mask, message)
    masked_message = re.sub(r'(["\']email["\']:\s*[\'"])[^\'"]+', r'\1' + mask, masked_message)
    masked_message = re.sub(r'(USER-IP=[\'"])[^\'"]+', r'\1' + mask, masked_message)
    masked_message = re.sub(r'(["\']client_secret["\']:\s*[\'"])[^\'"]+', r'\1' + mask, masked_message)
    masked_message = re.sub(r'(client_secret=).+?(&|$|\|)', r'\1' + mask + r'\2', masked_message)
    masked_message = re.sub(r'(\\*["\']user_ip\\*["\']:\\*["\']).+?(\\*["\'])', r'\1' + mask + r'\2', masked_message)
    masked_message = re.sub(r'(["\'](?:nauth)*sig["\']: ["\'])[^\'"]+', r'\1' + mask, masked_message)
    return masked_message


def _add_leader(message):
    if xbmc:
        message = 'script.module.python.twitch: %s' % message
    return message


def prep_log_message(message):
    message = copy.deepcopy(message)
    message = _mask(message)
    message = _add_leader(message)
    return message


class Log:
    def __init__(self):
        if xbmc:
            self._log = xbmc.log
        else:
            self._log = logging.getLogger('twitch')
            self._log.addHandler(NullHandler())

    def info(self, message):
        message = prep_log_message(message)
        if xbmc:
            self._log(message, xbmc.LOGINFO)
        else:
            self._log.info(message)

    def debug(self, message):
        message = prep_log_message(message)
        if xbmc:
            self._log(message, xbmc.LOGDEBUG)
        else:
            self._log.debug(message)

    def warning(self, message):
        message = prep_log_message(message)
        if xbmc:
            self._log(message, xbmc.LOGWARNING)
        else:
            self._log.debug(message)

    def error(self, message):
        message = prep_log_message(message)
        if xbmc:
            self._log(message, xbmc.LOGERROR)
        else:
            self._log.error(message)

    def critical(self, message):
        message = prep_log_message(message)
        if xbmc:
            self._log(message, xbmc.LOGFATAL)
        else:
            self._log.critical(message)

    def deprecated_query(self, old, new=None):
        if new:
            self.warning('DEPRECATED call to |{0}| detected, please use |{1}| instead'.format(old, new))
        else:
            self.warning('DEPRECATED call to |{0}| detected, no alternatives available'.format(old))

    def deprecated_endpoint(self, old):
        self.warning('DEPRECATED call to |{0}| endpoint detected'.format(old))

    def deprecated_api_version(self, old, new, eol_date):
        self.warning('API version |{0}| is deprecated, update to |{1}| by |{2}|'.format(old, new, eol_date))


log = Log()
