from __future__ import absolute_import, division, print_function

from trakt.core.helpers import clean_username, dictfilter
from trakt.core.pagination import PaginationIterator
from trakt.interfaces.base import Interface, authenticated
from trakt.mapper import SyncMapper

import requests


class UsersWatchlistInterface(Interface):
    path = 'users/*/watchlist'
    flags = {'in_watchlist': True}

    def get(self, username, media=None, sort=None, store=None, extended=None,
            page=None, per_page=None, **kwargs):

        # Build parameters
        params = []

        if media:
            params.append(media)

        if sort:
            params.append(sort)

        # Build query
        query = {
            'extended': extended,
            'page': page,
            'limit': per_page
        }

        # Send request
        response = self.http.get(
            '/users/%s/watchlist' % (clean_username(username)),
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

        # Map items
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
    def movies(self, username, sort=None, store=None, **kwargs):
        return self.get(
            username, 'movies',
            sort=sort,
            store=store,
            **kwargs
        )

    @authenticated
    def shows(self, username, sort=None, store=None, **kwargs):
        return self.get(
            username, 'shows',
            sort=sort,
            store=store,
            **kwargs
        )

    @authenticated
    def seasons(self, username, sort=None, store=None, **kwargs):
        return self.get(
            username, 'seasons',
            sort=sort,
            store=store,
            **kwargs
        )

    @authenticated
    def episodes(self, username, sort=None, store=None, **kwargs):
        return self.get(
            username, 'episodes',
            sort=sort,
            store=store,
            **kwargs
        )
