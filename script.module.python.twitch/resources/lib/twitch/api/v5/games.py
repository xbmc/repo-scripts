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
from ...queries import GQLQuery as GQLQry
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
def _check_follows(username, name, headers={}):
    q = HQry('users/{username}/follows/games/isFollowing', headers=headers, use_token=False)
    q.add_urlkw(keys.USERNAME, username)
    q.add_param(keys.NAME, name)
    return q


# required scope: none
# undocumented / unsupported
@query
def _get_followed(limit=100, headers={}):
    data = [{
        "operationName": "FollowingGames_CurrentUser",
        "variables": {
            "limit": limit,
            "type": "LIVE"
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "8446d4d234005813dc1f024f487ce95434c3e4202f451dd42777935b5ed035ce"
            }
        }
    }]
    q = GQLQry('', headers=headers, data=data, use_token=False)
    return q


# required scope: user_follows_edit
# undocumented / unsupported
@query
def _follow(game_id, headers={}):
    data = [{
        "operationName": "FollowGameButton_FollowGame",
        "variables": {
            "input": {
                "gameID": str(game_id)
            }
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "b846b65ba4bc9a3561dbe2d069d95deed9b9e031bcfda2482d1bedd84a1c2eb3"
            }
        }
    }]
    q = GQLQry('', headers=headers, data=data, use_token=False)
    return q


# required scope: user_follows_edit
# undocumented / unsupported
@query
def _unfollow(game_id, headers={}):
    data = [{
        "operationName": "FollowGameButton_UnfollowGame",
        "variables": {
            "input": {
                "gameID": str(game_id)
            }
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "811e02e396ebba0664f21ff002f2eff3c6f57e8af9aedb4f4dfa77cefd0db43d"
            }
        }
    }]
    q = GQLQry('', headers=headers, data=data, use_token=False)
    return q
