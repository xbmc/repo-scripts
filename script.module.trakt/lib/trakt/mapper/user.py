from __future__ import absolute_import, division, print_function

from trakt.mapper.core.base import Mapper


class UserMapper(Mapper):
    @classmethod
    def users(cls, client, items, **kwargs):
        if not items:
            return None

        return [item for item in [cls.user(client, item, **kwargs) for item in items] if item]

    @classmethod
    def user(cls, client, item, **kwargs):
        if 'user' in item:
            i_user = item['user']
        else:
            i_user = item

        pk, keys = cls.get_ids('user', i_user)

        if pk is None:
            return None

        # Create object
        user = cls.construct(client, 'user', i_user, keys, **kwargs)

        # Update with root info
        if 'user' in item:
            user._update(item)

        return user
