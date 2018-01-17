# -*- encoding: utf-8 -*-
# https://dev.twitch.tv/docs/
# V5 is deprecated and will be removed entirely on 2/14/18
from twitch.logging import log

log.deprecated_api_version('V5', 'Helix', '2/14/18')

from twitch.api.v5 import bits  # NOQA
from twitch.api.v5 import channel_feed  # NOQA
from twitch.api.v5 import channels  # NOQA
from twitch.api.v5 import chat  # NOQA
from twitch.api.v5 import clips  # NOQA
from twitch.api.v5 import collections  # NOQA
from twitch.api.v5 import communities  # NOQA
from twitch.api.v5 import games  # NOQA
from twitch.api.v5 import ingests  # NOQA
from twitch.api.v5.root import root  # NOQA
from twitch.api.v5 import search  # NOQA
from twitch.api.v5 import streams  # NOQA
from twitch.api.v5 import teams  # NOQA
from twitch.api.v5 import users  # NOQA
from twitch.api.v5 import videos  # NOQA
