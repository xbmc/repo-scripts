from mock import patch, Mock
import unittest
import json

from test.xbmc_base_test_case import XbmcBaseTestCase
from resources.factory.movie_factory import movie_factory
from test.test_data import xbmc_movie_result


class GivenConnection(XbmcBaseTestCase, object):
    """
    Test class for connections
    """

    xbmc = None
    xbmcgui = None
    http_mock = None
    http = Mock()

    def setUp(self):
        super(GivenConnection, self).setUp()
        self.import_resurse()

    def import_resurse(self):
        import resources.lib.connection.connection as connection
        self.connection = connection.Connection(self.http)

    @patch('resources.lib.helper.get_username', lambda: "username")
    @patch('resources.lib.helper.get_api_key', lambda: "key")
    def test_should_send_a_post_request_to_eh(self):
        movies = [movie_factory(m) for m in xbmc_movie_result.get('The Hunger Games')]

        self.connection.set_movies_watched(movies)

        args, kwargs = self.http.make_request.call_args
        self.assertEqual(args[0], '/v2/movie/watched')
        expecting = {
            "username": "username",
            "apikey": "key",
            "movies": [
                {
                    "plays": 3,
                    "last_played": 1412964211,
                    "title": "The Hunger Games",
                    "imdb_id": "tt1392170",
                    "year": 2011
                }]}
        actually = json.loads(args[1])
        self.assertEqual(len(set(actually.keys()).difference(set(expecting.keys()))), 0)
        self.assertEqual(expecting['username'], actually['username'])
        self.assertEqual(expecting['apikey'], actually['apikey'])
        self.assertEqual(len(actually['movies']), len(expecting['movies']))
        self.assertEqual(len(set(actually.keys()).difference(set(expecting.keys()))), 0)


if __name__ == '__main__':
    unittest.main()
