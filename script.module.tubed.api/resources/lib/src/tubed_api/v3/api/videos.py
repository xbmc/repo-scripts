# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

from ..query import V3Query
from ..query import query


# https://developers.google.com/youtube/v3/docs/videos/list
@query
def get(parameters=None):
    return V3Query('get', 'videos', parameters=parameters)


# https://developers.google.com/youtube/v3/docs/videos/insert
@query
def insert(parameters=None, data=None):
    return V3Query('post', 'videos', parameters=parameters, data=data)


# https://developers.google.com/youtube/v3/docs/videos/update
@query
def update(parameters=None, data=None):
    return V3Query('put', 'videos', parameters=parameters, data=data)


# https://developers.google.com/youtube/v3/docs/videos/rate
@query
def rate(parameters=None):
    return V3Query('post', 'videos/rate', parameters=parameters)


# https://developers.google.com/youtube/v3/docs/videos/getRating
@query
def get_rating(parameters=None):
    return V3Query('get', 'videos/getRating', parameters=parameters)


# https://developers.google.com/youtube/v3/docs/videos/reportAbuse
@query
def report_abuse(parameters=None, data=None):
    return V3Query('post', 'videos/reportAbuse', parameters=parameters, data=data)


# https://developers.google.com/youtube/v3/docs/videos/delete
@query
def delete(parameters=None):
    return V3Query('delete', 'videos', parameters=parameters)
