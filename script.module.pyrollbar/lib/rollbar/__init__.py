from __future__ import absolute_import, annotations
from __future__ import unicode_literals

import copy
import functools
import inspect
import json
import logging
import os
import socket
import sys
import threading
import time
import traceback
import types
import uuid
import wsgiref.util
import warnings
import queue
from typing import Any, Callable, TypedDict, Literal, cast, Optional, TYPE_CHECKING
from urllib.parse import parse_qs, urljoin

try:
    # Python 3.11+
    # This is ignored for mypy to be happy with Python versions before 3.11.
    from typing import Unpack  # type: ignore
except ImportError:
    # Python 3.10
    from typing_extensions import Unpack

import requests  # type: ignore[import-untyped]

from rollbar.lib import events, filters, dict_merge, transport, defaultJSONEncode
from rollbar.lib.session import get_current_session, set_current_session, parse_session_request_baggage_headers

if TYPE_CHECKING:
    from rollbar.lib.payload import Attribute
    from rollbar.lib.type_info import KeyType

__version__ = '1.4.0'
__log_name__ = 'rollbar'

from rollbar.lib.transform import Transform

log = logging.getLogger(__log_name__)


# import request objects from various frameworks, if available
try:
    from webob import BaseRequest as WebobBaseRequest  # type: ignore[import-untyped]
except ImportError:
    WebobBaseRequest = None

try:
    from django.core.exceptions import ImproperlyConfigured
except ImportError:
    DjangoHttpRequest = None
    RestFrameworkRequest = None

else:
    try:
        from django.http import HttpRequest as DjangoHttpRequest # type: ignore[assignment]
    except (ImportError, ImproperlyConfigured):
        DjangoHttpRequest = None  # type: ignore[assignment, misc] # MyPy does not like types assigned to None.

    try:
        from rest_framework.request import Request as RestFrameworkRequest  # type: ignore[assignment, no-redef]
    except (ImportError, ImproperlyConfigured):
        RestFrameworkRequest = None  # type: ignore[assignment, misc] # MyPy does not like types assigned to None.

    del ImproperlyConfigured

try:
    from werkzeug.wrappers import Request as WerkzeugRequest
except (ImportError, SyntaxError):
    WerkzeugRequest = None  # type: ignore[assignment, misc] # MyPy does not like types assigned to None.

try:
    from werkzeug.local import LocalProxy as WerkzeugLocalProxy
except (ImportError, SyntaxError):
    WerkzeugLocalProxy = None  # type: ignore[assignment, misc] # MyPy does not like types assigned to None.

try:
    from tornado.httpserver import HTTPRequest as TornadoRequest  # type: ignore[import-untyped]
except ImportError:
    TornadoRequest = None  # type: ignore[assignment, misc] # MyPy does not like types assigned to None.

try:
    from bottle import BaseRequest as BottleRequest  # type: ignore[import-untyped]
except ImportError:
    BottleRequest = None  # type: ignore[assignment, misc] # MyPy does not like types assigned to None.

try:
    from sanic.request import Request as SanicRequest
except ImportError:
    SanicRequest = None  # type: ignore[assignment, misc] # MyPy does not like types assigned to None.

try:
    from google.appengine.api.urlfetch import fetch as AppEngineFetch  # type: ignore[import-untyped, import-not-found]
except (ImportError, KeyError):
    AppEngineFetch = None  # type: ignore[assignment, misc] # MyPy does not like types assigned to None.

try:
    from starlette.requests import Request as StarletteRequest, State as StarletteState
except ImportError:
    StarletteRequest = None  # type: ignore[assignment, misc] # MyPy does not like types assigned to None.
    StarletteState = None  # type: ignore[assignment, misc] # MyPy does not like types assigned to None.

try:
    from fastapi.requests import Request as FastAPIRequest
except ImportError:
    FastAPIRequest = None  # type: ignore[assignment, misc] # MyPy does not like types assigned to None.

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment, misc] # MyPy does not like types assigned to None.

AsyncHTTPClient = httpx

def passthrough_decorator(func):
    def wrap(*args, **kwargs):
        return func(*args, **kwargs)
    return wrap

try:
    from tornado.httpclient import AsyncHTTPClient as TornadoAsyncHTTPClient
except ImportError:
    TornadoAsyncHTTPClient = None  # type: ignore[assignment, misc] # MyPy does not like types assigned to None.

try:
    import treq  # type: ignore[import-not-found]
    from twisted.python import log as twisted_log
    from twisted.web.iweb import IPolicyForHTTPS
    from twisted.web.client import BrowserLikePolicyForHTTPS, Agent
    from twisted.internet.ssl import CertificateOptions
    from twisted.internet import task, defer, ssl, reactor
    from zope.interface import implementer  # type: ignore[import-untyped]

    @implementer(IPolicyForHTTPS)
    class VerifyHTTPS(object):
        def __init__(self):
            # by default, handle requests like a browser would
            self.default_policy = BrowserLikePolicyForHTTPS()

        def creatorForNetloc(self, hostname, port):
            # check if the hostname is in the the whitelist, otherwise return the default policy
            if not SETTINGS['verify_https']:
                return ssl.CertificateOptions(verify=False)
            return self.default_policy.creatorForNetloc(hostname, port)

    def log_handler(event):
        """
        Default uncaught error handler
        """
        try:
            if not event.get('isError') or 'failure' not in event:
                return

            err = event['failure']

            # Don't report Rollbar internal errors to ourselves
            if issubclass(err.type, ApiException):
                log.error('Rollbar internal error: %s', err.value)
            else:
                report_exc_info((err.type, err.value, err.getTracebackObject()))
        except:
            log.exception('Error while reporting to Rollbar')

    # Add Rollbar as a log handler which will report uncaught errors
    twisted_log.addObserver(log_handler)


except ImportError:
    treq = None

try:
    from falcon import Request as FalconRequest  # type: ignore[import-not-found]
except ImportError:
    FalconRequest = None


def get_request():
    """
    Get the current request object. Implementation varies on
    library support. Modified below when we know which framework
    is being used.
    """

    # TODO(cory): add in a generic _get_locals_request() which
    # will iterate up through the call stack and look for a variable
    # that appears to be valid request object.
    for fn in (_get_fastapi_request,
               _get_starlette_request,
               _get_bottle_request,
               _get_flask_request,
               _get_pyramid_request,
               _get_pylons_request):
        try:
            req = fn()
            if req is not None:
                return req
        except:
            pass

    return None


def _get_bottle_request():
    if BottleRequest is None:
        return None
    from bottle import request
    return request


def _get_flask_request():
    if WerkzeugRequest is None:
        return None
    from flask import request
    return request


def _get_pyramid_request():
    if WebobBaseRequest is None:
        return None
    from pyramid.threadlocal import get_current_request  # type: ignore[import-untyped]
    return get_current_request()


def _get_pylons_request():
    if WebobBaseRequest is None:
        return None
    from pylons import request  # type: ignore[import-not-found]
    return request


def _get_starlette_request():
    # Do not modify the returned object

    if StarletteRequest is None:
        return None

    from rollbar.contrib.starlette import get_current_request
    return get_current_request()


def _get_fastapi_request():
    # Do not modify the returned object

    if FastAPIRequest is None:
        return None

    from rollbar.contrib.fastapi import get_current_request
    return get_current_request()


BASE_DATA_HOOK: Callable[[Any, dict[str, Any]], None] | None = None

agent_log: logging.Logger | None = None

VERSION: str = __version__
DEFAULT_ENDPOINT: str = 'https://api.rollbar.com/api/1/'
DEFAULT_TIMEOUT: int = 3
ANONYMIZE = 'anonymize'

