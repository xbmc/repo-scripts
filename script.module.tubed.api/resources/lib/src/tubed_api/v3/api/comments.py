# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

from ..query import V3Query
from ..query import query


# https://developers.google.com/youtube/v3/docs/comments/list
@query
def get(parameters=None, unauthorized=False):
    return V3Query('get', 'comments', parameters=parameters, unauthorized=unauthorized)


# https://developers.google.com/youtube/v3/docs/comments/insert
@query
def insert(parameters=None, data=None):
    return V3Query('post', 'comments', parameters=parameters, data=data)


# https://developers.google.com/youtube/v3/docs/comments/update
@query
def update(parameters=None, data=None):
    return V3Query('put', 'comments', parameters=parameters, data=data)


# https://developers.google.com/youtube/v3/docs/comments/markAsSpam
@query
def mark_as_spam(parameters=None):
    return V3Query('post', 'comments/markAsSpam', parameters=parameters)


# https://developers.google.com/youtube/v3/docs/comments/setModerationStatus
@query
def set_moderation_status(parameters=None):
    return V3Query('post', 'comments/setModerationStatus', parameters=parameters)


# https://developers.google.com/youtube/v3/docs/comments/delete
@query
def delete(parameters=None):
    return V3Query('delete', 'comments', parameters=parameters)
