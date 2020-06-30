from __future__ import absolute_import, division, print_function

from trakt.objects.core.helpers import update_attributes
from trakt.objects.list.base import List


class PublicList(List):
    def __init__(self, client, keys, user):
        super(PublicList, self).__init__(client, keys, user)

        self.comment_total = None
        """
        :type: :class:`~python:int`

        Total number of comments
        """

        self.like_total = None
        """
        :type: :class:`~python:int`

        Total number of likes
        """

    @classmethod
    def _construct(cls, client, keys, info, user):
        if not info:
            return None

        obj = cls(client, keys, user)
        obj._update(info)
        return obj

    def _update(self, info=None):
        super(PublicList, self)._update(info)

        if not info:
            return

        update_attributes(self, info, [
            'comment_total',
            'like_total'
        ])
