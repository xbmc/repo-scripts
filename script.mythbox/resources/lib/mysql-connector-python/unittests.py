#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

"""Script for running unittests

unittests.py launches all or selected unittests.

Examples:
 Setting the MySQL account for running tests
 shell> python unittests.py -uroot -D dbtests
 
 Executing only the cursor tests
 shell> python unittests.py -t cursor

unittests.py has exit status 0 when tests were ran succesful, 1 otherwise.

"""
import sys
import os
import tempfile
import threading
import unittest
import logging
from optparse import OptionParser

if sys.version_info >= (2,4) and sys.version_info < (3,0):
    sys.path = ['python2/'] + sys.path
elif sys.version_info >= (3,1):
    sys.path = ['python3/'] + sys.path
else:
    raise RuntimeError("Python v%d.%d is not supported" %\
        sys.version_info[0:2])
    sys.exit(1)

import tests
from tests import mysqld

logger = logging.getLogger(tests.LOGGER_NAME)

MY_CNF = """
# MySQL option file for MySQL Connector/Python tests
[mysqld]
basedir = %(mysqld_basedir)s
datadir = %(mysqld_datadir)s
port = %(mysqld_port)d
socket = %(mysqld_socket)s
bind_address = %(mysqld_bind_address)s
server_id = 19771406
sql_mode = ""
default_time_zone = +00:00
log-error = myconnpy_mysqld.err
log-bin = myconnpy_bin
"""

def _add_options(p):
    p.add_option('-t','--test', dest='testcase', metavar='NAME',
        help='Tests to execute, one of %s' % tests.get_test_names())
    p.add_option('-l','--log', dest='logfile', metavar='NAME',
        default=None,
        help='Log file location (if not given, logging is disabled)')
    p.add_option('','--force', dest='force', action="store_true",
        default=False,
        help='Remove previous MySQL test installation.')
    p.add_option('','--keep', dest='keep', action="store_true",
        default=False,
        help='Keep MySQL installation (i.e. for debugging)')
    p.add_option('','--debug', dest='debug', action="store_true",
        default=False,
        help='Show/Log debugging messages')
    p.add_option('','--verbosity', dest='verbosity', metavar='NUMBER',
        default='0', type="int",
        help='Verbosity of unittests (default 0)')
    
    p.add_option('','--mysql-basedir', dest='mysql_basedir',
        metavar='NAME', default='/usr/local/mysql',
        help='Where MySQL is installed. This is used to bootstrap and '\
         'run a MySQL server which is used for unittesting only.')
    p.add_option('','--mysql-topdir', dest='mysql_topdir',
        metavar='NAME',
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
            'mysql_myconnpy'),
        help='Where to bootstrap the new MySQL instance for testing. '\
         'Defaults to current ./mysql_myconnpy')
    p.add_option('','--bind-address', dest='bind_address', metavar='NAME',
        default='127.0.0.1',
        help='IP address to bind to')
    p.add_option('-P','--port', dest='port', metavar='NUMBER',
        default='33770', type="int",
        help='Port to use for TCP/IP connections.')

def _set_config(options, unix_socket=None):
    if options.bind_address:
        tests.MYSQL_CONFIG['host'] = options.bind_address
    if options.port:
        tests.MYSQL_CONFIG['port'] = options.port
    if unix_socket:
        tests.MYSQL_CONFIG['unix_socket'] = unix_socket
    tests.MYSQL_CONFIG['user'] = 'root'
    tests.MYSQL_CONFIG['password'] = ''
    tests.MYSQL_CONFIG['database'] = 'myconnpy'

def _show_help(msg=None,parser=None,exit=0):
    tests.printmsg(msg)
    if parser is not None:
        parser.print_help()
    if exit > -1:
        sys.exit(exit)
    
def main():
    usage = 'usage: %prog [options]'
    parser = OptionParser()
    _add_options(parser)

    # Set options
    (options, args) = parser.parse_args()
    option_file = os.path.join(options.mysql_topdir,'myconnpy_my.cnf')
    unix_socket = os.path.join(options.mysql_topdir,'myconnpy_mysql.sock')
    _set_config(options, unix_socket=unix_socket)
    
    # Init the MySQL Server object
    mysql_server = mysqld.MySQLInit(options.mysql_basedir,
        options.mysql_topdir,
        MY_CNF,
        option_file,
        options.bind_address,
        options.port,
        unix_socket)
    mysql_server._debug = options.debug
    
    # Force removal of previous test data
    if options.force is True:
        mysql_server.remove()

    # Which tests cases to run
    if options.testcase is not None:
        if options.testcase in tests.get_test_names():
            testcases = [ 'tests.test_%s' % options.testcase ]
        else:
            msg = "Test case is not one of %s" % tests.get_test_names()
            _show_help(msg=msg,parser=parser,exit=1)
    else:
        testcases = tests.active_testcases
    
    # Enabling logging
    formatter = logging.Formatter("%(asctime)s [%(name)s:%(levelname)s] %(message)s")
    myconnpy_logger = logging.getLogger('myconnpy')
    fh = None
    if options.logfile is not None:
        fh = logging.FileHandler(options.logfile)
    else:
        fh = logging.StreamHandler()
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    if options.debug is True:
        logger.setLevel(logging.DEBUG)
        myconnpy_logger.setLevel(logging.DEBUG)
    else:
        myconnpy_logger.setLevel(logging.INFO)
    myconnpy_logger.addHandler(fh)
    logger.info("MySQL Connector/Python unittest started")
    
    # Bootstrap and start a MySQL server
    mysql_server.bootstrap()
    mysql_server.start()
    
    # Run test cases
    suite = unittest.TestLoader().loadTestsFromNames(testcases)
    result = unittest.TextTestRunner(verbosity=options.verbosity).run(suite)
    txt = ""
    if not result.wasSuccessful():
        txt = "not "
    logger.info("MySQL Connector/Python unittests were %ssuccessful" % txt)
    
    # Clean up
    mysql_server.stop()
    if options.keep is not True:
        mysql_server.remove()
    
    # Return result of tests as exit code
    sys.exit(not result.wasSuccessful())
    
if __name__ == '__main__':
    main()
