# coding: utf-8
# (c) Roman Miroshnychenko <roman1972@gmail.com> 2020
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

"""Scraper actions"""
# pylint: disable=missing-docstring
from __future__ import absolute_import, division, unicode_literals

import os
import re
import time
import uuid
from collections import defaultdict, namedtuple
from pprint import pformat

import pyqrcode
import six
from kodi_six import xbmc

from . import gui, medialibrary_api as medialib, tvmaze_api as tvmaze, kodi_service as kodi
from .kodi_service import logger
from .pulled_episodes_db import PulledEpisodesDb
from .time_utils import timestamp_to_time_string, time_string_to_timestamp

try:
    # pylint: disable=unused-import
    from typing import Text, Dict, Any, List, Tuple, Callable, Optional, Union
except ImportError:
    pass

_ = kodi.GETTEXT

SUPPORTED_IDS = ('tvmaze', 'tvdb', 'imdb')

UniqueId = namedtuple('UniqueId', ['show_id', 'provider'])  # pylint: disable=invalid-name


class StatusType(object):  # pylint: disable=too-few-public-methods
    """Episode statuses on TVmaze"""
    WATCHED = 0
    ACQUIRED = 1
    SKIPPED = 2


def _create_and_save_qrcode(string):
    # type: (Text) -> Text
    """Create a QR-code from a string and save it to the addon profile directory"""
    qrcode_image = pyqrcode.create(string)
    qrcode_filename = uuid.uuid4().hex + '.png'
    qrcode_path = os.path.join(kodi.ADDON_PROFILE_DIR, qrcode_filename)
    qrcode_image.png(qrcode_path, scale=10)
    return qrcode_path


def authorize_addon():
    # type: () -> None
    """
    Authorize the addon on TVmaze

    The function sends authorization request to TVmaze and saves TVmaze
    username and API token for scrobbling requests authorization
    """
    if tvmaze.is_authorized() and not gui.DIALOG.yesno(
            kodi.ADDON_NAME,
            _('The addon is already authorized.[CR]Authorize again?')):
        return
    keyboard = xbmc.Keyboard()
    keyboard.setHeading(_('Your TVmaze account email'))
    keyboard.doModal()
    if keyboard.isConfirmed():
        email = keyboard.getText()
        if re.search(r'^[\w.\-+]+@[\w.-]+\.[\w]+$', email) is None:
            logger.error('Invalid email: {}'.format(email))
            gui.DIALOG.notification(kodi.ADDON_NAME, _('Invalid email'), icon='error', time=3000)
            return
        try:
            token, confirm_url = tvmaze.start_authorization(email)
        except tvmaze.AuthorizationError as exc:
            message = _('Authorization error: {}').format(exc)
            logger.error(message)
            gui.DIALOG.notification(kodi.ADDON_NAME, message, icon='error')
            return
        qrcode_path = _create_and_save_qrcode(confirm_url)
        confirmation_dialog = gui.ConfirmationDialog(email, token, confirm_url, qrcode_path)
        confirmation_dialog.doModal()
        if confirmation_dialog.is_confirmed:
            kodi.ADDON.setSettingString('username', confirmation_dialog.username)
            kodi.ADDON.setSettingString('apikey', confirmation_dialog.apikey)
            gui.DIALOG.notification(kodi.ADDON_NAME, _('Addon has been authorized successfully'),
                                    icon=kodi.ADDON_ICON, sound=False, time=3000)
            if gui.DIALOG.yesno(kodi.ADDON_NAME,
                                _('Do you want to sync your TV shows with TVmaze now?')):
                sync_all_episodes()
        elif confirmation_dialog.error_message is not None:
            logger.error('Confirmation error: {}'.format(confirmation_dialog.error_message))
            message = _('Confirmation error: {}').format(confirmation_dialog.error_message)
            gui.DIALOG.notification(kodi.ADDON_NAME, message, icon='error')
        del confirmation_dialog


def reset_authorization():
    # type: () -> None
    """Clear stored username and API key"""
    if gui.DIALOG.yesno(_('Reset Authorization'),
                        _('This will clear stored authentication credentials.[CR]Are you sure?')):
        tvmaze.clear_credentials()


def _handle_authentication_error():
    # type: () -> None
    tvmaze.clear_credentials()
    gui.DIALOG.notification(kodi.ADDON_NAME,
                            'Authentication failed. You need to authorize the addon.',
                            icon='error')


