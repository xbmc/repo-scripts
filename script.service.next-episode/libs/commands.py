# coding: utf-8
# Created on: 17.03.2016
# Author: Roman Miroshnychenko aka Roman V.M. (romanvm@yandex.ua)
# License: GPL v. 3 <http://www.gnu.org/licenses/gpl-3.0.en.html>

import os
import sys
from copy import deepcopy
import xbmc
from xbmcaddon import Addon
from xbmcgui import Dialog
import pyxbmct
from medialibrary import (get_movies, get_tvshows, get_episodes, get_recent_movies,
                          get_recent_episodes, get_tvdb_id, NoDataError)
from nextepisode import (prepare_movies_list, prepare_episodes_list, update_data,
                         get_password_hash, LoginError, DataUpdateError)
from gui import NextEpDialog, ui_string

addon = Addon('script.service.next-episode')
icon = os.path.join(addon.getAddonInfo('path'), 'icon.png')
dialog = Dialog()


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
        self._password_field = pyxbmct.Edit('', isPassword=True)
        self.placeControl(self._password_field, 1, 1)
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
        self._ok_btn.setNavigation(self._password_field, self._username_field, self._cancel_btn, self._cancel_btn)
        self._cancel_btn.setNavigation(self._password_field, self._username_field, self._ok_btn, self._ok_btn)
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
        xbmc.log('next-episode.net: login failed! Re-enter your username and password.', xbmc.LOGERROR)
        dialog.notification('next-episode.net', ui_string(32007), icon='error')
    except DataUpdateError as ex:
        xbmc.log('next-episode.net: {0}'.format(ex), xbmc.LOGERROR)
        if addon.getSetting('disable_error_dialogs') != 'true':
            dialog.ok('next-epsisode.net',
                      ui_string(32020),
                      ui_string(32021).format(ex.failed_movies),
                      ui_string(32022).format(ex.failed_shows))
        else:
            dialog.notification('next-episode.net', ui_string(32008), icon='error')
    else:
        dialog.notification('next-episode.net', ui_string(32009), icon=icon, time=2000, sound=False)


def log_data_sent(data):
    """
    Log data sent to next-episode.net with sanitized username/hash

    :param data: data to be sent
    :type data: dict
    """
    logged_data = deepcopy(data)
    logged_data['user']['username'] = logged_data['user']['hash'] = '*****'
    xbmc.log('next-episode: data sent:\n{0}'.format(logged_data), xbmc.LOGNOTICE)


def sync_library():
    """
    Synchronize Kodi video library with next-episode.net
    """
    xbmc.executebuiltin('ActivateWindow(10138)')  # Busy dialog on
    data = {
    'user': {
        'username': addon.getSetting('username'),
        'hash': addon.getSetting('hash')
    }}
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
                episodes += prepare_episodes_list(get_episodes(show['tvshowid']))
            except NoDataError:
                continue
        data['tvshows'] = episodes
    if 'movies' in data or 'tvshows' in data:
        log_data_sent(data)
        send_data(data)
    else:
        xbmc.log('next-episode: Kodi video library has no movies and TV episodes.', xbmc.LOGWARNING)
    xbmc.executebuiltin('Dialog.Close(10138)')  # Busy dialog off


def sync_new_items():
    """
    Synchronize new video items with next-episode.net
    """
    data = {
        'user': {
            'username': addon.getSetting('username'),
            'hash': addon.getSetting('hash')
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
        xbmc.log('next-episode.net: Kodi video library has no recent movies and episodes.', xbmc.LOGWARNING)


def update_single_item(item):
    """
    Synchronize single item (movie or episode) with next-episode-net

    :param item: video item
    :type item: dict
    """
    data = {
        'user': {
            'username': addon.getSetting('username'),
            'hash': addon.getSetting('hash')
        }}
    if item['type'] == 'episode':
        data['tvshows'] = [{
            'thetvdb_id': get_tvdb_id(item['tvshowid']),
            'season': str(item['season']),
            'episode': str(item['episode']),
            'watched': '1' if item['playcount'] else '0'
            }]
    elif item['type'] == 'movie':
        data['movies'] = [{
            'imdb_id': item['imdbnumber'],
            'watched': '1' if item['playcount'] else '0'
        }]
    log_data_sent(data)
    send_data(data)


def login():
    """
    Login to next-episode.net

    :return: ``True`` on successful login, ``False`` if login is failed or cancelled
    :rtype: bool
    """
    login_dialog = LoginDialog(ui_string(32001), username=addon.getSetting('username'))
    login_dialog.doModal()
    result = False
    if not login_dialog.is_cancelled:
        xbmc.executebuiltin('ActivateWindow(10138)')
        username = login_dialog.username
        password = login_dialog.password
        try:
            hash_ = get_password_hash(username, password)
        except LoginError:
            dialog.ok('next-episode.net', ui_string(32007), ui_string(32010))
            xbmc.log('next-episode.net: login failed!', xbmc.LOGERROR)
        else:
            addon.setSetting('username', username)
            addon.setSetting('hash', hash_)
            xbmc.log('next-episode.net: successful login', xbmc.LOGNOTICE)
            dialog.notification('next-episode.net', ui_string(32011), time=3000, sound=False)
            result = True
        xbmc.executebuiltin('Dialog.Close(10138)')
    del login_dialog
    return result


if __name__ == '__main__':
    if sys.argv[1] == 'sync_library':
        sync_library()
    elif sys.argv[1] == 'login':
        login()
