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

"""Unittests for mysql.connector.connection
"""

import os
import socket
import logging
from collections import deque

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5

import tests
from tests import mysqld
from mysql.connector import connection, errors

logger = logging.getLogger(tests.LOGGER_NAME)

class MySQLBaseSocketTests(tests.MySQLConnectorTests):
    
    def setUp(self):
        config = self.getMySQLConfig()
        self._host = config['host']
        self._port = config['port']
        self.cnx = connection.MySQLBaseSocket()
    
    def tearDown(self):
        try:
            self.cnx.close_connection()
        except:
            pass
    
    def _get_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logger.debug("Get socket for %s:%d" % (self._host,self._port))
        sock.connect((self._host, self._port))
        return sock
        
    def test_init(self):
        """MySQLBaseSocket initialization"""
        exp = dict(
            sock = None,
            connection_timeout = None,
            buffer = deque(),
            recvsize = 1024*8,
        )
        
        for k,v in exp.items():
            self.assertEqual(v, self.cnx.__dict__[k])
    
    def test_open_connection(self):
        """Opening a connection"""
        try:
            self.cnx.open_connection()
        except:
            self.fail()
    
    def test_close_connection(self):
        """Closing a connection"""
        self.cnx.close_connection()
        self.assertEqual(None, self.cnx.sock)
    
    def test_get_address(self):
        """Get the address of a connection"""
        try:
            self.cnx.get_address()
        except:
            self.fail()
    
    def test_send(self):
        """Send data through the socket"""
        data = "abcdefghijklmnopq"
        self.assertRaises(errors.OperationalError, self.cnx.send, data, 0)
        
        self.cnx.sock = self._get_socket()
        try:
            self.cnx.send(data,0)
        except:
            self.fail()
    
    def test_recv(self):
        """Receive data from the socket"""
        self.cnx.sock = self._get_socket()
        
        # Handshake
        buf = self.cnx.recv()
        self.assertEqual((0,10), (ord(buf[3]),ord(buf[4])))
        
        self.cnx.sock.settimeout(1)
        self.assertRaises(errors.InterfaceError,self.cnx.recv)
        
        # Authenticate
        req = \
        '\x0d\xa2\x03\x00\x00\x00\xa0\x00\x21\x00\x00\x00'\
        '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'\
        '\x00\x00\x00\x00\x72\x6f\x6f\x74\x00\x00\x6d\x79\x73\x71\x6c\x00'
        exp = '\x07\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00'
        
        self.cnx.send(req,1)
        self.assertEqual(exp, self.cnx.recv())
        
        # Execute: SELECT "Ham"
        req = \
        '\x03\x53\x45\x4c\x45\x43\x54\x20\x22\x48\x61\x6d\x22'
        exp = (
        '\x01\x00\x00\x01\x01',
        '\x19\x00\x00\x02\x03\x64\x65\x66\x00\x00\x00\x03\x48\x61\x6d\x00'\
        '\x0c\x21\x00\x09\x00\x00\x00\xfd\x01\x00\x1f\x00\x00',
        '\x05\x00\x00\x03\xfe\x00\x00\x02\x00',
        '\x04\x00\x00\x04\x03\x48\x61\x6d',
        '\x05\x00\x00\x05\xfe\x00\x00\x02\x00',
        )
        result = []
        self.cnx.send(req,0)
        buf = self.cnx.recv()
        while buf:
            result.append(buf)
            if len(result) == len(exp):
                self.cnx.send('\x01',0)
            buf = self.cnx.recv()
        
        for i,expdata in enumerate(exp):
            self.assertEqual(expdata, result[i])
        
    def test_set_connection_timeout(self):
        """Set the connection timeout"""
        exp = 5
        self.cnx.set_connection_timeout(exp)
        self.assertEqual(exp, self.cnx.connection_timeout)

class MySQLUnixSocketTests(tests.MySQLConnectorTests):
    
    def setUp(self):
        config = self.getMySQLConfig()
        self._unix_socket = config['unix_socket']
        self.cnx = connection.MySQLUnixSocket(
            unix_socket=config['unix_socket'])
    
    def tearDown(self):
        try:
            self.cnx.close_connection()
        except:
            pass
    
    def test_init(self):
        """MySQLUnixSocket initialization"""
        exp = dict(
            unix_socket=self._unix_socket,
            sock = None,
            connection_timeout = None,
            buffer = deque(),
            recvsize = 1024*8,
        )
        
        for k,v in exp.items():
            self.assertEqual(v, self.cnx.__dict__[k])
    
    def test_get_address(self):
        """Get path to the Unix socket"""
        exp = self._unix_socket
        self.assertEqual(exp, self.cnx.get_address())
    
    def test_open_connection(self):
        """Open a connection using a Unix socket"""
        try:
            self.cnx.open_connection()
        except:
            self.fail()

class MySQLTCPSocketTests(tests.MySQLConnectorTests):
    
    def setUp(self):
        config = self.getMySQLConfig()
        self._host = config['host']
        self._port = config['port']
        self.cnx = connection.MySQLTCPSocket(
            host=self._host, port=self._port)
    
    def tearDown(self):
        try:
            self.cnx.close_connection()
        except:
            pass
        
    def test_init(self):
        """MySQLTCPSocket initialization"""
        exp = dict(
            server_host=self._host,
            server_port=self._port,
            sock = None,
            connection_timeout = None,
            buffer = deque(),
            recvsize = 1024*8,
        )

        for k,v in exp.items():
            self.assertEqual(v, self.cnx.__dict__[k])
    
    def test_get_address(self):
        """Get TCP/IP address"""
        exp = "%s:%s" % (self._host,self._port)
        self.assertEqual(exp, self.cnx.get_address())

    def test_open_connection(self):
        """Open a connection using TCP"""
        try:
            self.cnx.open_connection()
        except:
            self.fail()
        