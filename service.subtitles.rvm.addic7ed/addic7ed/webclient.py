# Copyright (C) 2016, Roman Miroshnychenko aka Roman V.M.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging

import simple_requests as requests
from xbmcvfs import File

from addic7ed.exceptions import Add7ConnectionError, NoSubtitlesReturned

__all__ = ['Session']

logger = logging.getLogger(__name__)

SITE = 'https://www.addic7ed.com'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Host': SITE[8:],
    'Accept-Charset': 'UTF-8',
}


class Session:
    """
    Webclient Session class
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.last_url = ''

    def _open_url(self, url, params, referer):
        logger.debug('Opening URL: %s', url)
        headers = HEADERS.copy()
        headers['Referer'] = referer
        try:
            response = requests.get(url, params=params, headers=headers, verify=False)
        except requests.RequestException as exc:
            logger.error('Unable to connect to Addic7ed.com!')
            raise Add7ConnectionError from exc
        logger.debug('Addic7ed.com returned page:\n%s', response.text)
        if not response.ok:
            logger.error('Addic7ed.com returned status: %s', response.status_code)
            raise Add7ConnectionError
        self.last_url = response.url
        return response

    def load_page(self, path, params=None):
        """
        Load webpage by its relative path on the site

        :param path: relative path starting from '/'
        :param params: URL query params
        :return: webpage content as a Unicode string
        :raises ConnectionError: if unable to connect to the server
        """
        response = self._open_url(SITE + path, params, referer=SITE + '/')
        self.last_url = response.url
        return response.text

    def download_subs(self, path, referer, filename='subtitles.srt'):
        """
        Download subtitles by their URL

        :param path: relative path to .srt starting from '/'
        :param referer: referer page
        :param filename: subtitles filename
        :return: subtitles file contents as a byte string
        :raises ConnectionError: if unable to connect to the server
        :raises NoSubtitlesReturned: if a HTML page is returned instead of subtitles
        """
        response = self._open_url(SITE + path, params=None, referer=referer)
        subtitles = response.content
        if subtitles[:9].lower() == b'<!doctype':
            raise NoSubtitlesReturned
        with File(filename, 'w') as fo:
            fo.write(bytearray(subtitles))
