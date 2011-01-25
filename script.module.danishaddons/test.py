import time
import os
import sys
import unittest
import tempfile

sys.path.append("xbmcstubs")

import xbmcaddon
import danishaddons
import danishaddons.info
import danishaddons.web

# contents of URL will change every second
URL = 'http://tommy.winther.nu/files/2010/12/now.php'

class TestDanishAddons(unittest.TestCase):

    def test00Init(self):
        expectedAddonId = 'script.module.danishaddons'

        self.assertEqual(None, danishaddons.ADDON_ID, msg = 'Expected ADDON_ID to be None before call to init()')
        danishaddons.init([os.getcwd(), '12345', '?key1=value1&key2=value2'])
        self.assertEqual(expectedAddonId, danishaddons.ADDON_ID, msg = 'Got unexpected ADDON_ID')
        self.assertTrue(isinstance(danishaddons.ADDON, xbmcaddon.Addon), msg = 'Expected instance of xbmcaddon.Addon class')
        self.assertEqual('/tmp/%s' % expectedAddonId, danishaddons.ADDON_DATA_PATH)
        self.assertEqual(os.getcwd(), danishaddons.ADDON_PATH)
        self.assertEqual(12345, danishaddons.ADDON_HANDLE)
        self.assertEqual({'key1' : 'value1', 'key2' : 'value2'}, danishaddons.ADDON_PARAMS)

    def testSecondsToDuration(self):
        self.assertEquals('00:00:10', danishaddons.info.secondsToDuration(10))
        self.assertEquals('00:01:00', danishaddons.info.secondsToDuration(60))
        self.assertEquals('00:10:00', danishaddons.info.secondsToDuration(600))
        self.assertEquals('01:00:00', danishaddons.info.secondsToDuration(3600))
        self.assertEquals('03:25:45', danishaddons.info.secondsToDuration(12345))
        self.assertEquals('15:05:21', danishaddons.info.secondsToDuration(54321))

    def testDownloadUrl(self):
        first = danishaddons.web.downloadUrl(URL)
        time.sleep(1)
        second = danishaddons.web.downloadUrl(URL)

        self.assertNotEquals(first, second, msg = 'Content is not different, perhaps it is cached?')

    def testDownloadAndCacheUrl(self):
        danishaddons.init([tempfile.gettempdir()])

        first = danishaddons.web.downloadAndCacheUrl(URL, os.path.join(danishaddons.ADDON_DATA_PATH, 'unittestcache.tmp'), 1)
        time.sleep(1)
        second = danishaddons.web.downloadAndCacheUrl(URL, os.path.join(danishaddons.ADDON_DATA_PATH, 'unittestcache.tmp'), 1)

        self.assertEquals(first, second, msg = 'Content is different, perhaps it is not cached?')

if __name__ == '__main__':
    unittest.main()
