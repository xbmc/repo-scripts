# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

from ..query import V3Query
from ..query import query


# https://developers.google.com/youtube/v3/docs/captions/list
@query
def get(parameters=None):
    return V3Query('get', 'captions', parameters=parameters)


# https://developers.google.com/youtube/v3/docs/captions/insert
@query
def insert(parameters=None, data=None):
    return V3Query('post', 'captions', parameters=parameters, data=data)


# https://developers.google.com/youtube/v3/docs/captions/update
@query
def update(parameters=None, data=None):
    return V3Query('put', 'captions', parameters=parameters, data=data)


# https://developers.google.com/youtube/v3/docs/captions/download
@query
def download(caption_id, parameters=None):
    return V3Query('get', 'captions/{id}'.format(id=caption_id), parameters=parameters)


# https://developers.google.com/youtube/v3/docs/captions/delete
@query
def delete(parameters=None):
    return V3Query('delete', 'captions', parameters=parameters)
