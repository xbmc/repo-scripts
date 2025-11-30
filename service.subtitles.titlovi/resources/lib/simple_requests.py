# Copyright (c) 2021, Roman Miroshnychenko
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
A simple library for making HTTP requests with API similar to the popular "requests" library

It depends only on the Python standard library and uses **urllib.request** module internally.

Supported:

* HTTP methods: GET, POST, PUT, PATCH, DELETE
* HTTP and HTTPS.
* Disabling SSL certificates validation.
* Request payload as form data, JSON and raw binary data.
* Custom headers.
* Cookies.
* Basic authentication.
* Gzipped response content.

Not supported:

* File upload.
* Persistent Session objects. Since Python's built-in **urllib.request** does not support keep-alive
  connections, persistent sessions do not make much sense in this case.
* Streaming requests and responses. simple-requests is not suitable for sending and receiving
  large volumes of data.

Example::

    from pprint import pprint

    import simple_requests as requests

    response = requests.get('https://httpbin.org/html')
    if not response.ok:
        response.raise_for_status()
    print(response.text)

    response = requests.post('https://httpbin.org/post',
                             data={'username': 'foo', 'password': 'bar'})
    if not response.ok:
        response.raise_for_status()
    pprint(response.json())

"""
import gzip
import io
import json as _json
import ssl
import threading
from base64 import b64encode
from email.message import Message
from http.cookiejar import CookieJar, Cookie
from typing import Optional, Dict, Any, Tuple, Union, List, BinaryIO, Iterable
from urllib import request as url_request
from urllib.error import HTTPError as _HTTPError
from urllib.parse import urlparse, urlencode

__all__ = [
    'RequestException',
    'ConnectionError',
    'HTTPError',
    'RequestsCookieJar',
    'get',
    'post',
    'put',
    'patch',
    'delete',
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


class RequestsCookieJar(CookieJar):
    """A picklable CookieJar class with dictionary-like interface"""

    def __setitem__(self, name: str, value: str) -> None:
        """Set a cookie like in a dictionary."""
        cookie = Cookie(
            version=0,
            name=name,
            value=value,
            port=None,
            port_specified=False,
            domain="",
            domain_specified=False,
            domain_initial_dot=False,
            path="/",
            path_specified=True,
            secure=False,
            expires=None,
            discard=True,
            comment=None,
            comment_url=None,
            rest={'HttpOnly': None},
            rfc2109=False
        )
        self.set_cookie(cookie)

    def __getitem__(self, name: str) -> str:
        """Retrieve a cookie's value by name."""
        for cookie in self:
            if cookie.name == name:
                return cookie.value
        raise KeyError(f"Cookie with name {name} not found.")

    def __delitem__(self, name: str) -> None:
        """Delete a cookie by name."""
        cookies_to_keep = [cookie for cookie in self if cookie.name != name]
        self.clear()  # Remove all cookies
        for cookie in cookies_to_keep:
            self.set_cookie(cookie)

    def __contains__(self, name) -> bool:
        """Check if a cookie with the given name exists."""
        for cookie in self:
            if cookie.name == name:
                return True
        return False

    def items(self) -> Iterable[Tuple[str, str]]:
        for cookie in self:
            yield cookie.name, cookie.value

    def keys(self) -> Iterable[str]:
        """Return the names of all cookies."""
        for cookie in self:
            yield cookie.name

    def values(self) -> Iterable[str]:
        for cookie in self:
            yield cookie.value

    def get_dict(self) -> Dict[str, str]:
        return dict(self.items())

    def update(self, cookies: Union[Dict[str, str], CookieJar]):
        if isinstance(cookies, dict):
            for key, value in cookies.items():
                self[key] = value
            return
        for cookie in cookies:
            self.set_cookie(cookie)

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __getstate__(self):
        """Return the state for pickling."""
        state = self.__dict__.copy()
        # Get the list of cookies for pickling
        state['cookies'] = list(self)
        state['_cookies_lock'] = None
        return state

    def __setstate__(self, state):
        """Restore the state from pickling."""
        state['_cookies_lock'] = threading.RLock()
        self.__dict__.update(state)
        # Re-set cookies from pickled state
        cookies = state.get('cookies', [])
        self.clear()
        for cookie in cookies:
            self.set_cookie(cookie)


