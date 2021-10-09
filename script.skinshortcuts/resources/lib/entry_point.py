# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

# pylint: disable=import-error
from skinshorcuts import skinshortcuts
from skinshorcuts.common import log
from skinshorcuts.constants import ADDON_VERSION

log('script version %s started' % ADDON_VERSION)
script = skinshortcuts.Script()
script.route()
log('script stopped')
