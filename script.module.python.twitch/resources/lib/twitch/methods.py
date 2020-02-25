# -*- encoding: utf-8 -*-
"""

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

GET = 'GET'
POST = 'POST'
PUT = 'PUT'
DELETE = 'DELETE'

valid = [GET, POST, PUT, DELETE]


def validate(value):
    if value in valid:
        return value
    raise ValueError(value)
