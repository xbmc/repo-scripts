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
import unittest
from optparse import OptionParser

if sys.version_info >= (2,4) and sys.version_info < (3,0):
    sys.path = ['.'] + sys.path
elif sys.version_info >= (3,1):
    sys.path = ['py3k/'] + sys.path
else:
    raise RuntimeError("Python %s is not a supported.")
    sys.exit(1)

import tests

def _add_options(p):
    p.add_option('-H','--host', dest='hostname', metavar='NAME',
        help='Connect to MySQL running on host.')
    p.add_option('-P','--port', dest='port', metavar='NUMBER',
        default='3306', type="int",
        help='Port to use for TCP/IP connections.')
    p.add_option('-S','--socket', dest='unix_socket', metavar='FILE',
        help='Socket file to use for connecting to MySQL.'
        )
    p.add_option('-u','--user', dest='username', metavar='NAME',
        help='User for login if not current user.')
    p.add_option('-p','--password', dest='password', metavar='PASSWORD',
        help='Password to use when connecting to server.')
    p.add_option('-D','--database', dest='database', metavar='NAME',
        help='Database to use.')

    p.add_option('-t','--test', dest='testcase', metavar='NAME',
        help='Tests to execute, one of %s' % tests.get_test_names())

def _set_config(options):
    if options.hostname:
        tests.MYSQL_CONFIG['host'] = options.hostname
    if options.hostname:
        tests.MYSQL_CONFIG['port'] = options.port
    if options.unix_socket:
        tests.MYSQL_CONFIG['unix_socket'] = options.unix_socket
    if options.username:
        tests.MYSQL_CONFIG['user'] = options.username
    if options.password:
        tests.MYSQL_CONFIG['password'] = options.password
    if options.database:
        tests.MYSQL_CONFIG['database'] = options.database

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

    (options, args) = parser.parse_args()
    _set_config(options)

    if options.testcase is not None:
        if options.testcase in tests.get_test_names():
            testcases = [ 'tests.test_%s' % options.testcase ]
        else:
            msg = "Test case is not one of %s" % tests.get_test_names()
            _show_help(msg=msg,parser=parser,exit=1)
    else:
        testcases = tests.active_testcases

    suite = unittest.TestLoader().loadTestsFromNames(testcases)
    result = unittest.TextTestRunner(verbosity=2).run(suite)    
    sys.exit(not result.wasSuccessful())
    
if __name__ == '__main__':
    main()
