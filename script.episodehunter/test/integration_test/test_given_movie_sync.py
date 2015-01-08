from mock import patch, Mock
import unittest
import json

from test.xbmc_base_test_case import XbmcBaseTestCase
from test.test_data import eh_movie_result, xbmc_movie_result
from test.mocks import connection_mock


class GivenMovieSync(XbmcBaseTestCase, object):
    """
    Test class for movie sync methods between EH and XBMC
    """

    xbmc = None
    xbmcgui = None

    def setUp(self):
        super(GivenMovieSync, self).setUp()
        import resources.lib.sync.sync_movies as sync
        self.sync = sync

        self.progress = Mock()
        self.progress.iscanceled.return_value = False
        self.xbmcgui.DialogProgress = Mock(return_value=self.progress)

    @patch('resources.lib.xbmc_helper.get_movies_from_xbmc')
    def test_shuld_upload_one_movie(self, xbmc_helper_mock):
        # Arrange
        connection = connection_mock.ConnectionMock(
            watched_movies=eh_movie_result.get('The Hunger Games', 'The Thing'),
            return_status_code=200
        )
        xbmc_helper_mock.return_value = xbmc_movie_result.get('The Hunger Games', 'The Thing', 'Battleship')
        self.xbmc.abortRequested = False

        # Act
        sync = self.sync.Movies(connection)
        sync.sync()

        # Assert
        movie_to_upload = connection.called['set_movies_watched'][0]

        self.assertEqual(len(movie_to_upload), 1, 'Should have uploaded one movie')
        self.assertEqual(len(connection.called['set_movies_watched']), 1, 'set_movies_watched should have been called once')

    @patch('resources.lib.xbmc_helper.get_movies_from_xbmc')
    def test_shuld_upload_two_movies(self, xbmc_helper_mock):
        # Arrange
        connection = connection_mock.ConnectionMock(
            watched_movies=eh_movie_result.get('The Hunger Games'),
            return_status_code=200
        )
        xbmc_helper_mock.return_value = xbmc_movie_result.get('The Hunger Games', 'The Thing', 'Battleship')
        self.xbmc.abortRequested = False

        # Act
        sync = self.sync.Movies(connection)
        sync.sync()

        # Assert
        movie_to_upload = connection.called['set_movies_watched'][0]

        self.assertEqual(len(movie_to_upload), 2, 'Should have uploaded two movies')
        self.assertEqual(len(connection.called['set_movies_watched']), 1, 'set_movies_watched should have been called once')

    @patch('resources.lib.xbmc_helper.get_movies_from_xbmc')
    def test_shuld_upload_battleship(self, xbmc_helper_mock):
        # Arrange
        connection = connection_mock.ConnectionMock(
            watched_movies=eh_movie_result.get('The Hunger Games', 'The Thing'),
            return_status_code=200
        )
        xbmc_helper_mock.return_value = xbmc_movie_result.get('The Hunger Games', 'The Thing', 'Battleship')
        self.xbmc.abortRequested = False

        # Act
        sync = self.sync.Movies(connection)
        sync.sync()

        # Assert
        movie_to_upload = connection.called['set_movies_watched'][0]

        self.assertEqual(movie_to_upload[0].title, 'Battleship', 'Should have uploaded Battleship')



if __name__ == '__main__':
    unittest.main()
