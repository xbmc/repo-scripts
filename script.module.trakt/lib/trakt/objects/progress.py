from __future__ import absolute_import, division, print_function

from trakt.core.helpers import dictfilter, from_iso8601_datetime, to_iso8601_datetime
from trakt.objects.core.helpers import update_attributes

LABELS = {
    'last_progress_change': {
        'watched': 'last_watched_at',
        'collection': 'last_collected_at'
    },
    'episode_progress_change': {
        'watched': 'last_watched_at',
        'collection': 'collected_at'
    }
}


class BaseProgress(object):
    def __init__(self, aired=None, completed=None):
        self.aired = aired
        """
        :type: :class:`~python:int`

        Number of aired episodes
        """

        self.completed = completed
        """
        :type: :class:`~python:int`

        Number of completed episodes
        """

    def to_dict(self):
        return {
            'aired': self.aired,
            'completed': self.completed
        }

    def _update(self, info=None, **kwargs):
        if not info:
            return

        update_attributes(self, info, [
            'aired',
            'completed'
        ])

    def __repr__(self):
        return '%d/%d episodes completed' % (self.completed, self.aired)


class Progress(BaseProgress):
    progress_type = None
    """
    :type: :class:`~python:str`

    Progress Type (:code:`watched` or :code:`collection`)
    """

    def __init__(self, client, aired=None, completed=None):
        super(Progress, self).__init__(aired, completed)

        self._client = client

        self.last_progress_change = None
        """
        :type: :class:`~python:datetime.datetime`

        Last watched or collected date/time
        """

        self.reset_at = None
        """
        :type: :class:`~python:datetime.datetime`

        Reset date/time (not applicable for collected progress)
        """

        self.seasons = {}
        """
        :type: :class:`~python:dict`

        Season Progress, defined as :code:`{season_num: SeasonProgress}`
        """

        self.hidden_seasons = None
        """
        :type: :class:`~python:dict`

        Hidden Seasons, defined as :code:`{season_num: Season}`
        """

        self.next_episode = None
        """
        :type: :class:`trakt.objects.episode.Episode`

        Next Episode the user should watch or collect
        """

        self.last_episode = None
        """
        :type: :class:`trakt.objects.episode.Episode`

        Last Episode the user watched or collected
        """

    def to_dict(self):
        """Dump progress to a dictionary.

        :return: Progress dictionary
        :rtype: :class:`~python:dict`
        """

        result = super(Progress, self).to_dict()

        label = LABELS['last_progress_change'][self.progress_type]
        result[label] = to_iso8601_datetime(self.last_progress_change)

        if self.progress_type == 'watched':
            result['reset_at'] = self.reset_at

        result['seasons'] = [
            season.to_dict()
            for season in self.seasons.values()
        ]

        if self.hidden_seasons:
            result['hidden_seasons'] = [
                dictfilter(season.to_dict(), pop=['number', 'ids'])
                for season in self.hidden_seasons.values()
            ]

        if self.next_episode:
            result['next_episode'] = dictfilter(self.next_episode.to_dict(), pop=['season', 'number', 'title', 'ids'])
            result['next_episode']['season'] = self.next_episode.keys[0][0]

        if self.last_episode:
            result['last_episode'] = dictfilter(self.last_episode.to_dict(), pop=['season', 'number', 'title', 'ids'])
            result['last_episode']['season'] = self.last_episode.keys[0][0]

        return result

    def _update(self, info=None, **kwargs):
        if not info:
            return

        super(Progress, self)._update(info, **kwargs)

        label = LABELS['last_progress_change'][self.progress_type]

        if label in info:
            self.last_progress_change = from_iso8601_datetime(info.get(label))

        if 'reset_at' in info:
            self.reset_at = from_iso8601_datetime(info.get('reset_at'))

        if 'seasons' in info:
            for season in info['seasons']:
                season_progress = SeasonProgress._construct(season, progress_type=self.progress_type)

                if season_progress:
                    self.seasons[season_progress.pk] = season_progress

        if 'hidden_seasons' in info:
            self.hidden_seasons = {}

            for season in info['hidden_seasons']:
                hidden_season = self._client.construct('season', season)

                if hidden_season:
                    self.hidden_seasons[hidden_season.pk] = hidden_season

        if 'next_episode' in info:
            episode = self._client.construct('episode', info['next_episode'])

            if episode:
                self.next_episode = episode

        if 'last_episode' in info:
            episode = self._client.construct('episode', info['last_episode'])

            if episode:
                self.last_episode = episode

    @classmethod
    def _construct(cls, client, info=None, **kwargs):
        if not info:
            return

        progress = cls(client)
        progress._update(info, **kwargs)

        return progress


class WatchedProgress(Progress):
    progress_type = 'watched'


class CollectionProgress(Progress):
    progress_type = 'collection'


class SeasonProgress(BaseProgress):
    def __init__(self, pk=None, aired=None, completed=None):
        super(SeasonProgress, self).__init__(aired, completed)

        self.pk = pk
        """
        :type: :class:`~python:int`

        Season Number
        """

        self.episodes = {}
        """
        :type: :class:`~python:dict`

        Episode Progress, defined as :code:`{episode_num: EpisodeProgress}`
        """

    def to_dict(self):
        result = super(SeasonProgress, self).to_dict()

        result['number'] = self.pk
        result['episodes'] = [
            episode.to_dict()
            for episode in self.episodes.values()
        ]
        return result

    def _update(self, info=None, **kwargs):
        if not info:
            return

        super(SeasonProgress, self)._update(info, **kwargs)

        self.pk = info['number']

        if 'episodes' in info:
            for episode in info['episodes']:
                episode_progress = EpisodeProgress._construct(episode, **kwargs)

                if episode_progress:
                    self.episodes[episode_progress.pk] = episode_progress

    @classmethod
    def _construct(cls, info=None, **kwargs):
        if not info:
            return

        season_progress = cls()
        season_progress._update(info, **kwargs)

        return season_progress


class EpisodeProgress(object):
    def __init__(self, pk=None):
        self.progress_type = None

        self.pk = pk
        """
        :type: :class:`~python:int`

        Episode Number
        """

        self.completed = None
        """
        :type: :class:`~python:bool`

        Whether or not the episode has been watched or collected
        """

        self.progress_timestamp = None
        """
        :type: :class:`~python:datetime.datetime`

        Date/time episode was collected or last watched
        """

    def to_dict(self):
        result = {
            'number': self.pk,
            'completed': self.completed if self.completed is not None else 0
        }

        if self.progress_type:
            label = LABELS['episode_progress_change'][self.progress_type]
        else:
            label = 'progress_timestamp'

        result[label] = to_iso8601_datetime(self.progress_timestamp)

        return result

    def _update(self, info=None, **kwargs):
        if not info:
            return

        self.pk = info['number']

        if 'progress_type' in kwargs:
            self.progress_type = kwargs['progress_type']

        self.completed = info['completed']

        if 'last_watched_at' in info:
            self.progress_timestamp = from_iso8601_datetime(info.get('last_watched_at'))

        elif 'collected_at' in info:
            self.progress_timestamp = from_iso8601_datetime(info.get('collected_at'))

    @classmethod
    def _construct(cls, info=None, **kwargs):
        if not info:
            return

        episode_progress = cls()
        episode_progress._update(info, **kwargs)

        return episode_progress
