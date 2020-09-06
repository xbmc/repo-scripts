# coding: utf-8
from __future__ import absolute_import, unicode_literals

import datetime
import time

from dateutil import tz

try:
    from typing import Text  # pylint: disable=unused-import
except ImportError:
    pass

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class proxydt(datetime.datetime):  # pylint: disable=invalid-name
    """
    A hack to fix Kodi datetime.strptime problem

    More info: https://forum.kodi.tv/showthread.php?tid=112916
    """

    @classmethod
    def strptime(cls, date_string, format):  # pylint: disable=redefined-builtin
        return datetime.datetime(*(time.strptime(date_string, format)[:6]))


datetime.datetime = proxydt


def timestamp_to_time_string(posix_timestamp):
    # type: (int) -> Text
    date_time = datetime.datetime.fromtimestamp(posix_timestamp, tz=tz.tzlocal())
    return date_time.strftime(DATETIME_FORMAT)


def time_string_to_timestamp(time_string):
    # type: (Text) -> int
    time_object = datetime.datetime.strptime(time_string, DATETIME_FORMAT)
    time_object = time_object.replace(tzinfo=tz.tzlocal())
    timetuple = time_object.timetuple()
    timestamp = int(time.mktime(timetuple))
    return timestamp if timestamp >= 0 else 0
