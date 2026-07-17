# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

from .config import ADDON_ID
from .config import TEMP_DIRECTORY

# the actual constants
__all__ = ['ADDON_ID', 'TEMP_DIRECTORY']

# the modules containing the constants
__all__ += ['config']
