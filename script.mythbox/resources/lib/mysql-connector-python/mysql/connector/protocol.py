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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USAs

"""Implementing the MySQL Client/Server protocol
"""

import re
import struct

try:
    from hashlib import sha1
except ImportError:
    from sha import new as sha1

from datetime import datetime
from time import strptime
from decimal import Decimal

from constants import *
import errors
import utils

def packet_is_error(idx=0,label=None):
    def deco(func):
        def call(*args, **kwargs):
            try:
                if label:
                    pktdata = kwargs[label]
                else:
                    pktdata = args[idx]
            except Exception, e:
                raise errors.InterfaceError(
                    "Can't check for Error packet; %s" % e)
            
            try:
                if pktdata and pktdata[4] == '\xff':
                    errors.raise_error(pktdata)
            except errors.Error:
                raise
            except:
                pass
            return func(*args, **kwargs)
        return call
    return deco

def packet_is_ok(idx=0,label=None):
    def deco(func):
        def call(*args, **kwargs):
            try:
                if label:
                    pktdata = kwargs[label]
                else:
                    pktdata = args[idx]
            except:
                raise errors.InterfaceError("Can't check for OK packet.")
            
            try:
                if pktdata and pktdata[4] == '\x00':
                    return func(*args, **kwargs)
                else:
                    raise
            except:
                raise errors.InterfaceError("Expected OK packet")
        return call
    return deco

def packet_is_eof(idx=0,label=None):
    def deco(func):
        def call(*args, **kwargs):
            try:
                if label:
                    pktdata = kwargs[label]
                else:
                    pktdata = args[idx]
            except:
                raise errors.InterfaceError("Can't check for EOF packet.")
            if pktdata[4] == '\xfe' and len(pktdata) == 9:
                return func(*args, **kwargs)
            else:
                raise errors.InterfaceError("Expected EOF packet")

        return call
    return deco

def set_pktnr(idx=1,label=None):
    def deco(func):
        def call(*args, **kwargs):
            try:
                if label:
                    pktdata = kwargs[label]
                else:
                    pktdata = args[idx]
            except:
                raise errors.InterfaceError("Can't check for EOF packet.")
            
            try:
                args[0].pktnr = ord(pktdata[3])
                pktdata = pktdata[4:]
                if label:
                    kwargs[label] = pktdata
                else:
                    args = list(args)
                    args[idx] = pktdata
            except:
                raise errors.InterfaceError("Failed getting Packet Number.")
            return func(*args,**kwargs)
        return call
    return deco

def reset_pktnr(func):
    def deco(*args, **kwargs):
        try:
            args[0].pktnr = -1
        except:
            pass
        return func(*args, **kwargs)
        
    return deco

class MySQLProtocolBase(object):
    pass

