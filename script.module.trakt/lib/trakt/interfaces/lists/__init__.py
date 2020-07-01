from __future__ import absolute_import, division, print_function

from trakt.core.helpers import dictfilter
from trakt.core.pagination import PaginationIterator
from trakt.interfaces.base import Interface
from trakt.mapper import ListMapper

import requests


class ListsInterface(Interface):
    path = 'lists'

    def popular(self, page=None, per_page=None, **kwargs):
        response = self.http.get('popular', query={
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
            return items.with_mapper(lambda items: ListMapper.public_lists(self.client, items))

        if isinstance(items, requests.Response):
            return items

        return ListMapper.public_lists(self.client, items)

    def trending(self, page=None, per_page=None, **kwargs):
        response = self.http.get('trending', query={
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
            return items.with_mapper(lambda items: ListMapper.public_lists(self.client, items))

        if isinstance(items, requests.Response):
            return items

        return ListMapper.public_lists(self.client, items)
