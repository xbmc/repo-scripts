"""
Connection class
Makes all HTTP request to episodehunter.tv
"""

import json
from resources.lib import helper


class Connection(object):
    """ Makes all HTTP request to episodehunter.tv """

    def __init__(self, http):
        self.__connection = http

    def make_request(self, api_endpoint, args=None):
        """ Send message """
        args = args or {}

        helper.check_user_credentials()

        args['username'] = helper.get_username()
        args['apikey'] = helper.get_api_key()

        json_data = json.dumps(args, default=lambda o: o.__dict__)

        return self.__connection.make_request(api_endpoint, json_data)

    def set_movies_watched(self, movies_seen=None):
        """ Set a movie as watched """
        movies_seen = movies_seen or []
        return self.make_request('/v2/movie/watched', {'movies': movies_seen})

    def set_shows_watched(self, shows):
        """ Set a several episodes for a TV show as watched """
        for show in shows:
            self.set_show_as_watched(show)

    def set_show_as_watched(self, show):
        """ Set a show as watched on episodehunter.tv """
        # Expecting: {'tvdb_id': Number, 'title': String, 'year': Number, 'episodes': []{season: number, episode: number}}
        self.make_request('/v2/tv/watched', show)

    def get_watched_movies(self):
        """ Get watched movies from episodehunter.tv """
        response = self.make_request('/v2/movie/getwatched')
        return response['value']

    def get_watched_shows(self):
        """ Get watched TV shows from episodehunter.tv """
        response = self.make_request('/v2/tv/getwatched')
        return response['value']

    def watching_movie(self, originaltitle, year, imdb_id, duration, percent):
        """ Set a movie as watching on episodehunter.tv """
        return self.make_request(
            '/v2/movie/watching',
            {
                'originaltitle': originaltitle,
                'year': year,
                'imdb_id': imdb_id,
                'duration': duration,
                'progress': percent
            }
        )

    def watching_episode(self, tvdb_id, title, year, season, episode, duration, percent):
        """ Set a episode as watching on episodehunter.tv """
        return self.make_request('/v2/tv/watching', {'tvdb_id': tvdb_id, 'title': title, 'year': year, 'season': season, 'episode': episode, 'duration': duration, 'progress': percent})

    def cancel_watching_movie(self):
        """ Cancel watching a movie"""
        return self.make_request('/v2/movie/cancelwatching', {})

    def cancel_watching_episode(self):
        """ Cancel watching an episode """
        return self.make_request('/v2/tv/cancelwatching', {})

    def scrobble_movie(self, originaltitle, year, imdb_id, duration, percent, timestamp=0):
        """ Scrobble a movie to episodehunter.tv """
        return self.make_request('/v2/movie/scrobble', {'originaltitle': originaltitle, 'year': year, 'imdb_id': imdb_id, 'duration': duration, 'progress': percent, 'time': timestamp})

    def scrobble_episode(self, tvdb_id, title, year, season, episode, duration, percent, timestamp=0):
        """ Scrobble en episode to episodehunter.tv """
        return self.make_request('/v2/tv/scrobble', {'tvdb_id': tvdb_id, 'title': title, 'year': year, 'season': season, 'episode': episode, 'duration': duration, 'progress': percent, 'time': timestamp})
