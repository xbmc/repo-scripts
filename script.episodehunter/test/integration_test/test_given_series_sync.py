import unittest
import json
from mock import Mock, MagicMock
from test.xbmc_base_test_case import XbmcBaseTestCase
from test.test_data import eh_series_result, xbmc_series_result
from test.mocks import connection_mock


class GivenSeriesSync(XbmcBaseTestCase, object):
    """
    Test class for tv shows sync methods between EH and XBMC
    """

    set_episodes_as_watched = None
    json_rcp_mock = None
    sync = None

    def setUp(self):
        super(GivenSeriesSync, self).setUp()
        from resources.lib import xbmc_repository
        import resources.lib.sync.sync_series as sync

        self.xbmc.executeJSONRPC = self.json_rcp_mock = MagicMock()
        xbmc_repository.set_episodes_as_watched = self.set_episodes_as_watched = MagicMock()
        self.sync = sync

        self.progress = Mock()
        self.progress.iscanceled.return_value = False
        self.xbmc.abortRequested = False
        self.xbmcgui.DialogProgress = Mock(return_value=self.progress)

    def test_should_upload_one_episodes(self):
        # Arrange
        mock_eh_series = eh_series_result.EHSeries()\
            .episode(1, 1, [1, 2, 3, 4, 5, 6])\
            .episode(1, 2, [1, 2, 3, 4, 5, 6])\
            .episode(2, 1, [1, 2, 3, 4, 5, 6])\
            .get()

        connection = connection_mock.ConnectionMock(
            watched_shows=mock_eh_series,
            return_status_code=200
        )

        xbmc_lost = xbmc_series_result.TvShows()
        xbmc_lost\
            .add_show(imdbnumber=1, title='Lost')\
            .add_watched_episodes(
                season=1,
                episode_range=xrange(1, 8)
            )\
            .add_watched_episodes(
                season=2,
                episode_range=xrange(1, 7)
            )

        self.json_rcp_mock.side_effect = [
            json.dumps(
                {'result': {'limits': {'total': 2}}}
            ),
            json.dumps(
                {'result': {'tvshows': xbmc_lost.get_tv_shows()}}
            ),
            json.dumps(
                {'result': {'episodes': xbmc_lost.get_episodes()}}
            ),
            json.dumps(
                {'result': {'tvshows': []}}
            ),
            json.dumps(
                {'result': {'limits': {'total': 0}}}
            )
        ]

        # Act
        sync = self.sync.Series(connection)
        sync.sync()

        # Assert
        self.assertIn('set_show_as_watched', connection.called)
        tvshows_to_upload = connection.called['set_show_as_watched']
        self.assertEqual(len(tvshows_to_upload), 1)

        tvshow_to_upload = tvshows_to_upload[0]
        self.assertEqual(tvshow_to_upload['title'], 'Lost')
        self.assertEqual(len(tvshow_to_upload['episodes']), 1)
        self.assertEqual(tvshow_to_upload['episodes'][0]['season'], 1)
        self.assertEqual(tvshow_to_upload['episodes'][0]['episode'], 7)

    def test_should_not_upload_episodes_that_missing_imdbnumber(self):
        # Arrange
        mock_eh_series = eh_series_result.EHSeries()\
            .episode(2, 1, [1])\
            .get()

        connection = connection_mock.ConnectionMock(
            watched_shows=mock_eh_series,
            return_status_code=200
        )

        xbmc_lost = xbmc_series_result.TvShows()
        xbmc_lost\
            .add_show(imdbnumber='', title='Lost')\
            .add_watched_episodes(
                season=1,
                episode_range=[1, 2]
            )
        xbmc_dexter = xbmc_series_result.TvShows()
        xbmc_dexter\
            .add_show(imdbnumber=2, title='Dexter')\
            .add_watched_episodes(
                season=1,
                episode_range=[1, 2]
            )

        self.json_rcp_mock.side_effect = [
            json.dumps(
                {'result': {'limits': {'total': 2}}}
            ),
            json.dumps(
                {'result': {'tvshows': xbmc_lost.get_tv_shows() + xbmc_dexter.get_tv_shows()}}
            ),
            json.dumps(
                {'result': {'episodes': xbmc_lost.get_episodes()}}
            ),
            json.dumps(
                {'result': {'episodes': xbmc_dexter.get_episodes()}}
            ),
            json.dumps(
                {'result': {'tvshows': []}}
            ),
            json.dumps(
                {'result': {'limits': {'total': 0}}}
            ),
        ]

        # Act
        sync = self.sync.Series(connection)
        sync.sync()

        # Assert
        self.assertIn('set_show_as_watched', connection.called)
        tvshows_to_upload = connection.called['set_show_as_watched']
        self.assertEqual(len(tvshows_to_upload), 1)

        tvshow_to_upload = tvshows_to_upload[0]
        self.assertEqual(tvshow_to_upload['title'], 'Dexter')
        self.assertEqual(len(tvshow_to_upload['episodes']), 1)
        self.assertEqual(tvshow_to_upload['episodes'][0]['season'], 1)
        self.assertEqual(tvshow_to_upload['episodes'][0]['episode'], 2)

    def test_should_not_upload_unwatched_episodes(self):
        # Arrange
        mock_eh_series = eh_series_result.EHSeries()\
            .episode(1, 1, [1, 2, 3, 4, 5, 6])\
            .get()

        connection = connection_mock.ConnectionMock(
            watched_shows=mock_eh_series,
            return_status_code=200
        )

        xbmc_lost = xbmc_series_result.TvShows()
        xbmc_lost\
            .add_show(imdbnumber=1, title='Lost')\
            .add_watched_episodes(
                season=1,
                episode_range=xrange(1, 7)
            )
        xbmc_dexter = xbmc_series_result.TvShows()
        xbmc_dexter\
            .add_show(imdbnumber=2, title='Dexter')\
            .add_unwatched_episodes(
                season=1,
                episode_range=[1]
            )

        self.json_rcp_mock.side_effect = [
            json.dumps(
                {'result': {'limits': {'total': 1}}}
            ),
            json.dumps(
                {'result': {'tvshows': xbmc_lost.get_tv_shows()}}
            ),
            json.dumps(
                {'result': {'episodes': xbmc_lost.get_episodes()}}
            ),
            json.dumps(
                {'result': {'tvshows': []}}
            ),
            json.dumps(
                {'result': {'limits': {'total': 1}}}
            ),
            json.dumps(
                {'result': {'tvshows': xbmc_dexter.get_tv_shows()}}
            ),
            json.dumps(
                {'result': {'episodes': xbmc_dexter.get_episodes()}}
            ),
            json.dumps(
                {'result': {'tvshows': []}}
            )
        ]

        # Act
        sync = self.sync.Series(connection)
        sync.sync()

        # Assert
        self.assertNotIn('set_show_as_watched', connection.called)
        self.assertFalse(self.set_episodes_as_watched.called)

    def test_should_not_set_any_episode_as_watched_when_library_is_up_to_date(self):
        # Arrange
        mock_eh_series = eh_series_result.EHSeries()\
            .episode(1, 1, [1, 2, 3, 4, 5, 6])\
            .episode(1, 2, [1, 2, 3, 4, 5, 6])\
            .episode(2, 1, [1, 2, 3, 4, 5, 6])\
            .get()

        connection = connection_mock.ConnectionMock(
            watched_shows=mock_eh_series,
            return_status_code=200
        )

        xbmc_lost = xbmc_series_result.TvShows()
        xbmc_lost\
            .add_show(imdbnumber=1, title='Lost')\
            .add_watched_episodes(
                season=1,
                episode_range=xrange(1, 7)
            )\
            .add_watched_episodes(
                season=2,
                episode_range=xrange(1, 7)
            )
        xbmc_dexter = xbmc_series_result.TvShows()
        xbmc_dexter\
            .add_show(imdbnumber=2, title='Dexter')\
            .add_watched_episodes(
                season=1,
                episode_range=xrange(1, 7)
            )

        self.json_rcp_mock.side_effect = [
            json.dumps(
                {'result': {'limits': {'total': 2}}}
            ),
            json.dumps(
                {'result': {'tvshows': xbmc_lost.get_tv_shows() + xbmc_dexter.get_tv_shows()}}
            ),
            json.dumps(
                {'result': {'episodes': xbmc_lost.get_episodes()}}
            ),
            json.dumps(
                {'result': {'episodes': xbmc_dexter.get_episodes()}}
            ),
            json.dumps(
                {'result': {'tvshows': []}}
            ),
            json.dumps(
                {'result': {'limits': {'total': 0}}}
            ),
        ]

        # Act
        sync = self.sync.Series(connection)
        sync.sync()

        # Assert
        self.assertNotIn('set_show_as_watched', connection.called)
        self.assertFalse(self.set_episodes_as_watched.called)

    def test_should_set_one_episode_on_eh_and_one_in_xbmc(self):
        # Arrange
        mock_eh_series = eh_series_result.EHSeries()\
            .episode(1, 1, [1, 2, 3, 4, 5, 6])\
            .episode(1, 2, [1, 2, 3, 4, 5, 6])\
            .episode(2, 1, [1, 2, 3, 4, 5, 6])\
            .get()

        connection = connection_mock.ConnectionMock(
            watched_shows=mock_eh_series,
            return_status_code=200
        )

        xbmc_lost = xbmc_series_result.TvShows()
        xbmc_lost\
            .add_show(imdbnumber=1, title='Lost')\
            .add_watched_episodes(
                season=1,
                episode_range=xrange(1, 7)
            )\
            .add_watched_episodes(
                season=2,
                episode_range=xrange(1, 8)
            )

        xbmc_dexter = xbmc_series_result.TvShows().add_show(imdbnumber=2, title='Dexter')
        xbmc_dexter_watched = xbmc_series_result.TvShows().add_watched_episodes(
            season=1,
            episode_range=xrange(1, 6)
        )
        xbmc_dexter_unwatched = xbmc_series_result.TvShows().add_unwatched_episodes(
            season=1,
            episode_range=[6]
        )

        self.json_rcp_mock.side_effect = [
            json.dumps(
                {'result': {'limits': {'total': 2}}}
            ),
            json.dumps(
                {'result': {'tvshows': xbmc_lost.get_tv_shows() + xbmc_dexter.get_tv_shows()}}
            ),
            json.dumps(
                {'result': {'episodes': xbmc_lost.get_episodes()}}
            ),
            json.dumps(
                {'result': {'episodes': xbmc_dexter_watched.get_episodes()}}
            ),
            json.dumps(
                {'result': {'tvshows': []}}
            ),
            json.dumps(
                {'result': {'limits': {'total': 1}}}
            ),
            json.dumps(
                {'result': {'tvshows': xbmc_dexter.get_tv_shows()}}
            ),
            json.dumps(
                {'result': {'episodes': xbmc_dexter_unwatched.get_episodes()}}
            ),
            json.dumps(
                {'result': {'tvshows': []}}
            )
        ]

        # Act
        sync = self.sync.Series(connection)
        sync.sync()

        # Assert
        self.assertIn('set_show_as_watched', connection.called)
        tvshows_to_upload = connection.called['set_show_as_watched']
        self.assertEqual(len(tvshows_to_upload), 1)

        tvshow_to_upload = tvshows_to_upload[0]
        self.assertEqual(tvshow_to_upload['title'], 'Lost')
        self.assertEqual(len(tvshow_to_upload['episodes']), 1)
        self.assertEqual(tvshow_to_upload['episodes'][0]['season'], 2)
        self.assertEqual(tvshow_to_upload['episodes'][0]['episode'], 7)

        self.set_episodes_as_watched.assert_called_once_with([6])


    def test_should_not_sync_anything_if_xbmc_library_is_empty(self):
        # Arrange
        mock_eh_series = eh_series_result.EHSeries()\
            .episode(1, 1, [1, 2, 3, 4, 5, 6])\
            .episode(1, 2, [1, 2, 3, 4, 5, 6])\
            .episode(2, 1, [1, 2, 3, 4, 5, 6])\
            .get()

        connection = connection_mock.ConnectionMock(
            watched_shows=mock_eh_series,
            return_status_code=200
        )

        self.json_rcp_mock.side_effect = [
            json.dumps(
                {'result': {'limits': {'total': 0}}}
            ),
            json.dumps(
                {'result': {'limits': {'total': 0}}}
            )
        ]

        # Act
        sync = self.sync.Series(connection)
        sync.sync()

        # Assert
        self.assertFalse(self.set_episodes_as_watched.called)
        self.assertNotIn('set_show_as_watched', connection.called)


if __name__ == '__main__':
    unittest.main()
