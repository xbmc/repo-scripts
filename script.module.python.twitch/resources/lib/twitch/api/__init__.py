# -*- encoding: utf-8 -*-

from twitch.api import v5  # V5 is deprecated and will be removed entirely on 2/14/18
from twitch.api import v5 as default
from twitch.api import helix

__all__ = ['v5', 'default', 'helix']
