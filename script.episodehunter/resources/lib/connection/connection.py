"""
Connection class
Makes all HTTP request to episodehunter.tv
"""

from resources.lib import helper


class Connection(object):
    """ Makes all HTTP request to episodehunter.tv """

    def __init__(self, http):
        self.__connection = http

    def make_request(self, **kargs):
        """ Send message """
        if not helper.valid_user_credentials():
            return None
        kargs['username'] = helper.username()
        kargs['apikey'] = helper.api_key()
        return self.__connection.make_request(kargs)

    def start_watching_movie(self, **kargs):
        """ Set a movie as watching on episodehunter.tv """
        return self.make_request(
            event_type='play',
            media_type='movie',
            **kargs
        )

    def start_watching_episode(self, **kargs):
        """ Set a episode as watching on episodehunter.tv """
        return self.make_request(
            event_type='play',
            media_type='episode',
            **kargs
        )

    def cancel_watching_movie(self, **kargs):
        """ Cancel watching a movie"""
        return self.make_request(
            event_type='stop',
            media_type='movie',
            **kargs
        )

    def cancel_watching_episode(self, **kargs):
        """ Cancel watching an episode """
        return self.make_request(
            event_type='stop',
            media_type='episode',
            **kargs
        )

    def scrobble_movie(self, **kargs):
        """ Scrobble a movie to episodehunter.tv """
        return self.make_request(
            event_type='scrobble',
            media_type='movie',
            **kargs
        )

    def scrobble_episode(self, **kargs):
        """ Scrobble en episode to episodehunter.tv """
        return self.make_request(
            event_type='scrobble',
            media_type='movie',
            **kargs
        )
