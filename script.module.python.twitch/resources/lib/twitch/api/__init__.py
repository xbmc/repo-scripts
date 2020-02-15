# -*- encoding: utf-8 -*-
"""

    Copyright (C) 2012-2016 python-twitch (https://github.com/ingwinlu/python-twitch)
    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

__all__ = ['v5', 'default', 'helix', 'parameters', 'usher']

from . import v5  # V5 is deprecated and will be removed entirely on TBD
from . import v5 as default
from . import helix
from . import parameters
from . import usher
