# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/v5/reference/collections/

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ... import keys, methods
from ...api.parameters import Boolean, Cursor
from ...queries import V5Query as Qry
from ...queries import query


# required scope: none
@query
def get_metadata(collection_id):
    q = Qry('collections/{collection_id}', use_token=False)
    q.add_urlkw(keys.COLLECTION_ID, collection_id)
    return q


# required scope: none
@query
def by_id(collection_id, include_all=Boolean.FALSE):
    q = Qry('collections/{collection_id}/items', use_token=False)
    q.add_urlkw(keys.COLLECTION_ID, collection_id)
    q.add_param(keys.INCLUDE_ALL_ITEMS, Boolean.validate(include_all), Boolean.FALSE)
    return q


# required scope: none
@query
def get_collections(channel_id, limit=10, cursor='MA==', containing_item=None):
    q = Qry('channels/{channel_id}/collections', use_token=False)
    q.add_urlkw(keys.CHANNEL_ID, channel_id)
    q.add_param(keys.LIMIT, limit, 10)
    q.add_param(keys.CURSOR, Cursor.validate(cursor), 'MA==')
    q.add_param(keys.CONTAINING_ITEM, containing_item, None)  # 'video:<video_id>'
    return q


# required scope: collections_edit
@query
def create(channel_id, title):
    q = Qry('channels/{channel_id}/collections', method=methods.POST)
    q.add_urlkw(keys.CHANNEL_ID, channel_id)
    q.add_data(keys.TITLE, title)
    return q


# required scope: collections_edit
@query
def update(collection_id, title):
    q = Qry('collections/{collection_id}', method=methods.PUT)
    q.add_urlkw(keys.COLLECTION_ID, collection_id)
    q.add_data(keys.TITLE, title)
    return q


# required scope: collections_edit
@query
def create_thumbnail(collection_id, item_id):
    q = Qry('collections/{collection_id}/thumbnail', method=methods.PUT)
    q.add_urlkw(keys.COLLECTION_ID, collection_id)
    q.add_data(keys.ITEM_ID, item_id)
    return q


# required scope: collections_edit
@query
def delete(collection_id):
    q = Qry('collections/{collection_id}', method=methods.DELETE)
    q.add_urlkw(keys.COLLECTION_ID, collection_id)
    return q


# required scope: collections_edit
@query
def add_to_collection(collection_id, video_id):
    q = Qry('collections/{collection_id}/items', method=methods.POST)
    q.add_urlkw(keys.COLLECTION_ID, collection_id)
    q.add_data(keys.ID, video_id)
    q.add_data(keys.TYPE, 'video')  # must be 'video'
    return q


# required scope: collections_edit
@query
def delete_from_collection(collection_id, item_id):
    q = Qry('collections/{collection_id}/items/{item_id}', method=methods.DELETE)
    q.add_urlkw(keys.COLLECTION_ID, collection_id)
    q.add_urlkw(keys.ITEM_ID, item_id)
    return q


# required scope: collections_edit
@query
def move_in_collection(collection_id, item_id, position):
    q = Qry('collections/{collection_id}/items/{item_id}', method=methods.PUT)
    q.add_urlkw(keys.COLLECTION_ID, collection_id)
    q.add_urlkw(keys.ITEM_ID, item_id)
    q.add_data(keys.POSITION, position)
    return q
