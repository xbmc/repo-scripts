from time import sleep, time

from trakt.api import HttpClient
from trakt.auth.base import BaseAdapter
from trakt.config import AuthConfig
from trakt.errors import (BadRequestException, RateLimitException,
                          TraktException)


class DeviceAuthAdapter(BaseAdapter):
    error_messages = {
        404: 'Invalid device_code',
        409: 'You already approved this code',
        410: 'The tokens have expired, restart the process',
        418: 'You explicitly denied this code',
    }

    success_message = (
        "You've been successfully authenticated. "
        "With access_token {access_token} and refresh_token {refresh_token}"
    )

    def __init__(self, client: HttpClient, config: AuthConfig):
        self.client = client
        self.config = config

    def authenticate(self):
        """Process for authenticating using device authentication.

        The function will attempt getting the device_id, and provide
        the user with a url and code. After getting the device
        id, a timer is started to poll periodic for a successful authentication.
        This is a blocking action, meaning you
        will not be able to run any other code, while waiting for an access token.

        If you want more control over the authentication flow, use the functions
        get_device_code and get_device_token.
        Where poll_for_device_token will check if the "offline"
        authentication was successful.
        """

        response = self.get_device_code()
        device_code = response['device_code']
        interval = response['interval']

        # No need to check for expiration, the API will notify us.
        while True:
            try:
                response = self.get_device_token(device_code)
                print(self.success_message.format_map(response))
                break
            except RateLimitException:
                # slow down
                interval *= 2
            except BadRequestException:
                # not pending
                pass
            except TraktException as e:
                print(self.error_messages.get(e.http_code, response.response))

            sleep(interval)

    def get_device_code(self):
        """Generate a device code, used for device oauth authentication.

        Trakt docs: https://trakt.docs.apiary.io/#reference/
        authentication-devices/device-code
        :return: Your OAuth device code.
        """

        data = {"client_id": self.config.CLIENT_ID}
        response = self.client.post('/oauth/device/code', data=data)

        print('Your user code is: {user_code}, please navigate to {verification_url} to authenticate'.format(
            user_code=response.get('user_code'),
            verification_url=response.get('verification_url')
        ))

        response['requested'] = time()

        return response

    def get_device_token(self, device_code):
        """
        Trakt docs: https://trakt.docs.apiary.io/#reference/
        authentication-devices/get-token
        Response:
        {
          "access_token": "",
          "token_type": "bearer",
          "expires_in": 7776000,
          "refresh_token": "",
          "scope": "public",
          "created_at": 1519329051
        }
        :return: Information regarding the authentication polling.
        :return type: dict
        """

        data = {
            "code": device_code,
            "client_id": self.config.CLIENT_ID,
            "client_secret": self.config.CLIENT_SECRET
        }

        # We only get json on success. Code throws on errors
        response = self.client.post('/oauth/device/token', data=data)

        self.config.update(
            OAUTH_TOKEN=response.get('access_token'),
            OAUTH_REFRESH=response.get('refresh_token'),
            OAUTH_EXPIRES_AT=response.get("created_at") + response.get("expires_in"),
        )

        return response
