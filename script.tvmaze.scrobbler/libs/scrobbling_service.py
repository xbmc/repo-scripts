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

from . import medialibrary_api as medialib
from . import tvmaze_api as tvmaze
from .gui import DIALOG, ConfirmationDialog, background_progress_dialog
from .kodi_service import ADDON, ADDON_ID, PROFILE_DIR, ICON, GETTEXT, logger

try:
    # pylint: disable=unused-import
    from typing import Text, Dict, Any, List, Tuple, Callable, Optional, Union
except ImportError:
    pass

_ = GETTEXT

SUPPORTED_IDS = ('tvmaze', 'tvdb', 'imdb')

UniqueId = namedtuple('UniqueId', ['show_id', 'provider'])  # pylint: disable=invalid-name


class StatusType(object):  # pylint: disable=too-few-public-methods
    """Episode statuses on TVmaze"""
    WATCHED = 0
    ACQUIRED = 1
    SKIPPED = 2


def authorize_addon():
    # type: () -> None
    """
    Authorize the addon on TVmaze

    The function sends authorization request to TVmaze and saves TVmaze
    username and API token for scrobbling requests authorization
    """
    if tvmaze.is_authorized():
        answer = DIALOG.yesno(
            _('TVmaze Scrobbler'),
            _('The addon is already authorized.[CR]Authorize again?')
        )
        if not answer:
            return
    keyboard = xbmc.Keyboard()
    keyboard.setHeading(_('Your TVmaze account email'))
    keyboard.doModal()
    if keyboard.isConfirmed():
        email = keyboard.getText()
        if re.search(r'^[\w.\-+]+@[\w.-]+\.[\w]+$', email) is None:
            logger.error('Invalid email: {}'.format(email))
            DIALOG.notification(ADDON_ID, _('Invalid email'), icon='error', time=3000)
            return
        try:
            token, confirm_url = tvmaze.start_authorization(email)
        except tvmaze.AuthorizationError as exc:
            logger.error('TVmaze authorization error: {}'.format(exc))
            message = _('Authorization error: {}').format(exc)
            DIALOG.notification(ADDON_ID, message, icon='error')
            return
        qrcode_filename = uuid.uuid4().hex + '.png'
        qrcode_path = os.path.join(PROFILE_DIR, qrcode_filename)
        qrcode_image = pyqrcode.create(confirm_url)
        qrcode_image.png(qrcode_path, scale=10)
        confirmation_dialog = ConfirmationDialog(email, token, confirm_url, qrcode_path)
        confirmation_dialog.doModal()
        if confirmation_dialog.is_confirmed:
            ADDON.setSettingString('username', confirmation_dialog.username)
            ADDON.setSettingString('apikey', confirmation_dialog.apikey)
            DIALOG.notification(ADDON_ID, _('Addon has been authorized successfully'),
                                icon=ICON, sound=False, time=3000)
        elif confirmation_dialog.error_message is not None:
            logger.error('Confirmation error: {}'.format(confirmation_dialog.error_message))
            message = _('Confirmation error: {}').format(confirmation_dialog.error_message)
            DIALOG.notification(ADDON_ID, message, icon='error')
        del confirmation_dialog


def reset_authorization():
    # type: () -> None
    """Clear stored username and API key"""
    if DIALOG.yesno(_('Reset Authorization'),
                    _('This will clear stored authentication credentials.[CR]Are you sure?')):
        ADDON.setSettingString('username', '')
        ADDON.setSettingString('apikey', '')


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
            episodes_for_tvmaze.append({
                'season': episode['season'],
                'episode': episode['episode'],
                'marked_at': int(time.time()),
                'type': StatusType.WATCHED if episode['playcount'] else StatusType.ACQUIRED,
            })
    return episodes_for_tvmaze


def _push_episodes_to_tvmaze(tvmaze_id, episodes):
    # type: (Union[int, Text], List[Dict[Text, int]]) -> bool
    """
    Push episodes statuses of a TV show to TVmaze

    :param tvmaze_id: show ID on TVmaze
    :param episodes: the list of episodes
    :return: success status
    """
    episodes_for_tvmaze = _prepare_episode_list(episodes)
    return tvmaze.push_episodes(episodes_for_tvmaze, tvmaze_id)


def _load_and_store_tvmaze_id(show_id, provider, kodi_tvshowid):
    # type: (Text, Text, int) -> Optional[int]
    show_info = tvmaze.get_show_info_by_external_id(show_id, provider)
    if show_info is None:
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


def _pull_watched_episodes(kodi_tv_shows=None):
    # type: (Optional[List[Dict[Text, Any]]]) -> None
    """Pull watched episodes from TVmaze and set them as watched in Kodi"""
    logger.debug('Pulling watched episodes from TVmaze')
    kodi_tv_shows = kodi_tv_shows or _get_tv_shows_from_kodi()
    if not kodi_tv_shows:
        return
    tvmaze_shows = {}
    for show in kodi_tv_shows:
        tvmaze_id = _get_tvmaze_id(show)
        if tvmaze_id is None:
            logger.error('Unable to determine TVmaze id from show info: {}'.format(pformat(show)))
            continue
        tvmaze_episodes = tvmaze.get_episodes_from_watchlist(tvmaze_id, type_=StatusType.WATCHED)
        if tvmaze_episodes is None:
            continue
        logger.debug('Episodes from TVmaze for {}:\n{}'.format(tvmaze_id, pformat(tvmaze_episodes)))
        tvmaze_shows[show['tvshowid']] = tvmaze_episodes
    for tvshowid, episodes in six.iteritems(tvmaze_shows):
        for episode in episodes:
            tvmaze_episode_info = episode['_embedded']['episode']
            if (episode['type'] == StatusType.WATCHED
                    and 'season' in tvmaze_episode_info  # Todo: add support for specials
                    and 'number' in tvmaze_episode_info):
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
                    kodi_episodes = medialib.get_episodes(tvshowid, filter_=filter_)
                    if not kodi_episodes:
                        raise medialib.NoDataError
                except medialib.NoDataError:
                    continue
                if kodi_episodes:
                    kodi_episode_info = kodi_episodes[0]
                    medialib.set_episode_playcount(kodi_episode_info['episodeid'])


