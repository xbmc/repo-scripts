from __future__ import absolute_import, division, print_function

from trakt.core.helpers import dictfilter
from trakt.interfaces.base import Interface, authenticated


class UsersSettingsInterface(Interface):
    path = 'users/settings'

    @authenticated
    def get(self, **kwargs):
        response = self.http.get(
            **dictfilter(kwargs, pop=[
                'authenticated',
                'validate_token'
            ])
        )

        return self.get_data(response, **kwargs)
