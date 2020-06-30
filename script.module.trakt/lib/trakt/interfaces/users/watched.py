from __future__ import absolute_import, division, print_function

from trakt.core.helpers import clean_username, dictfilter
from trakt.core.pagination import PaginationIterator
from trakt.interfaces.base import Interface, authenticated
from trakt.mapper import SyncMapper

import requests


class UsersWatchedInterface(Interface):
    path = 'users/*/watched'
    flags = {'is_watched': True}

    def get(self, username, media=None, store=None, extended=None, page=None, per_page=None, **kwargs):

        if not media or media not in ['shows', 'movies']:
            raise ValueError('The "media" have to be  one of ["shows", "media"]')

        # Build parameters
        params = []

        if media:
            params.append(media)

        # Build query
        query = {
            'extended': extended,
            'page': page,
            'limit': per_page
        }

        # Send request
        response = self.http.get(
            '/users/%s/watched' % (clean_username(username)),
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

    def movies(self, username, store=None, **kwargs):
        return self.get(
            username, 'movies',
            store=store,
            **kwargs
        )

    @authenticated
    def shows(self, username, store=None, **kwargs):
        return self.get(
            username, 'shows',
            store=store,
            **kwargs
        )
