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

"""Python exceptions
"""

import logging
import utils

logger = logging.getLogger('myconnpy')

# see get_mysql_exceptions method for errno ranges and smaller lists
__programming_errors = (
    1083,1084,1090,1091,1093,1096,1097,1101,1102,1103,1107,1108,1110,1111,
    1113,1120,1124,1125,1128,1136,1366,1139,1140,1146,1149,)
__operational_errors = (
    1028,1029,1030,1053,1077,1078,1079,1080,1081,1095,1104,1106,1114,1116,
    1117,1119,1122,1123,1126,1133,1135,1137,1145,1147,)
    
def get_mysql_exception(errno,msg):
    
    exception = OperationalError
    
    if (errno >= 1046 and errno <= 1052) or \
        (errno >= 1054 and errno <= 1061) or \
        (errno >= 1063 and errno <= 1075) or \
        errno in __programming_errors:
        exception = ProgrammingError
    elif errno in (1097,1109,1118,1121,1138,1292):
        exception = DataError
    elif errno in (1031,1089,1112,1115,1127,1148,1149):
        exception = NotSupportedError
    elif errno in (1062,1082,1099,1100):
        exception = IntegrityError
    elif errno in (1085,1086,1094,1098):
        exception = InternalError
    elif (errno >= 1004 and errno <= 1030) or \
        (errno >= 1132 and errno <= 1045) or \
        (errno >= 1141 and errno <= 1145) or \
        (errno >= 1129 and errno <= 1133) or \
        errno in __operational_errors:
        exception = OperationalError
    
    return exception(msg,errno=errno)

def raise_error(buf):
    """Raise an errors.Error when buffer has a MySQL error"""
    errno = errmsg = None
    try:
        buf = buf[5:]
        (buf,errno) = utils.read_int(buf, 2)
        if buf[0] != '\x23':
            # Error without SQLState
            errmsg = buf
        else:
            (buf,sqlstate) = utils.read_bytes(buf[1:],5)
            errmsg = buf
    except Exception, e:
        raise InterfaceError("Failed getting Error information (%r)"\
            % e)
    else:
        raise get_mysql_exception(errno,errmsg)

