import os
import sys
import time
import rarfile
import zipfile
import tempfile
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../resources/lib")

from TorecSubtitlesDownloader import TorecSubtitlesDownloader
from SubtitleHelper import convert_to_utf

class TVShowTests(unittest.TestCase):
	@classmethod
	def setUpClass(self):
		self.downloader  = TorecSubtitlesDownloader()

	def test_search_tvshow_sanity(self):
		item    = self._create_test_valid_item()
		options = self.downloader.search_tvshow(item['tvshow'], item['season'], item['episode'])
		self.assertIsNotNone(options)
		self.assertGreaterEqual(len(options), 5)

	def test_search_tvshow_last_season_episode(self):
		item    = {
			'tvshow': 'house of cards',
			'season': '3',
			'episode': '13'
		}

		options = self.downloader.search_tvshow(item['tvshow'], item['season'], item['episode'])
		self.assertIsNotNone(options)
		self.assertGreaterEqual(len(options), 1)

	def test_search_inexisting_tvshow(self):
		item = {
			'tvshow': 'house of lards',
			'season': '3',
			'episode': '1'
		}

		options = self.downloader.search_tvshow(item['tvshow'], item['season'], item['episode'])
		self.assertIsNone(options)

	def test_search_existing_tvshow_with_no_subtitles(self):
		item = {
			'tvshow': 'Cowboy Bebop',
			'season': '1',
			'episode': '1'
		}

		options = self.downloader.search_tvshow(item['tvshow'], item['season'], item['episode'])
		self.assertIsNone(options)	

	def test_download_tvshow_sanity(self):
		item    = self._create_test_valid_item()
		options = self.downloader.search_tvshow(item['tvshow'], item['season'], item['episode'])

		option      = options[-1]
		page_id     = option.sub_id
		subtitle_id = option.option_id

		download_link = self.downloader.get_download_link(page_id, subtitle_id)
		self.assertTrue(len(download_link) != 0)

		subtitleData, fileName = self.downloader.download(download_link)
		self.assertIsNotNone(subtitleData)

		self._assert_subtitle_data(subtitleData, fileName)

	def _create_test_valid_item(self):
		return {
			'tvshow': 'house of cards',
			'season': '3',
			'episode': '1'
		}

	def _assert_subtitle_data(self, subtitleData, fileName):
		extension = os.path.splitext(fileName)[1]

		temp = tempfile.NamedTemporaryFile()
		temp.write(subtitleData)
		temp.flush()

		if (extension == ".zip"):
			rf = zipfile.ZipFile(temp.name)
		elif (extension == ".rar"):
			rf = rarfile.RarFile(temp.name)
		else:
			fail("unknown extension found %s", extension)

		for f in rf.infolist():
			data = rf.read(f.filename)

			temp = tempfile.NamedTemporaryFile()
			temp.write(data)
			temp.flush()

			self.assertIsNotNone(temp.read())
			break

if __name__ == '__main__':
    unittest.main()