from functools import partial
from urllib import urlencode

from soundcloud.resource import wrapped_resource
from soundcloud.request import make_request


class Client(object):
    """A client for interacting with Soundcloud resources."""

    use_ssl = True
    host = 'api.soundcloud.com'

    def __init__(self, **kwargs):
        """Create a client instance with the provided options. Options should
        be passed in as kwargs.
        """
        self.use_ssl = kwargs.get('use_ssl', self.use_ssl)
        self.host = kwargs.get('host', self.host)
        self.scheme = self.use_ssl and 'https://' or 'http://'
        self.options = kwargs
        self._authorize_url = None

        self.client_id = kwargs.get('client_id')

        if 'access_token' in kwargs:
            self.access_token = kwargs.get('access_token')
            return

        if 'client_id' not in kwargs:
            raise TypeError("At least a client_id must be provided.")

        if 'scope' in kwargs:
            self.scope = kwargs.get('scope')

        # decide which protocol flow to follow based on the arguments
        # provided by the caller.
        if self._options_for_authorization_code_flow_present():
            self._authorization_code_flow()
        elif self._options_for_credentials_flow_present():
            self._credentials_flow()
        elif self._options_for_token_refresh_present():
            self._refresh_token_flow()

    def exchange_token(self, code):
        """Given the value of the code parameter, request an access token."""
        url = '%s%s/oauth2/token' % (self.scheme, self.host)
        options = {
            'grant_type': 'authorization_code',
            'redirect_uri': self._redirect_uri(),
            'client_id': self.options.get('client_id'),
            'client_secret': self.options.get('client_secret'),
            'code': code,
        }
        options.update({
            'verify_ssl': self.options.get('verify_ssl', True),
            'proxies': self.options.get('proxies', None)
        })
        self.token = wrapped_resource(
            make_request('post', url, options))
        self.access_token = self.token.access_token
        return self.token

    def authorize_url(self):
        """Return the authorization URL for OAuth2 authorization code flow."""
        return self._authorize_url

    def _authorization_code_flow(self):
        """Build the the auth URL so the user can authorize the app."""
        options = {
            'scope': getattr(self, 'scope', 'non-expiring'),
            'client_id': self.options.get('client_id'),
            'response_type': 'code',
            'redirect_uri': self._redirect_uri()
        }
        url = '%s%s/connect' % (self.scheme, self.host)
        self._authorize_url = '%s?%s' % (url, urlencode(options))

    def _refresh_token_flow(self):
        """Given a refresh token, obtain a new access token."""
        url = '%s%s/oauth2/token' % (self.scheme, self.host)
        options = {
            'grant_type': 'refresh_token',
            'client_id': self.options.get('client_id'),
            'client_secret': self.options.get('client_secret'),
            'refresh_token': self.options.get('refresh_token')
        }
        options.update({
            'verify_ssl': self.options.get('verify_ssl', True),
            'proxies': self.options.get('proxies', None)
        })
        self.token = wrapped_resource(
            make_request('post', url, options))
        self.access_token = self.token.access_token

    def _credentials_flow(self):
        """Given a username and password, obtain an access token."""
        url = '%s%s/oauth2/token' % (self.scheme, self.host)
        options = {
            'client_id': self.options.get('client_id'),
            'client_secret': self.options.get('client_secret'),
            'username': self.options.get('username'),
            'password': self.options.get('password'),
            'scope': getattr(self, 'scope', ''),
            'grant_type': 'password'
        }
        options.update({
            'verify_ssl': self.options.get('verify_ssl', True),
            'proxies': self.options.get('proxies', None)
        })
        self.token = wrapped_resource(
            make_request('post', url, options))
        self.access_token = self.token.access_token

    def _request(self, method, resource, **kwargs):
        """Given an HTTP method, a resource name and kwargs, construct a
        request and return the response.
        """
        url = self._resolve_resource_name(resource)

        if hasattr(self, 'access_token'):
            kwargs.update(dict(oauth_token=self.access_token))
        if hasattr(self, 'client_id'):
            kwargs.update(dict(client_id=self.client_id))

        kwargs.update({
            'verify_ssl': self.options.get('verify_ssl', True),
            'proxies': self.options.get('proxies', None)
        })
        return wrapped_resource(make_request(method, url, kwargs))

    def __getattr__(self, name, **kwargs):
        """Translate an HTTP verb into a request method."""
        if name not in ('get', 'post', 'put', 'head', 'delete'):
            raise AttributeError
        return partial(self._request, name, **kwargs)

    def _resolve_resource_name(self, name):
        """Convert a resource name (e.g. tracks) into a URI."""
        if name[:4] == 'http':  # already a url
            if name[:4] != 'json' and name[-8:] not in ('download', 'stream'):
                return '%s.json' % (name,)
            return name
        name = name.rstrip('/').lstrip('/')
        if name[-13:] == 'contributions':
            return '%s%s/%s' % (self.scheme, self.host, name)
        return '%s%s/%s.json' % (self.scheme, self.host, name)

    def _redirect_uri(self):
        """
        Return the redirect uri. Checks for ``redirect_uri`` or common typo,
        ``redirect_url``
        """
        return self.options.get(
            'redirect_uri',
            self.options.get('redirect_url', None))

    # Helper functions for testing arguments provided to the constructor.
    def _options_present(self, options, kwargs):
        return all(map(lambda k: k in kwargs, options))

    def _options_for_credentials_flow_present(self):
        required = ('client_id', 'client_secret', 'username', 'password')
        return self._options_present(required, self.options)

    def _options_for_authorization_code_flow_present(self):
        required = ('client_id', 'redirect_uri')
        or_required = ('client_id', 'redirect_url')
        return (self._options_present(required, self.options) or
                self._options_present(or_required, self.options))

    def _options_for_token_refresh_present(self):
        required = ('client_id', 'client_secret', 'refresh_token')
        return self._options_present(required, self.options)
