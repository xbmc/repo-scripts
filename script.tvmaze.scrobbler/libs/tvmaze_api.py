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

"""Functions to work with TVmaze API"""
# pylint: disable=missing-docstring

from __future__ import absolute_import, unicode_literals

from pprint import pformat

import requests

from .kodi_service import logger, ADDON

try:
    from typing import Union, Text, List, Optional, Tuple, Dict, Any  # pylint: disable=unused-import
    DataType = Dict[Text, Any]  # pylint: disable=invalid-name
except ImportError:
    pass

API_URL = 'http://api.tvmaze.com'
USER_API_URL = 'https://api.tvmaze.com/v1'
AUTH_START_PATH = '/auth/start'
AUTH_POLL_PATH = '/auth/poll'
SCROBBLE_SHOWS_PATH = '/scrobble/shows'
SHOW_LOOKUP_PATH = '/lookup/shows'

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Kodi scrobbler for tvmaze.com',
    'Accept': 'application/json',
})

AUTHENTICATION_ERROR = 'Invalid username or API key'


class ApiError(Exception):

    @staticmethod
    def extract_error_message_from_response(response):
        # type: (requests.Response) -> Text
        if 'application/json' in response.headers.get('Content-Type', ''):
            payload = response.json()
            if isinstance(payload, dict):
                name = payload.get('name', '')
                message = payload.get('message', '')
                if name and message:
                    return '{}: {}'.format(name, message)
                return message or name
            if response.status_code == 207 and isinstance(payload, list):
                failed_episodes = [item for item in payload if item['code'] != 200]
                # Todo: collect detailed info about failed episodes
                return 'Failed to update {} episodes'.format(len(failed_episodes))
        return response.text

    def __init__(self, message='', response=None):
        # type: (Text, Optional[requests.Response]) -> None
        self.error_message = message
        if response is not None:
            error_message = self.extract_error_message_from_response(response)
            if error_message:
                self.error_message = error_message
        super(ApiError, self).__init__(self.error_message)


class AuthorizationError(ApiError):
    pass


def _get_credentials():
    # type: () -> Tuple[Text, Text]
    username = ADDON.getSettingString('username')
    apikey = ADDON.getSettingString('apikey')
    return username, apikey


def is_authorized():
    # type: () -> bool
    return all(_get_credentials())


def clear_credentials():
    # type: () -> None
    ADDON.setSettingString('username', '')
    ADDON.setSettingString('apikey', '')


def _send_request(url, method='get', **requests_kwargs):
    # type: (Text, Text, **Optional[Union[tuple, dict, list]]) -> requests.Response
    """
    Send a HTTP request to TVmaze API

    :param url: API url
    :param method: HTTP method
    :param requests_kwargs: kwagrs to be passed to a Requests call
    :return: Requests response object
    :raises requests.HTTPError:
    """
    method_func = getattr(SESSION, method, SESSION.get)
    auth = requests_kwargs.pop('auth', None)  # Remove credentials before logging
    logger.debug(
        'Calling URL "{}"... method: {}, parameters:\n{}'.format(
            url, method, pformat(requests_kwargs))
    )
    response = method_func(url, auth=auth, **requests_kwargs)
    if not response.ok:
        logger.error('TVmaze returned error {}'.format(response.status_code))
    logger.debug('API response:\n{}'.format(pformat(response.json())))
    return response


def _call_common_api(path, method='get', **requests_kwargs):
    # type: (Text, Text, **Optional[Union[tuple, dict, list]]) -> requests.Response
    """
    Call common TVmaze API

    :param path: API path
    :param method: HTTP method
    :param requests_kwargs: kwagrs to be passed to a Requests call
    :return: Requests response object
    :raises requests.HTTPError: on any error response from API
    """
    url = API_URL + path
    response = _send_request(url, method, **requests_kwargs)
    if not response.ok:
        response.raise_for_status()
    return response


