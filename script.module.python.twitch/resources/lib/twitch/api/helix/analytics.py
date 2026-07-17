# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/api/reference

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ..parameters import IntRange, Cursor, ReportType
from ... import keys
from ...queries import HelixQuery as Qry
from ...queries import query


# required scope: analytics:read:extensions
@query
def extensions(started_at='', ended_at='', extension_id='', report_type='', after='MA==', first=20, use_app_token=False):
    q = Qry('analytics/extensions', use_app_token=use_app_token)
    q.add_param(keys.STARTED_AT, started_at, '')
    q.add_param(keys.ENDED_AT, ended_at, '')
    q.add_param(keys.EXTENSION_ID, extension_id, '')
    if report_type:
        q.add_param(keys.TYPE, ReportType.validate(report_type))
    if not extension_id:
        q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.FIRST, IntRange(1, 100).validate(first), 20)

    return q


# required scope: analytics:read:games
@query
def games(started_at='', ended_at='', game_id='', report_type='', after='MA==', first=20, use_app_token=False):
    q = Qry('analytics/games', use_app_token=use_app_token)
    q.add_param(keys.STARTED_AT, started_at, '')
    q.add_param(keys.ENDED_AT, ended_at, '')
    q.add_param(keys.GAME_ID, game_id, '')
    if report_type:
        q.add_param(keys.TYPE, ReportType.validate(report_type))
    if not game_id:
        q.add_param(keys.AFTER, Cursor.validate(after), 'MA==')
    q.add_param(keys.FIRST, IntRange(1, 100).validate(first), 20)

    return q
