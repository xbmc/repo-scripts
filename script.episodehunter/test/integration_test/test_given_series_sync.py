from mock import Mock
import unittest
import json

from test.xbmc_base_test_case import XbmcBaseTestCase
from test.test_data import eh_series_result, xbmc_series_result
from test.mocks import connection_mock


class GivenSeriesSync(XbmcBaseTestCase, object):
    """
    Test class for tv shows sync methods between EH and XBMC
    """

    xbmc = None
    xbmcgui = None
    get_tv_shows_from_xbmc = None
    get_seasons_from_xbmc = None
    get_episodes_from_xbmc = None
    set_series_as_watched = None

    def setUp(self):
        super(GivenSeriesSync, self).setUp()
        from resources.lib import xbmc_helper

        self.get_tv_shows_from_xbmc = Mock()
        self.get_seasons_from_xbmc = Mock()
        self.get_episodes_from_xbmc = Mock()
        self.set_series_as_watched = Mock()

        xbmc_helper.get_tv_shows_from_xbmc = self.get_tv_shows_from_xbmc
        xbmc_helper.get_seasons_from_xbmc = self.get_seasons_from_xbmc
        xbmc_helper.get_episodes_from_xbmc = self.get_episodes_from_xbmc
        xbmc_helper.set_series_as_watched = self.set_series_as_watched

        import resources.lib.sync.sync_series as sync
        self.sync = sync

        self.progress = Mock()
        self.progress.iscanceled.return_value = False
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

        mock_xbmc_series = xbmc_series_result.TvShows()
        mock_xbmc_series\
            .add_show(imdbnumber=1, title='Lost')\
            .add_show(imdbnumber=2)\
            .add_watched_episodes(
                tvshowid=1,
                season=1,
                episode_range=xrange(1, 8)
            )\
            .add_watched_episodes(
                tvshowid=1,
                season=2,
                episode_range=xrange(1, 7)
            )

        self.get_tv_shows_from_xbmc.side_effect = mock_xbmc_series.get_tv_shows
        self.get_seasons_from_xbmc.side_effect = mock_xbmc_series.get_seasons
        self.get_episodes_from_xbmc.side_effect = mock_xbmc_series.get_episodes

        self.xbmc.abortRequested = False

        # Act
        sync = self.sync.Series(connection)
        sync.sync()

        # Assert
        self.assertIn('set_series_as_watched', connection.called)
        tvshows_to_upload = connection.called['set_series_as_watched'][0]
        tvshow_to_upload = tvshows_to_upload[0]
        self.assertEqual(len(tvshows_to_upload), 1)
        self.assertEqual(tvshow_to_upload.title, 'Lost')
        self.assertEqual(len(tvshow_to_upload.episodes), 1)
        self.assertEqual(tvshow_to_upload.episodes[0].season, 1)
        self.assertEqual(tvshow_to_upload.episodes[0].episode, 7)

    def test_should_not_upload_unwatched_episodes(self):
        # Arrange
        mock_eh_series = eh_series_result.EHSeries()\
            .episode(1, 1, [1, 2, 3, 4, 5, 6])\
            .get()

        connection = connection_mock.ConnectionMock(
            watched_shows=mock_eh_series,
            return_status_code=200
        )

        mock_xbmc_series = xbmc_series_result.TvShows()
        mock_xbmc_series\
            .add_show(imdbnumber=1, title='Lost')\
            .add_watched_episodes(
                tvshowid=1,
                season=1,
                episode_range=xrange(1, 7)
            )\
            .add_unwatched_episodes(
                tvshowid=1,
                season=1,
                episode_range=[7]
            )

        self.get_tv_shows_from_xbmc.side_effect = mock_xbmc_series.get_tv_shows
        self.get_seasons_from_xbmc.side_effect = mock_xbmc_series.get_seasons
        self.get_episodes_from_xbmc.side_effect = mock_xbmc_series.get_episodes

        self.xbmc.abortRequested = False

        # Act
        sync = self.sync.Series(connection)
        sync.sync()

        # Assert
        self.assertNotIn('set_series_as_watched', connection.called)
        self.assertFalse(self.set_series_as_watched.called)
        self.assertEqual(len(sync.upstream_sync), 0)
        self.assertEqual(len(sync.downstream_sync), 0)

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

        mock_xbmc_series = xbmc_series_result.TvShows()
        mock_xbmc_series\
            .add_show(imdbnumber=1)\
            .add_watched_episodes(
                tvshowid=1,
                season=1,
                episode_range=xrange(1, 7)
            )\
            .add_watched_episodes(
                tvshowid=1,
                season=2,
                episode_range=xrange(1, 7)
            )\
            .add_show(imdbnumber=2)\
            .add_watched_episodes(
                tvshowid=2,
                season=1,
                episode_range=xrange(1, 7)
            )

        self.get_tv_shows_from_xbmc.side_effect = mock_xbmc_series.get_tv_shows
        self.get_seasons_from_xbmc.side_effect = mock_xbmc_series.get_seasons
        self.get_episodes_from_xbmc.side_effect = mock_xbmc_series.get_episodes

        self.xbmc.abortRequested = False

        # Act
        sync = self.sync.Series(connection)
        sync.sync()

        # Assert
        self.assertNotIn('set_series_as_watched', connection.called)
        self.assertFalse(self.set_series_as_watched.called)
        self.assertEqual(len(sync.upstream_sync), 0)
        self.assertEqual(len(sync.downstream_sync), 0)

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

        mock_xbmc_series = xbmc_series_result.TvShows()
        mock_xbmc_series\
            .add_show(imdbnumber=1, title='Lost')\
            .add_watched_episodes(
                tvshowid=1,
                season=1,
                episode_range=xrange(1, 7)
            )\
            .add_watched_episodes(
                tvshowid=1,
                season=2,
                episode_range=xrange(1, 8)
            )\
            .add_show(imdbnumber=2)\
            .add_watched_episodes(
                tvshowid=2,
                season=1,
                episode_range=xrange(1, 6)
            )\
            .add_unwatched_episodes(
                tvshowid=2,
                season=1,
                episode_range=[6]
            )

        self.get_tv_shows_from_xbmc.side_effect = mock_xbmc_series.get_tv_shows
        self.get_seasons_from_xbmc.side_effect = mock_xbmc_series.get_seasons
        self.get_episodes_from_xbmc.side_effect = mock_xbmc_series.get_episodes

        self.xbmc.abortRequested = False

        # Act
        sync = self.sync.Series(connection)
        sync.sync()

        # Assert
        self.assertIn('set_series_as_watched', connection.called)
        tvshows_to_upload = connection.called['set_series_as_watched'][0]
        tvshow_to_upload = tvshows_to_upload[0]
        self.assertEqual(len(tvshows_to_upload), 1)
        self.assertEqual(tvshow_to_upload.title, 'Lost')
        self.assertEqual(len(tvshow_to_upload.episodes), 1)
        self.assertEqual(tvshow_to_upload.episodes[0].season, 2)
        self.assertEqual(tvshow_to_upload.episodes[0].episode, 7)

        self.set_series_as_watched.assert_called_once_with(sync.downstream_sync)
        self.assertEqual(len(sync.downstream_sync), 1)
        tvshow_to_download = sync.downstream_sync[0]
        self.assertEqual(len(tvshow_to_download.episodes), 1)
        self.assertEqual(tvshow_to_download.episodes[0].season, 1)
        self.assertEqual(tvshow_to_download.episodes[0].episode, 6)

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

        self.get_tv_shows_from_xbmc.return_value = None

        self.xbmc.abortRequested = False

        # Act
        sync = self.sync.Series(connection)
        sync.sync()

        # Assert
        self.assertFalse(self.set_series_as_watched.called)
        self.assertNotIn('set_series_as_watched', connection.called)


if __name__ == '__main__':
    unittest.main()
