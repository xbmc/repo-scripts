from mock_base_class import MockBaseClass


class ConnectionMock(MockBaseClass, object):

    def __init__(self, watched_movies=None, watched_shows=None, return_status_code=200):
        super(ConnectionMock, self).__init__()
        self.watched_movies = watched_movies
        self.watched_shows = watched_shows
        self.return_status_code = return_status_code

    def get_watched_shows(self):
        return self.watched_shows

    def get_watched_movies(self):
        return self.watched_movies

    def set_movies_watched(self, movies_seen=None):
        self._increase_called('set_movies_watched', movies_seen)
        return self._return()

    def set_show_as_watched(self, series_seen=None):
        self._increase_called('set_show_as_watched', series_seen)
        return self._return()

    def _return(self):
        return {'status': self.return_status_code}
