from __future__ import absolute_import, division, print_function

from trakt.core.helpers import dictfilter
from trakt.core.pagination import PaginationIterator
from trakt.interfaces.base import Interface, authenticated
from trakt.mapper.progress import ProgressMapper
from trakt.mapper.summary import SummaryMapper

import requests


class ShowsInterface(Interface):
    path = 'shows'

    def get(self, id, extended=None, **kwargs):
        response = self.http.get(str(id), query={
            'extended': extended
        })

        item = self.get_data(response, **kwargs)

        if isinstance(item, requests.Response):
            return item

        return SummaryMapper.show(self.client, item)

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
            return items.with_mapper(lambda items: SummaryMapper.shows(self.client, items))

        if isinstance(items, requests.Response):
            return items

        return SummaryMapper.shows(self.client, items)

    def next_episode(self, id, extended=None, **kwargs):
        response = self.http.get(str(id), 'next_episode', query={
            'extended': extended
        })

        item = self.get_data(response, **kwargs)

        if isinstance(item, requests.Response):
            return item

        return SummaryMapper.episode(self.client, item)

    def last_episode(self, id, extended=None, **kwargs):
        response = self.http.get(str(id), 'last_episode', query={
            'extended': extended
        })

        item = self.get_data(response, **kwargs)

        if isinstance(item, requests.Response):
            return item

        return SummaryMapper.episode(self.client, item)

    def seasons(self, id, extended=None, **kwargs):
        response = self.http.get(str(id), [
            'seasons'
        ], query={
            'extended': extended
        })

        items = self.get_data(response, **kwargs)

        if isinstance(items, requests.Response):
            return items

        return SummaryMapper.seasons(self.client, items)

    def season(self, id, season, extended=None, **kwargs):
        response = self.http.get(str(id), [
            'seasons', str(season)
        ], query={
            'extended': extended
        })

        items = self.get_data(response, **kwargs)

        if isinstance(items, requests.Response):
            return items

        return SummaryMapper.episodes(self.client, items)

    def episode(self, id, season, episode, extended=None, **kwargs):
        response = self.http.get(str(id), [
            'seasons', str(season),
            'episodes', str(episode)
        ], query={
            'extended': extended
        })

        item = self.get_data(response, **kwargs)

        if isinstance(item, requests.Response):
            return item

        return SummaryMapper.episode(self.client, item)

    @authenticated
    def progress(self, progress_type, id, hidden=False, specials=False, count_specials=True, **kwargs):
        query = {
            'hidden': hidden,
            'specials': specials,
            'count_specials': count_specials
        }

        response = self.http.get(str(id), [
            'progress', progress_type
        ], query=query, **dictfilter(kwargs, pop=[
            'authenticated',
            'validate_token'
        ]))

        item = self.get_data(response, **kwargs)

        if isinstance(item, requests.Response):
            return item

        return ProgressMapper.progress(self.client, progress_type, item)

    @authenticated
    def progress_collection(self, id, hidden=False, specials=False, count_specials=True, **kwargs):
        return self.progress('collection', id, hidden, specials, count_specials, **kwargs)

    @authenticated
    def progress_watched(self, id, hidden=False, specials=False, count_specials=True, **kwargs):
        return self.progress('watched', id, hidden, specials, count_specials, **kwargs)