DEFAULT_LOCALS_SIZES = {
    'maxlevel': 5,
    'maxdict': 10,
    'maxlist': 10,
    'maxtuple': 10,
    'maxset': 10,
    'maxfrozenset': 10,
    'maxdeque': 10,
    'maxarray': 10,
    'maxstring': 100,
    'maxlong': 40,
    'maxother': 100,
}

Level = Literal['debug', 'info', 'warning', 'error', 'critical']
IgnorableLevel = Level | Literal['ignored']


class NotifierSettings(TypedDict, total=False):
    name: str
    version: str


class LocalsSettings(TypedDict, total=False):
    enabled: bool
    safe_repr: bool
    scrub_varargs: bool
    sizes: dict[str, int]
    safelisted_types: list[type]
    whitelisted_types: list[type]  # deprecated, use safelisted_types instead


class SettingsParams(TypedDict, total=False):
    enabled: bool
    # List of tuples in the form (class, level) where class is an Exception class you want to always filter to the
    # respective level. Any subclasses of the given class will also be matched.
    # If class is a string, it will be lazy-evaluated to find the class by that name.
    exception_level_filters: list[tuple[type | str, IgnorableLevel]]
    root: str | None
    host: str | None
    branch: str | None
    code_version: str | None
    handler: Literal['default', 'blocking', 'thread', 'async', 'agent', 'tornado', 'gae', 'twisted', 'httpx', 'thread_pool']
    thread_pool_workers: int | None
    endpoint: str
    timeout: int
    agent_log_file: str
    notifier: NotifierSettings
    allow_logging_basic_config: bool
    locals: LocalsSettings
    verify_https: bool
    shortener_keys: list[tuple[str, ...]]
    suppress_reinit_warning: bool
    capture_email: bool
    capture_username: bool
    capture_ip: bool | Literal['anonymize']
    log_all_rate_limited_items: bool
    log_payload_on_error: bool
    http_proxy: str | None
    http_proxy_user: str | None
    http_proxy_password: str | None
    include_request_body: bool
    request_pool_connections: int | None
    request_pool_maxsize: int | None
    request_max_retries: int | None
    batch_transforms: bool
    custom_transforms: list[Transform]


# Deprecated, will be removed in version 2.0.0
SettingsIrregular = TypedDict('SettingsIrregular', {
    'agent.log_file': Optional[str],
})


class Settings(TypedDict, SettingsParams, SettingsIrregular):
    access_token: str | None
    environment: str
    scrub_fields: list[str]
    url_fields: list[str]


# configuration settings
# configure by calling init() or overriding directly
SETTINGS: Settings = {
    'access_token': None,
    'enabled': True,
    'environment': 'production',
    'exception_level_filters': [],
    'root': None,  # root path to your code
    'host': None,  # custom hostname of the current host
    'branch': None,  # git branch name
    'code_version': None,
    # 'blocking', 'thread' (default), 'async', 'agent', 'tornado', 'gae', 'twisted', 'httpx' or 'thread_pool'
    # 'async' requires Python 3.4 or higher.
    # 'httpx' requires Python 3.7 or higher.
    # 'thread_pool' requires Python 3.2 or higher.
    'handler': 'default',
    'thread_pool_workers': None,
    'endpoint': DEFAULT_ENDPOINT,
    'timeout': DEFAULT_TIMEOUT,
    # Deprecated, use 'agent_log_file' instead. Will be removed in version 2.0.0
    'agent.log_file': None,
    'agent_log_file': 'log.rollbar',
    'scrub_fields': [
        'pw',
        'passwd',
        'password',
        'secret',
        'confirm_password',
        'confirmPassword',
        'password_confirmation',
        'passwordConfirmation',
        'access_token',
        'accessToken',
        'auth',
        'authentication',
        'authorization',
    ],
    'url_fields': ['url', 'link', 'href'],
    'notifier': {
        'name': 'pyrollbar',
        'version': VERSION
    },
    'allow_logging_basic_config': True,  # set to False to avoid a call to logging.basicConfig()
    'locals': {
        'enabled': True,
        'safe_repr': True,
        'scrub_varargs': True,
        'sizes': DEFAULT_LOCALS_SIZES,
        'safelisted_types': [],
        'whitelisted_types': []
    },
    'verify_https': True,
    'shortener_keys': [],
    'suppress_reinit_warning': False,
    'capture_email': False,
    'capture_username': False,
    'capture_ip': True,
    'log_all_rate_limited_items': True,
    'log_payload_on_error': True,
    'http_proxy': None,
    'http_proxy_user': None,
    'http_proxy_password': None,
    'include_request_body': False,
    'request_pool_connections': None,
    'request_pool_maxsize': None,
    'request_max_retries': None,
    'batch_transforms': False,
    'custom_transforms': [],
}

_CURRENT_LAMBDA_CONTEXT = None
_LAST_RESPONSE_STATUS = None

# Set in init()
_transforms: list[Transform] = []
_serialize_transform: Transform | None = None
_scrub_redact_transform: Transform | None = None
_threads: queue.Queue

_initialized = False

from rollbar.lib.transforms.scrub_redact import REDACT_REF

from rollbar.lib import transforms
from rollbar.lib import type_info
from rollbar.lib.transforms.scrub import ScrubTransform
from rollbar.lib.transforms.scruburl import ScrubUrlTransform
from rollbar.lib.transforms.scrub_redact import ScrubRedactTransform
from rollbar.lib.transforms.serializable import SerializableTransform
from rollbar.lib.transforms.shortener import ShortenerTransform
from rollbar.lib.transforms.batched import BatchedTransform


## public api

