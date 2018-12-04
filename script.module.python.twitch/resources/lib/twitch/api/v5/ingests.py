# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/v5/reference/ingests/

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ...queries import V5Query as Qry
from ...queries import query


# required scope: none
@query
def ingests():
    q = Qry('ingests', use_token=False)
    return q
