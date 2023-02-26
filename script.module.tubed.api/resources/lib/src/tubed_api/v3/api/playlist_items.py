# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

from ..query import V3Query
from ..query import query


# https://developers.google.com/youtube/v3/docs/playlistItems/list
@query
def get(parameters=None):
    return V3Query('get', 'playlistItems', parameters=parameters)


# https://developers.google.com/youtube/v3/docs/playlistItems/insert
@query
def insert(parameters=None, data=None):
    return V3Query('post', 'playlistItems', parameters=parameters, data=data)


# https://developers.google.com/youtube/v3/docs/playlistItems/update
@query
def update(parameters=None, data=None):
    return V3Query('put', 'playlistItems', parameters=parameters, data=data)


# https://developers.google.com/youtube/v3/docs/playlistItems/delete
@query
def delete(parameters=None):
    return V3Query('delete', 'playlistItems', parameters=parameters)
