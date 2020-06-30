from __future__ import absolute_import, division, print_function

from trakt.core.helpers import dictfilter
from trakt.core.pagination import PaginationIterator
from trakt.interfaces.base import Interface, authenticated
from trakt.interfaces.users.following import UsersFollowingInterface
from trakt.interfaces.users.friends import UsersFriendsInterface
from trakt.interfaces.users.history import UsersHistoryInterface
from trakt.interfaces.users.lists import UsersListInterface, UsersListsInterface
from trakt.interfaces.users.profile import UsersProfileInterface
from trakt.interfaces.users.ratings import UsersRatingsInterface
from trakt.interfaces.users.settings import UsersSettingsInterface
from trakt.interfaces.users.watched import UsersWatchedInterface
from trakt.interfaces.users.watchlist import UsersWatchlistInterface
from trakt.mapper import CommentMapper, ListMapper

import logging
import requests

log = logging.getLogger(__name__)

__all__ = (
    'UsersInterface',
    'UsersFollowingInterface',
    'UsersFriendsInterface',
    'UsersHistoryInterface',
    'UsersListsInterface',
    'UsersListInterface',
    'UsersProfileInterface',
    'UsersRatingsInterface',
    'UsersSettingsInterface',
    'UsersWatchedInterface',
    'UsersWatchlistInterface'
)


class UsersInterface(Interface):
    path = 'users'

    @authenticated
    def likes(self, type=None, page=None, per_page=None, **kwargs):
        if type and type not in ['comments', 'lists']:
            raise ValueError('Unknown type specified: %r' % type)

        if kwargs.get('parse') is False:
            raise ValueError("Parse can't be disabled on this method")

        # Send request
        response = self.http.get('likes', [type], query={
            'page': page,
            'limit': per_page
        }, **dictfilter(kwargs, get=[
            'exceptions'
        ], pop=[
            'authenticated',
            'pagination',
            'validate_token'
        ]))

        # Parse response
        items = self.get_data(response, **kwargs)

        if isinstance(items, PaginationIterator):
            return items.with_mapper(self._map_items)

        if isinstance(items, requests.Response):
            return items

        return self._map_items(items)

    def _map_items(self, items):
        if items is None:
            return None

        # Map items to comment/list objects
        return [
            item for item in [self._map(item) for item in items]
            if item
        ]

    def _map(self, item):
        item_type = item.get('type')

        if item_type == 'comment':
            return CommentMapper.comment(
                self.client, item
            )

        if item_type == 'list':
            return ListMapper.custom_list(
                self.client, item
            )

        log.warning('Unknown item returned, type: %r', item_type)
        return None
