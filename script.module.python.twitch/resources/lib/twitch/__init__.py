# -*- encoding: utf-8 -*-
"""

    Copyright (C) 2012-2016 python-twitch (https://github.com/ingwinlu/python-twitch)
    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

__all__ = ['VERSION', 'CLIENT_ID', 'CLIENT_SECRET', 'OAUTH_TOKEN', 'APP_TOKEN', 'api', 'oauth',
           'exceptions', 'keys', 'log', 'methods', 'parser', 'queries', 'scraper']

VERSION = '2.0.0'
CLIENT_ID = ''
CLIENT_SECRET = ''
OAUTH_TOKEN = ''
APP_TOKEN = ''

from . import api
from . import oauth
from . import exceptions
from . import keys
from . import log
from . import methods
from . import parser
from . import queries
from . import scraper