class Response:
    NULL = object()

    def __init__(self):
        self.encoding: str = 'utf-8'
        self.status_code: int = -1
        self._headers: Optional[HTTPMessage] = None
        self.url: str = ''
        self.content: bytes = b''
        self._text = None
        self._json = self.NULL
        self.cookies: CookieJar = RequestsCookieJar()

    def __str__(self) -> str:
        return f'<Response [{self.status_code}]>'

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def headers(self) -> HTTPMessage:
        return self._headers

    @headers.setter
    def headers(self, value: HTTPMessage):
        charset = value.get_content_charset()
        if charset:
            self.encoding = charset
        self._headers = value

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    @property
    def text(self) -> str:
        """
        :return: Response payload as decoded text
        """
        if self._text is None:
            try:
                self._text = self.content.decode(self.encoding)
            except (UnicodeDecodeError, LookupError):
                self._text = self.content.decode('utf-8', 'replace')
        return self._text
        
    @property
    def reason(self):
        if self._headers and hasattr(self._headers, 'get'):
            reason = getattr(self._headers, 'reason', None)
            if reason:
                return reason
                
        status_reasons = {
            200: 'OK',
            201: 'Created',
            202: 'Accepted',
            204: 'No Content',
            301: 'Moved Permanently',
            302: 'Found',
            400: 'Bad Request',
            401: 'Unauthorized',
            403: 'Forbidden',
            404: 'Not Found',
            500: 'Internal Server Error',
            503: 'Service Unavailable'
        }
        return status_reasons.get(self.status_code, '')

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


def _create_request(url_structure,
                    method=None,
                    params=None,
                    data=None,
                    headers=None,
                    auth=None,
                    json=None):
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
    if body is None and isinstance(data, dict):
        body = urlencode(data, doseq=True).encode('ascii')
        prepared_headers['Content-Type'] = 'application/x-www-form-urlencoded'
    if body is None and isinstance(data, bytes):
        body = data
    if body is None and isinstance(data, str):
        body = data.encode('utf-8')
    if body is None and hasattr(data, 'read'):
        body = data.read()
    if body is not None and 'Content-Type' not in prepared_headers:
        prepared_headers['Content-Type'] = 'application/octet-stream'
    if auth is not None:
        encoded_credentials = b64encode((auth[0] + ':' + auth[1]).encode('utf-8')).decode('ascii')
        prepared_headers['Authorization'] = f'Basic {encoded_credentials}'
    if 'Accept-Encoding' not in prepared_headers:
        prepared_headers['Accept-Encoding'] = 'gzip'
    return url_request.Request(full_url, body, prepared_headers, method=method)


def _get_cookie_jar(cookies):
    if isinstance(cookies, CookieJar):
        return cookies
    cookie_jar = RequestsCookieJar()
    if cookies is not None:
        cookie_jar.update(cookies)
    return cookie_jar


def _execute_request(url: str,
                     method: Optional[str] = None,
                     params: Optional[Dict[str, Any]] = None,
                     data: Optional[Union[Dict[str, Any], str, bytes, BinaryIO]] = None,
                     headers: Optional[Dict[str, str]] = None,
                     cookies: Union[Dict[str, str], CookieJar] = None,
                     auth: Optional[Tuple[str, str]] = None,
                     timeout: Optional[float] = None,
                     verify: bool = True,
                     json: Optional[Dict[str, Any]] = None) -> Response:
    url_structure = urlparse(url)
    request = _create_request(url_structure, method, params, data, headers, auth, json)
    context = None
    if url_structure.scheme == 'https':
        context = ssl.SSLContext()
        if not verify:
            context.verify_mode = ssl.CERT_NONE
            context.check_hostname = False
    cookie_jar = _get_cookie_jar(cookies)
    opener_director = url_request.build_opener(
        url_request.HTTPSHandler(context=context),
        url_request.HTTPCookieProcessor(cookie_jar)
    )
    resp = None
    try:
        resp = opener_director.open(request, timeout=timeout)
        content = resp.read()
    except _HTTPError as exc:
        resp = exc
        content = resp.read()
    except Exception as exc:
        raise ConnectionError(str(exc), request.full_url) from exc
    finally:
        if resp is not None:
            resp.close()
    response = Response()
    response.status_code = resp.status if hasattr(resp, 'status') else resp.getstatus()
    response.headers = resp.headers if hasattr(resp, 'headers') else resp.info()
    response.url = resp.url if hasattr(resp, 'url') else resp.geturl()
    if resp.headers.get('Content-Encoding') == 'gzip':
        temp_fo = io.BytesIO(content)
        gzip_file = gzip.GzipFile(fileobj=temp_fo)
        content = gzip_file.read()
    response.content = content
    if isinstance(cookies, CookieJar):
        response.cookies = cookies
    response.cookies.extract_cookies(resp, request)
    return response


