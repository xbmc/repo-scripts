# coding: utf-8

from __future__ import absolute_import, unicode_literals
import requests
from .exceptions import Add7ConnectionError
from .utils import logger

__all__ = ['Session']

SITE = 'https://www.addic7ed.com'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Host': SITE[8:],
    'Accept-Charset': 'UTF-8',
    'Accept-Encoding': 'gzip,deflate'
}


class Session(object):
    """
    Webclient Session class
    """
    def __init__(self):
        self._session = requests.Session()
        self._session.headers = HEADERS.copy()
        self._last_url = ''

    @property
    def last_url(self):
        """
        Get actual url (with redirect) of the last loaded webpage

        :return: URL of the last webpage
        """
        return self._last_url

    def _open_url(self, url, params, referer):
        logger.debug('Opening URL: {0}'.format(url))
        self._session.headers['Referer'] = referer
        try:
            response = self._session.get(url, params=params, verify=False)
        except requests.RequestException:
            logger.error('Unable to connect to Addic7ed.com!')
            raise Add7ConnectionError
        response.encoding = 'utf-8'  # Encoding is auto-detected incorrectly
        logger.debug('Addic7ed.com returned page:\n{}'.format(response.text))
        if not response.ok:
            logger.error('Addic7ed.com returned status: {0}'.format(
                response.status_code)
            )
            raise Add7ConnectionError
        self._last_url = response.url
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
        self._last_url = response.url
        return response.text

    def download_subs(self, path, referer):
        """
        Download subtitles by their URL

        :param path: relative path to .srt starting from '/'
        :param referer: referer page
        :return: subtitles file contents as a byte string
        :raises ConnectionError: if unable to connect to the server
        """
        response = self._open_url(SITE + path, params=None, referer=referer)
        return response.content