class MySQLProtocol(MySQLProtocolBase):

    def __init__(self, conn):
        self.client_flags = 0
        self.conn = conn
        self.pktnr = -1
    
    @property
    def next_pktnr(self):
        self.pktnr = self.pktnr + 1
        return self.pktnr
    
    def _scramble_password(self, passwd, seed):
        """Scramble a password ready to send to MySQL"""
        hash4 = None
        try: 
            hash1 = sha1(passwd).digest()
            hash2 = sha1(hash1).digest() # Password as found in mysql.user()
            hash3 = sha1(seed + hash2).digest()
            xored = [ utils.intread(h1) ^ utils.intread(h3) 
                for (h1,h3) in zip(hash1, hash3) ]
            hash4 = struct.pack('20B', *xored)
        except Exception, e:
            raise errors.InterfaceError('Failed scrambling password; %s' % e)
        
        return hash4

    def _prepare_auth(self, usr, pwd, db, flags, seed):
        
        if usr is not None and len(usr) > 0:
            _username = usr + '\x00'
        else:
            _username = '\x00'
        
        if pwd is not None and len(pwd) > 0:
            _password = utils.int1store(20) +\
                self._scramble_password(pwd,seed)
        else:
            _password = '\x00'
        
        if db is not None and len(db):
            _database = db + '\x00'
        else:
            _database = '\x00'
        
        return (_username, _password, _database)

    def _pkt_make_auth(self, username=None, password=None, database=None,
        seed=None, charset=33, client_flags=0, max_allowed_packet=None):
        """Make a MySQL Authentication packet"""
        try:
            seed = seed or self.scramble
        except:
            raise errors.ProgrammingError('Seed missing')
        
        if max_allowed_packet is None:
            max_allowed_packet = 1073741824 # 1Gb
        
        (_username, _password, _database) = self._prepare_auth(
            username, password, database, client_flags, seed)
        data =  utils.int4store(client_flags) +\
                utils.int4store(max_allowed_packet) +\
                utils.int1store(charset) +\
                '\x00'*23 +\
                _username +\
                _password +\
                _database
        return data
    
    def _pkt_make_auth_ssl(self, username=None, password=None, database=None,
            seed=None, charset=33, client_flags=0, max_allowed_packet=None):
        try:
            seed = seed or self.scramble
        except:
            raise errors.ProgrammingError('Seed missing')
        
        if max_allowed_packet is None:
            max_allowed_packet = 1073741824 # 1Gb

        (_username, _password, _database) = self._prepare_auth(
                username, password, database, client_flags, seed)
        data =  utils.int4store(client_flags) +\
                    utils.int4store(max_allowed_packet) +\
                    utils.int1store(charset) +\
                    '\x00'*23
        return data
        
    def _pkt_make_command(self, command, argument=None):
        """Make a MySQL packet containing a command"""
        data = utils.int1store(command)
        if argument is not None:
            data += str(argument)
        return data
    
    def _pkt_make_changeuser(self, username=None, password=None,
        database=None, charset=8, seed=None):
        """Make a MySQL packet with the Change User command"""
        try:
            seed = seed or self.scramble
        except:
            raise errors.ProgrammingError('Seed missing')
        
        (_username, _password, _database) = self._prepare_auth(
            username, password, database, self.client_flags, seed)
        data =  utils.int1store(ServerCmd.CHANGE_USER) +\
                _username +\
                _password +\
                _database +\
                utils.int2store(charset)
        return data
        
    @set_pktnr(1)
    def _pkt_parse_handshake(self, buf):
        """Parse a MySQL Handshake-packet"""
        res = {}
        (buf,res['protocol']) = utils.read_int(buf,1)
        (buf,res['server_version_original']) = utils.read_string(buf,end='\x00')
        (buf,res['server_threadid']) = utils.read_int(buf,4)
        (buf,res['scramble']) = utils.read_bytes(buf, 8)
        buf = buf[1:] # Filler 1 * \x00
        (buf,res['capabilities']) = utils.read_int(buf,2)
        (buf,res['charset']) = utils.read_int(buf,1)
        (buf,res['server_status']) = utils.read_int(buf,2)
        buf = buf[13:] # Filler 13 * \x00
        (buf,scramble_next) = utils.read_bytes(buf,12)
        res['scramble'] += scramble_next
        return res
        
    @set_pktnr(1)
    def _pkt_parse_ok(self, buf):
        """Parse a MySQL OK-packet"""
        ok = {}
        (buf,ok['field_count']) = utils.read_int(buf,1)
        (buf,ok['affected_rows']) = utils.read_lc_int(buf)
        (buf,ok['insert_id']) = utils.read_lc_int(buf)
        (buf,ok['server_status']) = utils.read_int(buf,2)
        (buf,ok['warning_count']) = utils.read_int(buf,2)
        if buf:
            (buf,ok['info_msg']) = utils.read_lc_string(buf)
        return ok
        
    @set_pktnr(1)
    def _pkt_parse_field(self, buf):
        """Parse a MySQL Field-packet"""
        field = {}
        (buf,field['catalog']) = utils.read_lc_string(buf)
        (buf,field['db']) = utils.read_lc_string(buf)
        (buf,field['table']) = utils.read_lc_string(buf)
        (buf,field['org_table']) = utils.read_lc_string(buf)
        (buf,field['name']) = utils.read_lc_string(buf)
        (buf,field['org_name']) = utils.read_lc_string(buf)
        buf = buf[1:] # filler 1 * \x00
        (buf,field['charset']) = utils.read_int(buf, 2)
        (buf,field['length']) = utils.read_int(buf, 4)
        (buf,field['type']) = utils.read_int(buf, 1)
        (buf,field['flags']) = utils.read_int(buf, 2)
        (buf,field['decimal']) = utils.read_int(buf, 1)
        buf = buf[2:] # filler 2 * \x00
        
        res = (
            field['name'],
            field['type'],
            None, # display_size
            None, # internal_size
            None, # precision
            None, # scale
            ~field['flags'] & FieldFlag.NOT_NULL, # null_ok
            field['flags'], # MySQL specific
            )
        return res
        
    @set_pktnr(1)
    def _pkt_parse_eof(self, buf):
        """Parse a MySQL EOF-packet"""
        res = {}
        buf = buf[1:] # disregard the first checking byte
        (buf, res['warning_count']) = utils.read_int(buf, 2)
        (buf, res['status_flag']) = utils.read_int(buf, 2)
        return res
    
    def do_handshake(self):
        """Get the handshake from the MySQL server"""
        try:
            self.conn.open_connection()
            buf = self.conn.recv()
            self.handle_handshake(buf)
        except:
            raise
    
    def do_auth(self,  username=None, password=None, database=None,
        client_flags=0, charset=33):
        """Authenticate with the MySQL server
        """
        if client_flags & ClientFlag.SSL:
            pkt = self._pkt_make_auth_ssl(username=username,
                password=password, database=database, charset=charset,
                client_flags=client_flags)
            self.conn.send(pkt,self.next_pktnr)
            self.conn.switch_to_ssl()
        
        pkt = self._pkt_make_auth(username=username, password=password,
            database=database, charset=charset,
            client_flags=client_flags)
        self.conn.send(pkt,self.next_pktnr)
        buf = self.conn.recv()
        if buf[4] == '\xfe':
            raise errors.NotSupportedError(
              "Authentication with old (insecure) passwords "\
              "is not supported: "\
              "http://dev.mysql.com/doc/refman/5.1/en/password-hashing.html") 
        
        try:
            if not (client_flags & ClientFlag.CONNECT_WITH_DB) and database:
                self.cmd_init_db(database)
        except:
            raise
        
        return True
        
    def handle_handshake(self, buf):
        """Check and handle the MySQL server's handshake
        
        Check whether the buffer is a valid handshake. If it is, we set some
        member variables for later usage. The handshake packet is returned for later
        usuage, e.g. authentication.
        """
        try:
            res = self._pkt_parse_handshake(buf)
            for k,v in res.items():
                self.__dict__[k] = v
            
            regex_ver = re.compile("^(\d{1,2})\.(\d{1,2})\.(\d{1,3})(.*)")
            m = regex_ver.match(self.server_version_original)
            if not m:
                raise errors.InterfaceError("Failed parsing MySQL version number.")
            self.server_version = tuple([ int(v) for v in m.groups()[0:3]])
        except errors.Error:
            raise
        except Exception, e:
            raise errors.InterfaceError('Failed handling handshake; %s' % e)
    
    @packet_is_ok(1)
    def _handle_ok(self, buf):
        try:
            return self._pkt_parse_ok(buf)
        except:
            raise errors.InterfaceError("Failed parsing OK packet.")
        
    @packet_is_eof(1)
    def _handle_eof(self, buf):
        try:
            return self._pkt_parse_eof(buf)
        except:
            raise errors.InterfaceError("Failed parsing EOF packet.")
    
    @packet_is_error(1)
    @set_pktnr(1)
    def _handle_resultset(self, buf):
        (buf,nrflds) = utils.read_lc_int(buf)
        if nrflds == 0:
            raise errors.InterfaceError('Empty result set.')
            
        fields = []
        for i in xrange(0,nrflds):
            buf = self.conn.recv()
            fields.append(self._pkt_parse_field(buf))
        
        buf = self.conn.recv()
        eof = self._handle_eof(buf)
        return (nrflds, fields, eof)
            
    
    def get_rows(self, cnt=None):
        """Get all rows

        Returns a tuple with 2 elements: a list with all rows and
        the EOF packet.
        """
        rows = []
        eof = None
        rowdata = None
        i = 0
        while True:
            if eof is not None:
                break
            if i == cnt:
                break
            buf = self.conn.recv()
            if buf[0:3] == '\xff\xff\xff':
                data = buf[4:]
                buf = self.conn.recv()
                while buf[0:3] == '\xff\xff\xff':
                    data += buf[4:]
                    buf = self.conn.recv()
                if buf[4] == '\xfe':
                    eof = self._handle_eof(buf)
                else:
                    data += buf[4:]
                rowdata = utils.read_lc_string_list(data)
            elif buf[4] == '\xfe':
                eof = self._handle_eof(buf)
                rowdata = None
            else:
                eof = None
                rowdata = utils.read_lc_string_list(buf[4:])
            if eof is None and rowdata is not None:
                rows.append(rowdata)
            i += 1
        return (rows,eof)
    
    def get_row(self):
        (rows,eof) = self.get_rows(cnt=1)
        if len(rows):
            return (rows[0],eof)
        return (None,eof)
    
    def handle_cmd_result(self, buf):
        if buf[4] == '\x00':
            return self._handle_ok(buf)
        else:
            return self._handle_resultset(buf)[0:2]
    
    @reset_pktnr
    def cmd_query(self, query):
        """Sends a query to the MySQL server

        Returns a tuple, when the query returns a result. The tuple
        consist number of fields and a list containing their descriptions.
        If the query doesn't return a result set, a dictionary with
        information contained in an OKResult packet will be returned.
        """
        nrflds = 0
        fields = None
        try:
            pkt = self._pkt_make_command(ServerCmd.QUERY,query)
            self.conn.send(pkt,self.next_pktnr)
            return self.handle_cmd_result(self.conn.recv())
        except:
            raise
    
    @reset_pktnr
    def cmd_refresh(self, opts):
        """Send the Refresh command to the MySQL server

        The argument should be a bitwise value using contants.RefreshOption.
        Usage example:

         RefreshOption = mysql.connector.RefreshOption
         refresh = RefreshOption.LOG | RefreshOption.THREADS
         db.protocol().cmd_refresh(refresh)
        
        Returns a dict() with OK-packet information.
        """
        pkt = self._pkt_make_command(ServerCmd.REFRESH, opts)
        self.conn.send(pkt,self.next_pktnr)
        buf = self.conn.recv()
        return self._handle_ok(buf)

    @reset_pktnr
    def cmd_quit(self):
        """Closes the current connection with the server
        
        Returns the packet that was send.
        """
        pkt = self._pkt_make_command(ServerCmd.QUIT)
        self.conn.send(pkt,self.next_pktnr)
        return pkt

    @reset_pktnr
    def cmd_init_db(self, database):
        """Change the current database
        
        Change the current (default) database.
        
        Returns a dict() with OK-packet information.
        """
        pkt = self._pkt_make_command(ServerCmd.INIT_DB, database)
        self.conn.send(pkt,self.next_pktnr)
        buf = self.conn.recv()
        return self._handle_ok(buf)
    
    @reset_pktnr
    def cmd_shutdown(self):
        """Shuts down the MySQL Server

        Careful with this command if you have SUPER privileges! (Which your
        scripts probably don't need!)

        Returns a dict() with OK-packet information.
        """
        pkt = self._pkt_make_command(ServerCmd.SHUTDOWN)
        self.conn.send(pkt,self.next_pktnr)
        buf = self.conn.recv()
        return self._handle_eof(buf)
    
    @reset_pktnr
    def cmd_statistics(self):
        """Sends statistics command to the MySQL Server

        Returns a dictionary with various statistical information.
        """
        pkt = self._pkt_make_command(ServerCmd.STATISTICS)
        self.conn.send(pkt,self.next_pktnr)
        buf = self.conn.recv()
        buf = buf[4:]
        errmsg = "Failed getting COM_STATISTICS information"
        res = {}
         # Information is separated by 2 spaces
        pairs = buf.split('\x20\x20')
        for pair in pairs:
            try:
                (lbl,val) = [ v.strip() for v in pair.split(':',2) ]
            except:
                raise errors.InterfaceError(errmsg)
                
            # It's either an integer or a decimal
            try:
                res[lbl] = long(val)
            except:
                try:
                    res[lbl] = Decimal(val)
                except:
                    raise errors.InterfaceError(
                        "%s (%s:%s)." % (errmsg, lbl, val))
        return res

    @reset_pktnr
    def cmd_process_info(self):
        """Gets the process list from the MySQL Server

        (Unsupported)
        """
        raise errors.NotSupportedError(
            "Not implemented. Use a cursor to get processlist information.")

    @reset_pktnr
    def cmd_process_kill(self, mypid):
        """Kills a MySQL process using it's ID
        
        Returns a dict() with OK-packet information.
        """
        pkt = self._pkt_make_command(ServerCmd.PROCESS_KILL,
            utils.int4store(mypid))
        self.conn.send(pkt,self.next_pktnr)
        buf = self.conn.recv()
        return self._handle_ok(buf)

    @reset_pktnr
    def cmd_debug(self):
        """Send DEBUG command to the MySQL Server

        Needs SUPER privileges. The output will go to the MySQL server error
        log.

        Returns a dict() with EOF-packet information.
        """
        pkt = self._pkt_make_command(ServerCmd.DEBUG)
        self.conn.send(pkt,self.next_pktnr)
        buf = self.conn.recv()
        return self._handle_eof(buf)

    @reset_pktnr
    def cmd_ping(self):
        """Ping the MySQL server to check if the connection is still alive
        
        Raises errors.Error or an error derived from it when it fails
        to ping the MySQL server.
        
        Returns a dict() with OK-packet information.
        """
        pkt = self._pkt_make_command(ServerCmd.PING)
        self.conn.send(pkt,self.next_pktnr)
        buf = self.conn.recv()
        return self._handle_ok(buf)

    @reset_pktnr
    def cmd_change_user(self, username='', password='', database=''):
        """Change the user and optionally the current database
        
        Returns a dict() with OK-packet information.
        """
        _charset = self.charset or 33
        
        pkt = self._pkt_make_changeuser(username=username, password=password,
            database=database, charset=_charset, seed=self.scramble)
        self.conn.send(pkt,self.next_pktnr)
        buf = self.conn.recv()
        return self._handle_ok(buf)