def _get_unique_id(uniqueid_dict):
    # type: (Dict[Text, Text]) -> Optional[UniqueId]
    """
    Get a show ID in one of the supported online databases

    :param uniqueid_dict: uniqueid dict from Kodi JSON-RPC API
    :return: a named tuple of unique ID and online data provider
    """
    for provider in SUPPORTED_IDS:
        show_id = uniqueid_dict.get(provider)
        if show_id is not None:
            if provider == 'tvdb':
                provider = 'thetvdb'
            return UniqueId(show_id, provider)
    return None


def _prepare_episode_list(kodi_episode_list):
    # type: (List[Dict[Text, Any]]) -> List[Dict[Text, int]]
    episodes_for_tvmaze = []
    for episode in kodi_episode_list:
        if episode['season']:  # Todo: add support for specials
            marked_at_sting = episode.get('lastplayed') or episode.get('dateadded')
            if marked_at_sting:
                marked_at = time_string_to_timestamp(marked_at_sting)
            else:
                marked_at = int(time.time())
            episodes_for_tvmaze.append({
                'season': episode['season'],
                'episode': episode['episode'],
                'marked_at': marked_at,
                'type': StatusType.WATCHED if episode['playcount'] else StatusType.ACQUIRED,
            })
    return episodes_for_tvmaze


def _load_and_store_tvmaze_id(show_id, provider, kodi_tvshowid):
    # type: (Text, Text, int) -> Optional[int]
    try:
        show_info = tvmaze.get_show_info_by_external_id(show_id, provider)
    except tvmaze.ApiError:
        return None
    tvmaze_id = show_info['id']
    medialib.set_show_uniqueid(kodi_tvshowid, tvmaze_id)
    return tvmaze_id


def _get_tvmaze_id(kodi_show_info):
    # type: (Dict[Text, Any]) -> Optional[int]
    uniqueid_dict = kodi_show_info['uniqueid']
    unique_id = _get_unique_id(uniqueid_dict)
    if unique_id is None:
        return None
    if unique_id.provider == 'tvmaze':
        return int(unique_id.show_id)
    return _load_and_store_tvmaze_id(
        unique_id.show_id, unique_id.provider, kodi_show_info['tvshowid'])


def _get_tv_shows_from_kodi():
    # type: () -> Optional[List[Dict[Text, Any]]]
    try:
        return medialib.get_tvshows()
    except medialib.NoDataError:
        logger.warning('Medialibrary has no TV shows')
        return None


def _check_and_set_episode_playcount(kodi_tvshowid, tvmaze_episode):
    # type: (int, Dict[Text, Any]) -> None
    """Check episode watched status and set episode playcount in Kodi accordingly"""
    tvmaze_episode_info = tvmaze_episode['_embedded']['episode']
    if (tvmaze_episode['type'] == StatusType.WATCHED
            and tvmaze_episode_info.get('season') is not None
            and tvmaze_episode_info.get('number') is not None):
        # Todo: add support for specials
        filter_ = {
            'and': [
                {
                    'field': 'season',
                    'operator': 'is',
                    'value': str(tvmaze_episode_info['season']),
                },
                {
                    'field': 'episode',
                    'operator': 'is',
                    'value': str(tvmaze_episode_info['number']),
                },
                {
                    'field': 'playcount',
                    'operator': 'is',
                    'value': '0',
                },
            ]
        }
        try:
            kodi_episodes = medialib.get_episodes(kodi_tvshowid, filter_=filter_)
        except medialib.NoDataError:
            return
        if kodi_episodes:
            kodi_episode_info = kodi_episodes[0]
            marked_at = tvmaze_episode.get('marked_at')
            if marked_at is not None:
                last_played = timestamp_to_time_string(marked_at)
            else:
                last_played = None
            with PulledEpisodesDb() as database:
                database.upsert_episode(kodi_episode_info['episodeid'])
            medialib.set_episode_playcount(kodi_episode_info['episodeid'],
                                           last_played=last_played)


