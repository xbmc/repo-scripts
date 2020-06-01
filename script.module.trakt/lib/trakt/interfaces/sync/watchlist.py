from __future__ import absolute_import, division, print_function

from trakt.interfaces.base import authenticated
from trakt.interfaces.sync.core.mixins import Get, Add, Remove


class SyncWatchlistInterface(Get, Add, Remove):
    path = 'sync/watchlist'
    flags = {'in_watchlist': True}

    def get(self, media=None, sort=None, store=None, extended=None, flat=False,
            page=None, per_page=None, **kwargs):

        if media and not flat and page is not None:
            raise ValueError('`page` parameter is only supported with `flat=True`')

        # Build parameters
        params = []

        if sort:
            params.append(sort)

        # Build query
        query = {
            'extended': extended,
            'page': page,
            'limit': per_page
        }

        # Request watched history
        return super(SyncWatchlistInterface, self).get(
            media, store,
            params=params,
            query=query,
            flat=flat or media is None,
            **kwargs
        )

    #
    # Shortcut methods
    #

    @authenticated
    def movies(self, sort=None, store=None, **kwargs):
        return self.get(
            'movies',
            sort=sort,
            store=store,
            **kwargs
        )

    @authenticated
    def shows(self, sort=None, store=None, **kwargs):
        return self.get(
            'shows',
            sort=sort,
            store=store,
            **kwargs
        )

    @authenticated
    def seasons(self, sort=None, store=None, **kwargs):
        return self.get(
            'seasons',
            sort=sort,
            store=store,
            **kwargs
        )

    @authenticated
    def episodes(self, sort=None, store=None, **kwargs):
        return self.get(
            'episodes',
            sort=sort,
            store=store,
            **kwargs
        )
