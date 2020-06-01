from __future__ import absolute_import, division, print_function

from trakt.core.helpers import clean_username, dictfilter, to_iso8601_datetime
from trakt.core.pagination import PaginationIterator
from trakt.interfaces.base import Interface, authenticated
from trakt.mapper import SyncMapper

import requests


class UsersHistoryInterface(Interface):
    path = 'users/*/history'
    flags = {'is_watched': True}

    def get(self, username, media=None, id=None, start_at=None, end_at=None, store=None,
            extended=None, page=None, per_page=None, **kwargs):

        if not media and id:
            raise ValueError('The "id" parameter also requires the "media" parameter to be defined')

        # Build parameters
        params = []

        if media:
            params.append(media)

        if id:
            params.append(id)

        # Build query
        query = {
            'extended': extended,
            'page': page,
            'limit': per_page
        }

        if start_at:
            query['start_at'] = to_iso8601_datetime(start_at)

        if end_at:
            query['end_at'] = to_iso8601_datetime(end_at)

        # Send request
        response = self.http.get(
            '/users/%s/history' % (clean_username(username)),
            params=params,
            query=query,
            **dictfilter(kwargs, get=[
                'exceptions'
            ], pop=[
                'authenticated',
                'pagination',
                'validate_token'
            ])
        )

        # Parse response
        items = self.get_data(response, **kwargs)

        if isinstance(items, PaginationIterator):
            return items.with_mapper(lambda items: SyncMapper.process(
                self.client, store, items,
                media=media,
                flat=True,
                **self.flags
            ))

        if isinstance(items, requests.Response):
            return items

        if type(items) is not list:
            return None

        return SyncMapper.process(
            self.client, store, items,
            media=media,
            flat=True,
            **self.flags
        )

    #
    # Shortcut methods
    #

    @authenticated
    def movies(self, username, id=None, start_at=None, end_at=None, store=None, **kwargs):
        return self.get(
            username, 'movies',
            id=id,
            start_at=start_at,
            end_at=end_at,
            store=store,
            **kwargs
        )

    @authenticated
    def shows(self, username, id=None, start_at=None, end_at=None, store=None, **kwargs):
        return self.get(
            username, 'shows',
            id=id,
            start_at=start_at,
            end_at=end_at,
            store=store,
            **kwargs
        )

    @authenticated
    def seasons(self, username, id=None, start_at=None, end_at=None, store=None, **kwargs):
        return self.get(
            username, 'seasons',
            id=id,
            start_at=start_at,
            end_at=end_at,
            store=store,
            **kwargs
        )

    @authenticated
    def episodes(self, username, id=None, start_at=None, end_at=None, store=None, **kwargs):
        return self.get(
            username, 'episodes',
            id=id,
            start_at=start_at,
            end_at=end_at,
            store=store,
            **kwargs
        )
