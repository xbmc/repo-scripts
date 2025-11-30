# -*- coding: utf-8 -*-
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import unicode_literals

import json
import os

import requests
from future.utils import PY3, PY26

if PY3:
    import http.cookiejar as cookielib
else:
    import cookielib

from simpleplugin import Addon

__all__ = ['WebClient', 'WebClientError']


class WebClientError(Exception):

    def __init__(self, error):
        self.message = error
        super(WebClientError, self).__init__(self.message)


class WebClient(requests.Session):
    _secret_data = ['password']

    def __init__(self, headers=None, cookie_file=None):
        super(WebClient, self).__init__()

        if cookie_file is not None:
            self.cookies = cookielib.LWPCookieJar(cookie_file)
            if os.path.exists(cookie_file):
                self.cookies.load(ignore_discard=True, ignore_expires=True)

        if headers is not None:
            self.headers.update(headers)

        self._addon = Addon()

    def __save_cookies(self):
        if isinstance(self.cookies, cookielib.LWPCookieJar) \
                and self.cookies.filename:
            self.cookies.save(ignore_expires=True, ignore_discard=True)

    def post(self, url, **kwargs):

        func = super(WebClient, self).post
        return self._run(func, url, **kwargs)

    def get(self, url, **kwargs):

        func = super(WebClient, self).get
        return self._run(func, url, **kwargs)

    def put(self, url, **kwargs):

        func = super(WebClient, self).put
        return self._run(func, url, **kwargs)

    def delete(self, url, **kwargs):

        func = super(WebClient, self).delete
        return self._run(func, url, **kwargs)

    def head(self, url, **kwargs):

        func = super(WebClient, self).head
        return self._run(func, url, **kwargs)

    def _run(self, func, url, **kwargs):

        try:
            r = func(url, **kwargs)
            r.raise_for_status()
        except (requests.HTTPError, requests.ConnectionError) as e:
            self._log_error(e)
            raise WebClientError(e)
        else:
            self._log_debug(r)
            if r.headers.get('set-cookie') is not None:
                self.__save_cookies()
            return r

    def _log_debug(self, response):
        debug_info = []

        request = getattr(response, 'request', None)

        if request is not None:
            request_info = self._get_request_info(request)
            if request:
                debug_info.append(request_info)

        if response is not None:
            response_info = self._get_response_info(response)
            if response_info:
                debug_info.append(response_info)

        self._addon.log_debug('\n'.join(debug_info))

    def _log_error(self, error):
        error_info = [str(error)]

        response = getattr(error, 'response', None)
        request = getattr(error, 'request', None)

        if request is not None:
            request_info = self._get_request_info(request)
            if request:
                error_info.append(request_info)

        if response is not None:
            response_info = self._get_response_info(response)
            if response_info:
                error_info.append(response_info)

        self._addon.log_error('\n'.join(error_info))

    @staticmethod
    def _get_response_info(response):
        response_info = ['Response info', 'Status code: {0}'.format(response.status_code),
                         'Reason: {0}'.format(response.reason)]
        if not PY26:
            response_info.append('Elapsed: {0:.4f} sec'.format(response.elapsed.total_seconds()))
        if response.url:
            response_info.append('URL: {0}'.format(response.url))
        if response.headers:
            response_info.append('Headers: {0}'.format(response.headers))

        if response.text \
                and response.encoding:
            response_info.append('Content: {0}'.format(response.text))

        return '\n'.join(response_info)

    @classmethod
    def _get_request_info(cls, request):
        request_info = ['Request info', 'Method: {0}'.format(request.method)]

        if request.url:
            request_info.append('URL: {0}'.format(request.url))
        if request.headers:
            request_info.append('Headers: {0}'.format(request.headers))
        if request.body:
            try:
                j = json.loads(request.body)
                for field in cls._secret_data:
                    if j.get(field) is not None:
                        j[field] = '<SECRET>'
                data = json.dumps(j)
            except ValueError:
                data = request.body
                for param in data.split('&'):
                    if '=' in param:
                        field, value = param.split('=')
                        if field in cls._secret_data:
                            data = data.replace(param, '{0}=<SECRET>'.format(field))
            request_info.append('Data: {0}'.format(data))

        return '\n'.join(request_info)
