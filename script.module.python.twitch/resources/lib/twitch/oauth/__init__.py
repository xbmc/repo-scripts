# -*- encoding: utf-8 -*-

from twitch.oauth import v5  # V5 is deprecated and will be removed entirely on 2/14/18
from twitch.oauth import helix
from twitch.oauth import v5 as default
from twitch.oauth import clients

__all__ = ['v5', 'default', 'helix', 'clients']
