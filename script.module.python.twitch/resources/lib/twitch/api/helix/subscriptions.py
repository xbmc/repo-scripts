# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/api/reference

    Copyright (C) 2016-2019 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ..parameters import ItemCount
from ... import keys, methods
from ...queries import HelixQuery as Qry
from ...queries import query


# required scope: channel:read:subscriptions
@query
def get_broadcaster_subscriptions(broadcaster_id):
    q = Qry('subscriptions', use_app_token=False, method=methods.GET)
    q.add_param(keys.BROADCASTER_ID, broadcaster_id)

    return q


# required scope: channel:read:subscriptions
@query
def get_user_subscriptions(broadcaster_id, user_id):
    q = Qry('subscriptions', use_app_token=False, method=methods.GET)
    q.add_param(keys.BROADCASTER_ID, broadcaster_id)
    q.add_param(keys.USER_ID, ItemCount().validate(user_id), list())

    return q
