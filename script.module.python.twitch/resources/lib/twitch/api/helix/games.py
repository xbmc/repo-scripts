# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/api/reference

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ... import keys
from ...api.parameters import Cursor, IntRange, ItemCount
from ...queries import HelixQuery as Qry
from ...queries import query


# required scope: none
@query
def get_games(game_id=list(), game_name=list(), use_app_token=False):
    q = Qry('games', use_app_token=use_app_token)
    q.add_param(keys.ID, ItemCount().validate(game_id), list())
    q.add_param(keys.NAME, ItemCount().validate(game_name), list())

    return q


# required scope: none
@query
def get_top(after='MA==', before='MA==', first=20, use_app_token=False):
    q = Qry('games/top', use_app_token=use_app_token)
    q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.BEFORE, Cursor.validate(before), 'MA==')
    q.add_param(keys.FIRST, IntRange(1, 100).validate(first), 20)

    return q
