# -*- coding: utf-8 -*-

# Copyright (C) 2018 Alexander Seiler
#
#
# This file is part of script.module.srgssr.
#
# script.module.srgssr is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# script.module.srgssr is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with script.module.srgssr.
# If not, see <http://www.gnu.org/licenses/>.

import datetime
import re
import sys


def try_get(dictionary, keys, data_type=str, default=''):
    """
    Accesses a nested dictionary in a save way.

    Keyword Arguments:
    dictionary   -- the dictionary to access
    keys         -- either a tuple/list containing the keys that should be
                    accessed, or a string/int if only one key should be
                    accessed
    data_type    -- the expected data type of the final element
                    (default: str)
    default      -- a default value to return (default: '')
    """
    d = dictionary
    try:
        if isinstance(keys, (list, tuple)):
            for key in keys:
                d = d[key]
            if isinstance(d, data_type):
                return d
            return default
        if isinstance(d[keys], data_type):
            return d[keys]
        return default
    except (KeyError, IndexError, TypeError):
        return default


def assemble_query_string(query_list):
    """
    Assembles a query for an URL and returns the assembled query string.

    Keyword arguments:
    query_list -- a list of queries
    """
    if sys.version_info[0] >= 3:
        return '&'.join(['{}={}'.format(k, v) for (k, v) in query_list])
    return '&'.join(
        ['{}={}'.decode('utf-8').format(k, v) for (k, v) in query_list])


def str_or_none(inp, default=None):
    """
    Convert an input to a string (if possible), otherwise
    return a default value.

    Keyword arguments:
    inp     -- input
    default -- the default value to return (default: None)
    """
    if inp is None:
        return default
    try:
        return str(inp, 'utf-8')
    except TypeError:
        return inp


def get_duration(duration_string):
    """
    Converts a duration string into an integer respresenting the
    total duration in seconds. There are three possible input string
    forms possible, either
    <hours>:<minutes>:<seconds>
    or
    <minutes>:<seconds>
    or
    <seconds>
    In case of failure a NoneType will be returned.

    Keyword arguments:
    duration_string -- a string of the above Form.
    """
    if not isinstance(duration_string, str):
        return None
    durrex = r'(((?P<hour>\d+):)?(?P<minute>\d+):)?(?P<second>\d+)'
    match = re.match(durrex, duration_string)
    if match:
        hour = int(match.group('hour')) if match.group('hour') else 0
        minute = int(match.group('minute')) if match.group('minute') else 0
        second = int(match.group('second'))
        return 60 * 60 * hour + 60 * minute + second
    # log('Cannot convert duration string: &s' % duration_string)
    return None


def parse_datetime(input_string):
    """
    Tries to create a datetime object from a given input string. There are
    several different forms of input strings supported, for more details
    have a look in the documentations of the called functions. In case
    of failure, a NoneType will be returned.

    Keyword arguments:
    input_string -- a string to convert into a datetime object
    """
    date_time = _parse_weekday_time(input_string)
    if date_time:
        return date_time
    date_time = _parse_date_time(input_string)
    if date_time:
        return date_time
    date_time = _parse_date_time_tz(input_string)
    return date_time


def _parse_date_time_tz(input_string):
    """
    Creates a datetime object from a string of the form
    %Y-%m-%dT%H:%M:%S<tz>
    where <tz> represents the timezone info and is of the form
    (+|-)%H:%M.
    A NoneType will be returned in the case where it was not possible
    to create a datetime object.

    Keyword arguments:
    input_string -- a string of the above form
    """
    dt_regex = r'''(?x)
                    (?P<dt>
                        \d{4}-\d{2}-\d{2}T\d{2}(:|h)\d{2}:\d{2}
                    )
                    (?P<tz>
                        (?:[-+]\d{2}(:|h)\d{2}|Z)
                    )
                '''
    match = re.match(dt_regex, input_string)
    if match:
        dts = match.group('dt')
        # We ignore timezone information for now
        try:
            # Strange behavior of strptime in Kodi?
            # dt = datetime.datetime.strptime(dts, '%Y-%m-%dT%H:%M:%S')
            # results in a TypeError in some cases...
            year = int(dts[0:4])
            month = int(dts[5:7])
            day = int(dts[8:10])
            hour = int(dts[11:13])
            minute = int(dts[14:16])
            second = int(dts[17:19])
            date_time = datetime.datetime(
                year, month, day, hour, minute, second)
            return date_time
        except ValueError:
            return None
    return None


