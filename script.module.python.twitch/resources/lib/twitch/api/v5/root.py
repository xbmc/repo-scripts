# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/v5/guides/using-the-twitch-api/

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ...queries import V5Query as Qry
from ...queries import query


# required scope: any
@query
def root():
    return Qry('')
