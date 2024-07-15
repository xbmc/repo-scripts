# (c) Roman Miroshnychenko, 2023
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
from copy import deepcopy
from pprint import pformat

from xbmcgui import Dialog

import pyxbmct
from libs.addon import ADDON, ICON, KODI_VERSION
from libs.gui import NextEpDialog, ui_string, busy_spinner
from libs.medialibrary import (get_movies, get_tvshows, get_episodes,
                               get_recent_movies, get_recent_episodes, get_tvdb_id,
                               NoDataError)
from libs.nextepisode import (prepare_movies_list, prepare_episodes_list, update_data,
                              get_password_hash, LoginError, DataUpdateError)

DIALOG = Dialog()


class LoginDialog(NextEpDialog):
    """
    Enter login/password dialog
    """
    def __init__(self, title='', username=''):
        super(LoginDialog, self).__init__(450, 210, 3, 2, title)
        self.username = username
        self._username_field.setText(username)
        self.password = ''
        self.is_cancelled = True

    def _set_controls(self):
        login_label = pyxbmct.Label(ui_string(32003))
        self.placeControl(login_label, 0, 0)
        password_label = pyxbmct.Label(ui_string(32004))
        self.placeControl(password_label, 1, 0)
        self._username_field = pyxbmct.Edit('')
        self.placeControl(self._username_field, 0, 1)
        password_field_kwargs = {}
        if KODI_VERSION < '18':
            password_field_kwargs['isPassword'] = True
        self._password_field = pyxbmct.Edit('', **password_field_kwargs)
        self.placeControl(self._password_field, 1, 1)
        if KODI_VERSION >= '18':
            from xbmcgui import INPUT_TYPE_TEXT, INPUT_TYPE_PASSWORD
            self._username_field.setType(INPUT_TYPE_TEXT, ui_string(32003))
            self._password_field.setType(INPUT_TYPE_PASSWORD, ui_string(32004))
        self._ok_btn = pyxbmct.Button(ui_string(32005))
        self.placeControl(self._ok_btn, 2, 1)
        self._cancel_btn = pyxbmct.Button(ui_string(32006))
        self.placeControl(self._cancel_btn, 2, 0)

    def _set_connections(self):
        super(LoginDialog, self)._set_connections()
        self.connect(self._ok_btn, self._ok)
        self.connect(self._cancel_btn, self.close)

    def _set_navigation(self):
        self._username_field.controlUp(self._ok_btn)
        self._username_field.controlDown(self._password_field)
        self._password_field.controlUp(self._username_field)
        self._password_field.controlDown(self._ok_btn)
        self._ok_btn.setNavigation(self._password_field, self._username_field,
                                   self._cancel_btn, self._cancel_btn)
        self._cancel_btn.setNavigation(self._password_field,
                                       self._username_field,
                                       self._ok_btn, self._ok_btn)
        self.setFocus(self._username_field)

    def _ok(self):
        self.is_cancelled = False
        self.username = self._username_field.getText()
        self.password = self._password_field.getText()
        self.close()

    def close(self):
        if self.is_cancelled:
            self.username = self.password = ''
        super(LoginDialog, self).close()


def send_data(data):
    """
    Send data to next-episode.net and process possible errors

    :param data: data to be sent
    :type data: dict
    """
    try:
        update_data(data)
    except LoginError:
        logging.error('Login failed! Re-enter your username and password.')
        DIALOG.notification('next-episode.net', ui_string(32007), icon='error')
    except DataUpdateError as ex:
        logging.exception(str(ex))
        if ADDON.getSetting('disable_error_dialogs') != 'true':
            DIALOG.ok('next-epsisode.net',
                      '[CR]'.join((
                          ui_string(32020),
                          ui_string(32021).format(ex.failed_movies),
                          ui_string(32022).format(ex.failed_shows)
                      )))
        else:
            DIALOG.notification('next-episode.net', ui_string(32008),
                                icon='error')
    else:
        DIALOG.notification('next-episode.net', ui_string(32009),
                            icon=ICON, time=2000, sound=False)