def _pull_watched_episodes(kodi_tv_shows=None):
    # type: (Optional[List[Dict[Text, Any]]]) -> None
    """Pull watched episodes from TVmaze and set them as watched in Kodi"""
    logger.debug('Pulling watched episodes from TVmaze')
    with gui.background_progress_dialog(_('TVmaze Scrobbler'), _('Syncing episodes')) as dialog:
        kodi_tv_shows = kodi_tv_shows or _get_tv_shows_from_kodi()
        if not kodi_tv_shows:
            return
        tvmaze_shows = {}
        for show in kodi_tv_shows:
            tvmaze_id = _get_tvmaze_id(show)
            if tvmaze_id is None:
                logger.error('Unable to determine TVmaze id from show info: {}'.format(
                    pformat(show)))
                continue
            try:
                tvmaze_episodes = tvmaze.get_episodes_from_watchlist(tvmaze_id,
                                                                     type_=StatusType.WATCHED)
            except tvmaze.ApiError as exc:
                logger.error('Unable to pull episodes from TVmaze for show "{}": {}'.format(
                    show['label'], exc
                ))
                if six.text_type(exc) == tvmaze.AUTHENTICATION_ERROR:
                    _handle_authentication_error()
                    return
                continue
            logger.debug('Episodes from TVmaze for {}:\n{}'.format(
                tvmaze_id, pformat(tvmaze_episodes)))
            tvmaze_shows[show['tvshowid']] = tvmaze_episodes
        shows_count = len(tvmaze_shows)
        for n, (tvshowid, tvmaze_episodes) in enumerate(six.iteritems(tvmaze_shows), 1):
            percent = int(100 * n / shows_count)
            dialog.update(percent,
                          _('TVmaze Scrobbler'),
                          _('Updating TV shows in Kodi: {} of {}').format(n, shows_count))
            for episode in tvmaze_episodes:
                _check_and_set_episode_playcount(tvshowid, episode)


def pull_watched_episodes():
    # type: () -> None
    if not tvmaze.is_authorized():
        logger.warning('Addon is not authorized')
        return
    _pull_watched_episodes()
    if kodi.ADDON.getSettingBool('show_notifications'):
        gui.DIALOG.notification(kodi.ADDON_NAME,
                                _('Synced watched episodes from TVmaze'),
                                icon=kodi.ADDON_ICON, time=3000, sound=False)


def _push_all_episodes(kodi_tv_shows):
    # type: (List[Dict[Text, Any]]) -> None
    """Push TV shows to TVmaze"""
    logger.info('Pushing all episodes to TVmaze...')
    success = True
    with gui.background_progress_dialog(_('TVmaze Scrobbler'), _('Syncing episodes')) as dialog:
        shows_count = len(kodi_tv_shows)
        for n, show in enumerate(kodi_tv_shows, 1):
            percent = int(100 * n / shows_count)
            message = _(r'Syncing episodes for show \"{show_name}\": {count}/{total}').format(
                show_name=show['label'],
                count=n,
                total=shows_count
            )
            dialog.update(percent, _('TVmaze Scrobbler'), message)
            tvmaze_id = _get_tvmaze_id(show)
            if tvmaze_id is None:
                logger.error(
                    'Unable to determine TVmaze id from show info: {}'.format(pformat(show)))
                success = False
                continue
            try:
                episodes = medialib.get_episodes(show['tvshowid'])
            except medialib.NoDataError:
                logger.warning('TV show "{}" has no episodes'.format(show['label']))
                continue
            episodes_for_tvmaze = _prepare_episode_list(episodes)
            try:
                tvmaze.push_episodes(episodes_for_tvmaze, tvmaze_id)
            except tvmaze.ApiError as exc:
                logger.error(
                    'Unable to push episodes for show "{}": {}'.format(show['label'], exc))
                if six.text_type(exc) == tvmaze.AUTHENTICATION_ERROR:
                    _handle_authentication_error()
                    return
                success = False
                continue
    if success and kodi.ADDON.getSettingBool('show_notifications'):
        gui.DIALOG.notification(kodi.ADDON_NAME, _('Sync completed'), icon=kodi.ADDON_ICON,
                                time=3000, sound=False)
    else:
        gui.DIALOG.notification(kodi.ADDON_NAME,
                                _('Sync completed with errors. Check the log for more info.'),
                                icon='warning')


def sync_all_episodes():
    # type: () -> None
    """Pull watched episodes from TVmaze and then push all TV shows from Kodi to TVmaze"""
    if not tvmaze.is_authorized():
        logger.warning('Addon is not authorized')
        return
    tv_shows = _get_tv_shows_from_kodi()
    if tv_shows is None:
        gui.DIALOG.notification(kodi.ADDON_NAME, _('Medialibrary has no TV episodes'),
                                icon='warning')
        return
    if kodi.ADDON.getSettingBool('pull_from_tvmaze'):
        _pull_watched_episodes(tv_shows)
    _push_all_episodes(tv_shows)


