# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/api/reference

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ... import keys, methods
from ...api.parameters import Cursor, IntRange, ItemCount
from ...queries import GQLQuery as GQLQry
from ...queries import HelixQuery as Qry
from ...queries import query


# optional scope: user:read:email
@query
def get_users(user_id=list(), user_login=list(), use_app_token=False):
    use_token = (not user_id and not user_login)
    use_app_token = False if use_token else use_app_token
    q = Qry('users', use_app_token=use_app_token)
    q.add_param(keys.ID, ItemCount().validate(user_id), list())
    q.add_param(keys.LOGIN, ItemCount().validate(user_login), list())

    return q


# required scope: none
@query
def get_follows(user_id='', after='MA==', first=20, use_app_token=False):
    q = Qry('channels/followed', use_app_token=use_app_token)
    q.add_param(keys.USER_ID, user_id, '')
    q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.FIRST, IntRange(1, 100).validate(first), 20)

    return q


# required scope: user:edit
@query
def put_users(description):
    q = Qry('users', method=methods.PUT)
    q.add_param(keys.DESCRIPTION, description, '')

    return q


# required scope: user:read:broadcast
@query
def get_extensions():
    q = Qry('users/extensions/list')

    return q


# optional scope: user:read:broadcast or user:edit:broadcast
@query
def get_active_extensions(user_id=''):
    q = Qry('users/extensions')
    q.add_param(keys.USER_ID, user_id, '')

    return q


# required scope: user:edit:broadcast
@query
def update_extensions():
    q = Qry('users/extensions', method=methods.PUT)

    return q


# required scope: user_follows_edit
@query
def _follow_channel(channel_id, headers={}, notifications=False):
    data = [{
        "operationName": "FollowButton_FollowUser",
        "variables": {
            "input": {
                "disableNotifications": notifications,
                "targetID": str(channel_id)
            }
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "14319edb840c1dfce880dc64fa28a1f4eb69d821901e9e96eb9610d2e52b54f2"
            }
        }
    }]
    q = GQLQry('', headers=headers, data=data, use_token=False)
    return q


# required scope: user_follows_edit
@query
def _unfollow_channel(channel_id, headers={}):
    data = [{
        "operationName": "FollowButton_UnfollowUser",
        "variables": {
            "input": {
                "targetID": str(channel_id)
            }
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "29783a1dac24124e02f7295526241a9f1476cd2f5ce1e394f93ea50c253d8628"
            }
        }
    }]
    q = GQLQry('', headers=headers, data=data, use_token=False)
    return q
