from __future__ import absolute_import, division, print_function

from trakt.core.helpers import to_iso8601_datetime
from trakt.interfaces.base import authenticated
from trakt.interfaces.sync.core.mixins import Get, Add, Remove


class SyncHistoryInterface(Get, Add, Remove):
    path = 'sync/history'
    flags = {'is_watched': True}

    def get(self, media=None, id=None, start_at=None, end_at=None, store=None,
            extended=None, page=None, per_page=None, **kwargs):

        if not media and id:
            raise ValueError('The "id" parameter also requires the "media" parameter to be defined')

        # Build parameters
        params = []

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

        # Request watched history
        return super(SyncHistoryInterface, self).get(
            media, store, params,
            flat=True,
            query=query,
            **kwargs
        )

    #
    # Shortcut methods
    #

    @authenticated
    def movies(self, id=None, start_at=None, end_at=None, store=None, **kwargs):
        return self.get(
            'movies',
            id=id,
            start_at=start_at,
            end_at=end_at,
            store=store,
            **kwargs
        )

    @authenticated
    def shows(self, id=None, start_at=None, end_at=None, store=None, **kwargs):
        return self.get(
            'shows',
            id=id,
            start_at=start_at,
            end_at=end_at,
            store=store,
            **kwargs
        )

    @authenticated
    def seasons(self, id=None, start_at=None, end_at=None, store=None, **kwargs):
        return self.get(
            'seasons',
            id=id,
            start_at=start_at,
            end_at=end_at,
            store=store,
            **kwargs
        )

    @authenticated
    def episodes(self, id=None, start_at=None, end_at=None, store=None, **kwargs):
        return self.get(
            'episodes',
            id=id,
            start_at=start_at,
            end_at=end_at,
            store=store,
            **kwargs
        )
