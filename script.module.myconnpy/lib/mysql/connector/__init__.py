# MySQL Connector/Python - MySQL driver written in Python.
# Copyright (c) 2009, 2013, Oracle and/or its affiliates. All rights reserved.

# MySQL Connector/Python is licensed under the terms of the GPLv2
# <http://www.gnu.org/licenses/old-licenses/gpl-2.0.html>, like most
# MySQL Connectors. There are special exceptions to the terms and
# conditions of the GPLv2 as it is applied to this software, see the
# FOSS License Exception
# <http://www.mysql.com/about/legal/licensing/foss-exception.html>.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

"""
MySQL Connector/Python - MySQL drive written in Python
"""

from mysql.connector.connection import MySQLConnection
from mysql.connector.errors import (  # pylint: disable=W0622
    Error, Warning, InterfaceError, DatabaseError,
    NotSupportedError, DataError, IntegrityError, ProgrammingError,
    OperationalError, InternalError, custom_error_exception, PoolError)
from mysql.connector.constants import (
    FieldFlag, FieldType, CharacterSet, RefreshOption, ClientFlag)
from mysql.connector.dbapi import (
    Date, Time, Timestamp, Binary, DateFromTicks, DateFromTicks,
    TimestampFromTicks, TimeFromTicks,
    STRING, BINARY, NUMBER, DATETIME, ROWID,
    apilevel, threadsafety, paramstyle)
from mysql.connector.pooling import (
    MySQLConnectionPool, generate_pool_name, CNX_POOL_ARGS,
    CONNECTION_POOL_LOCK)

try:
    from mysql.connector import version
except ImportError:
    # Development, try import from current directory
    try:
        import version
    except ImportError:
        raise ImportError("For development, make sure version.py is "
                          "in current directory.")

_CONNECTION_POOLS = {}


def connect(*args, **kwargs):
    """Create or get a MySQL connection object

    In its simpliest form, Connect() will open a connection to a
    MySQL server and return a MySQLConnection object.

    When any connection pooling arguments are given, for example pool_name
    or pool_size, a pool is created or a previously one is used to return
    a PooledMySQLConnection.

    Returns MySQLConnection or PooledMySQLConnection.
    """
    # Pooled connections
    if any([key in kwargs for key in CNX_POOL_ARGS]):
        # If no pool name specified, generate one
        try:
            pool_name = kwargs['pool_name']
        except KeyError:
            pool_name = generate_pool_name(**kwargs)

        # Setup the pool, ensuring only 1 thread can update at a time
        with CONNECTION_POOL_LOCK:
            if pool_name not in _CONNECTION_POOLS:
                _CONNECTION_POOLS[pool_name] = MySQLConnectionPool(
                    *args, **kwargs)
            elif isinstance(_CONNECTION_POOLS[pool_name], MySQLConnectionPool):
                # pool_size must be the same
                check_size = _CONNECTION_POOLS[pool_name].pool_size
                if ('pool_size' in kwargs
                        and kwargs['pool_size'] != check_size):
                    raise PoolError("Size can not be changed "
                                    "for active pools.")

        # Return pooled connection
        try:
            return _CONNECTION_POOLS[pool_name].get_connection()
        except AttributeError:
            raise InterfaceError(
                "Failed getting connection from pool '{0}'".format(pool_name))

    # Regular connection
    return MySQLConnection(*args, **kwargs)
Connect = connect  # pylint: disable=C0103

__version_info__ = version.VERSION
__version__ = version.VERSION_TEXT

__all__ = [
    'MySQLConnection', 'Connect', 'custom_error_exception',

    # Some useful constants
    'FieldType', 'FieldFlag', 'ClientFlag', 'CharacterSet', 'RefreshOption',

    # Error handling
    'Error', 'Warning',
    'InterfaceError', 'DatabaseError',
    'NotSupportedError', 'DataError', 'IntegrityError', 'ProgrammingError',
    'OperationalError', 'InternalError',

    # DBAPI PEP 249 required exports
    'connect', 'apilevel', 'threadsafety', 'paramstyle',
    'Date', 'Time', 'Timestamp', 'Binary',
    'DateFromTicks', 'DateFromTicks', 'TimestampFromTicks', 'TimeFromTicks',
    'STRING', 'BINARY', 'NUMBER',
    'DATETIME', 'ROWID',
    ]