def init(
    access_token: str,
    environment: str = 'production',
    scrub_fields: list[str] | None = None,
    url_fields: list[str] | None = None,
    **kw: Unpack[SettingsParams],
) -> None:
    """
    Saves configuration variables in this module's SETTINGS.

    :param access_token: Project access token.
    :param environment: Environment name. Any string up to 255 chars is OK. For best results, use production for your
                        production environment.
    :param scrub_fields: List of sensitive field names to scrub out of request params and locals. Values will be
                         replaced with asterisks. If overriding, make sure to list all fields you want to scrub, not
                         just fields you want to add to the default. Param names are converted to lowercase before
                         comparing against the scrub list.
    :param url_fields: List of fields treated as URLs to be parsed and scrubbed.
    :param agent_log_file: If using the 'agent' handler, the path to the log file to write to. Filename must end with
                           `.rollbar`, Defaults to `log.rollbar`.
    :param allow_logging_basic_config: When `True`, `logging.basicConfig()` will be called to set up the logging system.
                                       Set to `False` to skip this call. If using Flask, you'll want to set to False. If
                                       using Pyramid or Django, `True` should be fine.
    :param batch_transforms: If `True`, enables batching of transforms for improved performance. Default: `False`.
    :param branch: Name of the checked-out branch.
    :param capture_ip: If equal to `True`, we will attempt to capture the full client IP address from a request. If
                       equal to the string `anonymize`, we will capture the client IP address, but then semi-anonymize
                       it  by masking out the least significant bits. If equal to False, we will not capture the client
                       IP address from a request. Default: `True`.
    :param capture_email: If set to `True`, we will attempt to enrich person data with an email address if available.
    :param capture_username: If set to `True`, we will attempt to enrich person data with a username if available.
    :param code_version: A string describing the current code revision/version (i.e. a git sha). Max 40 characters.
    :param custom_transforms: A list of custom Transform instances to apply to payloads.
    :param enabled: Whether Rollbar error reporting is enabled.
    :param endpoint: URL items are posted to. Default: `https://api.rollbar.com/api/1/`.
    :param exception_level_filters: List of tuples in the form (class, level) where class is an Exception class you want
                                    to always filter to the respective level. Any subclasses of the given class will
                                    also be matched. If class is a string, it will be lazy-evaluated to find the class
                                    by that name.
    :param handler: The method for reporting rollbar items to api.rollbar.com. Default: `default`.
    :param host: Custom hostname of the current host. If not set, will use the system hostname.
    :param http_proxy: The HTTP proxy host and optional port e.g. `myhttpproxy.com:5000`. This should not include the
                       URL scheme. If set all reports to the Rollbar service will be sent through the proxy.
    :param http_proxy_user: The basic auth user to use with the HTTP proxy.
    :param http_proxy_password: The basic auth password to use with the HTTP proxy. Basic auth will only work if both
                                `http_proxy_user` and `http_proxy_password` are present.
    :param include_request_body: Set to `True` to add the raw HTTP request body to the error report. Currently, works
                                 with Django, Starlette, and FastAPI. Default: `False`.
    :param locals: Configuration for collecting local variables.
    :param log_all_rate_limited_items: Rollbar will log a warning if you have crossed your limit for logged items.
    :param request_pool_connections: If not `None`, used by requests to set the number of `urllib3` connection pools to
                                     cache. Default: `None`.
    :param request_pool_maxsize: If not `None`, used by requests to set the maximum number of connections to save in the
                                 pool. Default: `None`.
    :param request_max_retries: If not `None`, used by requests to set the maximum number of retries each connection
                                should attempt. Default: `None`.
    :param root: Absolute path to the root of your application, not including the final /.
    :param shortener_keys: A list of key prefixes (as tuple) to apply our shortener transform to. Added to built-in
                           list.
    :param suppress_reinit_warning: If `True`, suppresses the warning normally shown when `rollbar.init()` is called
                                    multiple times.
    :param timeout: Timeout for any HTTP requests made to the Rollbar API (in seconds).
    :param verify_https: If `True`, network requests will fail unless encountering a valid certificate. Default `True`.
    """
    global SETTINGS, agent_log, _initialized, _transforms, _serialize_transform, _scrub_redact_transform, _threads

    if scrub_fields is not None:
       SETTINGS['scrub_fields'] = list(scrub_fields)
    if url_fields is not None:
       SETTINGS['url_fields'] = list(url_fields)

    # Merge the extra config settings into SETTINGS
    # Both cast() and dict() are needed to satisfy MyPy
    SETTINGS = cast(Settings, dict_merge(dict(SETTINGS), dict(kw)))
    if _initialized:
        # NOTE: Temp solution to not being able to re-init.
        # New versions of pyrollbar will support re-initialization
        # via the (not-yet-implemented) configure() method.
        if not SETTINGS.get('suppress_reinit_warning'):
            log.warning('Rollbar already initialized. Ignoring re-init.')
        return

    SETTINGS['access_token'] = access_token
    SETTINGS['environment'] = environment
    _configure_transport(**SETTINGS)

    if SETTINGS.get('allow_logging_basic_config'):
        logging.basicConfig()

    if SETTINGS.get('handler') == 'agent':
        agent_log = _create_agent_log()
    elif SETTINGS.get('handler') == 'thread_pool':
        from rollbar.lib.thread_pool import init_pool
        init_pool(SETTINGS.get('thread_pool_workers', None))

    if not SETTINGS['locals']['safelisted_types'] and SETTINGS['locals']['whitelisted_types']:
        warnings.warn('whitelisted_types deprecated use safelisted_types instead', DeprecationWarning)
        SETTINGS['locals']['safelisted_types'] = SETTINGS['locals']['whitelisted_types']

    # We will perform these transforms in order:
    # 1. Serialize the payload to be all python built-in objects
    # 2. Scrub the payloads based on the key suffixes in SETTINGS['scrub_fields']
    # 3. Scrub URLs in the payload for keys that end with 'url'
    # 4. Optional - If local variable gathering is enabled, transform the
    #       trace frame values using the ShortReprTransform.
    _serialize_transform = SerializableTransform(safe_repr=SETTINGS['locals']['safe_repr'],
                                                 safelist_types=SETTINGS['locals']['safelisted_types'])

    _scrub_redact_transform = ScrubRedactTransform(suffixes=[(field,) for field in SETTINGS['scrub_fields']], redact_char='*')

    # A list of key prefixes to apply our shortener transform to. The request
    # being included in the body key is old behavior and is being retained for
    # backwards compatibility.
    shortener_keys: list[tuple[str, ...]] = [
        ('request', 'POST'),
        ('request', 'json'),
        ('body', 'request', 'POST'),
        ('body', 'request', 'json'),
    ]

    if SETTINGS['locals']['enabled']:
        for prefix in (('body', 'trace'), ('body', 'trace_chain', '*')):
            shortener_keys.append(prefix + ('frames', '*', 'code'))
            shortener_keys.append(prefix + ('frames', '*', 'args', '*'))
            shortener_keys.append(prefix + ('frames', '*', 'kwargs', '*'))
            shortener_keys.append(prefix + ('frames', '*', 'locals', '*'))

    shortener_keys.extend(SETTINGS['shortener_keys'])

    shortener = ShortenerTransform(safe_repr=SETTINGS['locals']['safe_repr'],
                                   keys=shortener_keys,
                                   **SETTINGS['locals']['sizes'])
    _transforms = [
        shortener,  # priority: 10
        _scrub_redact_transform,  # priority: 20
        _serialize_transform,  # priority: 30
        ScrubUrlTransform(suffixes=[(field,) for field in SETTINGS['url_fields']],
                          params_to_scrub=SETTINGS['scrub_fields'])  # priority: 50
    ]

    # Add custom transforms
    if len(SETTINGS['custom_transforms']) > 0:
        _transforms.extend(SETTINGS['custom_transforms'])

    # Sort the transforms by priority
    _transforms = sorted(_transforms, key=lambda x: x.priority)

    _threads = queue.Queue()
    events.reset()
    filters.add_builtin_filters(SETTINGS)

    _initialized = True


def _configure_transport(**kw):
    configuration = _requests_configuration(**kw)
    transport.configure_pool(**configuration)


def _requests_configuration(**kw):
    keys = {
        'request_pool_connections': 'pool_connections',
        'request_pool_maxsize': 'pool_maxsize',
        'request_max_retries': 'max_retries',
    }
    return {keys[k]: kw.get(k, None) for k in keys}


def lambda_function(f):
    """
    Decorator for making error handling on AWS Lambda easier
    """
    @functools.wraps(f)
    def wrapper(event, context):
        global _CURRENT_LAMBDA_CONTEXT
        _CURRENT_LAMBDA_CONTEXT = context
        try:
            result = f(event, context)
            return wait(lambda: result)
        except:
            cls, exc, trace = sys.exc_info()
            report_exc_info((cls, exc, trace.tb_next))
            wait()
            raise
    return wrapper


def report_exc_info(
        exc_info: tuple[type[BaseException], BaseException, types.TracebackType | None] | tuple[
            None, None, None] | None = None,
        request=None, extra_data=None, payload_data=None, level=None, **kw):
    """
    Reports an exception to Rollbar, using exc_info (from calling sys.exc_info())

    exc_info: optional, should be the result of calling sys.exc_info(). If omitted, sys.exc_info() will be called here.
    request: optional, a WebOb, Werkzeug-based or Sanic request object.
    extra_data: optional, will be included in the 'custom' section of the payload
    payload_data: optional, dict that will override values in the final payload
                  (e.g. 'level' or 'fingerprint')
    kw: provided for legacy purposes; unused.

    Example usage:

    rollbar.init(access_token='YOUR_PROJECT_ACCESS_TOKEN')
    try:
        do_something()
    except:
        rollbar.report_exc_info(sys.exc_info(), request, {'foo': 'bar'}, {'level': 'warning'})
    """
    if exc_info is None:
        exc_info = sys.exc_info()

    try:
        return _report_exc_info(exc_info, request, extra_data, payload_data, level=level)
    except Exception as e:
        log.exception("Exception while reporting exc_info to Rollbar. %r", e)