def get(url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Union[Dict[str, str], CookieJar] = None,
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
    :param cookies: cookies as a dict or a CookieJar object. If a CookieJar object is provided
        the same object will be attached to a response object with the updated set of cookies.
    :param auth: a tuple of (login, password) for Basic authentication
    :param timeout: request timeout in seconds
    :param verify: verify SSL certificates
    :raises: ConnectionError
    :return: Response object
    """
    return _execute_request(
        url,
        method='GET',
        params=params,
        headers=headers,
        cookies=cookies,
        auth=auth,
        timeout=timeout,
        verify=verify
    )


def post(url: str,
         params: Optional[Dict[str, Any]] = None,
         data: Optional[Union[Dict[str, Any], str, bytes, BinaryIO]] = None,
         headers: Optional[Dict[str, str]] = None,
         cookies: Union[Dict[str, str], CookieJar] = None,
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
    :param data: request payload as dict, str, bytes or a binary file object.
        For str, bytes or file object it's caller's responsibility to provide a proper
        'Content-Type' header.
    :param headers: additional headers
    :param cookies: cookies as a dict or a CookieJar object. If a CookieJar object is provided
        the same object will be attached to a response object with the updated set of cookies.
    :param auth: a tuple of (login, password) for Basic authentication
    :param timeout: request timeout in seconds
    :param verify: verify SSL certificates
    :param json: request payload as JSON. This parameter has precedence over "data", that is,
        if it's present then "data" is ignored.
    :raises: ConnectionError
    :return: Response object
    """
    return _execute_request(
        url,
        method='POST',
        params=params,
        data=data,
        headers=headers,
        cookies=cookies,
        auth=auth,
        timeout=timeout,
        verify=verify,
        json=json
    )


def put(url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], str, bytes, BinaryIO]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Union[Dict[str, str], CookieJar] = None,
        auth: Optional[Tuple[str, str]] = None,
        timeout: Optional[float] = None,
        verify: bool = True,
        json: Optional[Dict[str, Any]] = None) -> Response:
    """
    PUT request

    This function assumes that a request body should be encoded with UTF-8
    and by default sends Accept-Encoding: gzip header to receive response content compressed.

    :param url: URL
    :param params: URL query params
    :param data: request payload as dict, str, bytes or a binary file object.
        For str, bytes or file object it's caller's responsibility to provide a proper
        'Content-Type' header.
    :param headers: additional headers
    :param cookies: cookies as a dict or a CookieJar object. If a CookieJar object is provided
        the same object will be attached to a response object with the updated set of cookies.
    :param auth: a tuple of (login, password) for Basic authentication
    :param timeout: request timeout in seconds
    :param verify: verify SSL certificates
    :param json: request payload as JSON. This parameter has precedence over "data", that is,
        if it's present then "data" is ignored.
    :raises: ConnectionError
    :return: Response object
    """
    return _execute_request(
        url,
        method='PUT',
        params=params,
        data=data,
        headers=headers,
        cookies=cookies,
        auth=auth,
        timeout=timeout,
        verify=verify,
        json=json
    )


def patch(url: str,
          params: Optional[Dict[str, Any]] = None,
          data: Optional[Union[Dict[str, Any], str, bytes, BinaryIO]] = None,
          headers: Optional[Dict[str, str]] = None,
          cookies: Union[Dict[str, str], CookieJar] = None,
          auth: Optional[Tuple[str, str]] = None,
          timeout: Optional[float] = None,
          verify: bool = True,
          json: Optional[Dict[str, Any]] = None) -> Response:

    """
    PATCH request

    This function assumes that a request body should be encoded with UTF-8
    and by default sends Accept-Encoding: gzip header to receive response content compressed.

    :param url: URL
    :param params: URL query params
    :param data: request payload as dict, str, bytes or a binary file object.
        For str, bytes or file object it's caller's responsibility to provide a proper
        'Content-Type' header.
    :param headers: additional headers
    :param cookies: cookies as a dict or a CookieJar object. If a CookieJar object is provided
        the same object will be attached to a response object with the updated set of cookies.
    :param auth: a tuple of (login, password) for Basic authentication
    :param timeout: request timeout in seconds
    :param verify: verify SSL certificates
    :param json: request payload as JSON. This parameter has precedence over "data", that is,
        if it's present then "data" is ignored.
    :raises: ConnectionError
    :return: Response object
    """
    return _execute_request(
        url,
        method='PATCH',
        params=params,
        data=data,
        headers=headers,
        cookies=cookies,
        auth=auth,
        timeout=timeout,
        verify=verify,
        json=json
    )


