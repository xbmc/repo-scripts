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
def get_follows(from_id='', to_id='', after='MA==', before='MA==', first=20, use_app_token=False):
    q = Qry('users/follows', use_app_token=use_app_token)
    q.add_param(keys.FROM_ID, from_id, '')
    q.add_param(keys.TO_ID, to_id, '')
    q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.BEFORE, Cursor.validate(before), 'MA==')
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
