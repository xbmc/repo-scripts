#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2021 William Forde
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Urlquick II
-----------
Urlquick II is a wrapper for requests that add's support for http caching.
It act's just like requests but with a few extra parameters and features.
'Requests' itself is left untouched.

All GET, HEAD and POST requests are cached locally for a period of 4 hours, this can be changed. When the cache expires,
conditional headers are added to any new request e.g. "Etag" and "Last-modified". Then if the server
returns a 304 Not-Modified response, the cache is used, saving having to re-download the content body.

Github: https://github.com/willforde/urlquick
Documentation: http://urlquick.readthedocs.io/en/stable/?badge=stable
Testing: https://www.travis-ci.com/github/willforde/urlquick
Code Coverage: https://coveralls.io/github/willforde/urlquick?branch=master
Code Quality: https://codeclimate.com/github/willforde/urlquick
"""

__version__ = "2.0.0"

# Standard Lib
from functools import wraps
import warnings
import logging
import hashlib
import sqlite3
import sys
import os

try:
    # noinspection PyPep8Naming, PyUnresolvedReferences
    import cPickle as pickle  # Python 2
except ImportError:
    import pickle  # Works for both python 2 & 3

# Third Party
from htmlement import HTMLement
from requests.structures import CaseInsensitiveDict
from requests.adapters import HTTPResponse
from requests import adapters
from requests import *
import requests

# Change some values if running within Kodi
try:
    # noinspection PyUnresolvedReferences
    import xbmc, xbmcvfs, xbmcaddon
    _addon_data = xbmcaddon.Addon()
    _translate_path = xbmcvfs.translatePath if hasattr(xbmcvfs, "translatePath") else xbmc.translatePath
    _CACHE_LOCATION = _translate_path(_addon_data.getAddonInfo("profile"))
    _DEFAULT_RAISE_FOR_STATUS = True
except ImportError:
    _CACHE_LOCATION = os.path.join(os.getcwd(), ".urlquick.cache")
    _DEFAULT_RAISE_FOR_STATUS = False

# Check for python 2, for compatibility
py2 = sys.version_info.major == 2

# Unique logger for this module
logger = logging.getLogger("urlquick")
logging.captureWarnings(True)

# Cacheable Codes & Methods
CACHEABLE_METHODS = {"GET", "HEAD", "POST"}
CACHEABLE_CODES = {
    codes.ok,
    codes.non_authoritative_info,
    codes.no_content,
    codes.multiple_choices,
    codes.moved_permanently,
    codes.found,
    codes.see_other,
    codes.temporary_redirect,
    codes.permanent_redirect,
    codes.gone,
    codes.request_uri_too_large,
}
REDIRECT_CODES = {
    codes.moved_permanently,
    codes.found,
    codes.see_other,
    codes.temporary_redirect,
    codes.permanent_redirect,
}

#: The default location for the cached files
CACHE_LOCATION = _CACHE_LOCATION

#: The time in seconds where a cache item is considered stale.
#: Stale items will stay in the database to allow for conditional headers.
MAX_AGE = 60 * 60 * 4  # 4 Hours

#: The time in seconds where a cache item is considered expired.
#: Expired items will be removed from the database.
EXPIRES = 60 * 60 * 24 * 7  # 1 week

# Function components to wrap when overriding requests functions
WRAPPER_ASSIGNMENTS = ["__doc__"]


# Compatible with urlquick v1
class UrlError(RequestException):
    pass


# Compatible with urlquick v1
class MaxRedirects(TooManyRedirects):
    pass


# Compatible with urlquick v1
class ContentError(HTTPError):
    pass


# Compatible with urlquick v1
class ConnError(ConnectionError):
    pass


class CacheError(RequestException):
    pass


class Response(requests.Response):
    def __init__(self):
        super(Response, self).__init__()
        self.from_cache = False

    def xml(self):
        """
        Parse's "XML" document into a element tree.

        :return: The root element of the element tree.
        :rtype: xml.etree.ElementTree.Element
        """
        from xml.etree import ElementTree
        return ElementTree.fromstring(self.content)

    def parse(self, tag=u"", attrs=None):
        """
        Parse's "HTML" document into a element tree using HTMLement.

        .. seealso:: The htmlement documentation can be found at.\n
                     http://python-htmlement.readthedocs.io/en/stable/?badge=stable

        :param str tag: [opt] Name of 'element' which is used to filter tree to required section.

        :type attrs: dict
        :param attrs: [opt] Attributes of 'element', used when searching for required section.
                            Attrs should be a dict of unicode key/value pairs.

        :return: The root element of the element tree.
        :rtype: xml.etree.ElementTree.Element
        """
        tag = tag.decode() if isinstance(tag, bytes) else tag
        parser = HTMLement(tag, attrs)
        parser.feed(self.text)
        return parser.close()

    @classmethod
    def extend_response(cls, response):
        self = cls()
        self.__dict__.update(response.__dict__)
        return self

    def __conform__(self, protocol):
        """Convert Response to a sql blob."""
        if protocol is sqlite3.PrepareProtocol:  # pragma: no branch
            data = pickle.dumps(self, protocol=pickle.HIGHEST_PROTOCOL)
            return sqlite3.Binary(data)


def to_bytes_string(value):  # type: (...) -> bytes
    """Convert value to bytes if required."""
    return value.encode("utf8") if isinstance(value, type(u"")) else value


def hash_url(req):  # type: (PreparedRequest) -> str
    """Return url as a sha1 encoded hash."""
    data = to_bytes_string(req.url + req.method)
    body = to_bytes_string(req.body) if req.body else b''
    return hashlib.sha1(b''.join((data, body))).hexdigest()


class CacheRecord(object):
    """SQL cache data record."""

    def __init__(self, record):  # type: (sqlite3.Row) -> None
        self._response = response = pickle.loads(bytes(record["response"]))
        self._fresh = record["fresh"] or response.status_code in REDIRECT_CODES
        self._response.from_cache = True

    @property
    def response(self):  # type: () -> Response
        return self._response

    @property
    def isfresh(self):  # type: () -> bool
        return self._fresh

    def add_conditional_headers(self, headers):  # type: (CaseInsensitiveDict) -> None
        """Return a dict of conditional headers from cache."""
        # Fetch cached headers
        cached_headers = self._response.headers

        # Check for conditional headers
        if "Etag" in cached_headers:
            headers["If-none-match"] = cached_headers["ETag"]
        if "Last-modified" in cached_headers:
            headers["If-modified-since"] = cached_headers["Last-Modified"]


class CacheHTTPAdapter(adapters.HTTPAdapter):
    """Requests adapter that handels https requests and caches them for later use."""

    def __init__(self, cache_location, *args, **kwargs):  # type: (str, ..., ...) -> None
        super(CacheHTTPAdapter, self).__init__(*args, **kwargs)
        # sqlite3.enable_callback_tracebacks(True)
        self._closed = False

        # Create any missing directorys
        self.cache_file = os.path.join(cache_location, ".urlquick.slite3")
        if not os.path.exists(cache_location):
            os.makedirs(cache_location)

        # Connect to database
        self.conn = self.connect()
        self.clean()  # Remove expired

    def connect(self):  # type: () -> sqlite3.Connection
        """Connect to SQLite Database."""
        try:
            conn = sqlite3.connect(self.cache_file, timeout=1)
        except sqlite3.Error as e:
            raise CacheError(str(e))
        else:
            conn.row_factory = sqlite3.Row
            conn.execute("""CREATE TABLE IF NOT EXISTS urlcache(
                key TEXT PRIMARY KEY NOT NULL,
                response BLOB NOT NULL,
                cached_date TIMESTAMP NOT NULL
            )""")

            # Performance tweak may cause curruption errors
            # But not an issue as the database will be re-created if so
            conn.execute("PRAGMA journal_mode=MEMORY")

        return conn

    def execute(self, query, values=(), repeat=False):  # type: (str, tuple, bool) -> sqlite3.Cursor
        """Execute SQL Query."""
        try:
            with self.conn:
                # Automatically commits or rolls back on exception
                return self.conn.execute(query, values)
        except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
            # Check if database is currupted
            if repeat is False and (str(e).find("file is encrypted") > -1 or str(e).find("not a database") > -1):
                logger.debug("Corrupted database detected, Cleaning...")
                self.conn.cursor().close()
                self.conn.close()
                os.remove(self.cache_file)
                self.conn = self.connect()
                return self.execute(query, values, repeat=True)
            else:
                raise e

    def close(self):
        """Close the HTTPAdapter and SQLITE database."""
        super(CacheHTTPAdapter, self).close()
        if self._closed is False:
            self.conn.cursor().close()
            self.conn.close()
            self._closed = True

    def get_cache(self, urlhash, max_age):  # type: (str, int) -> CacheRecord
        """Return a cached response if one exists."""
        result = self.execute("""SELECT key, response,
        strftime('%s', 'now') - strftime('%s', cached_date, 'unixepoch') < ? AS fresh
        FROM urlcache WHERE key = ?""", (max_age, urlhash))
        record = result.fetchone()
        if record is not None:
            try:
                return CacheRecord(record)
            except ValueError as e:
                # If unsupported protocol is raised, then wipe the database clean
                # This can happen when downgrading python versions
                if "unsupported pickle protocol" in str(e):
                    self.wipe()
                else:
                    # Remove cache item
                    self.del_cache(urlhash)

    def set_cache(self, urlhash, resp):  # type: (str, Response) -> Response
        """Save a response to database and return original response."""
        self.execute(
            "REPLACE INTO urlcache (key, response, cached_date) VALUES (?,?,strftime('%s', 'now'))",
            (urlhash, resp)
        )
        return resp

    def del_cache(self, urlhash):
        """Remove a cache item from database."""
        self.execute(
            "DELETE FROM urlcache WHERE key = ?",
            (urlhash,)
        )

    def reset_cache(self, urlhash):  # type: (str) -> None
        """Reset the cached date to current time."""
        self.execute(
            "UPDATE urlcache SET cached_date=strftime('%s', 'now') WHERE key=?",
            (urlhash,)
        )

    def clean(self, expires=EXPIRES):  # type: (int) -> None
        """Clean the database of expired caches."""
        self.execute(
            "DELETE FROM urlcache WHERE strftime('%s', 'now') - strftime('%s', cached_date, 'unixepoch') > ?",
            (expires,)
        )

    def wipe(self):
        """Wipe the database clean."""
        self.execute("DELETE FROM urlcache")

    # noinspection PyShadowingNames
    def send(self, request, **kwargs):  # type: (PreparedRequest, ...) -> Response
        max_age = int(request.headers.pop("x-cache-max-age"))
        urlhash = hash_url(request) if max_age >= 0 else None
        cache = None

        # Check if request is already cached and valid
        if urlhash and request.method in CACHEABLE_METHODS:
            cache = self.get_cache(urlhash, max_age)
            if cache and cache.isfresh:
                logger.debug("Cache is fresh")
                return cache.response
            elif cache:
                # Allows for Not Modified check
                logger.debug("Cache is stale, adding conditional headers to request")
                cache.add_conditional_headers(request.headers)

        # Send request for remote resource
        response = super(CacheHTTPAdapter, self).send(request, **kwargs)
        return self.process_response(response, cache, urlhash) if urlhash else response

    def build_response(self, req, resp):  # type: (PreparedRequest, HTTPResponse) -> Response
        """Replace response object with our customized version."""
        resp = super(CacheHTTPAdapter, self).build_response(req, resp)
        return Response.extend_response(resp)

    def process_response(self, response, cache, urlhash):  # type: (Response, CacheRecord, str) -> Response
        """Save response to cache if possible."""
        # Check for Not Modified response
        if cache and response.status_code == codes.not_modified:
            logger.debug("Server return 304 Not Modified response, using cached response")
            response.close()
            self.reset_cache(urlhash)
            response = cache.response

        # Cache any cacheable responses
        elif response.request.method in CACHEABLE_METHODS and response.status_code in CACHEABLE_CODES:
            logger.debug("Caching %s %s response", response.status_code, response.reason)
            response = self.set_cache(urlhash, response)

        return response


class Session(sessions.Session):
    def __init__(self, cache_location=CACHE_LOCATION, **kwargs):  # type: (str, ...) -> None
        super(Session, self).__init__()

        #: When set to True, This attribute checks if the status code of the
        #: response is between 400 and 600 to see if there was a client error
        #: or a server error. Raising a :class:`HTTPError` if so.
        self.raise_for_status = kwargs.get("raise_for_status", _DEFAULT_RAISE_FOR_STATUS)

        #: Age the 'cache' can be, before it’s considered stale. -1 will disable caching.
        #: Defaults to :data:`MAX_AGE <urlquick.MAX_AGE>`
        self.max_age = kwargs.get("max_age", MAX_AGE)

        self.cache_adapter = adapter = CacheHTTPAdapter(cache_location)
        self.mount("https://", adapter)
        self.mount("http://", adapter)

    def _raise_for_status(self, response, raise_for_status):  # type: (Response, bool) -> None
        """Raise :class:`HTTPError` if status code is between 400 and 600."""
        if self.raise_for_status if raise_for_status is None else raise_for_status:
            response.raise_for_status()

    def _merge_max_age(self, max_age):  # type: (int) -> int
        """Return a valid max age. Use session value if request did not containe one."""
        return (-1 if self.max_age is None else self.max_age) if max_age is None else max_age

    def request(self, *args, **kwargs):  # type: (...) -> Response
        # Sometimes people pass in None for headers
        # So we need to keep this in mind
        if len(args) >= 5:
            headers = args[4] or {}
            args = list(args)
            args[4] = headers
        else:
            headers = kwargs.get("headers") or {}
            kwargs["headers"] = headers

        # Add max age to headers so the adapter can access it
        max_age = self._merge_max_age(kwargs.pop("max_age", None))
        headers["x-cache-max-age"] = str(max_age)

        # This is here to indicate to 'self.send' that it's been called internally
        # This is to pervent 'self.send' checking for max age & raise_for_status
        headers["x-cache-internal"] = "true"

        raise_for_status = kwargs.pop("raise_for_status", None)
        response = super(Session, self).request(*args, **kwargs)
        self._raise_for_status(response, raise_for_status)
        return response

    # noinspection PyShadowingNames
    def send(self, request, **kwargs):  # type: (PreparedRequest, ...) -> Response
        # If the headers does not contain 'x-cache-internal' then this method
        # must be getting called directly, so check for extra parameters
        if request.headers.pop("x-cache-internal", None):
            return super(Session, self).send(request, **kwargs)
        else:
            # Add max age to request headers
            max_age = self._merge_max_age(kwargs.pop("max_age", None))
            request.headers["x-cache-max-age"] = str(max_age)

            # Make request and check for status code
            raise_for_status = kwargs.pop("raise_for_status", None)
            response = super(Session, self).send(request, **kwargs)
            self._raise_for_status(response, raise_for_status)
            return response

    def get(self, url, **kwargs):  # type: (...) -> Response
        return super(Session, self).get(url, **kwargs)

    def options(self, url, **kwargs):  # type: (...) -> Response
        return super(Session, self).options(url, **kwargs)

    def head(self, url, **kwargs):  # type: (...) -> Response
        return super(Session, self).head(url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):  # type: (...) -> Response
        return super(Session, self).post(url, data, json, **kwargs)

    def put(self, url, data=None, **kwargs):  # type: (...) -> Response
        return super(Session, self).put(url, data, **kwargs)

    def patch(self, url, data=None, **kwargs):  # type: (...) -> Response
        return super(Session, self).patch(url, data, **kwargs)

    def delete(self, url, **kwargs):  # type: (...) -> Response
        return super(Session, self).delete(url, **kwargs)


@wraps(requests.request, assigned=WRAPPER_ASSIGNMENTS)
def request(method, url, **kwargs):  # type: (...) -> Response
    with Session() as s:
        return s.request(method=method, url=url, **kwargs)


@wraps(requests.get, assigned=WRAPPER_ASSIGNMENTS)
def get(url, params=None, **kwargs):  # type: (...) -> Response
    kwargs.setdefault('allow_redirects', True)
    return request('get', url, params=params, **kwargs)


@wraps(requests.options, assigned=WRAPPER_ASSIGNMENTS)
def options(url, **kwargs):  # type: (...) -> Response
    kwargs.setdefault('allow_redirects', True)
    return request('options', url, **kwargs)


@wraps(requests.head, assigned=WRAPPER_ASSIGNMENTS)
def head(url, **kwargs):  # type: (...) -> Response
    kwargs.setdefault('allow_redirects', False)
    return request('head', url, **kwargs)


@wraps(requests.post, assigned=WRAPPER_ASSIGNMENTS)
def post(url, data=None, json=None, **kwargs):  # type: (...) -> Response
    return request('post', url, data=data, json=json, **kwargs)


@wraps(requests.put, assigned=WRAPPER_ASSIGNMENTS)
def put(url, data=None, **kwargs):  # type: (...) -> Response
    return request('put', url, data=data, **kwargs)


@wraps(requests.patch, assigned=WRAPPER_ASSIGNMENTS)
def patch(url, data=None, **kwargs):  # type: (...) -> Response
    return request('patch', url, data=data, **kwargs)


@wraps(requests.delete, assigned=WRAPPER_ASSIGNMENTS)
def delete(url, **kwargs):  # type: (...) -> Response
    return request('delete', url, **kwargs)


@wraps(requests.session, assigned=WRAPPER_ASSIGNMENTS)
def session():  # type: (...) -> Session
    return Session()


# noinspection PyUnusedLocal
def cache_cleanup(max_age=None):
    warnings.warn("No longer Needed", DeprecationWarning)


# noinspection PyUnusedLocal
def auto_cache_cleanup(max_age=None):
    warnings.warn("No longer Needed", DeprecationWarning)
    return True
