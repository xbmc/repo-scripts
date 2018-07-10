# -*- encoding: utf-8 -*-
# https://dev.twitch.tv/docs/
# V5 is deprecated and will be removed entirely on 12/31/18

__all__ = ['bits', 'channel_feed', 'channels', 'chat', 'clips', 'collections', 'communities',
           'games', 'ingests', 'root', 'search', 'streams', 'teams', 'users', 'videos']

from ...log import log

log.deprecated_api_version('V5', 'Helix', '12/31/18')

from . import bits  # NOQA
from . import channel_feed  # NOQA
from . import channels  # NOQA
from . import chat  # NOQA
from . import clips  # NOQA
from . import collections  # NOQA
from . import communities  # NOQA
from . import games  # NOQA
from . import ingests  # NOQA
from .root import root  # NOQA
from . import search  # NOQA
from . import streams  # NOQA
from . import teams  # NOQA
from . import users  # NOQA
from . import videos  # NOQA
