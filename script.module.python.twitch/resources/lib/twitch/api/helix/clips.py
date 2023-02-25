# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/api/reference

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ..parameters import Boolean, Cursor, IntRange, ItemCount
from ... import keys, methods
from ...queries import HelixQuery as Qry
from ...queries import query


# required scope: none
@query
def get_clip(broadcaster_id='', game_id='', clip_id=list(),
             after='MA==', before='MA==', first=20, use_app_token=False):
    q = Qry('clips', use_app_token=use_app_token)
    q.add_param(keys.ID, ItemCount().validate(clip_id), list())
    if len(clip_id) != 1:
        q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
        q.add_param(keys.BEFORE, Cursor.validate(before), 'MA==')
        q.add_param(keys.FIRST, IntRange(1, 100).validate(first), 20)
        q.add_param(keys.BROADCASTER_ID, broadcaster_id, '')
        q.add_param(keys.GAME_ID, game_id, '')
        q.add_param(keys.ID, ItemCount().validate(clip_id), list())

    return q


# required scope: clips:edit
@query
def create_clip(broadcaster_id, has_delay=Boolean.FALSE, use_app_token=False):
    q = Qry('clips', use_app_token=use_app_token, method=methods.POST)
    q.add_param(keys.BROADCASTER_ID, broadcaster_id, '')
    q.add_param(keys.HAS_DELAY, Boolean.validate(has_delay), Boolean.FALSE)

    return q
