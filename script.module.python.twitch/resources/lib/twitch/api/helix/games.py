# -*- encoding: utf-8 -*-
# https://dev.twitch.tv/docs/api/reference

from twitch import keys
from twitch.api.parameters import Cursor
from twitch.queries import HelixQuery as Qry
from twitch.queries import query


# required scope: none
@query
def get_games(game_id=list(), game_name=list(), use_app_token=False):
    q = Qry('games', use_app_token=use_app_token)
    q.add_param(keys.ID, game_id, list())
    q.add_param(keys.NAME, game_name, list())
    return q


# required scope: none
@query
def get_top(after='MA==', before='MA==', first=20, use_app_token=False):
    q = Qry('games/top', use_app_token=use_app_token)
    q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.BEFORE, Cursor.validate(before), 'MA==')
    q.add_param(keys.FIRST, first, 20)

    return q
