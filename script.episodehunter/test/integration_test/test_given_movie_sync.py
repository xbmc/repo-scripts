import unittest
import json
from mock import Mock, MagicMock
from test.xbmc_base_test_case import XbmcBaseTestCase
from test.test_data import eh_movie_result, xbmc_movie_result
from test.mocks import connection_mock


class GivenMovieSync(XbmcBaseTestCase, object):
    """
    Test class for movie sync methods between EH and XBMC
    """

    sync = None
    set_movies_as_watched = None

    def setUp(self):
        super(GivenMovieSync, self).setUp()
        import resources.lib.sync.sync_movies as sync
        from resources.lib import xbmc_repository
        self.sync = sync
        self.xbmc.executeJSONRPC = self.json_rcp_mock = MagicMock()
        xbmc_repository.set_movies_as_watched = self.set_movies_as_watched = MagicMock()

        self.progress = Mock()
        self.xbmc.abortRequested = False
        self.progress.iscanceled.return_value = False
        self.xbmcgui.DialogProgress = Mock(return_value=self.progress)


    def test_shuld_upload_one_movie(self):
        # Arrange
        connection = connection_mock.ConnectionMock(
            watched_movies=eh_movie_result.get('The Hunger Games', 'The Thing'),
            return_status_code=200
        )
        self.json_rcp_mock.side_effect = [
            json.dumps(
                {'result': {'limits': {'total': 3}}}
            ),
            json.dumps(
                {'result': {'movies': xbmc_movie_result.get('The Hunger Games', 'The Thing', 'Battleship')}}
            ),
            json.dumps(
                {'result': {'movies': []}}
            ),
            json.dumps(
                {'result': {'limits': {'total': 0}}}
            )
        ]

        # Act
        sync = self.sync.Movies(connection)
        sync.sync()

        # Assert
        movie_to_upload = connection.called['set_movies_watched']
        self.assertEqual(len(movie_to_upload), 1, 'set_movies_watched should have been called once')
        self.assertEqual(len(movie_to_upload[0]), 1, 'Should have uploaded one movie')
        self.assertEqual(movie_to_upload[0][0]['title'], 'Battleship')
        self.assertEqual(movie_to_upload[0][0]['plays'], 1)
        self.assertEqual(movie_to_upload[0][0]['year'], 2014)
        self.assertTrue(1410000000 <= movie_to_upload[0][0]['time'] <= 1419000000)
        self.assertEqual(movie_to_upload[0][0]['imdb_id'], 'tt1440129')


    def test_shuld_upload_and_download_one_movie(self):
        # Arrange
        connection = connection_mock.ConnectionMock(
            watched_movies=eh_movie_result.get('The Hunger Games'),
            return_status_code=200
        )
        self.json_rcp_mock.side_effect = [
            json.dumps(
                {'result': {'limits': {'total': 2}}}
            ),
            json.dumps(
                {'result': {'movies': xbmc_movie_result.get('Battleship')}}
            ),
            json.dumps(
                {'result': {'movies': []}}
            ),
            json.dumps(
                {'result': {'limits': {'total': 1}}}
            ),
            json.dumps(
                {'result': {'movies': xbmc_movie_result.get('The Hunger Games')}}
            ),
            json.dumps(
                {'result': {'movies': []}}
            ),
        ]

        # Act
        sync = self.sync.Movies(connection)
        sync.sync()

        # Assert
        movie_to_upload = connection.called['set_movies_watched']
        self.assertEqual(len(movie_to_upload), 1, 'set_movies_watched should have been called once')
        self.assertEqual(len(movie_to_upload[0]), 1, 'Should have uploaded one movie')
        self.set_movies_as_watched.assert_called_once_with([1])


if __name__ == '__main__':
    unittest.main()
