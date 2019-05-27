import unittest
import logging
logging.getLogger("urllib3").setLevel(logging.WARNING)

from myepisodes import MyEpisodes

USERNAME="test1337"
PASSWORD="test1234"

class TestMyEpisodes(unittest.TestCase):

    mye = None

    @classmethod
    def setUpClass(cls):
        cls.mye = MyEpisodes(USERNAME, PASSWORD)

    def test_01_false_login(self):
        mye_wrong_login = MyEpisodes("aaaa", "bbbb")
        mye_wrong_login.login()
        self.assertFalse(mye_wrong_login.is_logged)

    def test_02_login(self):
        self.mye.login()
        self.assertTrue(self.mye.is_logged)

    def test_03_populate_shows(self):
        self.mye.populate_shows()
        results = {u'scandal': 8603,
                   u'zbrodnia': 16034,
                   u'mr. robot': 15082,
                   u'mr robot': 15082}
        self.assertDictEqual(self.mye.shows, results)

    def test_04_find_show_id(self):
        self.assertNotEqual(self.mye.shows, {})

        self.assertEqual(self.mye.find_show_id("South Park"), 7)
        self.assertEqual(self.mye.find_show_id("Doctor Who"), 114)
        self.assertEqual(self.mye.find_show_id("Scandal"), 8603)
        self.assertEqual(self.mye.find_show_id("Scandal Us"), 8603)
        self.assertEqual(self.mye.find_show_id("Mr Robot"), 15082)

    def test_05_add_show(self):
        self.mye.add_show(6585)
        self.assertTrue('pretty little liars' in self.mye.shows.keys())
        self.assertEqual(self.mye.shows['pretty little liars'], 6585)

    def test_06_del_show(self):
        self.mye.del_show(6585)
        self.assertFalse('pretty little liars' in self.mye.shows.keys())

    def test_07_set_episode_watched(self):
        ret = self.mye.set_episode_watched(15082, "1", "1")
        self.assertTrue(ret)
        ret = self.mye.set_episode_watched(15082, 1, 2)
        self.assertTrue(ret)
        ret = self.mye.set_episode_watched(8603, "07", "18")
        self.assertTrue(ret)

    def test_08_set_episode_unwatched(self):
        ret = self.mye.set_episode_unwatched(15082, "1", "1")
        self.assertTrue(ret)
        ret = self.mye.set_episode_unwatched(15082, 1, 2)
        self.assertTrue(ret)
        ret = self.mye.set_episode_unwatched(8603, "07", "18")
        self.assertTrue(ret)


if __name__ == '__main__':
    unittest.main()
