# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/v5/reference/streams/

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ... import keys
from ...api.parameters import Boolean, StreamType, Language, Platform
from ...queries import V5Query as Qry
from ...queries import query


# required scope: none
@query
def by_id(channel_id, stream_type=StreamType.LIVE):
    q = Qry('streams/{channel_id}', use_token=False)
    q.add_urlkw(keys.CHANNEL_ID, channel_id)
    q.add_param(keys.STREAM_TYPE, StreamType.validate(stream_type), StreamType.LIVE)
    return q


# required scope: none
# platform undocumented / unsupported
@query
def get_all(game=None, channel_ids=None, language=Language.ALL,
            stream_type=StreamType.LIVE, platform=Platform.ALL, limit=25, offset=0):
    q = Qry('streams', use_token=False)
    q.add_param(keys.GAME, game)
    q.add_param(keys.CHANNEL, channel_ids)
    q.add_param(keys.BROADCASTER_LANGUAGE, Language.validate(language), Language.ALL)
    q.add_param(keys.STREAM_TYPE, StreamType.validate(stream_type), StreamType.LIVE)
    platform = Platform.validate(platform)
    if platform == Platform.XBOX_ONE:
        q.add_param(keys.XBOX_HEARTBEAT, Boolean.TRUE)
    elif platform == Platform.PS4:
        q.add_param(keys.SCE_PLATFORM, 'PS4')
    q.add_param(keys.LIMIT, limit, 25)
    q.add_param(keys.OFFSET, offset, 0)
    return q


# required scope: none
@query
def get_summary(game=None):
    q = Qry('streams/summary', use_token=False)
    q.add_param(keys.GAME, game)
    return q


# required scope: none
@query
def get_featured(limit=25, offset=0):
    q = Qry('streams/featured', use_token=False)
    q.add_param(keys.LIMIT, limit, 25)
    q.add_param(keys.OFFSET, offset, 0)
    return q


# required scope: user_read
@query
def get_followed(stream_type=StreamType.LIVE, limit=25, offset=0):
    q = Qry('streams/followed')
    q.add_param(keys.STREAM_TYPE, StreamType.validate(stream_type), StreamType.LIVE)
    q.add_param(keys.LIMIT, limit, 25)
    q.add_param(keys.OFFSET, offset, 0)
    return q
