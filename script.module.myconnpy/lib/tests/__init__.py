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

"""Unittests
"""

import sys
import logging
import inspect
import unittest

MYSQL_CONFIG = {
    'host' : '127.0.0.1',
    'port' : 33770,
    'unix_socket' : None,
    'user' : 'root',
    'password' : '',
    'database' : 'myconnpy',
}

LOGGER_NAME = "myconnpy_tests"

__all__ = [
    'MySQLConnectorTests',
    'get_test_names','printmsg',
    'active_testcases',
    'LOGGER_NAME',
]

active_testcases = [
    'tests.test_utils',
    'tests.test_protocol',
    'tests.test_constants',
    'tests.test_conversion',
    'tests.test_connection',
    'tests.test_cursor',
    'tests.test_pep249',
    'tests.test_bugs',
    'tests.test_examples',
    'tests.test_mysql_datatypes',
]

class MySQLConnectorTests(unittest.TestCase):
    
    def getMySQLConfig(self):
        return MYSQL_CONFIG.copy()

    def checkAttr(self, obj, attrname, default):
        cls_name = obj.__class__.__name__
        self.assertTrue(hasattr(obj,attrname),
            "%s object has no '%s' attribute" % (cls_name,attrname))
        self.assertEqual(default,getattr(obj,attrname),
            "%s object's '%s' should default to %s '%s'" % (
                cls_name, attrname, type(default).__name__, default)
            )
    
    def checkMethod(self, obj, method):
        cls_name = obj.__class__.__name__
        self.assertTrue(hasattr(obj,method),
            "%s object has no '%s' method" % (cls_name, method))
        self.assertTrue(inspect.ismethod(getattr(obj,method)),
            "%s object defines %s, but is not a method" % (
                cls_name, method))

    def haveEngine(self, db, engine):
        """Check if the given storage engine is supported"""
        have = False
        engine = engine.lower()
        c = None
        try:
            c = db.cursor()
            # Should use INFORMATION_SCHEMA, but play nice with v4.1
            c.execute("SHOW ENGINES")
            rows = c.fetchall()
            for row in rows:
                if row[0].lower() == engine:
                    if row[1].lower() == 'yes':
                        have=True
                    break
        except:
            raise
        
            try:
                c.close()
            except:
                pass
            return have

    def cmpResult(self, res1, res2):
        """Compare results (list of tuples) comming from MySQL
        
        For certain results, like SHOW VARIABLES or SHOW WARNINGS, the
        order is unpredictable. To check if what is expected in the
        tests, we need to compare each row.
        """
        try:
            if len(res1) != len(res2):
                return False
        
                for row in res1:
                    if row not in res2:
                        return False
        except:
            return False
            
        return True
    
def get_test_names():
    return [ s.replace('tests.test_','') for s in active_testcases]

def printmsg(msg=None):
    if msg is not None:
        print(msg)
