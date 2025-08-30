from urllib.parse import urljoin

from requests_oauthlib import OAuth2Session

from trakt.api import HttpClient
from trakt.auth.base import BaseAdapter
from trakt.config import AuthConfig


class OAuthAdapter(BaseAdapter):
    def __init__(self, username, client: HttpClient, config: AuthConfig, oauth_cb=None):
        """
        :param username: Your trakt.tv username
        :param oauth_cb: Callback function to handle the retrieving of the OAuth
            PIN. Default function `_terminal_oauth_pin` for terminal auth
        """
        self.username = username
        self.client = client
        self.config = config
        self.oauth_cb = self.terminal_oauth_pin if oauth_cb is None else oauth_cb

    def authenticate(self):
        """Generate an access_token to allow your application to authenticate via
        OAuth
        """

        base_url = self.client.base_url
        authorization_base_url = urljoin(base_url, '/oauth/authorize')
        token_url = urljoin(base_url, '/oauth/token')

        # OAuth endpoints given in the API documentation
        oauth = OAuth2Session(self.config.CLIENT_ID, redirect_uri=self.REDIRECT_URI, state=None)

        # Authorization URL to redirect user to Trakt for authorization
        authorization_url, _ = oauth.authorization_url(authorization_base_url, username=self.username)

        # Calling callback function to get the OAuth PIN
        oauth_pin = self.oauth_cb(authorization_url)

        # Fetch, assign, and return the access token
        oauth.fetch_token(token_url, client_secret=self.config.CLIENT_SECRET, code=oauth_pin)
        self.config.update(
            OAUTH_TOKEN=oauth.token['access_token'],
            OAUTH_REFRESH=oauth.token['refresh_token'],
            OAUTH_EXPIRES_AT=oauth.token["created_at"] + oauth.token["expires_in"],
        )

    @staticmethod
    def terminal_oauth_pin(authorization_url):
        """Default OAuth callback used for terminal applications.

        :param authorization_url: Predefined url by function `oauth_auth`. URL will
            be prompted to you in the terminal
        :return: OAuth PIN
        """
        print('Please go here and authorize,', authorization_url)

        # Get the authorization verifier code from the callback url
        response = input('Paste the Code returned here: ')
        return response