def _parse_weekday_time(input_string):
    """
    Creates a datetime object from a string of the form
    <weekday>,? %H:%M(:S)?
    where <weekday> is either a german name of a weekday
    ('Montag', 'Dienstag', ...) or 'gestern', 'heute', 'morgen'.
    Other supported languages are English, French and Italian.
    If it is not possible to create a datetime object from
    the given input string, a NoneType will be returned.

    Keyword arguments:
    input_string -- a string of the above form
    """
    weekdays_german = (
        'Montag',
        'Dienstag',
        'Mittwoch',
        'Donnerstag',
        'Freitag',
        'Samstag',
        'Sonntag',
    )
    special_weekdays_german = (
        'gestern',
        'heute',
        'morgen',
    )
    identifiers_german = weekdays_german + special_weekdays_german

    weekdays_french = (
        'Lundi',
        'Mardi',
        'Mercredi',
        'Jeudi',
        'Vendredi',
        'Samedi',
        'Dimanche',
    )
    special_weekdays_french = (
        'hier',
        'aujourd\'hui',
        'demain',
    )
    identifiers_french = weekdays_french + special_weekdays_french

    weekdays_italian = (
        'Lunedì',
        'Martedì',
        'Mercoledì',
        'Giovedì',
        'Venerdì',
        'Sabato',
        'Domenica',
    )
    special_weekdays_italian = (
        'ieri',
        'oggi',
        'domani',
    )
    identifiers_italian = weekdays_italian + special_weekdays_italian

    weekdays_english = (
        'Monday',
        'Tuesday',
        'Wednesday',
        'Thursday',
        'Friday',
        'Saturday',
        'Sunday',
    )
    special_weekdays_english = (
        'yesterday',
        'today',
        'tomorrow',
    )
    identifiers_english = weekdays_english + special_weekdays_english

    identifiers = {
        'german': identifiers_german,
        'french': identifiers_french,
        'italian': identifiers_italian,
        'english': identifiers_english,
    }

    recent_date_regex = r'''(?x)
                            (?P<weekday>[a-zA-z\'ì]+)
                            \s*,\s*
                            (?P<hour>\d{2})(:|h)
                            (?P<minute>\d{2})
                            (:
                                (?P<second>\d{2})
                            )?
                        '''
    recent_date_match = re.match(recent_date_regex, input_string)
    if recent_date_match:
        # This depends on correct date settings in Kodi...
        today = datetime.date.today()
        # wdl = [x for x in weekdays if input_string.startswith(x)]
        for key in list(identifiers.keys()):
            wdl = [x for x in identifiers[key] if re.match(
                x, input_string, re.IGNORECASE)]
            lang = key
            if wdl:
                break
        if not wdl:
            return None
        index = identifiers[lang].index(wdl[0])
        if index == 9:  # tomorrow
            offset = datetime.timedelta(1)
        elif index == 8:  # today
            offset = datetime.timedelta(0)
        elif index == 7:  # yesterday
            offset = datetime.timedelta(-1)
        else:  # Monday, Tuesday, ..., Sunday
            days_off_pos = (today.weekday() - index) % 7
            offset = datetime.timedelta(-days_off_pos)
        try:
            hour = int(recent_date_match.group('hour'))
            minute = int(recent_date_match.group('minute'))
            time = datetime.time(hour, minute)
        except ValueError:
            return None
        try:
            second = int(recent_date_match.group('second'))
            time = datetime.time(hour, minute, second)
        except (ValueError, TypeError):
            pass
        date_time = datetime.datetime.combine(today, time) + offset
    else:
        return None
    return date_time


def _parse_date_time(input_string):
    """
    Creates a datetime object from a string of the following form:
    %d.%m.%Y,? %H:%M(:%S)?

    Note that the delimiter between the date and the time is optional, and also
    the seconds in the time are optional.

    If the given string cannot be transformed into a appropriate datetime
    object, a NoneType will be returned.

    Keyword arguments:
    input_string -- the date and time in the above form
    """
    full_date_regex = r'''(?x)
                        (?P<day>\d{2})\.
                        (?P<month>\d{2})\.
                        (?P<year>\d{4})
                        \s*,?\s*
                        (?P<hour>\d{2})(:|h)
                        (?P<minute>\d{2})
                        (:
                            (?P<second>\d{2})
                        )?
                    '''
    full_date_match = re.match(full_date_regex, input_string)
    if full_date_match:
        try:
            year = int(full_date_match.group('year'))
            month = int(full_date_match.group('month'))
            day = int(full_date_match.group('day'))
            hour = int(full_date_match.group('hour'))
            minute = int(full_date_match.group('minute'))
            date_time = datetime.datetime(year, month, day, hour, minute)
        except ValueError:
            return None
        try:
            second = int(full_date_match.group('second'))
            date_time = datetime.datetime(
                year, month, day, hour, minute, second)
            return date_time
        except (ValueError, TypeError):
            return date_time
    return None


def generate_unique_list(input, unique_key):
    """
    Merges a list of similar dictionaries (at least one key has to be
    available in every dictionary) into a single list.

    Keyword arguments:
    input       -- a list of similar dictionaries
    unique_key  -- the key which is taken to compare the values
    """
    unique_keys = []
    output = []
    for li in input:
        for elem in li:
            if elem[unique_key] not in unique_keys:
                unique_keys.append(elem[unique_key])
                output.append(elem)
    return output
