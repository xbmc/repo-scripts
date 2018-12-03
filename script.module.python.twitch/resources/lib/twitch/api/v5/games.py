# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/v5/reference/games/

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ... import keys, methods
from ...queries import V5Query as Qry
from ...queries import HiddenApiQuery as HQry
from ...queries import query


# required scope: none
@query
def get_top(limit=10, offset=0):
    q = Qry('games/top', use_token=False)
    q.add_param(keys.LIMIT, limit, 10)
    q.add_param(keys.OFFSET, offset, 0)
    return q


# required scope: none
# undocumented / unsupported
@query
def _check_follows(username, name):
    q = HQry('users/{username}/follows/games/isFollowing', use_token=False)
    q.add_urlkw(keys.USERNAME, username)
    q.add_param(keys.NAME, name)
    return q


# required scope: none
# undocumented / unsupported
@query
def _get_followed(username, limit=25, offset=0):
    q = HQry('users/{username}/follows/games', use_token=False)
    q.add_urlkw(keys.USERNAME, username)
    q.add_param(keys.LIMIT, limit, 25)
    q.add_param(keys.OFFSET, offset, 0)
    return q


# required scope: user_follows_edit
# undocumented / unsupported
@query
def _follow(username, name):
    q = HQry('users/{username}/follows/games/follow', method=methods.PUT)
    q.add_urlkw(keys.USERNAME, username)
    q.add_data(keys.NAME, name)
    return q


# required scope: user_follows_edit
# undocumented / unsupported
@query
def _unfollow(username, name):
    q = HQry('users/{username}/follows/games/unfollow', method=methods.DELETE)
    q.add_urlkw(keys.USERNAME, username)
    q.add_data(keys.NAME, name)
    return q
