# MySQL Connector/Python - MySQL driver written in Python.
# Copyright (c) 2009,2011, Oracle and/or its affiliates. All rights reserved.
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

import socket
import struct
import os
import weakref
from collections import deque
import zlib
try:
    import ssl
except ImportError:
    pass

import constants
import conversion
import protocol
import errors
import utils
import cursor

MAX_PACKET_LENGTH = 16777215

class MySQLBaseSocket(object):
    """Base class for MySQL Connections subclasses.
    
    Should not be used directly but overloaded, changing the
    open_connection part. Examples of subclasses are
      MySQLTCPSocket
      MySQLUnixSocket
    """
    def __init__(self):
        self.sock = None # holds the socket connection
        self.connection_timeout = None
        self.buffer = deque()
        self.recvsize = 8192
        self.send = self.send_plain
        self.recv = self.recv_plain
        
    def open_connection(self):
        pass
    
    def close_connection(self):
        try:
            self.sock.close()
        except:
            pass
    
    def get_address(self):
        pass

    def _prepare_packets(self, buf, pktnr):
        pkts = []
        pllen = len(buf)
        while pllen > MAX_PACKET_LENGTH:
            pkts.append('\xff\xff\xff' + struct.pack('<B',pktnr) 
                + buf[:MAX_PACKET_LENGTH])
            buf = buf[MAX_PACKET_LENGTH:]
            pllen = len(buf)
            pktnr = pktnr + 1
        pkts.append(struct.pack('<I',pllen)[0:3] +
            struct.pack('<B',pktnr) + buf)
        return pkts

    def send(self):
        pass
    
    def send_plain(self, buf, pktnr):
        pkts = self._prepare_packets(buf,pktnr)

        for pkt in pkts:
            pktlen = len(pkt)
            try:
                while pktlen:
                    pktlen -= self.sock.send(pkt)
            except Exception, e:
                raise errors.OperationalError('%s' % e)

    def send_compressed(self, buf, pktnr):
        pllen = len(buf)
        zpkts = []
        if pllen > 16777215:
            pkts = self._prepare_packets(buf,pktnr)
            tmpbuf = ''.join(pkts)
            del pkts
            seqid = 0
            zbuf = zlib.compress(tmpbuf[:16384])
            zpkts.append(struct.pack('<I',len(zbuf))[0:3]
                + struct.pack('<B',seqid) + '\x00\x40\x00' + zbuf)
            tmpbuf = tmpbuf[16384:]
            pllen = len(tmpbuf)
            seqid = seqid + 1
            while pllen > MAX_PACKET_LENGTH:
                zbuf = zlib.compress(tmpbuf[:MAX_PACKET_LENGTH])
                zpkts.append(struct.pack('<I',len(zbuf))[0:3]
                    + struct.pack('<B',seqid) + '\xff\xff\xff' + zbuf)
                tmpbuf = tmpbuf[MAX_PACKET_LENGTH:]
                pllen = len(tmpbuf)
                seqid = seqid + 1
            if tmpbuf:
                zbuf = zlib.compress(tmpbuf)
                zpkts.append(struct.pack('<I',len(zbuf))[0:3] +
                    struct.pack('<B',seqid) + struct.pack('<I',pllen)[0:3]
                    + zbuf)
            del tmpbuf
        else:
            pkt = (struct.pack('<I',pllen)[0:3] +
                struct.pack('<B',pktnr) + buf)
            pllen = len(pkt)
            if pllen > 50:
                zbuf = zlib.compress(pkt)
                zpkts.append(struct.pack('<I',len(zbuf))[0:3] +
                    struct.pack('<B',0) + struct.pack('<I',pllen)[0:3] +
                        zbuf)
            else:
                zpkts.append(struct.pack('<I',pllen)[0:3] +
                    struct.pack('<B',0) + struct.pack('<I',0)[0:3] + pkt)
        
        for zpkt in zpkts:
            zpktlen = len(zpkt)
            try:
                while zpktlen:
                    zpktlen -= self.sock.send(zpkt)
            except Exception, e:
                raise errors.OperationalError('%s' % e)
            
    def recv(self):
        pass
    
    def recv_plain(self):
        try:
            buf = self.buffer.popleft()
            if buf[4] == '\xff':
                errors.raise_error(buf)
            else:
                return buf
        except IndexError:
            pass

        pktsize = 0
        try:
            buf = self.sock.recv(self.recvsize)
            while buf:
                totalsize = len(buf)
                if pktsize == 0 and totalsize >= 4:
                    pktsize = struct.unpack("<I", buf[0:3]+'\x00')[0]
                if pktsize > 0 and totalsize >= pktsize+4:
                    size = pktsize+4
                    self.buffer.append(buf[0:size])
                    buf = buf[size:]
                    pktsize = 0
                    if not buf:
                        try:
                            buf = self.buffer.popleft()
                            if buf[4] == '\xff':
                                errors.raise_error(buf)
                            else:
                                return buf
                        except IndexError, e:
                            break
                elif totalsize < pktsize+4:
                    buf += self.sock.recv(self.recvsize)
        except socket.timeout, e:
            raise errors.InterfaceError(errno=2013)
        except socket.error, e:
            raise errors.InterfaceError(errno=2055,
                values=dict(socketaddr=self.get_address(),errno=e.errno))
        except:
            raise

    def recv_compressed(self):
        try:
            return self.buffer.popleft()
        except IndexError:
            pass
        
        pkts = []
        zpktsize = 0
        try:
            buf = self.sock.recv(self.recvsize)
            while buf:
                totalsize = len(buf)
                if zpktsize == 0 and totalsize >= 7:
                    zpktsize = struct.unpack("<I", buf[0:3]+'\x00')[0]
                    pktsize = struct.unpack("<I", buf[4:4+3]+'\x00')[0]
                if zpktsize > 0 and totalsize >= zpktsize+7:
                    size = zpktsize+7
                    pkts.append(buf[0:size])
                    buf = buf[size:]
                    zpktsize = 0
                    # Keep reading for packets that were to big
                    if pktsize == 16384:
                        buf = self.sock.recv(self.recvsize)
                    elif not buf:
                        break
                    zpktsize = 0
                elif totalsize < pktsize+7:
                    buf += self.sock.recv(self.recvsize)
        except socket.timeout, e:
            raise errors.InterfaceError(errno=2013)
        except socket.error, e:
            raise errors.InterfaceError(errno=2055,
                values=dict(socketaddr=self.get_address(),errno=e.errno))
        except:
            raise
        
        bigbuf = ''
        tmp = []
        for pkt in pkts:
            pktsize = struct.unpack("<I", pkt[4:7]+'\x00')[0]
            if pktsize == 0:
                tmp.append(pkt[7:])
            else:
                tmp.append(zlib.decompress(pkt[7:]))
            pktparts = ()
            
        bigbuf = ''.join(tmp)
        del tmp
        
        while bigbuf:
            pktsize = struct.unpack("<I", bigbuf[0:3]+'\x00')[0]
            pktnr = int(ord(bigbuf[3]))
            self.buffer.append(bigbuf[0:pktsize+4])
            bigbuf = bigbuf[pktsize+4:]
        
        try:
            return self.buffer.popleft()
        except IndexError:
            pass

    def set_connection_timeout(self, timeout):
        self.connection_timeout = timeout
    
    def set_ssl(self, ssl_ca, ssl_cert, ssl_key):
        self._ssl_ca = ssl_ca
        self._ssl_cert = ssl_cert
        self._ssl_key = ssl_key
        
    def switch_to_ssl(self):
        try:
            self.sock = ssl.wrap_socket(self.sock,
                keyfile=self._ssl_key, certfile=self._ssl_cert,
                ca_certs=self._ssl_ca, cert_reqs=ssl.CERT_REQUIRED,
                do_handshake_on_connect=False,
                ssl_version=ssl.PROTOCOL_TLSv1)
            self.sock.do_handshake()
        except NameError:
            raise errors.NotSupportedError(
                "Python installation has no SSL support")
        except ssl.SSLError, e:
            raise errors.InterfaceError("SSL error: %s" % e)
            
