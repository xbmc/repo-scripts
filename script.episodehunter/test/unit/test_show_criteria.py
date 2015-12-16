import unittest
from mock import Mock
from test.xbmc_base_test_case import XbmcBaseTestCase
from test.test_data import xbmc_series_result


class TestShowCriteria(XbmcBaseTestCase, object):
    """
    Test class for series criteria method
    """

    xbmc = None
    xbmcgui = None

    def setUp(self):
        super(TestShowCriteria, self).setUp()
        import resources.lib.xbmc_repository as helper

        self.helper = helper

        self.xbmc.abortRequested = False
        self.progress = Mock()
        self.progress.iscanceled.return_value = False
        self.xbmcgui.DialogProgress = Mock(return_value=self.progress)

    def test_should_return_true_if_series_is_valid(self):
        # Arrange
        series_mock = xbmc_series_result.TvShows()
        series_mock.add_show(tvshowid=1, title='Dexter')
        tv_shows = series_mock.get_tv_shows()[0]

        # Act
        result = self.helper.meet_show_criteria(tv_shows)

        # Assert
        self.assertTrue(result)

    def test_should_return_fasle_if_series_has_no_title(self):
        # Arrange
        series_mock = xbmc_series_result.TvShows()
        series_mock.add_show(tvshowid=1)
        tv_shows = series_mock.get_tv_shows()[0]
        tv_shows.pop('title', None)

        # Act
        result = self.helper.meet_show_criteria(tv_shows)

        # Assert
        self.assertFalse(result)

    def test_should_return_fasle_if_series_has_no_tvdb_id(self):
        # Arrange
        series_mock = xbmc_series_result.TvShows()
        series_mock.add_show(tvshowid=1, title='Dexter')
        tv_shows = series_mock.get_tv_shows()[0]
        tv_shows.pop('imdbnumber', None)

        # Act
        result = self.helper.meet_show_criteria(tv_shows)

        # Assert
        self.assertFalse(result)

    def test_should_return_false_if_series_has_no_year(self):
        # Arrange
        series_mock = xbmc_series_result.TvShows()
        series_mock.add_show(tvshowid=1, title='Dexter')
        tv_shows = series_mock.get_tv_shows()[0]
        tv_shows.pop('year', None)

        # Act
        result = self.helper.meet_show_criteria(tv_shows)

        # Assert
        self.assertFalse(result)

    def test_should_return_false_if_series_has_year_but_it_is_zero(self):
        # Arrange
        series_mock = xbmc_series_result.TvShows()
        series_mock.add_show(tvshowid=1, title='Dexter')
        tv_shows = series_mock.get_tv_shows()[0]
        tv_shows['year'] = 0

        # Act
        result = self.helper.meet_show_criteria(tv_shows)

        # Assert
        self.assertFalse(result)

    def test_should_return_true_even_if_series_has_no_play_count(self):
        # Arrange
        series_mock = xbmc_series_result.TvShows()
        series_mock.add_show(tvshowid=1, title='Dexter')
        tv_shows = series_mock.get_tv_shows()[0]
        tv_shows.pop('playcount', None)

        # Act
        result = self.helper.meet_show_criteria(tv_shows)

        # Assert
        self.assertTrue(result)

    def test_should_return_true_if_series_has_play_count_event_if_its_zero(self):
        # Arrange
        series_mock = xbmc_series_result.TvShows()
        series_mock.add_show(tvshowid=1, title='Dexter')
        tv_shows = series_mock.get_tv_shows()[0]
        tv_shows['playcount'] = 0

        # Act
        result = self.helper.meet_show_criteria(tv_shows)

        # Assert
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