def pull_watched_episodes():
    # type: () -> None
    if not tvmaze.is_authorized():
        logger.warning('Addon is not authorized')
        return
    _pull_watched_episodes()
    if ADDON.getSettingBool('show_notifications'):
        DIALOG.notification(ADDON_ID,
                            _('Pulled watched episodes from TVmaze'),
                            icon=ICON, time=3000, sound=False)


def _push_all_episodes(kodi_tv_shows):
    # type: (List[Dict[Text, Any]]) -> None
    """Push TV shows to TVmaze"""
    logger.info('Pushing all episodes to TVmaze...')
    success = True
    with background_progress_dialog(_('TVmaze Scrobbler'), _('Pushing episodes')) as dialog:
        shows_count = len(kodi_tv_shows)
        for n, show in enumerate(kodi_tv_shows, 1):
            percent = int(100 * n / shows_count)
            message = _(r'Pushing episodes for show \"{show_name}\": {count}/{total}').format(
                show_name=show['label'],
                count=n,
                total=shows_count
            )
            dialog.update(percent, _('TVmaze Scrobbler'), message)
            tvmaze_id = _get_tvmaze_id(show)
            if tvmaze_id is None:
                logger.error(
                    'Unable to determine TVmaze id from show info: {}'.format(pformat(show)))
                continue
            try:
                episodes = medialib.get_episodes(show['tvshowid'])
            except medialib.NoDataError:
                logger.warning('TV show "{}" has no episodes'.format(show['label']))
                continue
            success = _push_episodes_to_tvmaze(tvmaze_id, episodes)
            if not success:
                logger.error(
                    'Unable to push episodes for show "{}".'.format(show['label']))
                continue
    if success and ADDON.getSettingBool('show_notifications'):
        DIALOG.notification(ADDON_ID, _('Push completed'), icon=ICON, time=3000, sound=False)
    else:
        DIALOG.notification(ADDON_ID, _('Push completed with errors'), icon='error')


def sync_all_episodes():
    # type: () -> None
    """Pull watched episodes from TVmaze and then push all TV shows from Kodi to TVmaze"""
    if not tvmaze.is_authorized():
        logger.warning('Addon is not authorized')
        return
    tv_shows = _get_tv_shows_from_kodi()
    if tv_shows is None:
        return
    if ADDON.getSettingBool('pull_from_tvmaze'):
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
    success = tvmaze.push_episodes(episodes_for_tvmaze, tvmaze_id)
    if success and ADDON.getSettingBool('show_notifications'):
        DIALOG.notification(
            ADDON_ID, _('Pushed episode status'), icon=ICON, time=3000, sound=False)
    else:
        logger.error('Failed to push episode status.')
        DIALOG.notification(ADDON_ID, _('Failed to push episode status'), icon='error')


def _push_recent_episodes():
    # type: () -> None
    """Push recent episodes to TVmaze"""
    logger.debug('Pushing recent episodes to TVmaze')
    if ADDON.getSettingBool('pull_from_tvmaze'):
        _pull_watched_episodes()
    try:
        recent_episodes = medialib.get_recent_episodes()
    except medialib.NoDataError:
        return
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
        success = _push_episodes_to_tvmaze(tvmaze_id, episodes)
        if not success:
            logger.error(
                'Unable to update episodes for show {}.'.format(tvmaze_id))
            continue
    if success and ADDON.getSettingBool('show_notifications'):
        DIALOG.notification(ADDON_ID, _('Push completed'), icon=ICON, time=3000, sound=False)
    else:
        DIALOG.notification(ADDON_ID, _('Push completed with errors'), icon='error')


def sync_recent_episodes():
    """Pull watched episodes from TVmaze and then push recent episodes to TVmaze"""
    if not tvmaze.is_authorized():
        logger.warning('Addon is not authorized')
        return
    if ADDON.getSettingBool('pull_from_tvmaze'):
        _pull_watched_episodes()
    _push_recent_episodes()


def get_menu_actions():
    # type: () -> List[Tuple[Text, Callable[[], None]]]
    """
    Get main menu actions

    :return: the list of tuples (menu_label, action_callable)
    """
    actions = [(_('Authorize the addon'), authorize_addon)]
    if tvmaze.is_authorized():
        actions = [
            (_('Push all shows'), sync_all_episodes),
            (_('Push recent episodes'), sync_recent_episodes),
            (_('Pull watched episodes from TVmaze'), pull_watched_episodes),
            (_('Reset Authorization'), reset_authorization),
        ] + actions
    return actions
