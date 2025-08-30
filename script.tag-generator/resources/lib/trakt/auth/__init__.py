# -*- coding: utf-8 -*-
"""Authentication methods"""

__author__ = 'Jon Nappi, Elan Ruusamäe'

from trakt.config import AuthConfig
from trakt.core import DEVICE_AUTH, OAUTH_AUTH, PIN_AUTH, api
from trakt.core import config as config_factory


def pin_auth(*args, config, **kwargs):
    from trakt.auth.pin import PinAuthAdapter

    return PinAuthAdapter(*args, client=api(), config=config, **kwargs).authenticate()


def oauth_auth(*args, config, **kwargs):
    from trakt.auth.oauth import OAuthAdapter

    return OAuthAdapter(*args, client=api(), config=config, **kwargs).authenticate()


def device_auth(config):
    from trakt.auth.device import DeviceAuthAdapter

    return DeviceAuthAdapter(client=api(), config=config).authenticate()


def get_client_info(app_id: bool, config: AuthConfig):
    """Helper function to poll the user for Client ID and Client Secret
    strings

    :return: A 2-tuple of client_id, client_secret
    """
    print('If you do not have a client ID and secret. Please visit the '
          'following url to create them.')
    print('https://trakt.tv/oauth/applications')
    client_id = input('Please enter your client id: ')
    client_secret = input('Please enter your client secret: ')
    if app_id:
        msg = f'Please enter your application ID ({config.APPLICATION_ID}): '
        user_input = input(msg)
        if user_input:
            config.APPLICATION_ID = user_input
    return client_id, client_secret


def init_auth(method: str, *args, client_id=None, client_secret=None, store=False, **kwargs):
    """Run the auth function specified by *AUTH_METHOD*

    :param store: Boolean flag used to determine if your trakt api auth data
    should be stored locally on the system. Default is :const:`False` for
    the security conscious
    """

    methods = {
        PIN_AUTH: pin_auth,
        OAUTH_AUTH: oauth_auth,
        DEVICE_AUTH: device_auth,
    }

    config = config_factory()
    adapter_func = methods.get(method, pin_auth)
    # Get the actual adapter class for NEEDS_APPLICATION_ID
    if method == PIN_AUTH:
        from trakt.auth.pin import PinAuthAdapter
        needs_app_id = PinAuthAdapter.NEEDS_APPLICATION_ID
    elif method == OAUTH_AUTH:
        from trakt.auth.oauth import OAuthAdapter
        needs_app_id = OAuthAdapter.NEEDS_APPLICATION_ID
    elif method == DEVICE_AUTH:
        from trakt.auth.device import DeviceAuthAdapter
        needs_app_id = DeviceAuthAdapter.NEEDS_APPLICATION_ID
    else:
        needs_app_id = False

    if client_id is None and client_secret is None:
        client_id, client_secret = get_client_info(needs_app_id, config)
    config.CLIENT_ID, config.CLIENT_SECRET = client_id, client_secret

    return adapter_func(*args, config=config, **kwargs)

    if store:
        config.store()
