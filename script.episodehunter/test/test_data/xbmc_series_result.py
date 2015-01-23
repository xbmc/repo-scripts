TV_SHOWS = [
    {
        'tvshowid': 1,
        'title': 'Game of Thrones',
        'season': -1,
        'watchedepisodes': 9,
        'label': 'Game of Thrones',
        'imdbnumber': '121361',
        'year': 2011,
        'playcount': 1
    }
]

SEASONS = [
    {
        'seasonid': 3,
        'season': 1,
        'watchedepisodes': 5,
        'label': 'Season 1'
    }
]

EPISODE = [
    {
        'season': 1,
        'playcount': 1,
        'episode': 1,
        'episodeid': 1,
        'label': u'1x01. Winter Is Coming'
    }
]


def iterate_over_key(iterable, key):
    if key in iterable:
        for e in iterable[key]:
            yield e
    else:
        return


class TvShows():

    def __init__(self):
        self._shows = []
        self._episodes = {}

    def add_show(self, tvshowid=None, title='', watchedepisodes=None, imdbnumber=None, year=1989, playcount=None):
        self._shows.append({
            'tvshowid': tvshowid or imdbnumber,
            'title': title,
            'season': -1,
            'watchedepisodes': watchedepisodes,
            'label': title,
            'imdbnumber': imdbnumber,
            'year': year,
            'playcount': playcount
        })
        return self

    def add_episodes(self, tvshowid, season, episodes):
        if tvshowid not in self._episodes:
            self._episodes[tvshowid] = []

        existing_episodes = next((x for x in self._episodes[tvshowid] if x['season'] == season), None)

        if existing_episodes is None:
            self._episodes[tvshowid].append({
                'season': season,
                'episodes': episodes
            })
        else:
            existing_episodes['episodes'].extend(episodes)

        return self

    def add_watched_episodes(self, tvshowid, season, episode_range):
        episodes = [{
            'season': season,
            'playcount': 1,
            'episode': n,
            'episodeid': n
        } for n in episode_range]
        self.add_episodes(tvshowid, season, episodes)
        return self

    def add_unwatched_episodes(self, tvshowid, season, episode_range):
        episodes = [{
            'season': season,
            'playcount': 0,
            'episode': n,
            'episodeid': n
        } for n in episode_range]
        self.add_episodes(tvshowid, season, episodes)
        return self

    def get_tv_shows(self):
        return self._shows

    def get_seasons(self, tvshow):
        return [
            {
                'season': s['season']
            } for s in iterate_over_key(self._episodes, tvshow['tvshowid'])
        ]

    def get_episodes(self, tvshow, season):
        for e in self._episodes[tvshow['tvshowid']]:
            if e['season'] == season:
                return e['episodes']

        raise Exception('No episodes found :(')
