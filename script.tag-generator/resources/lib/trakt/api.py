import json
import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from json import JSONDecodeError

from requests import Session
from requests.auth import AuthBase

from trakt import errors
from trakt.config import AuthConfig
from trakt.core import TIMEOUT
from trakt.errors import BadRequestException, BadResponseException, OAuthException

__author__ = 'Elan Ruusamäe'


class HttpClient:
    """Class for abstracting HTTP requests
    """

    logger = logging.getLogger(__name__)

    #: Default request HEADERS
    headers = {'Content-Type': 'application/json', 'trakt-api-version': '2'}

    def __init__(self, base_url: str, session: Session, timeout=None):
        """
        Initialize an HTTP client for making requests to a specified base URL.

        Parameters:
            base_url (str): The base URL for API requests.
            session (Session): A requests Session object for managing HTTP connections.
            timeout (float, optional): Request timeout in seconds. Defaults to a predefined TIMEOUT value if not specified.
        """
        self._auth = None
        self.base_url = base_url
        self.session = session
        self.timeout = timeout or TIMEOUT

    def get(self, url: str):
        """
        Send a GET request to the specified URL.

        Parameters:
            url (str): The endpoint URL to send the GET request to.

        Returns:
            dict: The JSON-decoded response from the server.

        Raises:
            Various exceptions from `raise_if_needed` based on HTTP status codes.
        """
        return self.request('get', url)

    def delete(self, url: str):
        self.request('delete', url)

    def post(self, url: str, data):
        return self.request('post', url, data=data)

    def put(self, url: str, data):
        """
        Send a PUT request to the specified URL with the given data.

        Parameters:
            url (str): The target URL for the PUT request.
            data (dict, optional): The payload to be sent with the request.

        Returns:
            dict: The JSON-decoded response from the server.

        Raises:
            Various exceptions from `raise_if_needed` based on HTTP response status.
        """
        return self.request('put', url, data=data)

    @property
    def auth(self):
        """
        Get the current authentication object for the HTTP client.

        Returns:
            Auth | None: The authentication object associated with the HTTP client, which can be None or an authentication instance.
        """
        return self._auth

    @auth.setter
    def auth(self, auth):
        """
        Set the authentication method for the HTTP client.

        Parameters:
            auth (Auth | None): An authentication object to be used for API requests.
        """
        self._auth = auth

    def request(self, method, url, data=None):
        """
        Send an HTTP request to the Trakt API and process the response.

        Sends a request to the specified URL using the given HTTP method, with optional data payload.
        Handles different request types, logs request and response details, and processes the API response.

        Parameters:
            method (str): HTTP method to use ('get', 'post', 'put', 'delete')
            url (str): Relative URL path to send the request to
            data (dict, optional): Payload to send with the request. Defaults to None.

        Returns:
            dict or None: Decoded JSON response from the Trakt API, or None for 204 No Content responses

        Raises:
            TraktException: If the API returns a non-200 status code
            JSONDecodeError: If the response cannot be decoded as JSON

        Notes:
            - For GET requests, data is passed as URL parameters
            - For other methods, data is JSON-encoded in the request body
            - Automatically prepends the base URL to the provided URL
            - Logs debug information for request and response
            - Handles authentication via the configured auth mechanism
        """

        url = self.base_url + url
        self.logger.debug('REQUEST [%s] (%s)', method, url)
        if method == 'get':  # GETs need to pass data as params, not body
            response = self.session.request(method, url, headers=self.headers, auth=self.auth, timeout=self.timeout, params=data)
        else:
            response = self.session.request(method, url, headers=self.headers, auth=self.auth, timeout=self.timeout, data=json.dumps(data))
        self.logger.debug('RESPONSE [%s] (%s): %s', method, url, str(response))
        if response.status_code == 204:  # HTTP no content
            return None
        self.raise_if_needed(response)

        return self.decode_response(response)

    @staticmethod
    def decode_response(response):
        try:
            return json.loads(response.content.decode('UTF-8', 'ignore'))
        except JSONDecodeError as e:
            raise BadResponseException(f"Unable to parse JSON: {e}")

    def raise_if_needed(self, response):
        if response.status_code in self.error_map:
            raise self.error_map[response.status_code](response)

    @property
    @lru_cache(maxsize=None)
    def error_map(self):
        """Map HTTP response codes to exception types
        """

        # Get all of our exceptions except the base exception
        errs = [getattr(errors, att) for att in errors.__all__
                if att != 'TraktException']

        return {err.http_code: err for err in errs}


