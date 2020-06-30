from __future__ import absolute_import, division, print_function

from trakt.core.helpers import from_iso8601_datetime
from trakt.objects.core.helpers import update_attributes


class List(object):
    def __init__(self, client, keys, user):
        self._client = client

        self.keys = keys
        """
        :type: :class:`~python:list` of :class:`~python:tuple`

        Keys (for trakt, imdb, tvdb, etc..), defined as:

        ..code-block::

            [
                (<service>, <id>)
            ]

        """

        self.user = user
        """
        :type: :class:`trakt.objects.User`

        Author
        """

        self.name = None
        """
        :type: :class:`~python:str`

        Name
        """

        self.description = None
        """
        :type: :class:`~python:str`

        Description
        """

        self.privacy = None
        """
        :type: :class:`~python:str`

        Privacy

        **Possible values:**
         - :code:`private`
         - :code:`friends`
         - :code:`public`
        """

        self.likes = None
        """
        :type: :class:`~python:int`

        Number of likes
        """

        self.allow_comments = None
        """
        :type: :class:`~python:bool`

        Flag indicating this list allows comments
        """

        self.display_numbers = None
        """
        :type: :class:`~python:bool`

        Flag indicating this list displays numbers
        """

        self.sort_by = None
        """
        :type: :class:`~python:str`

        Sort By

        **Possible values:**
         - :code:`rank`
         - :code:`added`
         - :code:`title`
         - :code:`released`
         - :code:`runtime`
         - :code:`popularity`
         - :code:`percentage`
         - :code:`votes`
         - :code:`my_rating`
         - :code:`random`
         - :code:`watched`
         - :code:`collected`
        """

        self.sort_how = None
        """
        :type: :class:`~python:str`

        Sort Direction

        **Possible values:**
         - :code:`asc`
         - :code:`desc`
        """

        self.created_at = None
        """
        :type: :class:`~python:datetime.datetime`

        Timestamp of when this list was created
        """

        self.liked_at = None
        """
        :type: :class:`~python:datetime.datetime`

        Timestamp of when this list was liked
        """

        self.updated_at = None
        """
        :type: :class:`~python:datetime.datetime`

        Timestamp of when this list was last updated
        """

        self.comment_count = None
        """
        :type: :class:`~python:int`

        Number of comments
        """

        self.item_count = None
        """
        :type: :class:`~python:int`

        Number of items
        """

    @property
    def id(self):
        """Retrieve the list identifier.

        :rtype: :class:`~python:int`
        """

        if self.pk is None:
            return None

        _, sid = self.pk

        return sid

    @property
    def pk(self):
        """Retrieve the primary key (unique identifier for the list).

        :return: :code:`("trakt", <id>)` or :code:`None` if no primary key is available
        :rtype: :class:`~python:tuple`
        """

        if not self.keys:
            return None

        return self.keys[0]

    @property
    def username(self):
        """Retrieve author username.

        :rtype: :class:`~python:str`
        """
        if not self.user:
            return None

        return self.user.username

    @property
    def like_count(self):
        """Retrieve the number of likes.

        :rtype: :class:`~python:int`
        """
        return self.likes

    def _update(self, info=None):
        if not info:
            return

        if 'created_at' in info:
            self.updated_at = from_iso8601_datetime(info.get('updated_at'))

        if 'liked_at' in info:
            self.liked_at = from_iso8601_datetime(info.get('liked_at'))

        if 'updated_at' in info:
            self.updated_at = from_iso8601_datetime(info.get('updated_at'))

        update_attributes(self, info, [
            'name',
            'description',
            'privacy',

            'likes',

            'allow_comments',
            'display_numbers',
            'sort_by',
            'sort_how',

            'comment_count',
            'item_count'
        ])

    def items(self, **kwargs):
        """Retrieve list items.

        :param kwargs: Extra request options
        :type kwargs: :class:`~python:dict`

        :return: Current list items
        :rtype: :class:`~python:list` of :class:`trakt.objects.media.Media`
        """

        return self._client['users/*/lists/*'].items(self.user.username, self.id, **kwargs)

    #
    # Actions
    #

    def like(self, **kwargs):
        """Like the list.

        :param kwargs: Extra request options
        :type kwargs: :class:`~python:dict`

        :return: Boolean to indicate if the request was successful
        :rtype: :class:`~python:bool`
        """

        return self._client['users/*/lists/*'].like(self.user.username, self.id, **kwargs)

    def unlike(self, **kwargs):
        """Un-like the list.

        :param kwargs: Extra request options
        :type kwargs: :class:`~python:dict`

        :return: Boolean to indicate if the request was successful
        :rtype: :class:`~python:bool`
        """

        return self._client['users/*/lists/*'].unlike(self.user.username, self.id, **kwargs)

    def __getstate__(self):
        state = self.__dict__

        if hasattr(self, '_client'):
            del state['_client']

        return state

    def __repr__(self):
        _, sid = self.pk

        return '<List %r (%s)>' % (self.name, sid)

    def __str__(self):
        return self.__repr__()
