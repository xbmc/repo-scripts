import unittest2
from unittest2 import TestCase
from brightcove.api import Brightcove
from brightcove.objects import Video, Playlist, VideoItemCollection, PlaylistItemCollection
from tests import utils


class TestBrightcove(TestCase):

    def test_init(self):
        b = Brightcove('xxx')
        self.assertEqual(b.token, 'xxx')


class TestVideoApis(utils.MockHTTPTestCase):

    def test_find_video_by_id(self):
        video_id = 1809541469
        v = self.b.find_video_by_id(video_id)
        self.assertEqual(video_id, v.id)
        self.assertIsInstance(v, Video)

    def test_find_videos_by_ids(self):
        videoid1 = 1809541469
        videoid2 = 1809586449
        videos = self.b.find_videos_by_ids([videoid1, videoid2])
        self.assertIsInstance(videos, VideoItemCollection)
        self.assertIsInstance(videos.items[0], Video)
        self.assertEqual(videos.items[0].id, videoid1)
        self.assertIsInstance(videos.items[1], Video)
        self.assertEqual(videos.items[0].id, videoid1)

    def test_find_video_by_reference_id(self):
        refid = 1194817110596
        v = self.b.find_video_by_reference_id(refid)
        self.assertIsInstance(v, Video)

    def test_find_videos_by_reference_ids(self):
        refid1 = '1194817110596'
        refid2 = '1194817110591'
        videos = self.b.find_videos_by_reference_ids([refid1, refid2])
        self.assertIsInstance(videos, VideoItemCollection)
        self.assertIsInstance(videos.items[0], Video)
        self.assertIsInstance(videos.items[1], Video)

    def test_find_all_videos(self):
        videos = self.b.find_all_videos()
        self.assertIsInstance(videos, VideoItemCollection)
        self.assertIsInstance(videos.items[0], Video)
        self.assertIsInstance(videos.items[1], Video)

    def test_find_modified_videos(self):
        videos = self.b.find_modified_videos(20380320)
        self.assertIsInstance(videos, VideoItemCollection)
        self.assertIsInstance(videos.items[0], Video)
        self.assertIsInstance(videos.items[1], Video)

    def test_find_related_videos(self):
        videos = self.b.find_related_videos(video_id=1809541469)
        self.assertIsInstance(videos, VideoItemCollection)
        self.assertIsInstance(videos.items[0], Video)
        self.assertIsInstance(videos.items[1], Video)

    def test_search_videos(self):
        videos = self.b.search_videos(all='Obama')
        self.assertIsInstance(videos, VideoItemCollection)
        self.assertIsInstance(videos.items[0], Video)
        self.assertIsInstance(videos.items[1], Video)

    ## Playlist tests
    def test_find_playlist_by_id(self):
        playlist_id = 49934418001
        playlist = self.b.find_playlist_by_id(playlist_id)
        self.assertIsInstance(playlist, Playlist)
        self.assertEqual(playlist.id, playlist_id)

    def test_find_playlists_by_ids(self):
        playlist1_id = 49934418001
        playlist2_id = 1811464211
        playlists = self.b.find_playlists_by_ids([playlist1_id, playlist2_id])
        self.assertIsInstance(playlists, PlaylistItemCollection)
        self.assertIsInstance(playlists.items[0], Playlist)
        self.assertEqual(playlists.items[0].id, playlist1_id)
        self.assertIsInstance(playlists.items[1], Playlist)
        self.assertEqual(playlists.items[1].id, playlist2_id)

    def test_find_playlist_by_reference_id(self):
        refid = 1194811622205
        playlist = self.b.find_playlist_by_reference_id(refid)
        self.assertIsInstance(playlist, Playlist)

    def test_find_playlists_by_reference_ids(self):
        refid1 = '1194811622205'
        refid2 = '1194811622271'
        playlists = self.b.find_playlists_by_reference_ids([refid1, refid2])
        self.assertIsInstance(playlists, PlaylistItemCollection)
        self.assertIsInstance(playlists.items[0], Playlist)
        self.assertIsInstance(playlists.items[1], Playlist)

    def test_find_all_playlists(self):
        playlists = self.b.find_all_playlists()
        self.assertIsInstance(playlists, PlaylistItemCollection)
        self.assertIsInstance(playlists.items[0], Playlist)
        self.assertIsInstance(playlists.items[1], Playlist)
