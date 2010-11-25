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

"""Implementing communication to MySQL servers
"""

import sys
import socket
import os
from collections import deque

import errors
import utils

class MySQLBaseConnection(object):
    """Base class for MySQL Connections subclasses.
    
    Should not be used directly but overloaded, changing the
    open_connection part. Examples over subclasses are
      MySQLTCPConnection
      MySQLUNIXConnection
    """
    def __init__(self):
        self.sock = None # holds the socket connection
        self.connection_timeout = None
        self.socket_flags = 0
        self.buffer = deque()
        self.recvsize = 1024*8
        self._set_socket_flags()
        
    def open_connection(self):
        pass
    
    def close_connection(self):
        try:
            self.sock.close()
        except:
            pass
    
    def get_address(self):
        pass

    def send(self, buf):
        """
        Send packets using the socket to the server.
        """
        pktlen = len(buf)
        try:
            while pktlen:
                pktlen -= self.sock.send(buf)
        except Exception, e:
            raise errors.OperationalError('%s' % e)

    def _next_buffer(self):
        buf = self.buffer.popleft()
        return buf
            
    def recv(self):
        """Receive packets from the MySQL server
        """
        try:
            return self._next_buffer()
        except:
            pass
        
        pktnr = -1
        
        try:
            buf = self.sock.recv(self.recvsize, self.socket_flags)
            while buf:
                totalsize = len(buf)
                if pktnr == -1 and totalsize > 4:
                    pktsize = utils.intread(buf[0:3])
                    pktnr = utils.intread(buf[3])
                if pktnr > -1 and totalsize >= pktsize+4:
                    size = pktsize+4
                    self.buffer.append(buf[0:size])
                    buf = buf[size:]
                    pktnr = -1
                    if len(buf) == 0:
                        break
                elif len(buf) < pktsize+4:
                    buf += self.sock.recv(self.recvsize, self.socket_flags)
        except socket.error, e:
            raise errors.InterfaceError(errno=2055,
                values=(self.get_address(),e.errno))
        except:
            raise
        
        return self._next_buffer()

    def set_connection_timeout(self, timeout):
        self.connection_timeout = timeout

    def _set_socket_flags(self, flags=None):
        self.socket_flags = 0
        if flags is None:
            if os.name in ('nt','cygwin'):
                flags = 0
            else:
                flags = 0
        if flags is not None:
            self.socket_flags = flags
    

class MySQLUnixConnection(MySQLBaseConnection):
    """Opens a connection through the UNIX socket of the MySQL Server."""
    
    def __init__(self, unix_socket='/tmp/mysql.sock'):
        MySQLBaseConnection.__init__(self)
        self.unix_socket = unix_socket
        
    def get_address(self):
        return self.unix_socket
        
    def open_connection(self):
        """Opens a UNIX socket and checks the MySQL handshake."""
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.settimeout(self.connection_timeout)
            self.sock.connect(self.unix_socket)
        except socket.error, e:
            try:
                m = e.errno
            except:
                m = e
            raise errors.InterfaceError(errno=2002,
                values=(self.get_address(),m))
        except StandardError, e:
            raise errors.InterfaceError('%s' % e)
        
class MySQLTCPConnection(MySQLBaseConnection):
    """Opens a TCP connection to the MySQL Server."""
    
    def __init__(self, host='127.0.0.1', port=3306):
        MySQLBaseConnection.__init__(self)
        self.server_host = host
        self.server_port = port
    
    def get_address(self):
        return "%s:%s" % (self.server_host,self.server_port)
        
    def open_connection(self):
        """Opens a TCP Connection and checks the MySQL handshake."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.connection_timeout)
            self.sock.connect( (self.server_host, self.server_port) )
        except socket.error, e:
            try:
                m = e.errno
            except:
                m = e
            raise errors.InterfaceError(errno=2003,
                values=(self.get_address(),m))
        except StandardError, e:
            raise errors.InterfaceError('%s' % e)
        except:
            raise
                
