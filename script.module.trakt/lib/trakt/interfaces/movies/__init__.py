from __future__ import absolute_import, division, print_function

from trakt.core.helpers import dictfilter
from trakt.core.pagination import PaginationIterator
from trakt.interfaces.base import Interface
from trakt.mapper.summary import SummaryMapper

import requests


class MoviesInterface(Interface):
    path = 'movies'

    def get(self, id, extended=None, **kwargs):
        response = self.http.get(str(id), query={
            'extended': extended
        })

        items = self.get_data(response, **kwargs)

        if isinstance(items, requests.Response):
            return items

        # Parse response
        return SummaryMapper.movie(self.client, items)

    def trending(self, extended=None, page=None, per_page=None, **kwargs):
        response = self.http.get('trending', query={
            'extended': extended,
            'page': page,
            'limit': per_page
        }, **dictfilter(kwargs, get=[
            'exceptions'
        ], pop=[
            'pagination'
        ]))

        # Parse response
        items = self.get_data(response, **kwargs)

        if isinstance(items, PaginationIterator):
            return items.with_mapper(lambda items: SummaryMapper.movies(self.client, items))

        if isinstance(items, requests.Response):
            return items

        return SummaryMapper.movies(self.client, items)
