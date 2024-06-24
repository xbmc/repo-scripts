# Copyright (C) 2019, Roman Miroshnychenko aka Roman V.M. <roman1972@gmail.com>
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
"""
A simple library for making HTTP requests with API similar to the popular "requests" library

It depends only on the Python standard library.

Supported:
* HTTP methods: GET, POST
* HTTP and HTTPS.
* Disabling SSL certificates validation.
* Request payload as form data and JSON.
* Custom headers.
* Basic authentication.
* Gzipped response content.
Not supported:
* Cookies.
* File upload.
"""
# pylint: skip-file
import gzip
import io
import json as _json
import ssl
from base64 import b64encode
from email.message import Message
from typing import Optional, Dict, Any, Tuple, Union, List
from urllib import request as url_request
from urllib.error import HTTPError as _HTTPError
from urllib.parse import urlparse, urlencode

__all__ = [
    'RequestException',
    'ConnectionError',
    'HTTPError',
    'get',
    'post',
]


class RequestException(IOError):

    def __repr__(self) -> str:
        return self.__str__()


class ConnectionError(RequestException):

    def __init__(self, message: str, url: str):
        super().__init__(message)
        self.message = message
        self.url = url

    def __str__(self) -> str:
        return f'ConnectionError for url {self.url}: {self.message}'


class HTTPError(RequestException):

    def __init__(self, response: 'Response'):
        self.response = response

    def __str__(self) -> str:
        return f'HTTPError: {self.response.status_code} for url: {self.response.url}'


class HTTPMessage(Message):

    def update(self, dct: Dict[str, str]) -> None:
        for key, value in dct.items():
            self[key] = value


class Response:
    NULL = object()

    def __init__(self):
        self.encoding: str = 'utf-8'
        self.status_code: int = -1
        self.headers: Dict[str, str] = {}
        self.url: str = ''
        self.content: bytes = b''
        self._text = None
        self._json = self.NULL

    def __str__(self) -> str:
        return f'<Response [{self.status_code}]>'

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    @property
    def text(self) -> str:
        """
        :return: Response payload as decoded text
        """
        if self._text is None:
            self._text = self.content.decode(self.encoding)
        return self._text

    def json(self) -> Optional[Union[Dict[str, Any], List[Any]]]:
        try:
            if self._json is self.NULL:
                self._json = _json.loads(self.content)
            return self._json
        except ValueError as exc:
            raise ValueError('Response content is not a valid JSON') from exc

    def raise_for_status(self) -> None:
        if not self.ok:
            raise HTTPError(self)


def _create_request(url_structure, params=None, data=None, headers=None, auth=None, json=None):
    query = url_structure.query
    if params is not None:
        separator = '&' if query else ''
        query += separator + urlencode(params, doseq=True)
    full_url = url_structure.scheme + '://' + url_structure.netloc + url_structure.path
    if query:
        full_url += '?' + query
    prepared_headers = HTTPMessage()
    if headers is not None:
        prepared_headers.update(headers)
    body = None
    if json is not None:
        body = _json.dumps(json).encode('utf-8')
        prepared_headers['Content-Type'] = 'application/json'
    if body is None and data is not None:
        body = urlencode(data, doseq=True).encode('ascii')
        prepared_headers['Content-Type'] = 'application/x-www-form-urlencoded'
    if auth is not None:
        encoded_credentials = b64encode((auth[0] + ':' + auth[1]).encode('utf-8')).decode('ascii')
        prepared_headers['Authorization'] = f'Basic {encoded_credentials}'
    if 'Accept-Encoding' not in prepared_headers:
        prepared_headers['Accept-Encoding'] = 'gzip'
    return url_request.Request(full_url, body, prepared_headers)


def post(url: str,
         params: Optional[Dict[str, Any]] = None,
         data: Optional[Dict[str, Any]] = None,
         headers: Optional[Dict[str, str]] = None,
         auth: Optional[Tuple[str, str]] = None,
         timeout: Optional[float] = None,
         verify: bool = True,
         json: Optional[Dict[str, Any]] = None) -> Response:
    """
    POST request

    This function assumes that a request body should be encoded with UTF-8
    and by default sends Accept-Encoding: gzip header to receive response content compressed.

    :param url: URL
    :param params: URL query params
    :param data: request payload as form data. If "data" or "json" are passed
        then a POST request is sent
    :param headers: additional headers
    :param auth: a tuple of (login, password) for Basic authentication
    :param timeout: request timeout in seconds
    :param verify: verify SSL certificates
    :param json: request payload as JSON. This parameter has precedence over "data", that is,
        if it's present then "data" is ignored.
    :return: Response object
    """
    url_structure = urlparse(url)
    request = _create_request(url_structure, params, data, headers, auth, json)
    context = None
    if url_structure.scheme == 'https':
        context = ssl.SSLContext()
        if not verify:
            context.verify_mode = ssl.CERT_NONE
            context.check_hostname = False
    fp = None
    try:
        r = fp = url_request.urlopen(request, timeout=timeout, context=context)
        content = fp.read()
    except _HTTPError as exc:
        r = exc
        fp = exc.fp
        content = fp.read()
    except Exception as exc:
        raise ConnectionError(str(exc), request.full_url) from exc
    finally:
        if fp is not None:
            fp.close()
    response = Response()
    response.status_code = r.status if hasattr(r, 'status') else r.getstatus()
    response.headers = r.headers
    response.url = r.url if hasattr(r, 'url') else r.geturl()
    if r.headers.get('Content-Encoding') == 'gzip':
        temp_fo = io.BytesIO(content)
        gzip_file = gzip.GzipFile(fileobj=temp_fo)
        content = gzip_file.read()
    response.content = content
    return response


def get(url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[Tuple[str, str]] = None,
        timeout: Optional[float] = None,
        verify: bool = True) -> Response:
    """
    GET request

    This function by default sends Accept-Encoding: gzip header
    to receive response content compressed.

    :param url: URL
    :param params: URL query params
    :param headers: additional headers
    :param auth: a tuple of (login, password) for Basic authentication
    :param timeout: request timeout in seconds
    :param verify: verify SSL certificates
    :return: Response object
    """
    return post(url=url, params=params, headers=headers, auth=auth, timeout=timeout, verify=verify)