class ClientError(object):
    
    client_errors = {
        2000: "Unknown MySQL error",
        2001: "Can't create UNIX socket (%(socketaddr)d)",
        2002: "Can't connect to local MySQL server through socket '%(socketaddr)s' (%(errno)s)",
        2003: "Can't connect to MySQL server on '%(socketaddr)s' (%(errno)s)",
        2004: "Can't create TCP/IP socket (%s)",
        2005: "Unknown MySQL server host '%(socketaddr)s' (%s)",
        2006: "MySQL server has gone away",
        2007: "Protocol mismatch; server version = %(server_version)d, client version = %(client_version)d",
        2008: "MySQL client ran out of memory",
        2009: "Wrong host info",
        2010: "Localhost via UNIX socket",
        2011: "%(misc)s via TCP/IP",
        2012: "Error in server handshake",
        2013: "Lost connection to MySQL server during query",
        2014: "Commands out of sync; you can't run this command now",
        2015: "Named pipe: %(socketaddr)s",
        2016: "Can't wait for named pipe to host: %(host)s  pipe: %(socketaddr)s (%(errno)d)",
        2017: "Can't open named pipe to host: %s  pipe: %s (%(errno)d)",
        2018: "Can't set state of named pipe to host: %(host)s  pipe: %(socketaddr)s (%(errno)d)",
        2019: "Can't initialize character set %(charset)s (path: %(misc)s)",
        2020: "Got packet bigger than 'max_allowed_packet' bytes",
        2021: "Embedded server",
        2022: "Error on SHOW SLAVE STATUS:",
        2023: "Error on SHOW SLAVE HOSTS:",
        2024: "Error connecting to slave:",
        2025: "Error connecting to master:",
        2026: "SSL connection error",
        2027: "Malformed packet",
        2028: "This client library is licensed only for use with MySQL servers having '%s' license",
        2029: "Invalid use of null pointer",
        2030: "Statement not prepared",
        2031: "No data supplied for parameters in prepared statement",
        2032: "Data truncated",
        2033: "No parameters exist in the statement",
        2034: "Invalid parameter number",
        2035: "Can't send long data for non-string/non-binary data types (parameter: %d)",
        2036: "Using unsupported buffer type: %d  (parameter: %d)",
        2037: "Shared memory: %s",
        2038: "Can't open shared memory; client could not create request event (%d)",
        2039: "Can't open shared memory; no answer event received from server (%d)",
        2040: "Can't open shared memory; server could not allocate file mapping (%d)",
        2041: "Can't open shared memory; server could not get pointer to file mapping (%d)",
        2042: "Can't open shared memory; client could not allocate file mapping (%d)",
        2043: "Can't open shared memory; client could not get pointer to file mapping (%d)",
        2044: "Can't open shared memory; client could not create %s event (%d)",
        2045: "Can't open shared memory; no answer from server (%d)",
        2046: "Can't open shared memory; cannot send request event to server (%d)",
        2047: "Wrong or unknown protocol",
        2048: "Invalid connection handle",
        2049: "Connection using old (pre-4.1.1) authentication protocol refused (client option 'secure_auth' enabled)",
        2050: "Row retrieval was canceled by mysql_stmt_close() call",
        2051: "Attempt to read column without prior row fetch",
        2052: "Prepared statement contains no metadata",
        2053: "Attempt to read a row while there is no result set associated with the statement",
        2054: "This feature is not implemented yet",
        2055: "Lost connection to MySQL server at '%(socketaddr)s', system error: %(errno)d",
        2056: "Statement closed indirectly because of a preceeding %s() call",
        2057: "The number of columns in the result set differs from the number of bound buffers. You must reset the statement, rebind the result set columns, and execute the statement again",
    }
    
    def __new__(cls):
        raise TypeError, "Can not instanciate from %s" % cls.__name__
    
    @classmethod
    def get_error_msg(cls,errno,values=None):
        res = None
        if cls.client_errors.has_key(errno):
            if values is not None:
                try:
                    res = cls.client_errors[errno] % values
                except:
                    logger.debug("Missing values for errno %d" % errno)
                    res = cls.client_errors[errno], "(missing values!)"
            else:
                res = cls.client_errors[errno]
        if res is None:
            res = "Unknown client error %d" % errno
            logger.debug(res)
        return res

class Error(StandardError):
    
    def __init__(self, m, errno=None, values=None):
        try:
            # process MySQL error packet
            self._process_packet(m)
        except:
            self.errno = errno or -1
            self.sqlstate = -1
            if m is None and (errno >= 2000 and errno < 3000):
                m = ClientError.get_error_msg(errno,values)
            elif m is None:
                m = 'Unknown error'
            if self.errno != -1:
                self.msg = "%s: %s" % (self.errno,m)
            else:
                self.msg = m
            
    def _process_packet(self, packet):
        self.errno = packet.errno
        self.sqlstate = packet.sqlstate
        if self.sqlstate:
            self.msg = '%d (%s): %s' % (self.errno,self.sqlstate,packet.errmsg)
        else:
            self.msg = '%d: %s' % (self.errno, packet.errmsg)
    
    def __str__(self):
        return self.msg
        
    def __unicode__(self):
        return self.msg
        
class Warning(StandardError):
    pass

class InterfaceError(Error):
    def __init__(self, m=None, errno=None, values=None):
        Error.__init__(self, m, errno, values)

class DatabaseError(Error):
    def __init__(self, m=None, errno=None, values=None):
        Error.__init__(self, m, errno, values)

class InternalError(DatabaseError):
    pass

class OperationalError(DatabaseError):
    pass

class ProgrammingError(DatabaseError):
    pass

class IntegrityError(DatabaseError):
    pass

class DataError(DatabaseError):
    pass

class NotSupportedError(DatabaseError):
    pass
