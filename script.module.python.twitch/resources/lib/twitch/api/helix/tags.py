# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/api/reference

    Copyright (C) 2016-2019 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ..parameters import Cursor, IntRange, ItemCount
from ... import keys, methods
from ...queries import HelixQuery as Qry
from ...queries import query


# required scope: none
# requires app access token
@query
def get_all_stream_tags(tag_id, after='MA==', first=20):
    q = Qry('tags/streams', use_app_token=True, method=methods.GET)
    q.add_param(keys.TAG_ID, ItemCount().validate(tag_id), list())
    q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.FIRST, IntRange(1, 100).validate(first), 20)

    return q


# required scope: none
# requires app access token
@query
def get_stream_tags(broadcaster_id):
    q = Qry('streams/tags', use_app_token=True, method=methods.GET)
    q.add_param(keys.BROADCASTER_ID, broadcaster_id)

    return q


# required scope: user:edit:broadcast
@query
def replace_stream_tags(broadcaster_id, tag_ids=list()):
    q = Qry('tags/streams', use_app_token=False, method=methods.PUT)
    q.add_param(keys.BROADCASTER_ID, broadcaster_id)
    q.add_param(keys.TAG_IDS, ItemCount().validate(tag_ids), list())

    return q