def report_message(message: str, level: Level = 'error', request=None, extra_data=None, payload_data=None):
    """
    Reports an arbitrary string message to Rollbar.

    message: the string body of the message
    level: level to report at. One of: 'critical', 'error', 'warning', 'info', 'debug'
    request: the request object for the context of the message
    extra_data: optional, will be included in the 'custom' section of the payload
    payload_data: param names to pass in the 'data' level of the payload; overrides defaults.
    """
    try:
        return _report_message(message, level, request, extra_data, payload_data)
    except Exception as e:
        log.exception("Exception while reporting message to Rollbar. %r", e)


def send_payload(payload, access_token: str):
    """
    Sends a payload object, (the result of calling _build_payload() + _serialize_payload()).
    Uses the configured handler from SETTINGS['handler']

    Available handlers:
    - 'blocking': calls _send_payload() (which makes an HTTP request) immediately, blocks on it
    - 'thread': starts a single-use thread that will call _send_payload(). returns immediately.
    - 'async': calls _send_payload_async() (which makes an async HTTP request using default async handler)
    - 'agent': writes to a log file to be processed by rollbar-agent
    - 'tornado': calls _send_payload_tornado() (which makes an async HTTP request using tornado's AsyncHTTPClient)
    - 'gae': calls _send_payload_appengine() (which makes a blocking call to Google App Engine)
    - 'twisted': calls _send_payload_twisted() (which makes an async HTTP request using Twisted and Treq)
    - 'httpx': calls _send_payload_httpx() (which makes an async HTTP request using HTTPX)
    - 'thread_pool': uses a pool of worker threads to make HTTP requests off the main thread. Returns immediately.
    """
    payload = events.on_payload(payload)
    if payload is False:
        return

    if sys.version_info >= (3, 6):
        from rollbar.lib._async import get_current_handler
        handler = get_current_handler()
    else:
        handler = SETTINGS.get('handler')

    if handler == 'twisted':
        payload['data']['framework'] = 'twisted'

    payload_str = _serialize_payload(payload)
    if handler == 'blocking':
        _send_payload(payload_str, access_token)
    elif handler == 'agent':
        if agent_log is None:
            log.error('Rollbar agent log not initialized')
            return
        agent_log.error(payload_str)
    elif handler == 'tornado':
        if TornadoAsyncHTTPClient is None:
            log.error('Unable to find tornado')
            return
        _send_payload_tornado(payload_str, access_token)
    elif handler == 'gae':
        if AppEngineFetch is None:
            log.error('Unable to find AppEngine URLFetch module')
            return
        _send_payload_appengine(payload_str, access_token)
    elif handler == 'twisted':
        if treq is None:
            log.error('Unable to find Treq')
            return
        _send_payload_twisted(payload_str, access_token)
    elif handler == 'httpx':
        if httpx is None:
            log.error('Unable to find HTTPX')
            return
        _send_payload_httpx(payload_str, access_token)
    elif handler == 'async':
        if AsyncHTTPClient is None:
            log.error('Unable to find async handler')
            return
        _send_payload_async(payload_str, access_token)
    elif handler == 'thread':
        _send_payload_thread(payload_str, access_token)
    elif handler == 'thread_pool':
        _send_payload_thread_pool(payload_str, access_token)
    else:
        # default to 'thread'
        _send_payload_thread(payload_str, access_token)


def search_items(title, return_fields=None, access_token=None, endpoint=None, **search_fields):
    """
    Searches a project for items that match the input criteria.

    title: all or part of the item's title to search for.
    return_fields: the fields that should be returned for each item.
            e.g. ['id', 'project_id', 'status'] will return a dict containing
                 only those fields for each item.
    access_token: a project access token. If this is not provided,
                  the one provided to init() will be used instead.
    search_fields: additional fields to include in the search.
            currently supported: status, level, environment
    """
    if not title:
        return []

    if return_fields is not None:
        return_fields = ','.join(return_fields)

    return _get_api('search/',
                    title=title,
                    fields=return_fields,
                    access_token=access_token,
                    endpoint=endpoint,
                    **search_fields)


def wait(f=None):
    _threads.join()
    if f is not None:
        return f()


class ApiException(Exception):
    """
    This exception will be raised if there was a problem decoding the
    response from an API call.
    """
    pass


class ApiError(ApiException):
    """
    This exception will be raised if the API response contains an 'err'
    field, denoting there was a problem fulfilling the api request.
    """
    pass


class Result(object):
    """
    This class encapsulates the response from an API call.
    Usage:

        result = search_items(title='foo', fields=['id'])
        print result.data
    """

    def __init__(self, access_token, path, params, data):
        self.access_token = access_token
        self.path = path
        self.params = params
        self.data = data

    def __str__(self):
        return str(self.data)


class PagedResult(Result):
    """
    This class wraps the response from an API call that responded with
    a page of results.
    Usage:

        result = search_items(title='foo', fields=['id'])
        print 'First page: %d, data: %s' % (result.page, result.data)
        result = result.next_page()
        print 'Second page: %d, data: %s' % (result.page, result.data)
    """
    def __init__(self, access_token, path, page_num, params, data, endpoint=None):
        super(PagedResult, self).__init__(access_token, path, params, data)
        self.page = page_num
        self.endpoint = endpoint

    def next_page(self):
        params = copy.copy(self.params)
        params['page'] = self.page + 1
        return _get_api(self.path, endpoint=self.endpoint, **params)

    def prev_page(self):
        if self.page <= 1:
            return self
        params = copy.copy(self.params)
        params['page'] = self.page - 1
        return _get_api(self.path, endpoint=self.endpoint, **params)


## internal functions


def _resolve_exception_class(idx, filter):
    cls, level = filter
    if isinstance(cls, str):
        # Lazily resolve class name
        parts = cls.split('.')
        module = '.'.join(parts[:-1])
        if module in sys.modules and hasattr(sys.modules[module], parts[-1]):
            cls = getattr(sys.modules[module], parts[-1])
            SETTINGS['exception_level_filters'][idx] = (cls, level)
        else:
            cls = None
    return cls, level


def _filtered_level(exception: BaseException):
    for i, filter in enumerate(SETTINGS['exception_level_filters']):
        cls, level = _resolve_exception_class(i, filter)
        if cls and isinstance(exception, cls):
            return level

    return None


def _is_ignored(exception):
    return _filtered_level(exception) == 'ignored'


def _create_agent_log():
    """
    Creates .rollbar log file for use with rollbar-agent
    """
    log_file = SETTINGS['agent_log_file']
    legacy_log_file = SETTINGS.get('agent.log_file')
    if isinstance(legacy_log_file, str) and legacy_log_file:
        log_file = legacy_log_file
    if not log_file.endswith('.rollbar'):
        log.error("Provided agent log file does not end with .rollbar, which it must. "
                  "Using default instead.")
        log_file = 'log.rollbar'

    retval = logging.getLogger('rollbar_agent')
    handler = logging.FileHandler(log_file, 'a', 'utf-8')
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    retval.addHandler(handler)
    retval.setLevel(logging.WARNING)
    return retval


