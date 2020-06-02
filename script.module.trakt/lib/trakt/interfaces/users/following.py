from __future__ import absolute_import, division, print_function

from trakt.core.helpers import clean_username, dictfilter
from trakt.interfaces.base import Interface
from trakt.mapper import UserMapper

import requests


class UsersFollowingInterface(Interface):
    path = 'users/*/following'

    def get(self, username, extended=None, **kwargs):
        response = self.http.get(
            '/users/%s/following' % (clean_username(username)),
            query={
                'extended': extended
            },
            **dictfilter(kwargs, get=[
                'exceptions'
            ], pop=[
                'authenticated',
                'validate_token'
            ])
        )

        # Parse response
        items = self.get_data(response, **kwargs)

        if isinstance(items, requests.Response):
            return items

        if type(items) is not list:
            return None

        return UserMapper.users(self.client, items)
