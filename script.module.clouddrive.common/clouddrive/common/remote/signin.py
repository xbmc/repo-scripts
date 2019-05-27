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

import base64
import urllib

from clouddrive.common.remote.request import Request
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils
from clouddrive.common.exception import ExceptionUtils
import urllib2


class Signin(object):
    
    def get_addon_header(self):
        return '%s %s/%s' % (KodiUtils.get_addon_info('id'), KodiUtils.get_addon_info('version'), KodiUtils.get_addon_info('version', 'script.module.clouddrive.common'))
    
    def create_pin(self, provider_name, request_params=None):
        request_params = Utils.default(request_params, {})
        headers = {'addon' : self.get_addon_header()}
        body = urllib.urlencode({'provider': provider_name})
        return Request(KodiUtils.get_signin_server() + '/pin', body, headers, **request_params).request_json()
    
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
    
    def fetch_tokens_info(self, pin_info, request_params=None):
        request_params = self._wrap_on_exception(request_params)
        headers = {'authorization': 'Basic ' + base64.b64encode(':' + pin_info['password']), 'addon' : self.get_addon_header()}
        return Request(KodiUtils.get_signin_server() + '/pin/' + pin_info['pin'], None, headers, **request_params).request_json()

    def refresh_tokens(self, provider_name, refresh_token, request_params=None):
        request_params = Utils.default(request_params, {})
        headers = {'addon' : self.get_addon_header()}
        body = urllib.urlencode({'provider': provider_name, 'refresh_token': refresh_token})
        return Request(KodiUtils.get_signin_server() + '/refresh', body, headers, **request_params).request_json()
