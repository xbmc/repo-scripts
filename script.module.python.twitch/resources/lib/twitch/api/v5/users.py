# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/v5/reference/users/

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ... import keys, methods
from ...api.parameters import Boolean, Direction, SortBy
from ...queries import V5Query as Qry
from ...queries import GQLQuery as GQLQry
from ...queries import query


# required scope: user_read
@query
def user():
    q = Qry('user')
    return q


# required scope: none
@query
def by_id(user_id):
    q = Qry('users/{user_id}', use_token=False)
    q.add_urlkw(keys.USER_ID, user_id)
    return q


# required scope: user_read
@query
def users(logins):
    q = Qry('users')
    q.add_param(keys.LOGIN, logins)
    return q


# required scope: user_subscriptions
@query
def get_emotes(user_id):
    q = Qry('users/{user_id}/emotes')
    q.add_urlkw(keys.USER_ID, user_id)
    return q


# required scope: user_subscriptions
@query
def check_subscription(user_id, channel_id):
    q = Qry('users/{user_id}/subscriptions/{channel_id}')
    q.add_urlkw(keys.USER_ID, user_id)
    q.add_urlkw(keys.CHANNEL_ID, channel_id)
    return q


# required scope: none
@query
def get_follows(user_id, limit=25, offset=0, direction=Direction.DESC,
                sort_by=SortBy.CREATED_AT):
    q = Qry('users/{user_id}/follows/channels', use_token=False)
    q.add_urlkw(keys.USER_ID, user_id)
    q.add_param(keys.LIMIT, limit, 25)
    q.add_param(keys.OFFSET, offset, 0)
    q.add_param(keys.DIRECTION, direction, Direction.DESC)
    q.add_param(keys.SORT_BY, sort_by, SortBy.CREATED_AT)
    return q


# required scope: none
@query
def check_follows(user_id, channel_id):
    q = Qry('users/{user_id}/follows/channels/{channel_id}', use_token=False)
    q.add_urlkw(keys.USER_ID, user_id)
    q.add_urlkw(keys.CHANNEL_ID, channel_id)
    return q


# required scope: user_follows_edit
@query
def follow_channel(channel_id, headers={}, notifications=False):
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
def unfollow_channel(channel_id, headers={}):
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


# required scope: user_blocks_read
@query
def get_blocks(user_id, limit=25, offset=0):
    q = Qry('users/{user_id}/blocks')
    q.add_urlkw(keys.USER_ID, user_id)
    q.add_param(keys.LIMIT, limit, 25)
    q.add_param(keys.OFFSET, offset, 0)
    return q


# required scope: user_blocks_edit
@query
def block_user(user_id, target_id):
    q = Qry('users/{user_id}/blocks/{target_id}', method=methods.PUT)
    q.add_urlkw(keys.USER_ID, user_id)
    q.add_urlkw(keys.TARGET_ID, target_id)
    return q


# required scope: user_blocks_edit
@query
def unblock_user(user_id, target_id):
    q = Qry('users/{user_id}/blocks/{target_id}', method=methods.DELETE)
    q.add_urlkw(keys.USER_ID, user_id)
    q.add_urlkw(keys.TARGET_ID, target_id)
    return q


# required scope: viewing_activity_read
@query
def create_connection_to_vhs(identifier):
    q = Qry('user/vhs', method=methods.PUT)
    q.add_data(keys.IDENTIFIER, identifier)
    return q


# required scope: user_read
@query
def check_connection_to_vhs():
    q = Qry('user/vhs')
    return q


# required scope: viewing_activity_read
@query
def delete_connection_to_vhs():
    q = Qry('user/vhs', method=methods.DELETE)
    return q