class MySQLUnixSocket(MySQLBaseSocket):
    """Opens a connection through the UNIX socket of the MySQL Server."""
    
    def __init__(self, unix_socket='/tmp/mysql.sock'):
        MySQLBaseSocket.__init__(self)
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
                values=dict(socketaddr=self.get_address(),errno=m))
        except StandardError, e:
            raise errors.InterfaceError('%s' % e)
        
class MySQLTCPSocket(MySQLBaseSocket):
    """Opens a TCP connection to the MySQL Server."""
    
    def __init__(self, host='127.0.0.1', port=3306):
        MySQLBaseSocket.__init__(self)
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
                values=dict(socketaddr=self.get_address(),errno=m))
        except StandardError, e:
            raise errors.InterfaceError('%s' % e)
        except:
            raise

class MySQLConnection(object):
    """MySQL"""

    def __init__(self, *args, **kwargs):
        """Initializing"""
        self.protocol = None
        self.converter = None
        self.cursors = []

        self.client_flags = constants.ClientFlag.get_default()
        self._charset = 33

        self._username = ''
        self._database = ''
        self._server_host = '127.0.0.1'
        self._server_port = 3306
        self._unix_socket = None
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
        self.connection_timeout = None
        self.buffered = False
        self.unread_result = False
        self.raw = False
        
        if len(kwargs) > 0:
            self.connect(*args, **kwargs)

    def connect(self, database=None, user='', password='',
            host='127.0.0.1', port=3306, unix_socket=None,
            use_unicode=True, charset='utf8', collation=None,
            autocommit=False,
            time_zone=None, sql_mode=None,
            get_warnings=False, raise_on_warnings=False,
            connection_timeout=None, client_flags=0,
            buffered=False, raw=False,
            ssl_ca=None, ssl_cert=None, ssl_key=None,
            passwd=None, db=None, connect_timeout=None, dsn=None):
        if db and not database:
            database = db
        if passwd and not password:
            password = passwd
        if connect_timeout and not connection_timeout:
            connection_timeout = connect_timeout
        
        if dsn is not None:
            errors.NotSupportedError("Data source name is not supported")

        self._server_host = host
        self._server_port = port
        self._unix_socket = unix_socket
        if database is not None:
            self._database = database.strip()
        else:
            self._database = None
        self._username = user

        self.set_warnings(get_warnings,raise_on_warnings)
        self.connection_timeout = connection_timeout
        self.buffered = buffered
        self.raw = raw
        self.use_unicode = use_unicode
        self.set_client_flags(client_flags)
        self._charset = constants.CharacterSet.get_charset_info(charset)[0]

        if user or password:
            self.set_login(user, password)

        self.disconnect()
        self._open_connection(username=user, password=password, database=database,
            client_flags=self.client_flags, charset=charset,
            ssl=(ssl_ca, ssl_cert, ssl_key))
        self._post_connection(time_zone=time_zone, sql_mode=sql_mode,
          collation=collation)

    def _get_connection(self, prtcls=None):
        """Get connection based on configuration

        This method will return the appropriated connection object using
        the connection parameters.

        Returns subclass of MySQLBaseSocket.
        """
        conn = None
        if self.unix_socket and os.name != 'nt':
            conn = MySQLUnixSocket(unix_socket=self.unix_socket)
        else:
            conn = MySQLTCPSocket(host=self.server_host,
                port=self.server_port)
        conn.set_connection_timeout(self.connection_timeout)
        return conn

    def _open_connection(self, username=None, password=None, database=None,
        client_flags=None, charset=None, ssl=None):
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
            if client_flags & constants.ClientFlag.SSL:
                self.protocol.conn.set_ssl(*ssl)
            self.protocol.do_auth(username, password, database, client_flags,
                self._charset)
            (self._charset, self.charset_name, c) = \
              constants.CharacterSet.get_charset_info(charset)
            self.set_converter_class(conversion.MySQLConverter)
            if client_flags & constants.ClientFlag.COMPRESS:
                self.protocol.conn.recv = self.protocol.conn.recv_compressed
                self.protocol.conn.send = self.protocol.conn.send_compressed
        except:
            raise

    def _post_connection(self, time_zone=None, autocommit=False,
        sql_mode=None, collation=None):
        """Post connection session setup

        Should be called after a connection was established"""
        try:
            if collation is not None:
              self.collation = collation
            self.autocommit = autocommit
            if time_zone is not None:
                self.time_zone = time_zone
            if sql_mode is not None:
                self.sql_mode = sql_mode
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
        self.converter_class = convclass
        self.converter = convclass(self.charset_name, self.use_unicode)

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

    @property
    def connection_id(self):
        """MySQL connection ID"""
        threadid = None
        try:
            threadid = self.protocol.server_threadid
        except:
            pass
        return threadid

    def set_login(self, username=None, password=None):
        """Set login information for MySQL

        Set the username and/or password for the user connecting to
        the MySQL Server.
        """
        if username is not None:
            self.username = username.strip()
        else:
            self.username = ''
        if password is not None:
            self.password = password.strip()
        else:
            self.password = ''

    def set_unicode(self, value=True):
        """Toggle unicode mode

        Set whether we return string fields as unicode or not.
        Default is True.
        """
        self.use_unicode = value
        if self.converter:
            self.converter.set_unicode(value)

    def set_charset(self, charset):
        try:
            (idx, charset_name, c) = \
                constants.CharacterSet.get_charset_info(charset)
            self._execute_query("SET NAMES '%s'" % charset_name)
        except:
            raise
        else:
            self._charset = idx
            self.charset_name = charset_name
            self.converter.set_charset(charset_name)
    def get_charset(self):
        return self._info_query(
            "SELECT @@session.character_set_connection")[0]
    charset = property(get_charset, set_charset,
        doc="Character set for this connection")

    def set_collation(self, collation):
        try:
            self._execute_query(
              "SET @@session.collation_connection = '%s'" % collation)
        except:
            raise
    def get_collation(self):
        return self._info_query(
            "SELECT @@session.collation_connection")[0]
    collation = property(get_collation, set_collation,
        doc="Collation for this connection")

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

    def set_client_flags(self, flags):
        """Set the client flags

        The flags-argument can be either an int or a list (or tuple) of
        ClientFlag-values. If it is an integer, it will set client_flags
        to flags as is.
        If flags is a list (or tuple), each flag will be set or unset
        when it's negative.

        set_client_flags([ClientFlag.FOUND_ROWS,-ClientFlag.LONG_FLAG])

        Returns self.client_flags
        """
        if isinstance(flags,int) and flags > 0:
            self.client_flags = flags
        else:
            if isinstance(flags,(tuple,list)):
                for f in flags:
                    if f < 0:
                        self.unset_client_flag(abs(f))
                    else:
                        self.set_client_flag(f)
        return self.client_flags

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

    @property
    def user(self):
        """User used while connecting to MySQL"""
        return self._username

    @property
    def server_host(self):
        """MySQL server IP address or name"""
        return self._server_host

    @property
    def server_port(self):
        "MySQL server TCP/IP port"
        return self._server_port

    @property
    def unix_socket(self):
        "MySQL Unix socket file location"
        return self._unix_socket

    def set_database(self, value):
        try:
            self.protocol.cmd_query("USE %s" % value)
        except:
            raise
    def get_database(self):
        """Get the current database"""
        return self._info_query("SELECT DATABASE()")[0]
    database = property(get_database, set_database,
        doc="Current database")

    def set_time_zone(self, value):
        try:
            self.protocol.cmd_query("SET @@session.time_zone = %s" % value)
        except:
            raise
    def get_time_zone(self):
        return self._info_query("SELECT @@session.time_zone")[0]
    time_zone = property(get_time_zone, set_time_zone,
        doc="time_zone value for current MySQL session")

    def set_sql_mode(self, value):
        try:
            self.protocol.cmd_query("SET @@session.sql_mode = %s" % value)
        except:
            raise
    def get_sql_mode(self):
        return self._info_query("SELECT @@session.sql_mode")[0]
    sql_mode = property(get_sql_mode, set_sql_mode,
        doc="sql_mode value for current MySQL session")

    def set_autocommit(self, value):
        try:
            if value:
                s = 'ON'
            else:
                s = 'OFF'
            self._execute_query("SET @@session.autocommit = %s" % s)
        except:
            raise
    def get_autocommit(self):
        value = self._info_query("SELECT @@session.autocommit")[0]
        if value == 1:
            return True
        return False
    autocommit = property(get_autocommit, set_autocommit,
        doc="autocommit value for current MySQL session")

    def close(self):
        del self.cursors[:]
        self.disconnect()

    def remove_cursor(self, c):
        try:
            self.cursors.remove(c)
        except ValueError:
            raise errors.ProgrammingError(
                "Cursor could not be removed.")

    def cursor(self, buffered=None, raw=None, cursor_class=None):
        """Instantiates and returns a cursor

        By default, MySQLCursor is returned. Depending on the options
        while connecting, a buffered and/or raw cursor instantiated
        instead.

        It is possible to also give a custom cursor through the
        cursor_class paramter, but it needs to be a subclass of
        mysql.connector.cursor.CursorBase.

        Returns a cursor-object
        """
        if cursor_class is not None:
            if not issubclass(cursor_class, cursor.CursorBase):
                raise errors.ProgrammingError(
                    "Cursor class needs be subclass of cursor.CursorBase")
            c = (cursor_class)(self)
        else:
            buffered = buffered or self.buffered
            raw = raw or self.raw

            t = 0
            if buffered is True:
                t |= 1
            if raw is True:
                t |= 2

            types = {
                0 : cursor.MySQLCursor,
                1 : cursor.MySQLCursorBuffered,
                2 : cursor.MySQLCursorRaw,
                3 : cursor.MySQLCursorBufferedRaw,
            }
            c = (types[t])(self)

        if c not in self.cursors:
            self.cursors.append(c)
        return c

    def commit(self):
        """Commit current transaction"""
        self._execute_query("COMMIT")

    def rollback(self):
        """Rollback current transaction"""
        self._execute_query("ROLLBACK")

    def _execute_query(self, query):
        if self.unread_result is True:
            raise errors.InternalError("Unread result found.")

        self.protocol.cmd_query(query)

    def _info_query(self, query):
        try:
            cur = self.cursor(buffered=True)
            cur.execute(query)
            row = cur.fetchone()
            cur.close()
        except:
            raise
        return row