class TokenAuth(AuthBase):
    """Attaches Trakt.tv token Authentication to the given Request object."""

    #: The OAuth2 Redirect URI for your OAuth Application
    REDIRECT_URI: str = 'urn:ietf:wg:oauth:2.0:oob'

    #: How many times to attempt token auth refresh before failing
    MAX_RETRIES = 1

    # Time margin before token expiry when refresh should be triggered
    TOKEN_REFRESH_MARGIN = {'minutes': 10}

    logger = logging.getLogger(__name__)

    def __init__(self, client: HttpClient, config: AuthConfig):
        super().__init__()
        self.config = config
        self.client = client
        # OAuth token validity checked
        self.OAUTH_TOKEN_VALID = None
        self.refresh_attempts = 0

    def __call__(self, r):
        # Skip oauth requests
        if r.path_url.startswith('/oauth/'):
            return r

        [client_id, client_token] = self.get_token()

        if client_id and client_token:
            r.headers.update({
                'trakt-api-key': client_id,
                'Authorization': f'Bearer {client_token}',
            })
        else:
            self.logger.debug("Skipping auth headers: missing credentials")

        return r

    def get_token(self):
        """Return client_id, client_token pair needed for Trakt.tv authentication
        """

        self.config.load()
        # Check token validity and refresh token if needed
        if not self.OAUTH_TOKEN_VALID and self.config.have_refresh_token():
            self.validate_token()

        return [
            self.config.CLIENT_ID,
            self.config.OAUTH_TOKEN,
        ]

    def validate_token(self):
        """Check if current OAuth token has not expired

        The token is considered valid if it expires in more than TOKEN_REFRESH_MARGIN
        (default: 10 minutes). This margin ensures the token doesn't expire during
        critical operations while also maximizing the token's useful lifetime.
        """

        current = datetime.now(tz=timezone.utc)
        expires_at = datetime.fromtimestamp(self.config.OAUTH_EXPIRES_AT, tz=timezone.utc)
        margin = expires_at - current
        if margin > timedelta(**self.TOKEN_REFRESH_MARGIN):
            self.OAUTH_TOKEN_VALID = True
        else:
            self.logger.debug("Token expires in %s, refreshing (margin: %s)", margin, self.TOKEN_REFRESH_MARGIN)
            self.refresh_token()

    def refresh_token(self):
        """Request Trakt API for a new valid OAuth token using refresh_token"""

        if self.refresh_attempts >= self.MAX_RETRIES:
            self.logger.error("Max token refresh attempts reached. Manual intervention required.")
            return
        self.refresh_attempts += 1

        self.logger.info("OAuth token has expired, refreshing now...")
        data = {
            'client_id': self.config.CLIENT_ID,
            'client_secret': self.config.CLIENT_SECRET,
            'refresh_token': self.config.OAUTH_REFRESH,
            'redirect_uri': self.REDIRECT_URI,
            'grant_type': 'refresh_token'
        }

        try:
            response = self.client.post('oauth/token', data)
            self.refresh_attempts = 0
        except (OAuthException, BadRequestException) as e:
            if e.response is not None:
                try:
                    error = e.response.json().get("error")
                    error_description = e.response.json().get("error_description")
                except JSONDecodeError:
                    error = "Invalid JSON response"
                    error_description = e.response.text
            else:
                error = "No error description"
                error_description = ""
            self.logger.error(
                "%s - Unable to refresh expired OAuth token (%s) %s",
                e.http_code, error, error_description
            )
            return

        self.config.update(
            OAUTH_TOKEN=response.get("access_token"),
            OAUTH_REFRESH=response.get("refresh_token"),
            OAUTH_EXPIRES_AT=response.get("created_at") + response.get("expires_in"),
        )
        self.OAUTH_TOKEN_VALID = True

        self.logger.info(
            "OAuth token successfully refreshed, valid until {}".format(
                datetime.fromtimestamp(self.config.OAUTH_EXPIRES_AT, tz=timezone.utc)
            )
        )
        self.config.store()
