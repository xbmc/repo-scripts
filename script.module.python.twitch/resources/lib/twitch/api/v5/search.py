# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/v5/reference/search/

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ... import keys
from ...api.parameters import Boolean
from ...queries import V5Query as Qry
from ...queries import query


# required scope: none
@query
def channels(search_query, limit=25, offset=0):
    q = Qry('search/channels', use_token=False)
    q.add_param(keys.QUERY, search_query)
    q.add_param(keys.LIMIT, limit, 25)
    q.add_param(keys.OFFSET, offset, 0)
    return q


# required scope: none
@query
def games(search_query, live=Boolean.FALSE):
    q = Qry('search/games', use_token=False)
    q.add_param(keys.QUERY, search_query)
    q.add_param(keys.TYPE, 'suggest')  # 'type' can currently only be suggest, so it is hardcoded

    q.add_param(keys.LIVE, live, Boolean.FALSE)
    return q


# required scope: none
@query
def streams(search_query, limit=25, offset=0, hls=Boolean.FALSE):
    q = Qry('search/streams', use_token=False)
    q.add_param(keys.QUERY, search_query)
    q.add_param(keys.LIMIT, limit, 25)
    q.add_param(keys.OFFSET, offset, 0)
    q.add_param(keys.HLS, hls, Boolean.FALSE)
    return q
