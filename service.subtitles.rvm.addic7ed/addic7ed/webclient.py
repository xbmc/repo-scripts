# coding: utf-8

from __future__ import absolute_import, unicode_literals
from future import standard_library
standard_library.install_aliases()

import os
import pickle
import requests
from kodi_six.xbmcgui import Dialog
from .addon import ADDON_ID, addon, profile, get_ui_string
from .exceptions import CookiesError, LoginError, Add7ConnectionError
from .utils import logger

__all__ = ['Session']

cookies = os.path.join(profile, 'cookies.pickle')
SITE = 'http://www.addic7ed.com'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) '
                  'Gecko/20100101 Firefox/60.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Host': SITE[7:],
    'Accept-Charset': 'UTF-8',
    'Accept-Encoding': 'gzip,deflate'
}


class Session(object):
    """
    Webclient Session class

    If login is enabled, it logins to the site and stores persistent cookies
    in addon profile directory.
    """
    def __init__(self):
        self._session = requests.Session()
        self._session.headers = HEADERS.copy()
        self._last_url = ''
        try:
            self._session.cookies = self._load_cookie_jar()
        except CookiesError:
            pass
        if addon.getSetting('do_login') == 'true' and not self.is_logged_in:
            try:
                self._login()
            except LoginError:
                logger.error('Login error! Check username and password.')
                Dialog().notification(
                    ADDON_ID,
                    get_ui_string(32009),
                    icon='error'
                )
            else:
                logger.notice('Successful login.')

    @property
    def is_logged_in(self):
        """
        Check if cookies contain user login data

        :return: if user is logged in
        """
        return 'wikisubtitlesuser' in self._session.cookies

    @property
    def last_url(self):
        """
        Get actual url (with redirect) of the last loaded webpage

        :return: URL of the last webpage
        """
        return self._last_url

    def _load_cookie_jar(self):
        """
        :return: CookieJar object
        :raises CookiesError: if unable to load cookies
        """
        if os.path.exists(cookies):
            with open(cookies, 'rb') as fo:
                try:
                    return pickle.load(fo)
                except (pickle.PickleError, EOFError):
                    pass
        raise CookiesError

    def _login(self):
        """
        :raises LoginError: on login error
        """
        self._session.headers['Referer'] = SITE + '/login.php'
        username = addon.getSetting('username')
        password = addon.getSetting('password')
        response = self._session.post(
            SITE + '/dologin.php',
            data={
                'username': username,
                'password': password,
                'remember': 'true',
                'url': '',
                'Submit': 'Log in'
            }
        )
        if not self.is_logged_in:
            response.encoding = 'utf-8'
            logger.debug(response.text)
            raise LoginError
        with open(cookies, 'wb') as fo:
            pickle.dump(self._session.cookies, fo, protocol=2)

    def _open_url(self, url, params, referer):
        logger.debug('Opening URL: {0}'.format(url))
        self._session.headers['Referer'] = referer
        try:
            response = self._session.get(url, params=params)
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
        self._last_url = response.url
        return response.content
