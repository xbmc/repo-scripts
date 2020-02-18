#-------------------------------------------------------------------------------
# Copyright (C) 2017 Carlos Guzman (cguZZman) carlosguzmang@protonmail.com
# 
# This file is part of Cloud Drive Common Module for Kodi
# 
# Cloud Drive Common Module for Kodi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Cloud Drive Common Module for Kodi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

import json
import re
import time
import urllib
import urllib2

from clouddrive.common.exception import ExceptionUtils, RequestException
from clouddrive.common.remote.request import Request
from clouddrive.common.ui.logger import Logger
from clouddrive.common.utils import Utils


class OAuth2(object):
    
    def _get_api_url(self):
        raise NotImplementedError()

    def _get_request_headers(self):
        raise NotImplementedError()
    
    def get_access_tokens(self):
        raise NotImplementedError()
    
    def refresh_access_tokens(self, request_params=None):
        raise NotImplementedError()
    
    def persist_access_tokens(self, access_tokens):
        raise NotImplementedError()
    
    def _on_exception(self, request, e, original_on_exception):
        ex = ExceptionUtils.extract_exception(e, urllib2.HTTPError)
        if ex and ex.code >= 400 and ex.code <= 599 and ex.code != 503:
            request.tries = request.current_tries
        if original_on_exception and not(original_on_exception is self._on_exception):
            original_on_exception(request, e)
            
    def _wrap_on_exception(self, request_params=None):
        request_params = Utils.default(request_params, {})
        original_on_exception = Utils.get_safe_value(request_params, 'on_exception', None)
        request_params['on_exception'] = lambda request, e: self._on_exception(request, e, original_on_exception)
        return request_params
    
    def _validate_access_tokens(self, access_tokens, url, data, request_headers):
        if not access_tokens or not 'access_token' in access_tokens or not 'refresh_token' in access_tokens or not 'expires_in' in access_tokens or not 'date' in access_tokens:
            raise RequestException('Access tokens provided are not valid: ' + Utils.str(access_tokens), None, 'Request URL: '+Utils.str(url)+'\nRequest data: '+Utils.str(data)+'\nRequest headers: '+Utils.str(request_headers), None)
    
    def _build_url(self, method, path, parameters):
        url = self._get_api_url()
        if re.search("^https?://", path):
            url = path
        else:
            if not (re.search("^\/", path)):
                path = '/' + path
            url += path
        if method == 'get' and parameters:
            url += '?' + parameters
        return url
    
    def prepare_request(self, method, path, parameters=None, request_params=None, access_tokens=None, headers=None):
        parameters = Utils.default(parameters, {})
        access_tokens = Utils.default(access_tokens, {})
        encoded_parameters = urllib.urlencode(parameters)
        url = self._build_url(method, path, encoded_parameters)
        request_params = self._wrap_on_exception(request_params)
        if not headers:
            headers = Utils.default(self._get_request_headers(), {})
        content_type = Utils.get_safe_value(headers, 'content-type', '')
        if content_type == 'application/json':
            data = json.dumps(parameters)
        else:
            data = None if method == 'get' else encoded_parameters
        if not access_tokens:
            access_tokens = self.get_access_tokens()
        self._validate_access_tokens(access_tokens, url, data, headers)
        if time.time() > (access_tokens['date'] + access_tokens['expires_in']):
            access_tokens.update(self.refresh_access_tokens(request_params))
            self._validate_access_tokens(access_tokens, 'refresh_access_tokens', 'Unknown', 'Unknown')
            self.persist_access_tokens(access_tokens)
        headers['authorization'] = 'Bearer ' + access_tokens['access_token']
        return Request(url, data, headers, **request_params) 
    
    def request(self, method, path, parameters=None, request_params=None, access_tokens=None, headers=None):
        return self.prepare_request(method, path, parameters, request_params, access_tokens, headers).request_json()
    
    def get(self, path, **kwargs):
        return self.request('get', path, **kwargs)
    
    def post(self, path, **kwargs):
        return self.request('post', path, **kwargs)
