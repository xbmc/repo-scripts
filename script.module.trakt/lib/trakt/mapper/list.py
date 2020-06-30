from __future__ import absolute_import, division, print_function

from trakt.mapper.core.base import Mapper
from trakt.mapper.user import UserMapper


class ListMapper(Mapper):
    @classmethod
    def custom_list(cls, client, item, username=None, **kwargs):
        if 'list' in item:
            i_list = item['list']
        else:
            i_list = item

        # Retrieve item keys
        pk, keys = cls.get_ids('custom_list', i_list)

        if pk is None:
            return None

        # Retrieve user details
        i_user = i_list.get('user') or {}

        if username:
            i_user.setdefault('username', username)

        # Create list
        custom_list = cls.construct(
            client, 'custom_list', i_list, keys,
            user=UserMapper.user(client, i_user),
            **kwargs
        )

        # Update with root info
        if 'list' in item:
            custom_list._update(item)

        return custom_list

    @classmethod
    def public_lists(cls, client, items, **kwargs):
        if not items:
            return None

        return [
            cls.public_list(client, item, **kwargs) for item in items
            if item
        ]

    @classmethod
    def public_list(cls, client, item, **kwargs):
        if 'list' in item:
            i_list = item['list']
        else:
            i_list = item

        # Retrieve item keys
        pk, keys = cls.get_ids('public_list', i_list)

        if pk is None:
            return None

        # Retrieve totals
        comment_total = i_list.get('comment_count')
        like_total = i_list.get('likes')

        # Create list
        public_list = cls.construct(
            client, 'public_list', i_list, keys,
            user=UserMapper.user(client, i_list['user']),
            **kwargs
        )

        public_list._update({
            'comment_total': comment_total,
            'like_total': like_total
        })

        # Update with root info
        if 'list' in item:
            info = item.copy()
            info['likes'] = info.pop('like_count')

            public_list._update(info)

        return public_list