def delete(url: str,
           params: Optional[Dict[str, Any]] = None,
           data: Optional[Union[Dict[str, Any], str, bytes, BinaryIO]] = None,
           headers: Optional[Dict[str, str]] = None,
           cookies: Union[Dict[str, str], CookieJar] = None,
           auth: Optional[Tuple[str, str]] = None,
           timeout: Optional[float] = None,
           verify: bool = True) -> Response:

    """
    DELETE request

    This function by default sends Accept-Encoding: gzip header
    to receive response content compressed.

    :param url: URL
    :param params: URL query params
    :param headers: additional headers
    :param cookies: cookies as a dict or a CookieJar object. If a CookieJar object is provided
        the same object will be attached to a response object with the updated set of cookies.
    :param auth: a tuple of (login, password) for Basic authentication
    :param timeout: request timeout in seconds
    :param verify: verify SSL certificates
    :raises: ConnectionError
    :return: Response object
    """
    return _execute_request(
        url,
        method='DELETE',
        params=params,
        data=data,
        headers=headers,
        cookies=cookies,
        auth=auth,
        timeout=timeout,
        verify=verify
    )

# ========== Requests Compatibility Patch ==========
# This patch provides drop-in compatibility with the most commonly used parts of the 'requests' library
# for third-party code expecting 'requests.codes', 'requests.exceptions', 'requests.Session', and 'requests.request'

class SSLError(RequestException):
    """Compatibility: Exception raised for SSL errors, like requests.exceptions.SSLError"""
    pass

class exceptions:
    Timeout = ConnectionError
    RequestException = RequestException
    ConnectionError = ConnectionError
    HTTPError = HTTPError
    SSLError = SSLError

class _codes:
    # HTTP status codes compatibility for requests.codes
    continue_ = 100
    switching_protocols = 101
    processing = 102

    ok = 200
    created = 201
    accepted = 202
    non_authoritative_information = 203
    no_content = 204
    reset_content = 205
    partial_content = 206
    multi_status = 207
    already_reported = 208
    im_used = 226

    multiple_choices = 300
    moved_permanently = 301
    found = 302
    see_other = 303
    not_modified = 304
    use_proxy = 305
    temporary_redirect = 307
    permanent_redirect = 308

    bad_request = 400
    unauthorized = 401
    payment_required = 402
    forbidden = 403
    not_found = 404
    method_not_allowed = 405
    not_acceptable = 406
    proxy_authentication_required = 407
    request_timeout = 408
    conflict = 409
    gone = 410
    length_required = 411
    precondition_failed = 412
    payload_too_large = 413
    uri_too_long = 414
    unsupported_media_type = 415
    range_not_satisfiable = 416
    expectation_failed = 417
    im_a_teapot = 418
    misdirected_request = 421
    unprocessable_entity = 422
    locked = 423
    failed_dependency = 424
    too_early = 425
    upgrade_required = 426
    precondition_required = 428
    too_many_requests = 429
    request_header_fields_too_large = 431
    unavailable_for_legal_reasons = 451

    internal_server_error = 500
    not_implemented = 501
    bad_gateway = 502
    service_unavailable = 503
    gateway_timeout = 504
    http_version_not_supported = 505
    variant_also_negotiates = 506
    insufficient_storage = 507
    loop_detected = 508
    not_extended = 510
    network_authentication_required = 511

codes = _codes()

def request(method, url, **kwargs):
    """
    Compatibility: calls the correct method (get, post, put, patch, delete) just like requests.request()
    """
    method = method.upper()
    if method == 'GET':
        return get(url, **kwargs)
    elif method == 'POST':
        return post(url, **kwargs)
    elif method == 'PUT':
        return put(url, **kwargs)
    elif method == 'PATCH':
        return patch(url, **kwargs)
    elif method == 'DELETE':
        return delete(url, **kwargs)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")

class Session:
    """
    Dummy requests.Session() implementation for compatibility.
    """
    def __init__(self):
        self.cookies = RequestsCookieJar()
        self.headers = {}

    def get(self, *args, **kwargs):
        kwargs.setdefault('cookies', self.cookies)
        kwargs.setdefault('headers', self.headers)
        return get(*args, **kwargs)

    def post(self, *args, **kwargs):
        kwargs.setdefault('cookies', self.cookies)
        kwargs.setdefault('headers', self.headers)
        return post(*args, **kwargs)

    def put(self, *args, **kwargs):
        kwargs.setdefault('cookies', self.cookies)
        kwargs.setdefault('headers', self.headers)
        return put(*args, **kwargs)

    def patch(self, *args, **kwargs):
        kwargs.setdefault('cookies', self.cookies)
        kwargs.setdefault('headers', self.headers)
        return patch(*args, **kwargs)

    def delete(self, *args, **kwargs):
        kwargs.setdefault('cookies', self.cookies)
        kwargs.setdefault('headers', self.headers)
        return delete(*args, **kwargs)

__all__ += ['exceptions', 'codes', 'Session', 'request']
