from mock import Mock
import unittest
import json

from test.xbmc_base_test_case import XbmcBaseTestCase
from test.mocks import xbmc_mock


class GivenEHPlayer(XbmcBaseTestCase, object):
    """
    Test class for connections
    """

    xbmc = None
    xbmcgui = None
    http_mock = None
    http = Mock()
    addon = None

    def setUp(self):
        super(GivenEHPlayer, self).setUp()
        self.xbmc = xbmc_mock
        import resources.lib.eh_player
        self.addon = resources.lib.eh_player

    def test_should_return_true_if_movie(self):
        data = {'type': 'movie'}
        result = self.addon.is_movie(data)
        self.assertTrue(result)

    def test_should_return_false_if_not_movie(self):
        data = {'type': 'episode'}
        result = self.addon.is_movie(data)
        self.assertFalse(result)

    def test_should_return_true_if_episode(self):
        data = {'type': 'episode'}
        result = self.addon.is_episode(data)
        self.assertTrue(result)

    def test_should_return_false_if_not_episode(self):
        data = {'type': 'movie'}
        result = self.addon.is_episode(data)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
