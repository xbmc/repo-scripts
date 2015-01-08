from mock_base_class import MockBaseClass


class ConnectionMock(MockBaseClass, object):

    def __init__(self, watched_movies=None, return_status_code=200):
        super(ConnectionMock, self).__init__()
        self.watched_movies = watched_movies
        self.return_status_code = return_status_code

    def get_watched_movies(self):
        return self.watched_movies

    def set_movies_watched(self, movies_seen=None):
        movies_seen = movies_seen or []
        self._increase_called('set_movies_watched', movies_seen)
        return self._return()

    def _return(self):
        return {'status': self.return_status_code}
