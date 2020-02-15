# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/api/reference

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ..parameters import Cursor, IntRange
from ... import keys
from ...queries import HelixQuery as Qry
from ...queries import query


# required scope: none
# requires app access token
@query
def subscriptions(after='MA==', first=20):
    q = Qry('webhooks/subscriptions', use_app_token=True)
    q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.FIRST, IntRange(1, 100).validate(first), 20)

    return q
