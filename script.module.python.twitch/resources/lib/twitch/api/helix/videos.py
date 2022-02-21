# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/api/reference

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ... import keys
from ...api.parameters import Cursor, Language, BroadcastTypeHelix, VideoSortHelix, PeriodHelix, IntRange, ItemCount
from ...queries import HelixQuery as Qry
from ...queries import HiddenApiQuery as HQry
from ...queries import query


# required scope: none
@query
def get_videos(video_id=list(), game_id='', user_id='',
               broadcast_type=BroadcastTypeHelix.ALL, language='',
               after='MA==', before='MA==', first=20,
               sort_order=VideoSortHelix.TIME, period=PeriodHelix.ALL, use_app_token=False):
    q = Qry('videos', use_app_token=use_app_token)
    if not video_id:
        q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
        q.add_param(keys.BEFORE, Cursor.validate(before), 'MA==')
        q.add_param(keys.FIRST, IntRange(1, 100).validate(first), 20)
        q.add_param(keys.GAME_ID, game_id, '')
        q.add_param(keys.USER_ID, user_id, '')
        q.add_param(keys.TYPE, BroadcastTypeHelix.validate(broadcast_type), BroadcastTypeHelix.ALL)
        q.add_param(keys.SORT, VideoSortHelix.validate(sort_order), VideoSortHelix.TIME)
        q.add_param(keys.PERIOD, PeriodHelix.validate(period), PeriodHelix.ALL)
        if language:
            q.add_param(keys.LANGUAGE, Language.validate(language), '')
    else:
        q.add_param(keys.ID, ItemCount().validate(video_id), list())

    return q


# required scope: none
# undocumented / unsupported
@query
def _by_id(video_id, headers={}):
    q = HQry('videos/{video_id}', headers=headers, use_token=False)
    q.add_urlkw(keys.VIDEO_ID, video_id)
    return q
