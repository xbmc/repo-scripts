# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/api/reference

    Copyright (C) 2016-2019 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ... import keys
from ...api.parameters import Cursor, Language, IntRange, ItemCount
from ... import methods
from ...queries import HelixQuery as Qry
from ...queries import query


# required scope: none
@query
def get_streams(game_id=list(), user_id=list(),
                user_login=list(), language=list(), after='MA==',
                before='MA==', first=20, use_app_token=False):
    q = Qry('streams', use_app_token=use_app_token)
    q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.BEFORE, Cursor.validate(before), 'MA==')
    q.add_param(keys.FIRST, IntRange(1, 100).validate(first), 20)
    q.add_param(keys.GAME_ID, ItemCount().validate(game_id), list())
    q.add_param(keys.USER_ID, ItemCount().validate(user_id), list())
    q.add_param(keys.USER_LOGIN, ItemCount().validate(user_login), list())
    if isinstance(language, list):
        _language = [lang for lang in language if lang in Language.valid()]
        q.add_param(keys.LANGUAGE, ItemCount().validate(_language), list())
    else:
        q.add_param(keys.LANGUAGE, Language.validate(language), '')

    return q


# required scope: user:read:follows
@query
def get_followed(user_id, after='MA==', first=20, use_app_token=False):
    q = Qry('streams/followed', use_app_token=use_app_token)
    q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.FIRST, IntRange(1, 100).validate(first), 20)
    q.add_param(keys.USER_ID, user_id)

    return q


# required scope: none
@query
def get_metadata(game_id=list(), user_id=list(),
                 user_login=list(), language=list(), after='MA==',
                 before='MA==', first=20, use_app_token=False):
    q = Qry('streams/metadata', use_app_token=use_app_token)
    q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.BEFORE, Cursor.validate(before), 'MA==')
    q.add_param(keys.FIRST, IntRange(1, 100).validate(first), 20)
    q.add_param(keys.GAME_ID, ItemCount().validate(game_id), list())
    q.add_param(keys.USER_ID, ItemCount().validate(user_id), list())
    q.add_param(keys.USER_LOGIN, ItemCount().validate(user_login), list())
    if isinstance(language, list):
        _language = [lang for lang in language if lang in Language.valid()]
        q.add_param(keys.LANGUAGE, ItemCount().validate(_language), list())
    else:
        q.add_param(keys.LANGUAGE, Language.validate(language), '')

    return q


# required scope: user:edit:broadcast
@query
def create_stream_marker(user_id, description=''):
    q = Qry('streams/markers', use_app_token=False, method=methods.POST)
    q.add_param(keys.USER_ID, user_id)
    q.add_param(keys.DESCRIPTION, description, '')

    return q


# required scope: user:read:broadcast
@query
def get_stream_markers(user_id, video_id, after='MA==', before='MA==', first=20):
    q = Qry('streams/markers', use_app_token=False, method=methods.GET)
    q.add_param(keys.USER_ID, user_id)
    q.add_param(keys.VIDEO_ID, video_id)
    q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.BEFORE, Cursor.validate(before), 'MA==')
    q.add_param(keys.FIRST, IntRange(1, 100).validate(first), 20)

    return q