def _report_exc_info(exc_info, request, extra_data, payload_data, level=None):
    """
    Called by report_exc_info() wrapper
    """

    if not _check_config():
        return

    filtered_level = _filtered_level(exc_info[1])
    if level is None:
        level = filtered_level

    filtered_exc_info = events.on_exception_info(exc_info,
                                                 request=request,
                                                 extra_data=extra_data,
                                                 payload_data=payload_data,
                                                 level=level)

    if filtered_exc_info is False:
        return

    cls, exc, trace = filtered_exc_info

    data = _build_base_data(request)
    if level is not None:
        data['level'] = level

    # walk the trace chain to collect cause and context exceptions
    trace_chain = _walk_trace_chain(cls, exc, trace)

    extra_trace_data = None
    if len(trace_chain) > 1:
        data['body'] = {
            'trace_chain': trace_chain
        }
        if payload_data and ('body' in payload_data) and ('trace' in payload_data['body']):
            extra_trace_data = payload_data['body']['trace']
            del payload_data['body']['trace']
    else:
        data['body'] = {
            'trace': trace_chain[0]
        }

    if extra_data:
        extra_data = extra_data
        if not isinstance(extra_data, dict):
            extra_data = {'value': extra_data}
        if extra_trace_data:
            extra_data = dict_merge(extra_data, extra_trace_data, silence_errors=True)
        data['custom'] = extra_data
    if extra_trace_data and not extra_data:
        data['custom'] = extra_trace_data

    request = _get_actual_request(request)
    _add_request_data(data, request)
    _add_person_data(data, request)
    _add_lambda_context_data(data)
    _add_session_data(data)
    data['server'] = _build_server_data()

    if payload_data:
        data = dict_merge(data, payload_data, silence_errors=True)

    payload = _build_payload(data)
    send_payload(payload, payload.get('access_token'))

    return data['uuid']


def _walk_trace_chain(cls, exc, trace):
    trace_chain = [_trace_data(cls, exc, trace)]

    seen_exceptions = {exc}

    while True:
        exc = getattr(exc, '__cause__', None) or getattr(exc, '__context__', None)
        if not exc:
            break
        trace_chain.append(_trace_data(type(exc), exc, getattr(exc, '__traceback__', None)))
        if exc in seen_exceptions:
            break
        seen_exceptions.add(exc)

    return trace_chain


def _trace_data(cls, exc, trace):
    # exception info
    # most recent call last
    raw_frames = traceback.extract_tb(trace)
    frames = [{'filename': f[0], 'lineno': f[1], 'method': f[2], 'code': f[3]} for f in raw_frames]

    trace_data = {
        'frames': frames,
        'exception': {
            'class': getattr(cls, '__name__', cls.__class__.__name__),
            'message': str(exc),
        }
    }

    _add_locals_data(trace_data, (cls, exc, trace))

    return trace_data


def _report_message(message, level, request, extra_data, payload_data):
    """
    Called by report_message() wrapper
    """
    if not _check_config():
        return

    filtered_message = events.on_message(message,
                                         request=request,
                                         extra_data=extra_data,
                                         payload_data=payload_data,
                                         level=level)

    if filtered_message is False:
        return

    data = _build_base_data(request, level=level)

    # message
    data['body'] = {
        'message': {
            'body': filtered_message
        }
    }

    if extra_data:
        extra_data = extra_data
        data['body']['message'].update(extra_data)
        data['custom'] = extra_data

    request = _get_actual_request(request)
    _add_request_data(data, request)
    _add_person_data(data, request)
    _add_lambda_context_data(data)
    _add_session_data(data)
    data['server'] = _build_server_data()

    if payload_data:
        data = dict_merge(data, payload_data, silence_errors=True)

    payload = _build_payload(data)
    send_payload(payload, payload.get('access_token'))

    return data['uuid']


def _add_session_data(data: dict) -> None:
    """
    Adds session data to the payload data if it can be found in the current session or request.
    """
    session_data = get_current_session()
    if session_data:
        _add_session_attributes(data, session_data)
        return

    request = _session_data_from_request(data)
    if request is None:
        return
    session_data = parse_session_request_baggage_headers(request.get('headers', {}))

    if session_data:
        _add_session_attributes(data, session_data)


def _add_session_attributes(data: dict, session_data: list[Attribute]) -> None:
    """
    Adds session attributes to the payload data. This function is careful to not overwrite any existing data in the
    payload.
    """
    if 'attributes' not in data:
        data['attributes'] = session_data
        return

    existing_keys = {a['key'] for a in data['attributes']}

    for attribute in session_data:
        if attribute['key'] not in existing_keys:
            data['attributes'].append(attribute)


def _session_data_from_request(data: dict) -> dict | None:
    """
    Tries to find session data in the request object. Use the request object if provided, otherwise check the data as
    it may already contain the request object. This is true for some frameworks (e.g. Django).
    """
    if data is not None and 'request' in data:
        return data.get('request', None)
    return _get_actual_request(_build_request_data(get_request()))


def _check_config():
    if not SETTINGS.get('enabled'):
        log.info("pyrollbar: Not reporting because rollbar is disabled.")
        return False

    # skip access token check for the agent handler
    if SETTINGS.get('handler') == 'agent':
        return True

    # make sure we have an access_token
    if not SETTINGS.get('access_token'):
        log.warning("pyrollbar: No access_token provided. Please configure by calling rollbar.init() with your access token.")
        return False

    return True


def _build_base_data(request, level='error') -> dict[str, Any]:
    data = {
        'timestamp': int(time.time()),
        'environment': SETTINGS['environment'],
        'level': level,
        'language': 'python %s' % '.'.join(str(x) for x in sys.version_info[:3]),
        'notifier': SETTINGS['notifier'],
        'uuid': str(uuid.uuid4()),
    }

    if SETTINGS.get('code_version'):
        data['code_version'] = SETTINGS['code_version']

    if BASE_DATA_HOOK is not None:
        BASE_DATA_HOOK(request, data)

    return data


def _add_person_data(data, request):
    try:
        person_data = _build_person_data(request)
    except Exception as e:
        log.exception("Exception while building person data for Rollbar payload: %r", e)
    else:
        if person_data:
            if not SETTINGS['capture_username'] and 'username' in person_data:
                person_data['username'] = None
            if not SETTINGS['capture_email'] and 'email' in person_data:
                person_data['email'] = None
            data['person'] = person_data


def _build_person_data(request):
    """
    Returns a dictionary describing the logged-in user using data from `request`.

    Try request.rollbar_person first, then 'user', then 'user_id'
    """
    if hasattr(request, 'rollbar_person'):
        rollbar_person_prop = request.rollbar_person
        person = rollbar_person_prop() if callable(rollbar_person_prop) else rollbar_person_prop
        if person and isinstance(person, dict):
            return person
        else:
            return None

    if StarletteRequest is not None:
        from rollbar.contrib.starlette.requests import hasuser
    else:
        def hasuser(request: StarletteRequest[StarletteState]) -> bool:
            return True

    if hasuser(request) and hasattr(request, 'user'):
        user_prop = request.user
        user = user_prop() if callable(user_prop) else user_prop
        if not user:
            return None
        elif isinstance(user, dict):
            return user
        else:
            retval = {}
            if getattr(user, 'id', None):
                retval['id'] = str(user.id)
            elif getattr(user, 'user_id', None):
                retval['id'] = str(user.user_id)

            # id is required, so only include username/email if we have an id
            if retval.get('id'):
                username = getattr(user, 'username', None)
                email = getattr(user, 'email', None)
                retval.update({
                    'username': username,
                    'email': email
                })
            return retval

    if hasattr(request, 'user_id'):
        user_id_prop = request.user_id
        user_id = user_id_prop() if callable(user_id_prop) else user_id_prop
        if not user_id:
            return None
        return {'id': str(user_id)}


