# -*- encoding: utf-8 -*-
# https://dev.twitch.tv/docs/api/reference

from twitch import keys
from twitch.api.parameters import Cursor, Language, BroadcastTypeHelix, VideoSortHelix, PeriodHelix
from twitch.queries import HelixQuery as Qry
from twitch.queries import query


# required scope: none
@query
def get_videos(video_id=list(), game_id=list(), user_id=list(),
               broadcast_type=BroadcastTypeHelix.ALL, language='',
               after='MA==', before='MA==', first=20,
               sort_order=VideoSortHelix.TIME, period=PeriodHelix.ALL, use_app_token=False):
    q = Qry('videos', use_app_token=use_app_token)
    if not video_id:
        q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
        q.add_param(keys.BEFORE, Cursor.validate(before), 'MA==')
        q.add_param(keys.FIRST, first, 20)
        q.add_param(keys.GAME_ID, game_id, list())
        q.add_param(keys.USER_ID, user_id, list())
        q.add_param(keys.TYPE, BroadcastTypeHelix.validate(broadcast_type), BroadcastTypeHelix.ALL)
        q.add_param(keys.SORT, VideoSortHelix.validate(sort_order), VideoSortHelix.TIME)
        q.add_param(keys.PERIOD, PeriodHelix.validate(period), PeriodHelix.ALL)
        if language:
            q.add_param(keys.LANGUAGE, Language.validate(language), '')
    else:
        q.add_param(keys.ID, video_id, list())

    return q
