import unittest
import json
from mock import MagicMock, call
from test.xbmc_base_test_case import XbmcBaseTestCase

class GivenXbmcHelper(XbmcBaseTestCase, object):

    json_rcp_mock = None
    helper = None

    def setUp(self):
        super(GivenXbmcHelper, self).setUp()
        self.xbmc.executeJSONRPC = self.json_rcp_mock = MagicMock()
        import resources.lib.xbmc_repository
        self.helper = resources.lib.xbmc_repository

    def test_should_get_active_player(self):
        # Arrange
        response = json.dumps({'result': [{'playerid': 5}]})
        self.json_rcp_mock.return_value = response

        # Act
        result = self.helper.active_player()

        # Assert
        self.assertEqual(result, 5)

    def test_should_get_watched_shows(self):
        # Arrange
        response = [
            json.dumps(
                {'result': {'tvshows': [
                    {'title': 'Dexter', 'imdbnumber': '12345', 'year': 2006}
                ]}}
            ),
            json.dumps(
                {'result': {'tvshows': [
                    {'title': 'Breaking Bad', 'imdbnumber': '54321', 'year': 2010}
                ]}}
            ),
            json.dumps(
                {'result': {'tvshows': []}}
            )
        ]
        self.json_rcp_mock.side_effect = response

        # Act
        result = self.helper.watched_shows()

        # Assert
        num_show = sum(1 for x in result)
        args_list = self.json_rcp_mock.call_args_list
        self.assertEqual(num_show, 2)
        self.assertEqual(self.json_rcp_mock.call_count, 3)
        self.assertEqual(args_list[0], call('{"jsonrpc": "2.0", "params": {"filter": {"operator": "greaterthan", "field": "playcount", "value": "0"}, "properties": ["title", "year", "imdbnumber", "playcount", "season", "watchedepisodes"], "limits": {"start": 0, "end": 5}}, "method": "VideoLibrary.GetTVShows", "id": 1}'))
        self.assertEqual(args_list[1], call('{"jsonrpc": "2.0", "params": {"filter": {"operator": "greaterthan", "field": "playcount", "value": "0"}, "properties": ["title", "year", "imdbnumber", "playcount", "season", "watchedepisodes"], "limits": {"start": 5, "end": 10}}, "method": "VideoLibrary.GetTVShows", "id": 1}'))
        self.assertEqual(args_list[2], call('{"jsonrpc": "2.0", "params": {"filter": {"operator": "greaterthan", "field": "playcount", "value": "0"}, "properties": ["title", "year", "imdbnumber", "playcount", "season", "watchedepisodes"], "limits": {"start": 10, "end": 15}}, "method": "VideoLibrary.GetTVShows", "id": 1}'))

if __name__ == '__main__':
    unittest.main()
