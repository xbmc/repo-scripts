# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

from ..query import V3Query
from ..query import query


# https://developers.google.com/youtube/v3/docs/commentThreads/list
@query
def get(parameters=None, unauthorized=False):
    return V3Query('get', 'commentThreads', parameters=parameters, unauthorized=unauthorized)


# https://developers.google.com/youtube/v3/docs/commentThreads/insert
@query
def insert(parameters=None, data=None):
    return V3Query('post', 'commentThreads', parameters=parameters, data=data)


# https://developers.google.com/youtube/v3/docs/commentThreads/update
@query
def update(parameters=None, data=None):
    return V3Query('put', 'commentThreads', parameters=parameters, data=data)
