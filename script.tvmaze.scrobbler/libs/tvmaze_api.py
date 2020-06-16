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
import six

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


@six.python_2_unicode_compatible
class ApiError(Exception):

    def __init__(self, status_code, reason):
        # type: (int, Text) -> None
        super(ApiError, self).__init__()
        self.status_code = status_code
        self.reason = reason

    def __str__(self):
        return '{}: {}; reason: {}'.format(self.__class__.__name__, self.status_code, self.reason)


class AuthorizationError(Exception):
    pass


def _get_credentials():
    # type: () -> Tuple[Text, Text]
    username = ADDON.getSettingString('username')
    apikey = ADDON.getSettingString('apikey')
    return username, apikey


def is_authorized():
    # type: () -> bool
    return all(_get_credentials())


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
        logger.error('TVmaze returned error {}: {}'.format(response.status_code, response.text))
        response.raise_for_status()
    return response


def _call_api(path, method='get', **requests_kwargs):
    # type: (Text, Text, **Optional[Union[tuple, dict, list]]) -> Union[DataType, List[DataType]]
    """
    Call TVmaze API

    :param path: API path
    :param method: HTTP method
    :param requests_kwargs: kwagrs to be passed to a Requests call
    :return: API response data
    :raises ApiError: on any error response from API
    """
    url = API_URL + path
    try:
        response = _send_request(url, method, **requests_kwargs)
    except requests.HTTPError as exc:
        raise ApiError(exc.response.status_code, exc.response.text)
    response_data = response.json()
    logger.debug('API response:\n{}'.format(pformat(response_data)))
    return response_data


def _call_user_api(path, method='get', authenticate=False, **requests_kwargs):
    # type: (Text, Text, bool, **Optional[Union[tuple, dict, list]]) -> Union[DataType, List[DataType]]  # pylint: disable=line-too-long
    """
    Call TVmaze user API with authentication

    :param path: API path
    :param method: HTTP method
    :param authenticate: authenticate request
    :param requests_kwargs: kwagrs to be passed to a Requests call
    :return: Requests response object
    :raises AuthorizationError: if authentication credentials are not set
    :raises ApiError: on any error response from API
    """
    if authenticate and not is_authorized():
        raise AuthorizationError('Missing TVmaze username and API key')
    auth = None
    if authenticate:
        username, apikey = _get_credentials()
        auth = (username, apikey)
    url = USER_API_URL + path
    try:
        response = _send_request(url, method, auth=auth, **requests_kwargs)
    except requests.HTTPError as exc:
        raise ApiError(exc.response.status_code, exc.response.text)
    if response.status_code == 207:
        raise ApiError(response.status_code, response.text)
    response_data = response.json()
    logger.debug('API response:\n{}'.format(pformat(response_data)))
    return response_data


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
        response_data = _call_user_api(AUTH_START_PATH, 'post', authenticate=False, json=data)
    except ApiError as exc:
        raise AuthorizationError(six.text_type(exc))
    return response_data.get('token'), response_data.get('confirm_url')


def poll_authorization(token):
    # type: (Text) -> Optional[Tuple[Text, Text]]
    """
    Poll authorization confirmation

    :return: (TVmaze username, API key) tuple
    """
    try:
        response_data = _call_user_api(AUTH_POLL_PATH, 'post', json={'token': token})
    except ApiError as exc:
        if exc.status_code == 403:
            return None
        raise AuthorizationError(six.text_type(exc))
    return response_data.get('username'), response_data.get('apikey')


def push_episodes(episodes, show_id, provider='tvmaze'):
    # type: (List[Dict[Text, int]], Union[int, Text], Text) -> bool
    """
    Send statuses of episodes to TVmase

    :param episodes: the list of episodes to update
    :param show_id: TV show ID in tvmaze, thetvdb or imdb online databases
    :param provider: ID provider
    :return: success status
    """
    provider += '_id'
    params = {provider: show_id}
    try:
        _call_user_api(SCROBBLE_SHOWS_PATH, 'post', authenticate=True, params=params, json=episodes)
    except ApiError:
        return False
    return True


def get_show_info_by_external_id(show_id, provider):
    # type: (Text, Text) -> Optional[DataType]
    """
    Get brief show info from TVmaze by external ID

    :param show_id: show ID in an external online DB
    :param provider: online DB provider
    :return: show info from TVmaze or None
    """
    params = {provider: show_id}
    try:
        return _call_api(SHOW_LOOKUP_PATH, 'get', params=params)
    except ApiError:
        return None


def get_episodes_from_watchlist(tvmaze_id, type_=None):
    # type: (Union[int, Text], Optional[int]) -> Optional[List[DataType]]
    """
    Get episodes for a TV show from user's watchlist on TVmaze

    :param tvmaze_id: show ID on TVmaze
    :param type_: get only episodes with the given status type
    :return: the list of episode infos from TVmaze
    """
    path = '{}/{}'.format(SCROBBLE_SHOWS_PATH, tvmaze_id)
    params = {'embed': 'episode'}
    if type_ is not None:
        params['type'] = type_
    try:
        return _call_user_api(path, 'get', authenticate=True, params=params)
    except ApiError:
        return None