def _call_user_api(path, method='get', authenticate=False, **requests_kwargs):
    # type: (Text, Text, bool, **Optional[Union[tuple, dict, list]]) -> requests.Response
    """
    Call TVmaze user API with authentication

    :param path: API path
    :param method: HTTP method
    :param authenticate: authenticate request
    :param requests_kwargs: kwagrs to be passed to a Requests call
    :return: Requests response object
    :raises AuthorizationError: if authentication credentials are not set
    :raises requests.HTTPError: on any error response from API
    """
    if authenticate and not is_authorized():
        raise AuthorizationError('Missing TVmaze username and API key')
    auth = None
    if authenticate:
        username, apikey = _get_credentials()
        auth = (username, apikey)
    url = USER_API_URL + path
    response = _send_request(url, method, auth=auth, **requests_kwargs)
    if not response.ok:
        response.raise_for_status()
    elif response.status_code == 207:
        raise requests.HTTPError('Update completed with errors', response=response)
    logger.debug('API response:\n{}'.format(pformat(response.json())))
    return response


def start_authorization(email):
    # type: (Text) -> Tuple[Text, Text]
    """
    Start scraper authorization flow

    :return: (authorization token, confirmation url) tuple
    :raises AuthorizationError: on authorization error
    """
    data = {
        'email': email,
        'email_confirmation': True,
    }
    try:
        response = _call_user_api(AUTH_START_PATH, 'post', authenticate=False, json=data)
    except requests.HTTPError as exc:
        raise AuthorizationError(response=exc.response)
    response_data = response.json()
    return response_data.get('token'), response_data.get('confirm_url')


def poll_authorization(token):
    # type: (Text) -> Optional[Tuple[Text, Text]]
    """
    Poll authorization confirmation

    :return: (TVmaze username, API key) tuple
    """
    try:
        response = _call_user_api(AUTH_POLL_PATH, 'post', json={'token': token})
    except requests.HTTPError as exc:
        if exc.response.status_code == 403:
            return None
        raise AuthorizationError(response=exc.response)
    response_data = response.json()
    return response_data.get('username'), response_data.get('apikey')


def push_episodes(episodes, show_id, provider='tvmaze'):
    # type: (List[Dict[Text, int]], Union[int, Text], Text) -> None
    """
    Send statuses of episodes to TVmase

    :param episodes: the list of episodes to update
    :param show_id: TV show ID in tvmaze, thetvdb or imdb online databases
    :param provider: ID provider
    """
    provider += '_id'
    params = {provider: show_id}
    try:
        _call_user_api(SCROBBLE_SHOWS_PATH, 'post', authenticate=True, params=params, json=episodes)
    except requests.HTTPError as exc:
        raise ApiError(response=exc.response)


def get_show_info_by_external_id(show_id, provider):
    # type: (Text, Text) -> DataType
    """
    Get brief show info from TVmaze by external ID

    :param show_id: show ID in an external online DB
    :param provider: online DB provider
    :return: show info from TVmaze
    :raises ApiError: on any API error
    """
    params = {provider: show_id}
    try:
        response = _call_common_api(SHOW_LOOKUP_PATH, 'get', params=params)
    except requests.HTTPError as exc:
        raise ApiError(response=exc.response)
    return response.json()


def get_episodes_from_watchlist(tvmaze_id, type_=None):
    # type: (Union[int, Text], Optional[int]) -> List[DataType]
    """
    Get episodes for a TV show from user's watchlist on TVmaze

    :param tvmaze_id: show ID on TVmaze
    :param type_: get only episodes with the given status type
    :return: the list of episode infos from TVmaze
    :raises ApiError: on any API error
    """
    path = '{}/{}'.format(SCROBBLE_SHOWS_PATH, tvmaze_id)
    params = {'embed': 'episode'}
    if type_ is not None:
        params['type'] = type_
    try:
        response = _call_user_api(path, 'get', authenticate=True, params=params)
    except requests.HTTPError as exc:
        raise ApiError(response=exc.response)
    return response.json()
