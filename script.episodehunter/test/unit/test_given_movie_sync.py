import unittest
from mock import Mock
from test.xbmc_base_test_case import XbmcBaseTestCase
from test.test_data import eh_movie_result, xbmc_movie_result
from test.mocks import connection_mock
from resources.exceptions import UserAbortExceptions

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

        self.xbmc.abortRequested = False
        self.progress = Mock()
        self.progress.iscanceled.return_value = False
        self.xbmcgui.DialogProgress = Mock(return_value = self.progress)

    def test_should_sync_one_movie_upstream(self):
        # Arrange
        connection = connection_mock.ConnectionMock()
        xbmc_mock = Mock()
        xbmc_mock.watched_movies = Mock(return_value=[xbmc_movie_result.get('The Hunger Games', 'The Thing', 'Battleship')])
        xbmc_mock.number_watched_movies = Mock(return_value=3)
        sync = self.sync.Movies(connection, xbmc_mock)
        sync.eh_watched_movies = eh_movie_result.get('The Hunger Games', 'Battleship')
        sync.progress = self.progress

        # Act
        sync.sync_upstream()

        # Assert
        movies_to_upload = connection.called['set_movies_watched']
        self.assertEqual(len(movies_to_upload), 1)
        self.assertEqual(len(movies_to_upload[0]), 1)

        movies_to_upload = movies_to_upload[0][0]
        self.assertEqual(movies_to_upload['title'], 'The Thing')
        self.assertEqual(movies_to_upload['imdb_id'], 'tt0905372')
        self.assertEqual(movies_to_upload['year'], 2014)
        self.assertEqual(movies_to_upload['plays'], 1)
        self.assertTrue(1410000000 <= movies_to_upload['time'] <= 1419000000)


    def test_should_sync_one_movie_downstream(self):
        # Arrange
        connection = connection_mock.ConnectionMock()
        xbmc_mock = Mock()
        xbmc_mock.unwatched_movies = Mock(return_value=[xbmc_movie_result.get('The Hunger Games', 'The Interview', 'Interstellar')])
        xbmc_mock.number_unwatched_movies = Mock(return_value=3)
        sync = self.sync.Movies(connection, xbmc_mock)
        sync.eh_watched_movies = eh_movie_result.get('The Interview')
        sync.progress = self.progress

        # Act
        sync.sync_downstream()

        # Assert
        xbmc_mock.set_movies_as_watched.assert_called_once_with([4])


    def test_should_rise_exception_when_abort_is_requested_for_downstream(self):
        connection = connection_mock.ConnectionMock()
        xbmc_mock = Mock()
        xbmc_mock.unwatched_movies = Mock(return_value=[xbmc_movie_result.get('The Hunger Games', 'The Interview', 'Interstellar')])
        xbmc_mock.number_unwatched_movies = Mock(return_value=3)
        sync = self.sync.Movies(connection, xbmc_mock)
        sync.eh_watched_movies = []
        sync.progress = self.progress
        self.xbmc.abortRequested = True

        with self.assertRaises(SystemExit):
            sync.sync_downstream()


    def test_should_rise_exception_when_abort_is_requested_for_upstream(self):
        connection = connection_mock.ConnectionMock()
        xbmc_mock = Mock()
        xbmc_mock.watched_movies = Mock(return_value=[xbmc_movie_result.get('The Hunger Games', 'The Interview', 'Interstellar')])
        xbmc_mock.number_watched_movies = Mock(return_value=3)
        sync = self.sync.Movies(connection, xbmc_mock)
        sync.eh_watched_movies = []
        sync.progress = self.progress
        self.xbmc.abortRequested = True

        with self.assertRaises(SystemExit):
            sync.sync_upstream()

    def test_should_rise_exception_when_canceled_is_requested_for_upstream(self):
        connection = connection_mock.ConnectionMock()
        xbmc_mock = Mock()
        xbmc_mock.watched_movies = Mock(return_value=[xbmc_movie_result.get('The Hunger Games', 'The Interview', 'Interstellar')])
        xbmc_mock.number_watched_movies = Mock(return_value=3)
        sync = self.sync.Movies(connection, xbmc_mock)
        sync.eh_watched_movies = []
        sync.progress = self.progress
        self.progress.iscanceled.return_value = True

        with self.assertRaises(UserAbortExceptions):
            sync.sync_upstream()


    def test_should_rise_exception_when_canceled_is_requested_for_downstream(self):
        connection = connection_mock.ConnectionMock()
        xbmc_mock = Mock()
        xbmc_mock.unwatched_movies = Mock(return_value=[xbmc_movie_result.get('The Hunger Games', 'The Interview', 'Interstellar')])
        xbmc_mock.number_unwatched_movies = Mock(return_value=3)
        sync = self.sync.Movies(connection, xbmc_mock)
        sync.eh_watched_movies = []
        sync.progress = self.progress
        self.progress.iscanceled.return_value = True

        with self.assertRaises(UserAbortExceptions):
            sync.sync_downstream()


if __name__ == '__main__':
    unittest.main()