def _get_func_from_frame(frame):
    func_name = inspect.getframeinfo(frame).function
    caller = frame.f_back
    if caller:
        func = caller.f_locals.get(func_name,
                                   caller.f_globals.get(func_name))
    else:
        func = None

    return func


def _add_locals_data(trace_data, exc_info) -> None:
    if not SETTINGS['locals']['enabled']:
        return

    frames = trace_data['frames']

    cur_tb = exc_info[2]
    frame_num = 0
    num_frames = len(frames)
    while cur_tb:
        cur_frame = frames[frame_num]
        tb_frame = cur_tb.tb_frame
        cur_tb = cur_tb.tb_next

        if not isinstance(tb_frame, types.FrameType):
            # this can happen if the traceback or frame is wrapped in some way,
            # for example by `ExceptionInfo` in
            # https://github.com/celery/billiard/blob/master/billiard/einfo.py
            log.warning('Traceback frame not a types.FrameType. Ignoring.')
            frame_num += 1
            continue

        # Create placeholders for argspec/varargspec/keywordspec/locals
        argspec = None
        varargspec = None
        keywordspec = None
        _locals: dict[str, Any] = {}

        try:
            arginfo = inspect.getargvalues(tb_frame)

            # Optionally fill in locals for this frame
            if arginfo.locals and _check_add_locals(cur_frame, frame_num, num_frames):
                # Get all of the named args
                argspec = arginfo.args

                if arginfo.varargs is not None:
                    varargspec = arginfo.varargs
                    if SETTINGS['locals']['scrub_varargs']:
                        temp_varargs = list(arginfo.locals[varargspec])
                        for i, arg in enumerate(temp_varargs):
                            temp_varargs[i] = REDACT_REF

                        arginfo.locals[varargspec] = tuple(temp_varargs)

                if arginfo.keywords is not None:
                    keywordspec = arginfo.keywords

                _locals.update(arginfo.locals.items())

        except Exception:
            log.exception('Error while extracting arguments from frame. Ignoring.')

        # Finally, serialize each arg/kwarg/local separately so that we only report
        # CircularReferences for each variable, instead of for the entire payload
        # as would be the case if we serialized that payload in one-shot.
        if argspec:
            cur_frame['argspec'] = argspec
        if varargspec:
            cur_frame['varargspec'] = varargspec
        if keywordspec:
            cur_frame['keywordspec'] = keywordspec
        if _locals:
            try:
                cur_frame['locals'] = {k: _serialize_frame_data(v) for k, v in _locals.items()}
            except Exception:
                log.exception('Error while serializing frame data.')

        frame_num += 1


def _serialize_frame_data(data):
    return transforms.transform(
        data,
        [_scrub_redact_transform, _serialize_transform],
        batch_transforms=SETTINGS['batch_transforms']
    )


def _add_lambda_context_data(data):
    """
    Attempts to add information from the lambda context if it exists
    """
    global _CURRENT_LAMBDA_CONTEXT
    context = _CURRENT_LAMBDA_CONTEXT
    if context is None:
        return
    try:
        lambda_data = {
            'lambda': {
                'remaining_time_in_millis': context.get_remaining_time_in_millis(),
                'function_name': context.function_name,
                'function_version': context.function_version,
                'arn': context.invoked_function_arn,
                'request_id': context.aws_request_id,
            }
        }
        if 'custom' in data:
            data['custom'] = dict_merge(data['custom'], lambda_data, silence_errors=True)
        else:
            data['custom'] = lambda_data
    except Exception as e:
        log.exception("Exception while adding lambda context data: %r", e)
    finally:
        _CURRENT_LAMBDA_CONTEXT = None


def _add_request_data(data, request):
    """
    Attempts to build request data; if successful, sets the 'request' key on `data`.
    """
    try:
        request_data = _build_request_data(request)
    except Exception as e:
        log.exception("Exception while building request_data for Rollbar payload: %r", e)
    else:
        if request_data:
            _filter_ip(request_data, SETTINGS['capture_ip'])
            data['request'] = request_data


def _check_add_locals(frame, frame_num, total_frames):
    """
    Returns True if we should record local variables for the given frame.
    """
    # Include the last frames locals
    # Include any frame locals that came from a file in the project's root
    root = SETTINGS.get('root')
    if root:
        # coerce to string, in case root is a Path object
        root = str(root)
    else:
        root = ''
    return any(((frame_num == total_frames - 1),
                ('root' in SETTINGS and (frame.get('filename') or '').lower().startswith(root.lower()))))


def _get_actual_request(request: Any | None) -> Any | None:
    if WerkzeugLocalProxy is not None and isinstance(request, WerkzeugLocalProxy):
        try:
            actual_request = request._get_current_object()
        except RuntimeError:
            return None
        return actual_request
    return request


def _build_request_data(request: Any) -> dict | None:
    """
    Returns a dictionary containing data from the request.
    """

    # webob (pyramid)
    if WebobBaseRequest is not None and isinstance(request, WebobBaseRequest):
        return _build_webob_request_data(request)

    # django
    if DjangoHttpRequest is not None and isinstance(request, DjangoHttpRequest):
        return _build_django_request_data(request)

    # django rest framework
    if RestFrameworkRequest is not None and isinstance(request, RestFrameworkRequest):
        return _build_django_request_data(request)

    # werkzeug (flask)
    if WerkzeugRequest is not None and isinstance(request, WerkzeugRequest):
        return _build_werkzeug_request_data(request)

    # tornado
    if TornadoRequest is not None and isinstance(request, TornadoRequest):
        return _build_tornado_request_data(request)

    # bottle
    if BottleRequest is not None and isinstance(request, BottleRequest):
        return _build_bottle_request_data(request)

    # Sanic
    if SanicRequest is not None and isinstance(request, SanicRequest):
        return _build_sanic_request_data(request)

    # falcon
    if FalconRequest is not None and isinstance(request, FalconRequest):
        return _build_falcon_request_data(request)

    # Plain wsgi (should be last)
    if isinstance(request, dict) and 'wsgi.version' in request:
        return _build_wsgi_request_data(request)

    # FastAPI (built on top of Starlette, so keep the order)
    if FastAPIRequest is not None and isinstance(request, FastAPIRequest):
        return _build_fastapi_request_data(request)

    # Starlette (should be the last one for Starlette based frameworks)
    if StarletteRequest is not None and isinstance(request, StarletteRequest):
        return _build_starlette_request_data(request)

    return None


def _build_webob_request_data(request) -> dict:
    request_data = {
        'url': request.url,
        'GET': dict(request.GET),
        'user_ip': _extract_user_ip(request),
        'headers': dict(request.headers),
        'method': request.method,
    }

    try:
        if request.json:
            request_data['json'] = request.json
    except:
        pass

    # pyramid matchdict
    if getattr(request, 'matchdict', None):
        request_data['params'] = request.matchdict

    # workaround for webob bug when the request body contains binary data but has a text
    # content-type
    try:
        request_data['POST'] = dict(request.POST)
    except UnicodeDecodeError:
        request_data['body'] = request.body

    return request_data


def _extract_wsgi_headers(items):
    headers = {}
    for k, v in items:
        if k.startswith('HTTP_'):
            header_name = '-'.join(k[len('HTTP_'):].replace('_', ' ').title().split(' '))
            headers[header_name] = v
    return headers


def _build_django_request_data(request) -> dict:
    url = request.build_absolute_uri()

    request_data = {
        'url': url,
        'method': request.method,
        'GET': dict(request.GET),
        'POST': dict(request.POST),
        'user_ip': _wsgi_extract_user_ip(request.META),
    }

    if SETTINGS['include_request_body']:
        try:
            request_data['body'] = request.body
        except:
            pass

    request_data['headers'] = _extract_wsgi_headers(request.META.items())

    return request_data


