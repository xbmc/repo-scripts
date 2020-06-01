from __future__ import absolute_import, division, print_function

from trakt.core.helpers import dictfilter
from trakt.core.pagination import PaginationIterator
from trakt.interfaces.base import Interface, authenticated
from trakt.mapper.sync import SyncMapper

import requests


class Get(Interface):
    flags = {}

    @authenticated
    def get(self, media=None, store=None, params=None, query=None, flat=False, **kwargs):
        if not params:
            params = []

        params.insert(0, media)

        # Request resource
        response = self.http.get(
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
            if not flat:
                raise ValueError('Pagination is only supported with `flat=True`')

            return items.with_mapper(lambda items: SyncMapper.process(
                self.client, store, items,
                media=media,
                flat=flat,
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
            flat=flat,
            **self.flags
        )

    #
    # Shortcut methods
    #

    @authenticated
    def movies(self, store=None, **kwargs):
        return self.get(
            'movies',
            store=store,
            **kwargs
        )

    @authenticated
    def shows(self, store=None, **kwargs):
        return self.get(
            'shows',
            store=store,
            **kwargs
        )


class Add(Interface):
    @authenticated
    def add(self, items, **kwargs):
        response = self.http.post(
            data=items,
            **dictfilter(kwargs, pop=[
                'authenticated',
                'validate_token'
            ])
        )

        return self.get_data(response, **kwargs)


class Remove(Interface):
    @authenticated
    def remove(self, items, **kwargs):
        response = self.http.post(
            'remove',
            data=items,
            **dictfilter(kwargs, pop=[
                'authenticated',
                'validate_token'
            ])
        )

        return self.get_data(response, **kwargs)


class Delete(Interface):
    @authenticated
    def delete(self, playbackid, **kwargs):
        response = self.http.delete(
            path=str(playbackid),
            **dictfilter(kwargs, pop=[
                'authenticated',
                'validate_token'
            ])
        )

        return 200 <= response.status_code < 300
