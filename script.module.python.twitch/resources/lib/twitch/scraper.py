# -*- encoding: utf-8 -*-
"""

    Copyright (C) 2012-2016 python-twitch (https://github.com/ingwinlu/python-twitch)
    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

import sys
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.parse import urlencode

import requests

from .keys import USER_AGENT, USER_AGENT_STRING
from .log import log
from .exceptions import ResourceUnavailableException
from . import methods

try:
    import json
except:
    import simplejson as json  # @UnresolvedImport

SSL_VERIFICATION = True
if sys.version_info <= (2, 7, 9):
    SSL_VERIFICATION = False

MAX_RETRIES = 5


def get_json(baseurl, parameters={}, headers={}, data={}, method=methods.GET):
    '''Download Data from an URL and returns it as JSON
    @param url Url to download from
    @param parameters Parameter dict to be encoded with url or list of tuple pairs
    @param headers Headers dict to pass with Request
    @param data Request body
    @param method Request method
    @returns JSON Object with data from URL
    '''
    method = methods.validate(method)
    jsonString = download(baseurl, parameters, headers, data, method)
    jsonDict = json.loads(jsonString)
    log.debug('url: |{0}| parameters: |{1}|\n{2}'.format(baseurl, parameters, json.dumps(jsonDict, indent=4, sort_keys=True)))
    return jsonDict


def get_json_and_headers(baseurl, parameters={}, headers={}, data={}, method=methods.GET):
    '''Download Data from an URL and returns it as JSON
    @param url Url to download from
    @param parameters Parameter dict to be encoded with url or list of tuple pairs
    @param headers Headers dict to pass with Request
    @param data Request body
    @param method Request method
    @returns JSON Object with data and headers from URL {'response': {}, 'headers': {}}
    '''
    method = methods.validate(method)
    content = download(baseurl, parameters, headers, data, method, response_headers=True)
    content['response'] = json.loads(content['response'])
    log.debug('url: |{0}| parameters: |{1}|\n{2}'.format(baseurl, parameters, json.dumps(content['response'], indent=4, sort_keys=True)))
    return content


def download(baseurl, parameters={}, headers={}, data={}, method=methods.GET, response_headers=False):
    '''Download Data from an url and returns it as a String
    @param method Request method
    @param baseurl Url to download from (e.g. http://www.google.com)
    @param parameters Parameter dict to be encoded with url or list of tuple pairs
    @param headers Headers dict to pass with Request
    @param data Request body
    @param method Request method
    @param response_headers Include response headers in response {'response': {}, 'headers': {}}
    @returns String of data from URL or {'response': {}, 'headers': {}} if response_headers is True
    '''
    method = methods.validate(method)

    if not parameters:
        url = baseurl
    elif isinstance(parameters, dict):
        url = '?'.join([baseurl, urlencode(parameters)])
    else:
        _parameters = ''
        for param in parameters:
            _parameters += '{0}={1}&'.format(param[0], quote_plus(str(param[1])))
        _parameters = _parameters.rstrip('&')
        url = '?'.join([baseurl, _parameters])

    log.debug('Downloading: |{0}|'.format(url))
    content = ""
    for _ in range(MAX_RETRIES):
        try:
            headers.update({USER_AGENT: USER_AGENT_STRING})
            if isinstance(data, list):
                json_body = data
                data = None
            else:
                json_body = None
            response = requests.request(method=method, url=url, headers=headers,
                                        json=json_body, data=data, verify=SSL_VERIFICATION)
            content = response.content
            if not content:
                content = '{{"status": {0}}}'.format(response.status_code)
            break
        except Exception as err:
            if not isinstance(err, URLError):
                log.debug('Error |{0}| during HTTP Request, abort'.format(repr(err)))
                raise  # propagate non-URLError
            log.debug('Error |{0}| during HTTP Request, retrying'.format(repr(err)))
    else:
        raise ResourceUnavailableException('Max retries exceeded')

    if isinstance(content, bytes):
        content = content.decode('utf-8')

    if not response_headers:
        return content
    else:
        return {'response': content, 'headers': response.headers}
