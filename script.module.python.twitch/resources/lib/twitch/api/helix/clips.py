# -*- encoding: utf-8 -*-
# https://dev.twitch.tv/docs/api/reference

from twitch import keys, methods
from twitch.queries import HelixQuery as Qry
from twitch.queries import query


# required scope: none
@query
def get_clip(clip_id, use_app_token=False):
    q = Qry('clips', use_app_token=use_app_token)
    q.add_param(keys.ID, clip_id, '')

    return q


# required scope: clips:edit
@query
def create_clip(broadcaster_id, use_app_token=False):
    q = Qry('clips', use_app_token=use_app_token, method=methods.POST)
    q.add_param(keys.BROADCASTER_ID, broadcaster_id, '')

    return q
