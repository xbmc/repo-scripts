# MySQL Connector/Python - MySQL driver written in Python.
# Copyright (c) 2009,2010, Oracle and/or its affiliates. All rights reserved.
# Use is subject to license terms. (See COPYING)

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation.
# 
# There are special exceptions to the terms and conditions of the GNU
# General Public License as it is applied to this software. View the
# full text of the exception in file EXCEPTIONS-CLIENT in the directory
# of this software distribution or see the FOSS License Exception at
# www.mysql.com.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

"""Main classes for interacting with MySQL
"""

import os
import weakref

from connection import *
import constants
import conversion
import protocol
import errors
import utils
import cursor


class MySQLBase(object):
    """MySQLBase"""

    def __init__(self):
        """Initializing"""
        self.conn = None # Holding the connection
        self.protocol = None
        self.converter = None
        
        self.client_flags = constants.ClientFlag.get_default()
        (self.charset,
         self.charset_name,
         self.collation_name) = constants.CharacterSet.get_charset_info('utf8')
        
        self.username = ''
        self.password = ''
        self.database = ''
        self.client_host = ''
        self.client_port = 0
        
        self.affected_rows = 0
        self.server_status = 0
        self.warning_count = 0
        self.field_count = 0
        self.insert_id = 0
        self.info_msg = ''
        self.use_unicode = True
        self.get_warnings = False
        self.raise_on_warnings = False
        self.autocommit = False
        self.connection_timeout = None
        self.buffered = False
        self.unread_result = False

    def connect(self):
        """To be implemented while subclassing MySQLBase."""
        pass
    
    def _get_connection(self, prtcls=None):
        """Automatically chooses based on configuration which connection type to setup."""
        conn = None
        if self.unix_socket and os.name != 'nt':
            conn = MySQLUnixConnection(unix_socket=self.unix_socket)
        else:
            conn = MySQLTCPConnection(host=self.server_host,
                port=self.server_port)
        conn.set_connection_timeout(self.connection_timeout)
        return conn
        
    def _open_connection(self):
        """Opens the connection
        
        Open the connection, check the MySQL version, and set the
        protocol.
        """        
        try:
            self.protocol = protocol.MySQLProtocol(self._get_connection())
            self.protocol.do_handshake()
            version = self.protocol.server_version
            if version < (4,1):
                raise errors.InterfaceError(
                    "MySQL Version %s is not supported." % version)
            self.protocol.do_auth(username=self.username,
                password=self.password, client_flags=self.client_flags,
                database=self.database, charset=self.charset)
        except:
            raise
        
    def _post_connection(self):
        """Should be called after a connection was established"""
        self.get_characterset_info()
        self.set_converter_class(conversion.MySQLConverter)
        try:
            self.set_autocommit(self.autocommit)
        except:
            raise
            
    def is_connected(self):
        """
        Check whether we are connected to the MySQL server.
        """
        return self.protocol.cmd_ping()
    ping = is_connected

    def disconnect(self):
        """
        Disconnect from the MySQL server.
        """
        if not self.protocol:
            return
            
        if self.protocol.conn.sock is not None:
            self.protocol.cmd_quit()
            try:
                self.protocol.conn.close_connection()
            except:
                pass
        self.protocol = None
        
    def set_converter_class(self, convclass):
        """
        Set the converter class to be used. This should be a class overloading
        methods and members of conversion.MySQLConverter.
        """
        #self.converter_class = convclass
        self.converter = convclass(self.charset_name, self.use_unicode)
    
    def get_characterset_info(self):
        try:
            (self.charset_name, self.collation_name) = constants.CharacterSet.get_info(self.charset)
        except:
            raise errors.ProgrammingError, "Illegal character set information (id=%d)" % self.charset
        return (self.charset_name, self.collation_name)
    
    def get_server_version(self):
        """Returns the server version as a tuple"""
        try:
            return self.protocol.server_version
        except:
            pass
        
        return None
    
    def get_server_info(self):
        """Returns the server version as a string"""
        return self.protocol.server_version_original
    
    def get_server_threadid(self):
        """Returns the MySQL threadid of the connection."""
        threadid = None
        try:
            threadid = self.protocol.server_threadid
        except:
            pass
        
        return threadid
        
    def set_host(self, host):
        """
        Set the host for connection to the MySQL server.
        """
        self.server_host = host
    
    def set_port(self, port):
        """
        Set the TCP port to be used when connecting to the server, usually 3306.
        """
        self.server_port = port
    
    def set_login(self, username=None, password=None):
        """
        Set the username and/or password for the user connecting to the MySQL Server.
        """
        if  username:
            self.username = username.strip() 
        else:
            self.username = ''
            
        if password:
            self.password = password.strip() 
        else:
            self.password = ''
    
    def set_unicode(self, value=True):
        """
        Set whether we return string fields as unicode or not.
        Default is True.
        """
        self.use_unicode = value
        if self.converter:
            self.converter.set_unicode(value)
        
    def set_database(self, database):
        """
        Set the database to be used after connection succeeded.
        """
        if database:
            self.database = database.strip()
        else:
            self.database = ''
    
    def set_charset_info(self, info=None, charset=None):
        
        if info is None and charset is not None:
            info = constants.CharacterSet.get_charset_info(charset)
        
        if info is not None:
            (self.charset, self.charset_name, self.collation_name) = info
    
    def set_charset(self, name):
        """
        Set the character set used for the connection. This is the recommended
        way of change it per connection basis. It does execute SET NAMES
        internally, but it's good not to use this command directly, since we
        are setting some other members accordingly.
        """
        if name not in constants.CharacterSet.get_supported():
            raise errors.ProgrammingError, "Character set '%s' not supported." % name
            return
        try:
            info = constants.CharacterSet.get_charset_info(name)
        except errors.ProgrammingError, e:
            raise
        
        try:
            self._execute_query("SET NAMES '%s'" % name)
        except:
            raise
        else:
            self.set_charset_info(info=info)
            self.converter.set_charset(self.charset_name)

    def set_warnings(self, fetch=False, raise_on_warnings=False):
        """Set how to handle warnings coming from MySQL
        
        Set wheter we should get warnings whenever an operation produced some.
        If you set raise_on_warnings to True, any warning will be raised
        as a DataError exception.
        """
        if raise_on_warnings is True:
            self.get_warnings = True
            self.raise_on_warnings = True
        else:
            self.get_warnings = fetch
            self.raise_on_warnings = False
    
    def set_autocommit(self, switch):
        """Set autocommit on or off
        
        Set auto commit on or off.
        """
        try:
            if switch:
                s = 'ON' 
            else:
                s = 'OFF'
            self._execute_query("SET AUTOCOMMIT = %s" % s)
        except:
            raise
        else:
            self.autocommit = switch
    
    def set_unixsocket(self, loc):
        """Set the UNIX Socket location. Does not check if it exists."""
        self.unix_socket = loc
    
    def set_connection_timeout(self, timeout):
        self.connection_timeout = timeout
    
    def set_client_flags(self, flags):
        self.client_flags = flags
    
    def set_client_flag(self, flag):
        if flag > 0:
            self.client_flags |= flag
    
    def unset_client_flag(self, flag):
        if flag > 0:
            self.client_flags &= ~flag
    
    def isset_client_flag(self, flag):
        if (self.client_flags & flag) > 0:
            return True
        return False
    
    def set_buffered(self, val=False):
        """Sets whether cursor .execute() fetches rows"""
        self.buffered = val

    def _execute_query(self, query):
        if self.unread_result is True:
            raise errors.InternalError("Unread result found.")

        self.protocol.cmd_query(query)

