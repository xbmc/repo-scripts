import sys

from trakt.api import HttpClient
from trakt.auth.base import BaseAdapter
from trakt.config import AuthConfig


class PinAuthAdapter(BaseAdapter):
    NEEDS_APPLICATION_ID = True

    def __init__(self, client: HttpClient, config: AuthConfig, pin=None):
        """
        :param pin: Optional Trakt API PIN code. If one is not specified, you will
            be prompted to go generate one
        """
        self.pin = pin
        self.client = client
        self.config = config

    def authenticate(self):
        """Generate an access_token from a Trakt API PIN code.
        """

        if self.pin is None and self.config.APPLICATION_ID is None:
            print('You must set the APPLICATION_ID of the Trakt application you '
                  'wish to use. You can find this ID by visiting the following '
                  'URL.')
            print('https://trakt.tv/oauth/applications')
            sys.exit(1)
        if self.pin is None:
            print('If you do not have a Trakt.tv PIN, please visit the following '
                  'url and log in to generate one.')
            pin_url = 'https://trakt.tv/pin/{id}'.format(id=self.config.APPLICATION_ID)
            print(pin_url)
            self.pin = input('Please enter your PIN: ')
        data = {
            'code': self.pin,
            'redirect_uri': self.REDIRECT_URI,
            'grant_type': 'authorization_code',
            'client_id': self.config.CLIENT_ID,
            'client_secret': self.config.CLIENT_SECRET,
        }

        response = self.client.post('/oauth/token', data)
        self.config.OAUTH_TOKEN = response.get('access_token', None)
        return self.config.OAUTH_TOKEN
