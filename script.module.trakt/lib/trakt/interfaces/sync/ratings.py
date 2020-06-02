from __future__ import absolute_import, division, print_function

from trakt.interfaces.base import authenticated
from trakt.interfaces.sync.core.mixins import Get, Add, Remove


class SyncRatingsInterface(Get, Add, Remove):
    path = 'sync/ratings'

    @authenticated
    def get(self, media=None, rating=None, store=None, extended=None, flat=False, page=None, per_page=None, **kwargs):
        if media and not flat and page is not None:
            raise ValueError('`page` parameter is only supported with `flat=True`')

        # Build parameters
        params = []

        if rating is not None:
            params.append(rating)

        # Build query
        query = {
            'extended': extended,
            'page': page,
            'limit': per_page
        }

        # Request ratings
        return super(SyncRatingsInterface, self).get(
            media, store, params,
            flat=flat or media is None,
            query=query,
            **kwargs
        )

    #
    # Shortcut methods
    #

    @authenticated
    def all(self, rating=None, store=None, **kwargs):
        return self.get(
            'all',
            rating=rating,
            store=store,
            **kwargs
        )

    @authenticated
    def movies(self, rating=None, store=None, **kwargs):
        return self.get(
            'movies',
            rating=rating,
            store=store,
            **kwargs
        )

    @authenticated
    def shows(self, rating=None, store=None, **kwargs):
        return self.get(
            'shows',
            rating=rating,
            store=store,
            **kwargs
        )

    @authenticated
    def seasons(self, rating=None, store=None, **kwargs):
        return self.get(
            'seasons',
            rating=rating,
            store=store,
            **kwargs
        )

    @authenticated
    def episodes(self, rating=None, store=None, **kwargs):
        return self.get(
            'episodes',
            rating=rating,
            store=store,
            **kwargs
        )