class MySQL(MySQLBase):
    """
    Class implementing Python DB API v2.0.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes the MySQL object. Calls connect() to open the connection
        when an instance is created.
        """
        MySQLBase.__init__(self)
        self.cursors = []
        self.affected_rows = 0
        self.server_status = 0
        self.warning_count = 0
        self.field_count = 0
        self.insert_id = 0
        self.info_msg = ''
        
        self.connect(*args, **kwargs)
            
    def connect(self, dsn='', user='', password='', passwd=None, host='127.0.0.1',
            port=3306, db=None, database=None, use_unicode=True, charset='utf8',
            get_warnings=False, raise_on_warnings=False,
            autocommit=False, unix_socket=None,
            connection_timeout=None, client_flags=0, buffered=False):
        """
        Establishes a connection to the MySQL Server. Called also when instansiating
        a new MySQLConnection object through the __init__ method.

        Possible parameters are:

        dsn
            (not used)
            
        user
            The username used to authenticate with the MySQL Server.

        password
        passwd
            The password to authenticate the user with the MySQL Server.
            (password takes precedence; MySQLdb compatibility)
            
        host
            The hostname or the IP address of the MySQL Server we are connecting with.
            (default 127.0.0.1)

        port
            TCP port to use for connecting to the MySQL Server.
            (default 3306)

        database
        db
            Initial database to use once we are connected with the MySQL Server.
            (database takes precedence; MySQLdb compatibility)

        use_unicode
            If set to true, string values received from MySQL will be returned
            as Unicode strings.
            Default: True

        charset
            Which character shall we use for sending data to MySQL. One can still
            override this by using the SET NAMES command directly, but this is
            discouraged. Instead, use the set_charset() method if you
            want to change it.
            Default: Whatever the MySQL server has default.

        get_warnings
            If set to true, whenever a query gives a warning, a SHOW WARNINGS will
            be done to fetch them. They will be available as MySQLCursor.warnings.
            The default is to ignore these warnings, for debugging it's good to
            enable it though, or use strict mode in MySQL to make most of these
            warnings errors.
            Default: False
        
        raise_on_warnings
            If set to True, warnings will be raised as exceptions. raise_on_warings
            overrides get_warnings.
            Default: False

        autocommit
            Auto commit is OFF by default, which is required by the Python Db API
            2.0 specification.
            Default: False

        unix_socket
            Full path to the MySQL Server UNIX socket. By default TCP connection will
            be used using the address specified by the host argument.
        
        connection_timeout
            Timeout for the TCP and UNIX socket connection.
        
        client_flags
            Allows to set flags for the connection. Check following for possible flags:
             >>> from mysql.connector.constants import ClientFlag
             >>> print '\n'.join(ClientFlag.get_full_info())
            By default, it will be set to constants.ClientFlag.get_default()
        
        buffered
            When set to True .execute() will fetch the rows immediatly.
            
        """
        if db and not database:
            database = db
        if passwd and not password:
            password = passwd

        self.set_host(host)
        self.set_port(port)
        self.set_database(database)
        self.set_warnings(get_warnings,raise_on_warnings)
        self.set_unixsocket(unix_socket)
        self.set_connection_timeout(connection_timeout)
        self.set_buffered(buffered)
        self.set_charset_info(charset=charset)
        self.use_unicode = use_unicode
        
        if client_flags is not None and client_flags > 0:
            self.set_client_flags(client_flags)
        else:
            self.set_client_flags(constants.ClientFlag.get_default())
        
        if user or password:
            self.set_login(user, password)

        self.disconnect()
        self._open_connection()
        self._post_connection()
    
    def close(self):
        del self.cursors[:]
        self.disconnect()
    
    def remove_cursor(self, c):
        try:
            self.cursors.remove(c)
        except ValueError:
            raise errors.ProgrammingError(
                "Cursor could not be removed.")
        
    def cursor(self):
        if self.buffered:
            c = (cursor.MySQLCursorBuffered)(self)
        else:
            c = (cursor.MySQLCursor)(self)
        
        if c not in self.cursors:
            self.cursors.append(c)
        return c
        
    def commit(self):
        """Shortcut for executing COMMIT."""
        self._execute_query("COMMIT")

    def rollback(self):
        """Shortcut for executing ROLLBACK"""
        self._execute_query("ROLLBACK")

    
