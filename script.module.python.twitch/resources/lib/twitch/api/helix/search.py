# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/api/reference

    Copyright (C) 2022- script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ... import keys
from ...api.parameters import Boolean, Cursor, IntRange
from ...queries import HelixQuery as Qry
from ...queries import query


# required scope: none
@query
def get_categories(search_query, after='MA==', first=20, use_app_token=False):
    q = Qry('search/categories', use_app_token=use_app_token)
    q.add_param(keys.QUERY, search_query)
    q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.FIRST, IntRange(1, 100).validate(first), 20)

    return q


# required scope: none
@query
def get_channels(search_query, after='MA==', first=20, live_only=True, use_app_token=False):
    q = Qry('search/channels', use_app_token=use_app_token)
    q.add_param(keys.QUERY, search_query)
    q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.FIRST, IntRange(1, 100).validate(first), 20)
    q.add_param(keys.LIVE_ONLY, Boolean.validate(live_only), Boolean.FALSE)

    return q
