import unittest
from test.xbmc_base_test_case import XbmcBaseTestCase
from test.test_data import xbmc_movie_result

class MovieCriteria(XbmcBaseTestCase, object):
    """
    Test class for movie sync methods between EH and XBMC
    """
    meet_movie_criteria = None

    def setUp(self):
        super(MovieCriteria, self).setUp()
        from resources.lib.xbmc_repository import meet_movie_criteria
        self.meet_movie_criteria = meet_movie_criteria

    def test_should_return_fasle_if_movie_has_no_imdb_id(self):
        movie = xbmc_movie_result.get('The Hunger Games', remove_attr=['imdbnumber'])[0]
        result = self.meet_movie_criteria(movie)
        self.assertFalse(result)

    def test_should_return_fasle_if_movie_has_empty_imdb_id(self):
        movie = xbmc_movie_result.get('The Hunger Games')[0]
        movie['imdbnumber'] = ''
        result = self.meet_movie_criteria(movie)
        self.assertFalse(result)

    def test_should_return_fasle_if_movie_has_no_title_nor_orginaltitle(self):
        movie = xbmc_movie_result.get('The Hunger Games', remove_attr=['title', 'originaltitle'])[0]
        result = self.meet_movie_criteria(movie)
        self.assertFalse(result)

    def test_should_return_true_if_movie_has_no_title_but_orginaltitle(self):
        movie = xbmc_movie_result.get('The Hunger Games', remove_attr=['title'])[0]
        result = self.meet_movie_criteria(movie)
        self.assertTrue(result)

    def test_should_return_true_if_movie_has_no_orginaltitle_but_title(self):
        movie = xbmc_movie_result.get('The Hunger Games', remove_attr=['originaltitle'])[0]
        result = self.meet_movie_criteria(movie)
        self.assertTrue(result)

    def test_should_return_false_if_movie_has_no_year(self):
        movie = xbmc_movie_result.get('The Hunger Games', remove_attr=['year'])[0]
        result = self.meet_movie_criteria(movie)
        self.assertFalse(result)

    def test_should_return_false_if_movie_has_year_but_its_zero(self):
        movie = xbmc_movie_result.get('The Hunger Games')[0]
        movie['year'] = 0
        result = self.meet_movie_criteria(movie)
        self.assertFalse(result)

    def test_should_return_true_if_movie_has_play_count_event_if_its_zero(self):
        movie = xbmc_movie_result.get('The Hunger Games')[0]
        movie['playcount'] = 0
        result = self.meet_movie_criteria(movie)
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
