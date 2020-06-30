from __future__ import absolute_import, division, print_function

from trakt.core.helpers import clean_username, dictfilter
from trakt.interfaces.base import Interface, authenticated
from trakt.mapper import UserMapper

import requests


class UsersProfileInterface(Interface):
    path = 'users/*'

    def get(self, username, extended=None, **kwargs):
        response = self.http.get(
            '/users/%s' % (clean_username(username)),
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
        item = self.get_data(response, **kwargs)

        if isinstance(item, requests.Response):
            return item

        if type(item) is not dict:
            return None

        return UserMapper.user(self.client, item)

    @authenticated
    def follow(self, username, **kwargs):
        response = self.http.post(
            '/users/%s/follow' % (clean_username(username))
        )

        return 200 <= response.status_code < 300

    @authenticated
    def unfollow(self, username, **kwargs):
        response = self.http.delete(
            '/users/%s/follow' % (clean_username(username))
        )

        return 200 <= response.status_code < 300
