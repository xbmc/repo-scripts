from __future__ import absolute_import, division, print_function

from trakt.objects.list.base import List


class CustomList(List):
    @classmethod
    def _construct(cls, client, keys, info, user):
        if not info:
            return None

        obj = cls(client, keys, user)
        obj._update(info)
        return obj

    #
    # Owner actions
    #

    def add(self, items, **kwargs):
        """Add specified items to the list.

        :param items: Items that should be added to the list
        :type items: :class:`~python:list`

        :param kwargs: Extra request options
        :type kwargs: :class:`~python:dict`

        :return: Response
        :rtype: :class:`~python:dict`
        """

        return self._client['users/*/lists/*'].add(self.user.username, self.id, items, **kwargs)

    def delete(self, **kwargs):
        """Delete the list.

        :param kwargs: Extra request options
        :type kwargs: :class:`~python:dict`

        :return: Boolean to indicate if the request was successful
        :rtype: :class:`~python:bool`
        """

        return self._client['users/*/lists/*'].delete(self.user.username, self.id, **kwargs)

    def update(self, **kwargs):
        """Update the list with the current object attributes.

        :param kwargs: Extra request options
        :type kwargs: :class:`~python:dict`

        :return: Boolean to indicate if the request was successful
        :rtype: :class:`~python:bool`
        """

        item = self._client['users/*/lists/*'].update(self.user.username, self.id, return_type='data', **kwargs)

        if not item:
            return False

        self._update(item)
        return True

    def remove(self, items, **kwargs):
        """Remove specified items from the list.

        :param items: Items that should be removed from the list
        :type items: :class:`~python:list`

        :param kwargs: Extra request options
        :type kwargs: :class:`~python:dict`

        :return: Response
        :rtype: :class:`~python:dict`
        """

        return self._client['users/*/lists/*'].remove(self.user.username, self.id, items, **kwargs)
