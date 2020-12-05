# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import time
from datetime import datetime

now = datetime.now


def strptime(timestamp, timestamp_format):
    import _strptime  # pylint: disable=import-outside-toplevel
    try:
        time.strptime('01 01 2012', '%d %m %Y')
    finally:
        return time.strptime(timestamp, timestamp_format)  # pylint: disable=lost-exception


def timestamp_diff(timestamp):
    try:
        then = datetime(*(strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')[0:6]))
    except ValueError:
        then = datetime(*(strptime(timestamp, '%Y-%m-%d %H:%M:%S')[0:6]))

    delta = now() - then

    return delta.total_seconds()