def _build_werkzeug_request_data(request) -> dict:
    request_data = {
        'url': request.url,
        'GET': dict(request.args),
        'POST': dict(request.form),
        'user_ip': _extract_user_ip(request),
        'headers': dict(request.headers),
        'method': request.method,
        'files_keys': list(request.files.keys()),
    }

    if SETTINGS['include_request_body']:
        try:
            if request.json:
                request_data['body'] = request.json
        except Exception:
            pass

    return request_data


def _build_tornado_request_data(request) -> dict:
    request_data = {
        'url': request.full_url(),
        'user_ip': request.remote_ip,
        'headers': dict(request.headers),
        'method': request.method,
        'files_keys': request.files.keys(),
        'start_time': getattr(request, '_start_time', None),
    }
    request_data[request.method] = request.arguments

    return request_data


def _build_bottle_request_data(request) -> dict:
    request_data = {
        'url': request.url,
        'user_ip': request.remote_addr,
        'headers': dict(request.headers),
        'method': request.method,
        'GET': dict(request.query)
    }


    if SETTINGS['include_request_body']:
        if request.json:
            try:
                request_data['body'] = request.body.getvalue()
            except:
                pass
        else:
            request_data['POST'] = dict(request.forms)

    return request_data


def _build_sanic_request_data(request) -> dict:
    request_data = {
        'url': request.url,
        'user_ip': request.remote_addr,
        'headers': request.headers,
        'method': request.method,
        'GET': dict(request.args)
    }

    if SETTINGS['include_request_body']:
        if request.json:
            try:
                request_data['body'] = request.json
            except:
                pass
        else:
            request_data['POST'] = request.form

    return request_data


def _build_falcon_request_data(request) -> dict:
    request_data = {
        'url': request.url,
        'user_ip': _wsgi_extract_user_ip(request.env),
        'headers': dict(request.headers),
        'method': request.method,
        'GET': dict(request.params),
        'context': dict(request.context),
    }

    return request_data


def _build_wsgi_request_data(request) -> dict:
    request_data = {
        'url': wsgiref.util.request_uri(request),
        'user_ip': _wsgi_extract_user_ip(request),
        'method': request.get('REQUEST_METHOD'),
    }
    if 'QUERY_STRING' in request:
        request_data['GET'] = parse_qs(request['QUERY_STRING'], keep_blank_values=True)
        # Collapse single item arrays
        request_data['GET'] = {k: (v[0] if len(v) == 1 else v) for k, v in request_data['GET'].items()}

    request_data['headers'] = _extract_wsgi_headers(request.items())

    if SETTINGS['include_request_body']:
        try:
            length = int(request.get('CONTENT_LENGTH', 0))
        except ValueError:
            length = 0
        input = request.get('wsgi.input')
        if length and input and hasattr(input, 'seek') and hasattr(input, 'tell'):
            pos = input.tell()
            input.seek(0, 0)
            request_data['body'] = input.read(length)
            input.seek(pos, 0)

    return request_data

def _build_starlette_request_data(request) -> dict:
    from starlette.datastructures import UploadFile

    request_data = {
        'url': str(request.url),
        'GET': dict(request.query_params),
        'headers': dict(request.headers),
        'method': request.method,
        'user_ip': _starlette_extract_user_ip(request),
        'params': dict(request.path_params),
    }

    if hasattr(request, '_form') and request._form is not None:
        request_data['POST'] = {
            k: v.filename if isinstance(v, UploadFile) else v
            for k, v in request._form.items()
        }
        request_data['files_keys'] = [
            field.filename
            for field in request._form.values()
            if isinstance(field, UploadFile)
        ]

    if hasattr(request, '_body'):
        body = request._body.decode()
    else:
        body = None

    if body and SETTINGS['include_request_body']:
        request_data['body'] = body

    if hasattr(request, '_json'):
        request_data['json'] = request._json
    elif body:
        try:
            request_data['json'] = json.loads(body)
        except json.JSONDecodeError:
            pass

    # Filter out empty values
    request_data = {k: v for k, v in request_data.items() if v}

    return request_data

def _build_fastapi_request_data(request) -> dict:
    return _build_starlette_request_data(request)


def _filter_ip(request_data, capture_ip):
    if 'user_ip' not in request_data or capture_ip == True:
        return

    current_ip = request_data['user_ip']
    if not current_ip:
        return

    new_ip = current_ip
    if not capture_ip:
        new_ip = None
    elif capture_ip == ANONYMIZE:
        try:
            if '.' in current_ip:
                new_ip = '.'.join(current_ip.split('.')[0:3]) + '.0'
            elif ':' in current_ip:
                parts = current_ip.split(':')
                if len(parts) > 2:
                    terminal = '0000:0000:0000:0000:0000'
                    new_ip = ':'.join(parts[0:3] + [terminal])
            else:
                new_ip = None
        except:
            new_ip = None

    request_data['user_ip'] = new_ip


def _build_server_data():
    """
    Returns a dictionary containing information about the server environment.
    """
    # server environment
    host = SETTINGS.get('host') or socket.gethostname()
    server_data = {
        'host': host,
        'pid': os.getpid()
    }

    # argv does not always exist in embedded python environments
    argv = getattr(sys, 'argv', None)
    if argv:
         server_data['argv'] = argv

    for key in ['branch', 'root']:
        if SETTINGS.get(key):
            server_data[key] = SETTINGS[key]

    return server_data


def _transform(obj: Any, key: tuple[KeyType, ...] | None = None):
    return transforms.transform(
        obj,
        _transforms,
        key=key,
        batch_transforms=SETTINGS['batch_transforms']
    )


def _build_payload(data: dict) -> dict:
    """
    Returns the full payload as a dict.
    """

    for k, v in data.items():
        data[k] = _transform(v, key=(k,))

    payload = {
        'access_token': SETTINGS['access_token'],
        'data': data
    }

    return payload


def _serialize_payload(payload):
    return json.dumps(payload, default=defaultJSONEncode)


def _send_payload(payload_str, access_token):
    try:
        _post_api('item/', payload_str, access_token=access_token)
    except Exception as e:
        log.exception('Exception while posting item %r', e)
    try:
        _threads.get_nowait()
        _threads.task_done()
    except queue.Empty:
        pass


def _send_payload_thread(payload_str, access_token):
    thread = threading.Thread(target=_send_payload, args=(payload_str, access_token))
    _threads.put(thread)
    thread.start()


def _send_payload_pool(payload_str, access_token):
    try:
        _post_api('item/', payload_str, access_token=access_token)
    except Exception as e:
        log.exception('Exception while posting item %r', e)


def _send_payload_thread_pool(payload_str, access_token):
    from rollbar.lib.thread_pool import submit
    submit(_send_payload_pool, payload_str, access_token)


def _send_payload_appengine(payload_str, access_token):
    try:
        _post_api_appengine('item/', payload_str, access_token=access_token)
    except Exception as e:
        log.exception('Exception while posting item %r', e)


def _post_api_appengine(path, payload_str, access_token=None):
    headers = {'Content-Type': 'application/json'}

    if access_token is not None:
        headers['X-Rollbar-Access-Token'] = access_token

    url = urljoin(SETTINGS['endpoint'], path)
    resp = AppEngineFetch(url,
                          method="POST",
                          payload=payload_str,
                          headers=headers,
                          allow_truncated=False,
                          deadline=SETTINGS.get('timeout', DEFAULT_TIMEOUT),
                          validate_certificate=SETTINGS.get('verify_https', True))

    return _parse_response(path, SETTINGS['access_token'], payload_str, resp)


