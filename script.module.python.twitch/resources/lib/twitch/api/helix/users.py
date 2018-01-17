# -*- encoding: utf-8 -*-
# https://dev.twitch.tv/docs/api/reference

from twitch import keys, methods
from twitch.api.parameters import Cursor
from twitch.queries import HelixQuery as Qry
from twitch.queries import query


# optional scope: user:read:email
@query
def get_users(user_id=list(), user_login=list(), use_app_token=False):
    use_token = (not user_id and not user_login)
    use_app_token = False if use_token else use_app_token
    q = Qry('users', use_app_token=use_app_token)
    q.add_param(keys.ID, user_id, list())
    q.add_param(keys.LOGIN, user_login, list())
    return q


# required scope: none
@query
def get_follows(from_id='', to_id='', after='MA==', before='MA==', first=20, use_app_token=False):
    q = Qry('users/follows', use_app_token=use_app_token)
    q.add_param(keys.FROM_ID, from_id, '')
    q.add_param(keys.TO_ID, to_id, '')
    q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.BEFORE, Cursor.validate(before), 'MA==')
    q.add_param(keys.FIRST, first, 20)
    return q


# required scope: user:edit
@query
def put_users(description):
    q = Qry('users', method=methods.PUT)
    q.add_param(keys.DESCRIPTION, description, '')
    return q