def log_data_sent(data):
    """
    Log data sent to next-episode.net with sanitized username/hash

    :param data: data to be sent
    :type data: dict
    """
    logged_data = deepcopy(data)
    logged_data['user']['username'] = logged_data['user']['hash'] = '*****'
    logging.debug('Data sent:\n%s', pformat(logged_data))


def sync_library():
    """
    Synchronize Kodi video library with next-episode.net
    """
    with busy_spinner():
        data = {
            'user': {
                'username': ADDON.getSetting('username'),
                'hash': ADDON.getSetting('hash')
            }
        }
        try:
            data['movies'] = prepare_movies_list(get_movies())
        except NoDataError:
            pass
        try:
            tvshows = get_tvshows()
        except NoDataError:
            pass
        else:
            episodes = []
            for show in tvshows:
                try:
                    episodes += prepare_episodes_list(
                        get_episodes(show['tvshowid'])
                    )
                except NoDataError:
                    continue
            data['tvshows'] = episodes
        if 'movies' in data or 'tvshows' in data:
            log_data_sent(data)
            send_data(data)
        else:
            logging.warning(
                'Kodi video library has no movies and TV episodes.'
            )


def sync_new_items():
    """
    Synchronize new video items with next-episode.net
    """
    data = {
        'user': {
            'username': ADDON.getSetting('username'),
            'hash': ADDON.getSetting('hash')
        }}
    try:
        data['movies'] = prepare_movies_list(get_recent_movies())
    except NoDataError:
        pass
    try:
        data['tvshows'] = prepare_episodes_list(get_recent_episodes())
    except NoDataError:
        pass
    if 'movies' in data or 'episodes' in data:
        log_data_sent(data)
        send_data(data)
    else:
        logging.warning(
            'Kodi video library has no recent movies and episodes.'
        )


def update_single_item(item):
    """
    Synchronize single item (movie or episode) with next-episode-net

    :param item: video item
    :type item: dict
    """
    data = {
        'user': {
            'username': ADDON.getSetting('username'),
            'hash': ADDON.getSetting('hash')
        }}
    if item['type'] == 'episode':
        tvdb_id = get_tvdb_id(item['tvshowid'])
        if tvdb_id is not None:
            data['tvshows'] = [{
                'thetvdb_id': tvdb_id,
                'season': str(item['season']),
                'episode': str(item['episode']),
                'watched': '1' if item['playcount'] else '0'
            }]
    elif item['type'] == 'movie':
        imdb_id = None
        if 'tt' in item['imdbnumber']:
            imdb_id = item['imdbnumber']
        elif 'uniqueid' in item and item['uniqueid'].get('imdb'):
            imdb_id = item['uniqueid']['imdb']
        if imdb_id is not None:
            data['movies'] = [{
                'imdb_id': imdb_id,
                'watched': '1' if item['playcount'] else '0'
            }]
    if data.get('movies') or data.get('tvshows'):
        log_data_sent(data)
        send_data(data)


def login():
    """
    Login to next-episode.net

    :return: ``True`` on successful login,
        ``False`` if login is failed or cancelled
    :rtype: bool
    """
    login_dialog = LoginDialog(ui_string(32001),
                               username=ADDON.getSetting('username'))
    login_dialog.doModal()
    result = False
    if not login_dialog.is_cancelled:
        with busy_spinner():
            username = login_dialog.username
            password = login_dialog.password
            try:
                hash_ = get_password_hash(username, password)
            except LoginError:
                DIALOG.ok('next-episode.net',
                          '[CR]'.join((
                              ui_string(32007),
                              ui_string(32010)
                          )))
                logging.error('Login failed!')
            else:
                ADDON.setSetting('username', username)
                ADDON.setSetting('hash', hash_)
                logging.debug('Successful login')
                DIALOG.notification('next-episode.net', ui_string(32011),
                                    time=3000, sound=False)
                result = True
    del login_dialog
    return result
