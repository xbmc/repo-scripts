from __future__ import absolute_import, division, print_function

from trakt.core.helpers import clean_username, dictfilter
from trakt.core.pagination import PaginationIterator
from trakt.interfaces.base import Interface, authenticated
from trakt.mapper import SyncMapper

import requests


class UsersRatingsInterface(Interface):
    path = 'users/*/ratings'

    def get(self, username, media=None, rating=None, store=None, extended=None,
            page=None, per_page=None, **kwargs):

        # Build parameters
        params = []

        if media:
            params.append(media)

        if rating is not None:
            params.append(rating)

        # Build query
        query = {
            'extended': extended,
            'page': page,
            'limit': per_page
        }

        # Send request
        response = self.http.get(
            '/users/%s/ratings' % (clean_username(username)),
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
                flat=True
            ))

        if isinstance(items, requests.Response):
            return items

        if type(items) is not list:
            return None

        # Map items
        return SyncMapper.process(
            self.client, store, items,
            media=media,
            flat=True
        )

    #
    # Shortcut methods
    #

    @authenticated
    def all(self, username, rating=None, store=None, **kwargs):
        return self.get(
            username, 'all',
            rating=rating,
            store=store,
            **kwargs
        )

    @authenticated
    def movies(self, username, rating=None, store=None, **kwargs):
        return self.get(
            username, 'movies',
            rating=rating,
            store=store,
            **kwargs
        )

    @authenticated
    def shows(self, username, rating=None, store=None, **kwargs):
        return self.get(
            username, 'shows',
            rating=rating,
            store=store,
            **kwargs
        )

    @authenticated
    def seasons(self, username, rating=None, store=None, **kwargs):
        return self.get(
            username, 'seasons',
            rating=rating,
            store=store,
            **kwargs
        )

    @authenticated
    def episodes(self, username, rating=None, store=None, **kwargs):
        return self.get(
            username, 'episodes',
            rating=rating,
            store=store,
            **kwargs
        )