def _post_api(path, payload_str, access_token=None):
    headers = {'Content-Type': 'application/json'}

    if access_token is not None:
        headers['X-Rollbar-Access-Token'] = access_token

    url = urljoin(SETTINGS['endpoint'], path)
    resp = transport.post(url,
                          data=payload_str,
                          headers=headers,
                          timeout=SETTINGS.get('timeout', DEFAULT_TIMEOUT),
                          verify=SETTINGS.get('verify_https', True),
                          proxy=SETTINGS.get('http_proxy'),
                          proxy_user=SETTINGS.get('http_proxy_user'),
                          proxy_password=SETTINGS.get('http_proxy_password'))

    return _parse_response(path, SETTINGS['access_token'], payload_str, resp)


def _get_api(path, access_token=None, endpoint=None, **params):
    access_token = access_token or SETTINGS['access_token']
    url = urljoin(endpoint or SETTINGS['endpoint'], path)
    params['access_token'] = access_token
    resp = transport.get(url,
                         params=params,
                         verify=SETTINGS.get('verify_https', True),
                         proxy=SETTINGS.get('http_proxy'),
                         proxy_user=SETTINGS.get('http_proxy_user'),
                         proxy_password=SETTINGS.get('http_proxy_password'))
    return _parse_response(path, access_token, params, resp, endpoint=endpoint)


def _send_payload_tornado(payload_str, access_token):
    try:
        _post_api_tornado('item/', payload_str, access_token=access_token)
    except Exception as e:
        log.exception('Exception while posting item %r', e)


def _post_api_tornado(path, payload_str, access_token=None):
    headers = {'Content-Type': 'application/json'}

    if access_token is not None:
        headers['X-Rollbar-Access-Token'] = access_token
    else:
        access_token = SETTINGS['access_token']

    url = urljoin(SETTINGS['endpoint'], path)

    def post_tornado_cb(resp):
        r = requests.Response()
        r._content = resp.body
        r.status_code = resp.code
        r.headers.update(resp.headers)
        try:
            _parse_response(path, access_token, payload_str, r)
        except Exception as e:
            log.exception('Exception while posting item %r', e)

    TornadoAsyncHTTPClient().fetch(url,
                                   callback=post_tornado_cb,
                                   raise_error=False,
                                   body=payload_str,
                                   method='POST',
                                   connect_timeout=SETTINGS.get('timeout', DEFAULT_TIMEOUT),
                                   request_timeout=SETTINGS.get('timeout', DEFAULT_TIMEOUT))


def _send_payload_twisted(payload_str, access_token):
    try:
        _post_api_twisted('item/', payload_str, access_token=access_token)
    except Exception as e:
        log.exception('Exception while posting item %r', e)

def _post_api_twisted(path, payload_str, access_token=None):
    def post_data_cb(data, resp):
        resp._content = data
        _parse_response(path, SETTINGS['access_token'], payload_str, resp)

    def post_cb(resp):
        r = requests.Response()
        r.status_code = resp.code
        r.headers.update(resp.headers.getAllRawHeaders())
        return treq.content(resp).addCallback(post_data_cb, r)

    headers = {'Content-Type': ['application/json; charset=utf-8']}
    if access_token is not None:
        headers['X-Rollbar-Access-Token'] = [access_token]

    url = urljoin(SETTINGS['endpoint'], path)
    try:
        encoded_payload = payload_str.encode('utf8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        encoded_payload = payload_str

    treq_client = treq.client.HTTPClient(Agent(reactor, contextFactory=VerifyHTTPS()))
    d = treq_client.post(url, encoded_payload, headers=headers,
                  timeout=SETTINGS.get('timeout', DEFAULT_TIMEOUT))
    d.addCallback(post_cb)

def _send_payload_httpx(payload_str, access_token):
    from rollbar.lib._async import call_later, _post_api_httpx
    try:
        call_later(_post_api_httpx('item/', payload_str,
                                   access_token=access_token))
    except Exception as e:
        log.exception('Exception while posting item %r', e)



def _send_payload_async(payload_str, access_token):
    try:
        _send_payload_httpx(payload_str, access_token=access_token)
    except Exception as e:
        log.exception('Exception while posting item %r', e)


def _send_failsafe(message, uuid, host):
    body_message = ('Failsafe from pyrollbar: {0}. Original payload may be found '
                    'in your server logs by searching for the UUID.').format(message)

    data = {
        'level': 'error',
        'environment': SETTINGS['environment'],
        'body': {
            'message': {
                'body': body_message
            }
        },
        'notifier': SETTINGS['notifier'],
        'custom': {
            'orig_uuid': uuid,
            'orig_host': host
        },
        'failsafe': True,
        'internal': True,
    }

    payload = _build_payload(data)

    try:
        send_payload(payload, SETTINGS['access_token'])
    except Exception:
        log.exception('Rollbar: Error sending failsafe.')


def _parse_response(path, access_token, params, resp, endpoint=None):
    if isinstance(resp, requests.Response):
        try:
            data = resp.text
        except Exception:
            data = resp.content
            log.error('resp.text is undefined, resp.content is %r', resp.content)
    else:
        data = resp.content

    global _LAST_RESPONSE_STATUS
    last_response_was_429 = _LAST_RESPONSE_STATUS == 429
    _LAST_RESPONSE_STATUS = resp.status_code

    if resp.status_code == 429:
        if SETTINGS['log_all_rate_limited_items'] or not last_response_was_429:
            log.warning("Rollbar: over rate limit, data was dropped.")
            if SETTINGS['log_payload_on_error']:
                log.warning("Payload was: %r", params)
        return
    elif resp.status_code == 502:
        log.exception('Rollbar api returned a 502')
        return
    elif resp.status_code == 413:
        uuid = None
        host = None

        try:
            payload = json.loads(params)
            uuid = payload['data']['uuid']
            host = payload['data']['server']['host']
            log.error("Rollbar: request entity too large for UUID %r\n.", uuid)
            if SETTINGS['log_payload_on_error']:
                log.error("Payload:\n%r", payload)
        except (TypeError, ValueError):
            log.exception('Unable to decode JSON for failsafe.')
        except KeyError:
            log.exception('Unable to find payload parameters for failsafe.')

        _send_failsafe('payload too large', uuid, host)
        # TODO: Should we return here?
    elif resp.status_code != 200:
        log.warning("Got unexpected status code from Rollbar api: %s\nResponse:\n%s",
                    resp.status_code, data)
        # TODO: Should we also return here?

    try:
        json_data = json.loads(data)
    except (TypeError, ValueError):
        log.exception('Could not decode Rollbar api response:\n%s', data)
        raise ApiException('Request to %s returned invalid JSON response', path)
    else:
        if json_data.get('err'):
            raise ApiError(json_data.get('message') or 'Unknown error')

        result = json_data.get('result', {})

        if 'page' in result:
            return PagedResult(access_token, path, result['page'], params, result, endpoint=endpoint)
        else:
            return Result(access_token, path, params, result)


def _extract_user_ip_from_headers(request):
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for
    real_ip = request.headers.get('X-Real-Ip')
    if real_ip:
        return real_ip
    return None


def _extract_user_ip(request):
    return _extract_user_ip_from_headers(request) or request.remote_addr


def _wsgi_extract_user_ip(environ):
    forwarded_for = environ.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for
    real_ip = environ.get('HTTP_X_REAL_IP')
    if real_ip:
        return real_ip
    return environ['REMOTE_ADDR']


def _starlette_extract_user_ip(request):
    if not hasattr(request, 'client'):
        return _extract_user_ip_from_headers(request)
    if not hasattr(request.client, 'host'):
        return _extract_user_ip_from_headers(request)
    return request.client.host or _extract_user_ip_from_headers(request)
