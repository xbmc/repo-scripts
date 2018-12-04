# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/v5/reference/bits/

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ... import keys
from ...queries import V5Query as Qry
from ...queries import query


# required scope: None
@query
def get_cheermotes(channel_id=None):
    q = Qry('bits/actions', use_token=False)
    q.add_param(keys.CHANNEL_ID, channel_id, None)
    return q
