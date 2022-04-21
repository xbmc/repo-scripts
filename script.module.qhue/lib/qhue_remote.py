# Access to the Hue Hub when using the remote API
# via the Philips servers.
#
# Qhue is (c) Quentin Stafford-Fraser 2021
# but distributed under the GPL v2.
# It expects Python v3.

import webbrowser
import requests
from requests_oauthlib import OAuth2Session
from typing import Optional

from .qhue import Resource, _DEFAULT_TIMEOUT
from .oauth_receiver import TokenCollector

# Remote API root URL for use if outside the LAN
REMOTE_API_BASE = "https://api.meethue.com/bridge"

OAUTH_AUTHORIZE_URL = "https://api.meethue.com/v2/oauth2/authorize"
OAUTH_TOKEN_URL = "https://api.meethue.com/v2/oauth2/token"
OAUTH_REFRESH_URL = OAUTH_TOKEN_URL


def _remote_api_url(username):
    # The username is sometimes called a 'whitelist entry'
    # in the API docs. You can get one on your local LAN
    # using the create_new_username function as described in the
    # README.
    # TODO: We aren't yet dealing with the situation where you
    # don't have the username but are remote.
    return "{}/{}".format(REMOTE_API_BASE, username)


class RemoteBridge(Resource):
    """
    A RemoteBridge is a Resource that represents the top-level connection to a
    Philips Hue Bridge (or 'Hub') from outside that bridge's local network.
    It is the basis for building other Resources that represent the things
    managed by that Bridge.
    It is similar to a bridge, but uses OAuth authentication to the Philips server.
    """
    def __init__(self, username: str, timeout: float = _DEFAULT_TIMEOUT, object_pairs_hook=None):
        """
        Create a new connection to a remote Hue bridge.
        The 'username' is the same as for a local bridge -
        sometimes called a whitelist_identifier in the docs.
        It is not the user's identifier on the Philips site.
        """
        self.username = username
        self.session = requests.Session()
        url = _remote_api_url(username)
        super().__init__(url, self.session, timeout=timeout, object_pairs_hook=object_pairs_hook)

    def authorize(
        self,
        client_id: str,
        client_secret: str,
        token: Optional[str] = None,
        open_browser: bool = True,
        use_local_server: bool = False
    ):
        """
        Open a browser to the Hue site to ask you to authorise remote access.
        An existing token can be passed if available, otheriwse authorization will be needed:
        If open_browser is True, python will try to open your browser to the necessary URL,
        otherwise it will just print it out.
        Once authorised, this redirects to an HTTPS address, passing the required token.

        TODO: We don't currently refresh tokens.
        """
        # Use an oauth session in place of a standard requests session.
        self.session = OAuth2Session(client_id, token=token)
        if token is not None:
            return token
        authorization_url, state = self.session.authorization_url(OAUTH_AUTHORIZE_URL)
        if open_browser:
            print("Opening a browser to take you to", authorization_url)
            webbrowser.open_new(authorization_url)
        else:
            print("Open a browser at", authorization_url)

        if use_local_server:
            c = TokenCollector()
            redirect_response = c.get_single_request()

        else:
            redirect_response = input('Paste the full redirect URL here:')

        print("redirect response is ", redirect_response)

        return self.session.fetch_token(
            OAUTH_TOKEN_URL,
            client_secret=client_secret,
            authorization_response=redirect_response)
