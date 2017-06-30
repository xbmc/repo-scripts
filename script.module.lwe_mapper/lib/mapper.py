# -*- coding: utf-8 -*-
"""
    Copyright: (c) 2015 linuxwhatelse (info@linuxwhatelse.de)
    License: GPLv3, see LICENSE for more details

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

__author__    = 'linuxwhatelse'
__email__     = 'info@linuxwhatelse.com'
__copyright__ = 'Copyright 2016, linuxwhatelse'
__license__   = 'GPLv3'

__version__   = '1.1.0'

import os.path
import re
import inspect
import urlparse

class Mapper(object):
    _data_store = []

    def url(self, pattern, method=None, type_cast=None):
        """Decorator for registering a path pattern.

        Args:
            pattern (str): Regex pattern to match a certain path
            method (Optional[str]): Usually used to define one of
                GET, POST, PUT, DELETE (However, you can use whatever you want)
                Defaults to None
            type_cast (Optional[dict]): Mapping between the param name and
                one of int, float, bool
        """
        if not type_cast:
            type_cast = {}

        def decorator(function):
            self.add(pattern, function, method, type_cast)

            return function

        return decorator

    def add(self, pattern, function, method=None, type_cast=None):
        """Function for registering a path pattern.

        Args:
            pattern (str): Regex pattern to match a certain path
            function (function): Function to associate with this path
            method (Optional[str]): Usually used to define one of
                GET, POST, PUT, DELETE (However, you can use whatever you want)
                Defaults to None
            type_cast (Optional[dict]): Mapping between the param name and
                one of int, float, bool
        """
        if not type_cast:
            type_cast = {}

        self._data_store.append({
            'pattern'   : pattern,
            'function'  : function,
            'method'    : method,
            'type_cast' : type_cast,
        })

    def s_url(self, path, method=None, type_cast=None):
        """Decorator for registering a simple path.

        Args:
            path (str): Path to be matched
            method (Optional[str]): Usually used to define one of
                GET, POST, PUT, DELETE (However, you can use whatever you want)
                Defaults to None
            type_cast (Optional[dict]): Mapping between the param name and
                one of int, float, bool
        """
        if not type_cast:
            type_cast = {}

        def decorator(function):
            self.s_add(path, function, method, type_cast)

            return function

        return decorator

    def s_add(self, path, function, method=None, type_cast=None):
        """Function for registering a simple path.

        Args:
            path (str): Path to be matched
            function (function): Function to associate with this path
            method (Optional[str]): Usually used to define one of
                GET, POST, PUT, DELETE (However, you can use whatever you want)
                Defaults to None
            type_cast (Optional[dict]): Mapping between the param name and
                one of int, float, bool
        """
        path = '^/%s' % path.lstrip('/')
        path = '%s/$' % path.rstrip('/')
        path = path.replace('<', '(?P<')
        path = path.replace('>', '>[^/]*)')

        self.add(path, function, method, type_cast)

    def clear(self):
        """Clears all data associated with the mappers data store"""
        del self._data_store[:]

    def call(self, url, method=None, args=None):
        """Calls the first function matching the urls pattern and method (if any)

        Args:
            url (str): Url where a matching function should be called
            method (Optional[str]): Method used while registering a function.
                Defaults to None
            args (Optional[dict]): Additional args in form of a dict
                which should be passed to the matching function

        Returns:
            Returns the functions return value, None if it didn't return anything.
            Also, it will return None if no matching function was called.
        """
        if not args:
            args = {}

        data = urlparse.urlparse(url)
        path = data.path.rstrip('/') + '/'
        _args = dict(urlparse.parse_qs(data.query, keep_blank_values=True))

        for elem in self._data_store:
            pattern     = elem['pattern']
            function    = elem['function']
            _method     = elem['method']
            type_cast   = elem['type_cast']

            result = re.match(pattern, path)

            # Found matching method
            if result and _method == method:
                _args = dict(_args, **result.groupdict())

                # Unpack value lists (due to urlparse.parse_qs) in case
                # theres only one value available
                for key, val in _args.items():
                    if isinstance(_args[key], list) and len(_args[key]) == 1:
                        _args[key] = _args[key][0]

                # Apply typ-casting if necessary
                for key, val in type_cast.items():

                    # Not within available _args, no type-cast required
                    if key not in _args:
                        continue

                    # Is None or empty, no type-cast required
                    if not _args[key]:
                        continue

                    # Try and cast the values
                    if isinstance(_args[key], list):
                        for i, _val in enumerate(_args[key]):
                            _args[key][i] = self._cast(_val, val)
                    else:
                        _args[key] = self._cast(_args[key], val)

                requiered_args = self._get_function_args(function)
                for key, val in args.items():
                    if key in requiered_args:
                        _args[key] = val

                return function(**_args)

        return None

    def _cast(self, value, to):
        val = None

        if to == int:
            val = int(value)

        elif to == float:
            val = float(value)

        elif to == bool:
            if value.lower() == 'true' or value== '1':
                val = True

            elif value.lower() == 'false' or value == '0':
                val = False

        return val

    def _get_function_args(self, func):
        args, varargs, varkw, defaults = inspect.getargspec(func)
        if defaults:
            args = args[:-len(defaults)]
        return args