def push_single_episode(episode_id):
    # type: (int) -> None
    """Push watched status for a single episode"""
    if not tvmaze.is_authorized():
        logger.warning('Addon is not authorized')
        return
    logger.debug('Pushing single episode to TVmaze')
    episode_info = medialib.get_episode_details(episode_id)
    tvshow_info = medialib.get_tvshow_details(episode_info['tvshowid'])
    tvmaze_id = _get_tvmaze_id(tvshow_info)
    if tvmaze_id is None:
        logger.error(
            'Unable to determine TVmaze id from show info: {}'.format(pformat(tvshow_info)))
        return
    episodes_for_tvmaze = _prepare_episode_list([episode_info])
    try:
        tvmaze.push_episodes(episodes_for_tvmaze, tvmaze_id)
    except tvmaze.ApiError as exc:
        logger.error('Failed to push episode status: {}'.format(exc))
        if six.text_type(exc) == tvmaze.AUTHENTICATION_ERROR:
            _handle_authentication_error()
        else:
            gui.DIALOG.notification(kodi.ADDON_NAME,
                                    _('Failed to sync episode status: {}'.format(exc)),
                                    icon='error')
        return
    if kodi.ADDON.getSettingBool('show_notifications'):
        gui.DIALOG.notification(kodi.ADDON_NAME,
                                _('Synced episode status'), icon=kodi.ADDON_ICON, time=3000,
                                sound=False)


def _push_recent_episodes(recent_episodes):
    # type: (List[Dict[Text, Any]]) -> None
    """Push recent episodes to TVmaze"""
    logger.debug('Pushing recent episodes to TVmaze')
    success = True
    id_mapping = {}
    episode_mapping = defaultdict(list)
    for episode in recent_episodes:
        if episode['tvshowid'] not in id_mapping:
            show_info = medialib.get_tvshow_details(episode['tvshowid'])
            tvmaze_id = _get_tvmaze_id(show_info)
            if tvmaze_id is None:
                logger.error(
                    'Unable to determine TVmaze id from show info: {}'.format(
                        pformat(show_info)))
                continue
            id_mapping[episode['tvshowid']] = tvmaze_id
            episode_mapping[tvmaze_id].append(episode)
        else:
            episode_mapping[id_mapping[episode['tvshowid']]].append(episode)
    for tvmaze_id, episodes in six.iteritems(episode_mapping):
        episodes_for_tvmaze = _prepare_episode_list(episodes)
        try:
            tvmaze.push_episodes(episodes_for_tvmaze, tvmaze_id)
        except tvmaze.ApiError as exc:
            logger.error(
                'Unable to update episodes for show {}: {}'.format(tvmaze_id, exc))
            if six.text_type(exc) == tvmaze.AUTHENTICATION_ERROR:
                _handle_authentication_error()
                return
            continue
    if success and kodi.ADDON.getSettingBool('show_notifications'):
        gui.DIALOG.notification(kodi.ADDON_NAME, _('Sync completed'), icon=kodi.ADDON_ICON,
                                time=3000, sound=False)
    else:
        gui.DIALOG.notification(kodi.ADDON_NAME,
                                _('Sync completed with errors. Check the log for more info.'),
                                icon='error')


def sync_recent_episodes(show_warning=True):
    # type: (bool) -> None
    """Pull watched episodes from TVmaze and then push recent episodes to TVmaze"""
    if not tvmaze.is_authorized():
        logger.warning('Addon is not authorized')
        return
    if kodi.ADDON.getSettingBool('pull_from_tvmaze'):
        _pull_watched_episodes()
    try:
        recent_episodes = medialib.get_recent_episodes()
        if not recent_episodes:
            raise medialib.NoDataError
    except medialib.NoDataError:
        if show_warning:
            gui.DIALOG.notification(kodi.ADDON_NAME, _('Medialibrary has no TV episodes'),
                                    icon='warning')
        return
    _push_recent_episodes(recent_episodes)


def get_menu_actions():
    # type: () -> List[Tuple[Text, Callable[[], None]]]
    """
    Get main menu actions

    :return: the list of tuples (menu_label, action_callable)
    """
    actions = [(_('Authorize the addon'), authorize_addon)]
    if tvmaze.is_authorized():
        actions = [
            (_('Sync all shows'), sync_all_episodes),
            (_('Sync recently added episodes'), sync_recent_episodes),
            (_('Sync watched episodes from TVmaze'), pull_watched_episodes),
            (_('Reset Authorization'), reset_authorization),
        ] + actions
    return actions
