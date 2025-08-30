"""Class for trakt.tv auth config"""

__author__ = 'Elan Ruusamäe'

import json
from dataclasses import dataclass
from os.path import exists
from typing import Optional


@dataclass
class AuthConfig:
    APPLICATION_ID: Optional[str]
    CLIENT_ID: Optional[str]
    CLIENT_SECRET: Optional[str]
    OAUTH_EXPIRES_AT: Optional[int]
    OAUTH_REFRESH: Optional[int]
    OAUTH_TOKEN: Optional[str]

    def __init__(self, config_path):
        self.config_path = config_path

    def have_refresh_token(self):
        return self.OAUTH_EXPIRES_AT and self.OAUTH_REFRESH

    def get(self, name, default=None):
        try:
            return self.__getattribute__(name)
        except AttributeError:
            return default

    def set(self, name, value):
        self.__setattr__(name, value)

    def update(self, **kwargs):
        for name, value in kwargs.items():
            self.__setattr__(name, value)

        return self

    def all(self):
        result = {}
        for key in self.__annotations__.keys():
            result[key] = self.get(key)

        return result

    def load(self):
        """
        Load in trakt API auth data from CONFIG_PATH
        """
        if self.CLIENT_ID and self.CLIENT_SECRET or not exists(self.config_path):
            return

        with open(self.config_path) as config_file:
            config_data = json.load(config_file)

        for key in self.__annotations__.keys():
            # Don't overwrite
            if self.get(key) is not None:
                continue

            value = config_data.get(key, None)
            self.set(key, value)

    def store(self):
        """Store Trakt configurations at ``CONFIG_PATH``
        """

        config = self.all()
        with open(self.config_path, 'w') as config_file:
            json.dump(config, config_file)
