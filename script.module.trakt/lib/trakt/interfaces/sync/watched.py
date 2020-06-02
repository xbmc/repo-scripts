from __future__ import absolute_import, division, print_function

from trakt.interfaces.sync.core.mixins import Get


class SyncWatchedInterface(Get):
    path = 'sync/watched'
    flags = {'is_watched': True}

    def get(self, media=None, store=None, params=None, extended=None, **kwargs):
        if media is None:
            raise ValueError('Invalid value provided for the "media" parameter')

        # Build query
        query = {
            'extended': extended
        }

        # Request watched
        return super(SyncWatchedInterface, self).get(
            media, store,
            params=params,
            query=query,
            **kwargs
        )
