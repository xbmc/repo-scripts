# -*- encoding: utf-8 -*-
# https://dev.twitch.tv/docs/api/reference

from twitch import keys
from twitch.api.parameters import Cursor, Language, StreamTypeHelix
from twitch.queries import HelixQuery as Qry
from twitch.queries import query


# required scope: none
@query
def get_streams(community_id=list(), game_id=list(), user_id=list(),
                user_login=list(), stream_type=StreamTypeHelix.ALL, language=list(),
                after='MA==', before='MA==', first=20, use_app_token=False):
    q = Qry('streams', use_app_token=use_app_token)
    q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.BEFORE, Cursor.validate(before), 'MA==')
    q.add_param(keys.FIRST, first, 20)
    q.add_param(keys.COMMUNITY_ID, community_id, list())
    q.add_param(keys.GAME_ID, game_id, list())
    q.add_param(keys.USER_ID, user_id, list())
    q.add_param(keys.USER_LOGIN, user_login, list())
    q.add_param(keys.TYPE, StreamTypeHelix.validate(stream_type), StreamTypeHelix.ALL)
    if isinstance(language, list):
        _language = [lang for lang in language if lang in Language.valid()]
        q.add_param(keys.LANGUAGE, _language, list())
    else:
        q.add_param(keys.LANGUAGE, Language.validate(language), '')

    return q


# required scope: none
@query
def get_metadata(community_id=list(), game_id=list(), user_id=list(),
                 user_login=list(), stream_type=StreamTypeHelix.ALL, language=list(),
                 after='MA==', before='MA==', first=20, use_app_token=False):
    q = Qry('streams/metadata', use_app_token=use_app_token)
    q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.BEFORE, Cursor.validate(before), 'MA==')
    q.add_param(keys.FIRST, first, 20)
    q.add_param(keys.COMMUNITY_ID, community_id, list())
    q.add_param(keys.GAME_ID, game_id, list())
    q.add_param(keys.USER_ID, user_id, list())
    q.add_param(keys.USER_LOGIN, user_login, list())
    q.add_param(keys.TYPE, StreamTypeHelix.validate(stream_type), StreamTypeHelix.ALL)
    if isinstance(language, list):
        _language = [lang for lang in language if lang in Language.valid()]
        q.add_param(keys.LANGUAGE, _language, list())
    else:
        q.add_param(keys.LANGUAGE, Language.validate(language), '')

    return q
