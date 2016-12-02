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

class MovieTests(unittest.TestCase):
	@classmethod
	def setUpClass(self):
		self.downloader  = TorecSubtitlesDownloader()

	def test_search_movie_sanity(self):
		item    = self._create_test_valid_item()
		options = self.downloader.search_movie(item['title'])
		self.assertIsNotNone(options)
		self.assertEqual(len(options), 22)

	def test_search_inexisting_movie(self):
		item = {
			'title': 'finding mori',
		}

		options = self.downloader.search_movie(item['title'])
		self.assertIsNone(options)

	def test_download_movie_sanity(self):
		item    = self._create_test_valid_item()
		options = self.downloader.search_movie(item['title'])

		option      = options[0]
		page_id     = option.sub_id
		subtitle_id = option.option_id

		result                 = self.downloader.get_download_link(page_id, subtitle_id)
		subtitleData, fileName = self.downloader.download(result)
		self.assertIsNotNone(subtitleData)

		self._assert_subtitle_data(subtitleData, fileName)

	def _create_test_valid_item(self):
		return {
			'title': 'finding dory',
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

			out = convert_to_utf(temp.name)

			self.assertIsNotNone(temp.read())
			break

if __name__ == '__main__':
    unittest.main()