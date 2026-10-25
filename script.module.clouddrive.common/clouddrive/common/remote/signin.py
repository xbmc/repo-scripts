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
import http.client
import platform
import socket
import urllib

from clouddrive.common.remote.request import Request
from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils
from clouddrive.common.exception import ExceptionUtils


class _AddressFamilyConnection(object):
    # Connects over one IP version only: family is socket.AF_INET or socket.AF_INET6.
    family = socket.AF_UNSPEC

    def _connect_socket(self):
        error = OSError('No address for %s' % self.host)
        for af, socktype, proto, _, address in socket.getaddrinfo(self.host, self.port, self.family, socket.SOCK_STREAM):
            sock = socket.socket(af, socktype, proto)
            try:
                sock.settimeout(self.timeout)
                sock.connect(address)
                return sock
            except OSError as e:
                sock.close()
                error = e
        raise error


class _HTTPConnection(_AddressFamilyConnection, http.client.HTTPConnection):
    def connect(self):
        self.sock = self._connect_socket()


class _HTTPSConnection(_AddressFamilyConnection, http.client.HTTPSConnection):
    def connect(self):
        self.sock = self._context.wrap_socket(self._connect_socket(), server_hostname=self.host)


class Signin(object):
    
    def get_addon_header(self):
        return '%s %s/%s' % (KodiUtils.get_addon_info('id'), KodiUtils.get_addon_info('version'), KodiUtils.get_addon_info('version', 'script.module.clouddrive.common'))

    def get_user_agent(self):
        # For the sign-in server's anonymous usage counts: which add-on, common module, Kodi and Python versions are in use.
        import xbmc
        kodi = (xbmc.getInfoLabel('System.BuildVersion') or '').split(' ')[0] or 'unknown'
        return '%s/%s clouddrive.common/%s Kodi/%s Python/%s' % (
            KodiUtils.get_addon_info('id'), KodiUtils.get_addon_info('version'), KodiUtils.get_addon_info('version', 'script.module.clouddrive.common'),
            kodi, '.'.join(platform.python_version_tuple()[:2]))

    def _headers(self):
        return {'addon' : self.get_addon_header(), 'user-agent': self.get_user_agent()}

    def create_pin(self, provider_name, request_params=None):
        request_params = Utils.default(request_params, {})
        headers = self._headers()
        body = urllib.parse.urlencode({'provider': provider_name})
        return Request(KodiUtils.get_signin_server() + '/pin', body, headers, **request_params).request_json()
    
    def _on_exception(self, request, e, original_on_exception):
        ex = ExceptionUtils.extract_exception(e, urllib.error.HTTPError)
        if ex and ex.code >= 400 and ex.code <= 599 and ex.code != 503:
            request.tries = request.current_tries
        if original_on_exception and not(original_on_exception is self._on_exception):
            original_on_exception(request, e)
            
    def _wrap_on_exception(self, request_params=None):
        request_params = Utils.default(request_params, {})
        original_on_exception = Utils.get_safe_value(request_params, 'on_exception', None)
        request_params['on_exception'] = lambda request, e: self._on_exception(request, e, original_on_exception)
        return request_params
    
    def _pin_headers(self, pin_info):
        headers = self._headers()
        headers['authorization'] = 'Basic ' + Utils.str(base64.b64encode(Utils.encode(':' + pin_info['password'])))
        return headers

    def _request_over(self, family, path, headers=None):
        # Status and body of a GET to the sign-in server over IPv4 or IPv6 only. Raises if that IP version doesn't work.
        server = urllib.parse.urlparse(KodiUtils.get_signin_server())
        connection_class = _HTTPSConnection if server.scheme == 'https' else _HTTPConnection
        connection = connection_class(server.hostname, server.port, timeout=10)
        connection.family = family
        try:
            connection.request('GET', server.path.rstrip('/') + path, headers=Utils.default(headers, {}))
            response = connection.getresponse()
            return response.status, Utils.str(response.read())
        finally:
            connection.close()

    def register_networks(self, pin_info):
        # The sign-in server only lets a browser on the same network as Kodi use the code. A home network can have
        # an IPv4 and an IPv6 side, and the phone may use either: polling the new code with its password over each
        # IP version tells the server both. Call it right after creating the code, before anyone can sign in with
        # it, so the polls can't collect the tokens. Returns the source ids of the IP versions that work.
        source_ids = []
        headers = self._pin_headers(pin_info)
        for family, name in ((socket.AF_INET, 'IPv4'), (socket.AF_INET6, 'IPv6')):
            try:
                status, ip = self._request_over(family, '/ip')
                if status == 200:
                    source_ids.append('%s (%s)' % (Utils.get_source_id(ip), name))
                self._request_over(family, '/pin/' + pin_info['pin'], headers)
            except Exception as e:
                Logger.debug('Sign-in server not reachable over %s: %s' % (name, e))
        return source_ids

    def fetch_tokens_info(self, pin_info, request_params=None):
        request_params = self._wrap_on_exception(request_params)
        headers = self._pin_headers(pin_info)
        return Request(KodiUtils.get_signin_server() + '/pin/' + pin_info['pin'], None, headers, **request_params).request_json()

    def refresh_tokens(self, provider_name, refresh_token, request_params=None):
        request_params = Utils.default(request_params, {})
        headers = self._headers()
        body = urllib.parse.urlencode({'provider': provider_name, 'refresh_token': refresh_token})
        return Request(KodiUtils.get_signin_server() + '/refresh', body, headers, **request_params).request_json()
