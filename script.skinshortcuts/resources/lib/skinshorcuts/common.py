# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import xbmc

from .constants import ADDON
from .constants import ADDON_ID


def log(txt):
    if ADDON.getSettingBool("enable_logging"):
        if isinstance(txt, bytes):
            txt = txt.decode('utf-8')

        message = '%s -- %s' % (ADDON_ID, txt)
        xbmc.log(msg=message, level=xbmc.LOGDEBUG)


def read_file(filename, mode='r'):
    encoding = None
    if 'b' not in mode:
        encoding = 'utf-8'
    with open(filename, mode, encoding=encoding) as file_handle:
        return file_handle.read()


def write_file(filename, contents, mode='w'):
    encoding = None
    if 'b' not in mode:
        encoding = 'utf-8'
    with open(filename, mode, encoding=encoding) as file_handle:
        file_handle.write(contents)
